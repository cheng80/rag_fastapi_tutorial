from __future__ import annotations

import argparse
import json
import random
from pathlib import Path
import sys
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


DEFAULT_DATA_DIR = PROJECT_ROOT / "data" / "processed" / "korean_correction_finetune"
DEFAULT_BASE_MODEL_DIR = PROJECT_ROOT / "data" / "models" / "tourism_korean_corrector_base"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "data" / "models" / "tourism_korean_corrector"


def project_relative(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(PROJECT_ROOT))
    except ValueError:
        return str(path)


def load_jsonl(path: Path) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        payload = json.loads(line)
        source = str(payload.get("source") or "").strip()
        target = str(payload.get("target") or "").strip()
        if source and target:
            rows.append({"source": source, "target": target})
    return rows


def pick_device(torch: Any, configured_device: str) -> str:
    if configured_device != "auto":
        return configured_device
    if torch.cuda.is_available():
        return "cuda"
    if getattr(torch.backends, "mps", None) and torch.backends.mps.is_available():
        return "mps"
    return "cpu"


def main() -> int:
    parser = argparse.ArgumentParser(description="Fine-tune a local Korean typo/spacing corrector for tourism queries.")
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR)
    parser.add_argument("--base-model-dir", type=Path, default=DEFAULT_BASE_MODEL_DIR)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--epochs", type=float, default=1.0)
    parser.add_argument("--batch-size", type=int, default=4)
    parser.add_argument("--gradient-accumulation-steps", type=int, default=1)
    parser.add_argument("--learning-rate", type=float, default=5e-5)
    parser.add_argument("--weight-decay", type=float, default=0.0)
    parser.add_argument("--warmup-ratio", type=float, default=0.0)
    parser.add_argument("--label-smoothing-factor", type=float, default=0.0)
    parser.add_argument("--max-length", type=int, default=128)
    parser.add_argument("--device", default="auto", choices=["auto", "cpu", "mps", "cuda"])
    parser.add_argument("--eval-steps", type=int, default=250)
    parser.add_argument("--save-steps", type=int, default=250)
    parser.add_argument("--early-stopping-patience", type=int, default=3)
    parser.add_argument("--early-stopping-threshold", type=float, default=0.0005)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--limit-train", type=int, default=0)
    parser.add_argument("--limit-validation", type=int, default=0)
    args = parser.parse_args()

    if not args.base_model_dir.exists():
        raise SystemExit(
            f"Local base model is missing: {args.base_model_dir}. "
            "Run scripts/materialize_korean_correction_base_model.py first."
        )

    import numpy as np
    import torch
    from torch.utils.data import Dataset
    from transformers import (
        AutoModelForSeq2SeqLM,
        AutoTokenizer,
        DataCollatorForSeq2Seq,
        EarlyStoppingCallback,
        Seq2SeqTrainer,
        Seq2SeqTrainingArguments,
    )

    class CorrectionDataset(Dataset):
        def __init__(self, rows: list[dict[str, str]], tokenizer: Any, max_length: int):
            self.rows = rows
            self.tokenizer = tokenizer
            self.max_length = max_length

        def __len__(self) -> int:
            return len(self.rows)

        def __getitem__(self, index: int) -> dict[str, Any]:
            row = self.rows[index]
            model_inputs = self.tokenizer(
                "맞춤법을 고쳐주세요: " + row["source"],
                truncation=True,
                max_length=self.max_length,
            )
            labels = self.tokenizer(
                text_target=row["target"],
                truncation=True,
                max_length=self.max_length,
            )
            model_inputs["labels"] = labels["input_ids"]
            return model_inputs

    random.seed(args.seed)
    np.random.seed(args.seed)
    torch.manual_seed(args.seed)

    train_rows = load_jsonl(args.data_dir / "train.jsonl")
    validation_rows = load_jsonl(args.data_dir / "validation.jsonl")
    if args.limit_train:
        train_rows = train_rows[: args.limit_train]
    if args.limit_validation:
        validation_rows = validation_rows[: args.limit_validation]
    if not train_rows:
        raise SystemExit("No training rows found.")

    tokenizer = AutoTokenizer.from_pretrained(args.base_model_dir, local_files_only=True)
    has_safetensors = (args.base_model_dir / "model.safetensors").exists()
    has_pytorch_bin = (args.base_model_dir / "pytorch_model.bin").exists()
    use_safetensors = True if has_safetensors and not has_pytorch_bin else False
    model = AutoModelForSeq2SeqLM.from_pretrained(
        args.base_model_dir,
        local_files_only=True,
        use_safetensors=use_safetensors,
    )
    device = pick_device(torch, args.device)
    model.to(device)

    train_dataset = CorrectionDataset(train_rows, tokenizer, args.max_length)
    eval_dataset = CorrectionDataset(validation_rows, tokenizer, args.max_length) if validation_rows else None
    collator = DataCollatorForSeq2Seq(tokenizer=tokenizer, model=model)
    training_args = Seq2SeqTrainingArguments(
        output_dir=str(args.output_dir / "trainer_runs"),
        num_train_epochs=args.epochs,
        per_device_train_batch_size=args.batch_size,
        per_device_eval_batch_size=args.batch_size,
        gradient_accumulation_steps=args.gradient_accumulation_steps,
        learning_rate=args.learning_rate,
        weight_decay=args.weight_decay,
        warmup_ratio=args.warmup_ratio,
        label_smoothing_factor=args.label_smoothing_factor,
        logging_steps=20,
        save_strategy="steps" if eval_dataset else "epoch",
        save_steps=args.save_steps,
        eval_strategy="steps" if eval_dataset else "no",
        eval_steps=args.eval_steps if eval_dataset else None,
        load_best_model_at_end=bool(eval_dataset),
        metric_for_best_model="eval_loss",
        greater_is_better=False,
        save_total_limit=3,
        report_to=[],
        predict_with_generate=False,
        seed=args.seed,
        data_seed=args.seed,
    )
    callbacks = []
    if eval_dataset:
        callbacks.append(
            EarlyStoppingCallback(
                early_stopping_patience=args.early_stopping_patience,
                early_stopping_threshold=args.early_stopping_threshold,
            )
        )
    trainer = Seq2SeqTrainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        eval_dataset=eval_dataset,
        data_collator=collator,
        processing_class=tokenizer,
        callbacks=callbacks,
    )
    trainer.train()

    args.output_dir.mkdir(parents=True, exist_ok=True)
    model.config.tie_word_embeddings = False
    trainer.save_model(args.output_dir)
    tokenizer.save_pretrained(args.output_dir)
    manifest = {
        "base_model_dir": project_relative(args.base_model_dir),
        "data_dir": project_relative(args.data_dir),
        "output_dir": project_relative(args.output_dir),
        "train_rows": len(train_rows),
        "validation_rows": len(validation_rows),
        "epochs": args.epochs,
        "batch_size": args.batch_size,
        "gradient_accumulation_steps": args.gradient_accumulation_steps,
        "learning_rate": args.learning_rate,
        "weight_decay": args.weight_decay,
        "warmup_ratio": args.warmup_ratio,
        "label_smoothing_factor": args.label_smoothing_factor,
        "device": device,
        "eval_steps": args.eval_steps,
        "save_steps": args.save_steps,
        "early_stopping_patience": args.early_stopping_patience,
        "early_stopping_threshold": args.early_stopping_threshold,
        "seed": args.seed,
        "best_model_checkpoint": trainer.state.best_model_checkpoint,
        "best_metric": trainer.state.best_metric,
        "runtime_policy": "FastAPI loads this local directory only. Runtime network calls are not allowed.",
    }
    (args.output_dir / "training_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

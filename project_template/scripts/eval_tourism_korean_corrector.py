from __future__ import annotations

import argparse
from difflib import SequenceMatcher
import json
from pathlib import Path
import sys
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


DEFAULT_DATA_PATH = PROJECT_ROOT / "data" / "processed" / "korean_correction_finetune" / "validation.jsonl"
DEFAULT_MODEL_DIR = PROJECT_ROOT / "data" / "models" / "tourism_korean_corrector"


def project_relative(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(PROJECT_ROOT))
    except ValueError:
        return str(path)


def compact(text: str) -> str:
    return "".join(str(text or "").split())


def load_rows(path: Path, limit: int = 0) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        payload = json.loads(line)
        source = str(payload.get("source") or "").strip()
        target = str(payload.get("target") or "").strip()
        if source and target:
            rows.append({**payload, "source": source, "target": target})
        if limit and len(rows) >= limit:
            break
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate a local Korean correction model on generation metrics.")
    parser.add_argument("--model-dir", type=Path, default=DEFAULT_MODEL_DIR)
    parser.add_argument("--data", type=Path, default=DEFAULT_DATA_PATH)
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--samples-output", type=Path, default=None)
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--max-length", type=int, default=128)
    parser.add_argument("--num-beams", type=int, default=3)
    parser.add_argument("--device", default="cpu", choices=["cpu", "mps", "cuda"])
    args = parser.parse_args()

    import torch
    from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

    rows = load_rows(args.data, args.limit)
    if not rows:
        raise SystemExit(f"No rows found: {args.data}")

    has_safetensors = (args.model_dir / "model.safetensors").exists()
    has_pytorch_bin = (args.model_dir / "pytorch_model.bin").exists()
    use_safetensors = True if has_safetensors and not has_pytorch_bin else False
    tokenizer = AutoTokenizer.from_pretrained(args.model_dir, local_files_only=True)
    model = AutoModelForSeq2SeqLM.from_pretrained(
        args.model_dir,
        local_files_only=True,
        use_safetensors=use_safetensors,
    )
    model.to(args.device)
    model.eval()

    samples: list[dict[str, Any]] = []
    exact = 0
    compact_exact = 0
    source_changed = 0
    ratio_sum = 0.0

    with torch.no_grad():
        for start in range(0, len(rows), args.batch_size):
            batch = rows[start : start + args.batch_size]
            prompts = ["맞춤법을 고쳐주세요: " + row["source"] for row in batch]
            encoding = tokenizer(
                prompts,
                return_tensors="pt",
                truncation=True,
                padding=True,
                max_length=args.max_length,
            )
            encoding = {key: value.to(args.device) for key, value in encoding.items()}
            generation_kwargs = {
                "max_length": args.max_length,
                "num_beams": args.num_beams,
            }
            if args.num_beams > 1:
                generation_kwargs["early_stopping"] = True
            outputs = model.generate(**encoding, **generation_kwargs)
            predictions = tokenizer.batch_decode(outputs, skip_special_tokens=True)
            for row, prediction in zip(batch, predictions, strict=True):
                pred = prediction.strip()
                target = row["target"]
                source = row["source"]
                is_exact = pred == target
                is_compact_exact = compact(pred) == compact(target)
                changed = compact(pred) != compact(source)
                similarity = SequenceMatcher(None, pred, target).ratio()
                exact += int(is_exact)
                compact_exact += int(is_compact_exact)
                source_changed += int(changed)
                ratio_sum += similarity
                samples.append(
                    {
                        "id": row.get("id"),
                        "origin": row.get("origin"),
                        "source": source,
                        "target": target,
                        "prediction": pred,
                        "exact": is_exact,
                        "compact_exact": is_compact_exact,
                        "similarity": similarity,
                    }
                )

    total = len(rows)
    metrics = {
        "model_dir": project_relative(args.model_dir),
        "data": project_relative(args.data),
        "rows": total,
        "num_beams": args.num_beams,
        "exact_accuracy": exact / total,
        "compact_exact_accuracy": compact_exact / total,
        "mean_sequence_similarity": ratio_sum / total,
        "changed_rate": source_changed / total,
    }
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(metrics, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if args.samples_output:
        args.samples_output.parent.mkdir(parents=True, exist_ok=True)
        args.samples_output.write_text(
            "\n".join(json.dumps(sample, ensure_ascii=False) for sample in samples) + "\n",
            encoding="utf-8",
        )
    print(json.dumps(metrics, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import argparse
import json
from pathlib import Path
import random
import sys
import time
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.services.tourism_query_service import CONDITION_KEYWORDS, TourismQueryService  # noqa: E402


CONDITION_LABELS = list(CONDITION_KEYWORDS)
DEFAULT_DATA_DIR = PROJECT_ROOT / "data" / "processed" / "tourism_condition_transformer"
DEFAULT_MODEL_NAME = PROJECT_ROOT / "data" / "models" / "klue_roberta_small"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "data" / "generated" / "tour_api" / "condition_transformer_robust"


class ConditionDataset:
    def __init__(self, rows: list[dict[str, Any]]):
        self.rows = rows

    def __len__(self) -> int:
        return len(self.rows)

    def __getitem__(self, index: int) -> dict[str, Any]:
        return self.rows[index]


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        payload = json.loads(line)
        text = str(payload.get("text") or "").strip()
        vector = payload.get("label_vector")
        if not vector:
            labels = set(payload.get("labels") or [])
            vector = [1 if label in labels else 0 for label in CONDITION_LABELS]
        if text:
            rows.append({**payload, "text": text, "label_vector": [float(value) for value in vector]})
    return rows


def collate_batch(tokenizer: Any, rows: list[dict[str, Any]], max_length: int, torch: Any) -> dict[str, Any]:
    encoded = tokenizer(
        [row["text"] for row in rows],
        padding=True,
        truncation=True,
        max_length=max_length,
        return_tensors="pt",
    )
    encoded["labels"] = torch.tensor([row["label_vector"] for row in rows], dtype=torch.float32)
    encoded["texts"] = [row["text"] for row in rows]
    return encoded


def pick_device(torch: Any, requested: str) -> Any:
    if requested != "auto":
        return torch.device(requested)
    if torch.cuda.is_available():
        return torch.device("cuda")
    if getattr(torch.backends, "mps", None) and torch.backends.mps.is_available():
        return torch.device("mps")
    return torch.device("cpu")


def seed_everything(seed: int, torch: Any) -> None:
    random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def predict_with_thresholds(probabilities: list[list[float]], thresholds: list[float]) -> list[list[int]]:
    return [[1 if value >= thresholds[index] else 0 for index, value in enumerate(row)] for row in probabilities]


def choose_thresholds(expected: list[list[int]], probabilities: list[list[float]]) -> list[float]:
    thresholds: list[float] = []
    candidates = [value / 100 for value in range(20, 81, 5)]
    for index in range(len(CONDITION_LABELS)):
        best_threshold = 0.5
        best_f1 = -1.0
        for threshold in candidates:
            tp = fp = fn = 0
            for expected_row, probability_row in zip(expected, probabilities, strict=True):
                actual = bool(expected_row[index])
                predicted = probability_row[index] >= threshold
                if actual and predicted:
                    tp += 1
                elif not actual and predicted:
                    fp += 1
                elif actual and not predicted:
                    fn += 1
            precision = tp / (tp + fp) if tp + fp else 1.0
            recall = tp / (tp + fn) if tp + fn else 1.0
            f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
            if f1 > best_f1:
                best_f1 = f1
                best_threshold = threshold
        thresholds.append(best_threshold)
    return thresholds


def infer_probabilities(model: Any, loader: Any, device: Any, torch: Any) -> tuple[list[list[float]], float]:
    model.eval()
    rows: list[list[float]] = []
    started = time.perf_counter()
    with torch.no_grad():
        for batch in loader:
            batch.pop("texts", None)
            batch.pop("labels", None)
            inputs = {key: value.to(device) for key, value in batch.items()}
            outputs = model(**inputs)
            rows.extend(torch.sigmoid(outputs.logits).detach().cpu().tolist())
    return rows, (time.perf_counter() - started) * 1000


def vector_to_set(vector: list[int | float]) -> set[str]:
    return {label for label, value in zip(CONDITION_LABELS, vector, strict=True) if value}


def evaluate(expected: list[list[int]], predicted: list[list[int]], rows: list[dict[str, Any]], latency_ms: float) -> dict[str, Any]:
    exact = 0
    total_expected = total_predicted = total_correct = 0
    per_label = {label: {"tp": 0, "fp": 0, "fn": 0} for label in CONDITION_LABELS}
    samples: list[dict[str, Any]] = []
    for row, expected_vector, predicted_vector in zip(rows, expected, predicted, strict=True):
        expected_set = vector_to_set(expected_vector)
        predicted_set = vector_to_set(predicted_vector)
        exact += int(expected_set == predicted_set)
        total_expected += len(expected_set)
        total_predicted += len(predicted_set)
        total_correct += len(expected_set & predicted_set)
        for label in CONDITION_LABELS:
            if label in expected_set and label in predicted_set:
                per_label[label]["tp"] += 1
            elif label not in expected_set and label in predicted_set:
                per_label[label]["fp"] += 1
            elif label in expected_set and label not in predicted_set:
                per_label[label]["fn"] += 1
        if expected_set != predicted_set and len(samples) < 30:
            samples.append(
                {
                    "id": row.get("id"),
                    "text": row.get("text"),
                    "expected": sorted(expected_set),
                    "predicted": sorted(predicted_set),
                }
            )
    precision = total_correct / total_predicted if total_predicted else 1.0
    recall = total_correct / total_expected if total_expected else 1.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {
        "rows": len(rows),
        "exact_match": round(exact / len(rows), 4) if rows else 0.0,
        "micro_precision": round(precision, 4),
        "micro_recall": round(recall, 4),
        "micro_f1": round(f1, 4),
        "latency": {
            "total_ms": round(latency_ms, 4),
            "mean_ms": round(latency_ms / len(rows), 4) if rows else 0.0,
        },
        "per_label": per_label,
        "sample_mismatches": samples,
    }


def evaluate_rule_baseline(rows: list[dict[str, Any]], enable_external_correction: bool) -> dict[str, Any]:
    service = TourismQueryService(enable_external_correction=enable_external_correction)
    expected: list[list[int]] = []
    predicted: list[list[int]] = []
    started = time.perf_counter()
    for item in rows:
        expected.append([int(value) for value in item["label_vector"]])
        query = service.extract(item["text"])
        conditions = set(query.get("conditions") or [])
        predicted.append([1 if label in conditions else 0 for label in CONDITION_LABELS])
    return evaluate(expected, predicted, rows, (time.perf_counter() - started) * 1000)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fine-tune local KLUE-RoBERTa for tourism condition labels.")
    parser.add_argument("--model-name", default=str(DEFAULT_MODEL_NAME))
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--epochs", type=int, default=2)
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--learning-rate", type=float, default=2e-5)
    parser.add_argument("--max-length", type=int, default=96)
    parser.add_argument("--seed", type=int, default=20260518)
    parser.add_argument("--device", default="auto")
    parser.add_argument("--save-model", action="store_true")
    parser.add_argument(
        "--skip-rule-baselines",
        action="store_true",
        help="Skip slow parser/corrector baselines when running repeated Transformer experiments.",
    )
    return parser.parse_args()


def main() -> None:
    try:
        import torch
        from torch.utils.data import DataLoader
        from transformers import AutoModelForSequenceClassification, AutoTokenizer, get_linear_schedule_with_warmup
    except ImportError as exc:
        raise SystemExit("Install ML dependencies first: .venv/bin/python -m pip install -r requirements-ml.txt") from exc

    args = parse_args()
    seed_everything(args.seed, torch)
    train_rows = load_jsonl(args.data_dir / "train.jsonl")
    validation_rows = load_jsonl(args.data_dir / "validation.jsonl")
    test_rows = load_jsonl(args.data_dir / "test.jsonl")

    tokenizer = AutoTokenizer.from_pretrained(args.model_name, local_files_only=Path(args.model_name).exists())
    model = AutoModelForSequenceClassification.from_pretrained(
        args.model_name,
        local_files_only=Path(args.model_name).exists(),
        num_labels=len(CONDITION_LABELS),
        problem_type="multi_label_classification",
        id2label={index: label for index, label in enumerate(CONDITION_LABELS)},
        label2id={label: index for index, label in enumerate(CONDITION_LABELS)},
        ignore_mismatched_sizes=True,
    )
    device = pick_device(torch, args.device)
    model.to(device)

    def make_loader(rows: list[dict[str, Any]], shuffle: bool) -> Any:
        return DataLoader(
            ConditionDataset(rows),
            batch_size=args.batch_size,
            shuffle=shuffle,
            collate_fn=lambda batch: collate_batch(tokenizer, batch, args.max_length, torch),
        )

    train_loader = make_loader(train_rows, shuffle=True)
    validation_loader = make_loader(validation_rows, shuffle=False)
    test_loader = make_loader(test_rows, shuffle=False)
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.learning_rate)
    total_steps = max(1, len(train_loader) * args.epochs)
    scheduler = get_linear_schedule_with_warmup(
        optimizer,
        num_warmup_steps=max(1, int(total_steps * 0.06)),
        num_training_steps=total_steps,
    )
    losses: list[float] = []
    train_started = time.perf_counter()
    for epoch in range(1, args.epochs + 1):
        model.train()
        epoch_loss = 0.0
        for batch in train_loader:
            labels = batch.pop("labels").to(device)
            batch.pop("texts", None)
            inputs = {key: value.to(device) for key, value in batch.items()}
            outputs = model(**inputs, labels=labels)
            loss = outputs.loss
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()
            scheduler.step()
            optimizer.zero_grad(set_to_none=True)
            epoch_loss += float(loss.detach().cpu())
        losses.append(round(epoch_loss / max(1, len(train_loader)), 6))
        print(json.dumps({"epoch": epoch, "train_loss": losses[-1]}, ensure_ascii=False), flush=True)
    train_latency_ms = (time.perf_counter() - train_started) * 1000

    validation_probabilities, validation_latency_ms = infer_probabilities(model, validation_loader, device, torch)
    validation_expected = [[int(value) for value in row["label_vector"]] for row in validation_rows]
    thresholds = choose_thresholds(validation_expected, validation_probabilities)
    validation_predicted = predict_with_thresholds(validation_probabilities, thresholds)
    validation_metrics = evaluate(validation_expected, validation_predicted, validation_rows, validation_latency_ms)

    test_probabilities, test_latency_ms = infer_probabilities(model, test_loader, device, torch)
    test_expected = [[int(value) for value in row["label_vector"]] for row in test_rows]
    test_predicted = predict_with_thresholds(test_probabilities, thresholds)
    test_metrics = evaluate(test_expected, test_predicted, test_rows, test_latency_ms)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    if args.save_model:
        model_dir = args.output_dir / "model"
        model.save_pretrained(model_dir)
        tokenizer.save_pretrained(model_dir)

    rule_baseline = None
    corrected_rule_baseline = None
    if not args.skip_rule_baselines:
        rule_baseline = evaluate_rule_baseline(test_rows, enable_external_correction=False)
        corrected_rule_baseline = evaluate_rule_baseline(test_rows, enable_external_correction=True)

    report = {
        "model_name": str(args.model_name),
        "device": str(device),
        "epochs": args.epochs,
        "batch_size": args.batch_size,
        "learning_rate": args.learning_rate,
        "max_length": args.max_length,
        "train_rows": len(train_rows),
        "validation_rows": len(validation_rows),
        "test_rows": len(test_rows),
        "train_loss_by_epoch": losses,
        "train_latency_ms": round(train_latency_ms, 4),
        "thresholds": {label: threshold for label, threshold in zip(CONDITION_LABELS, thresholds, strict=True)},
        "validation": validation_metrics,
        "test": test_metrics,
        "rule_baseline_test": rule_baseline,
        "corrected_rule_baseline_test": corrected_rule_baseline,
        "decision": {
            "adopt_runtime": False,
            "reason": "Adopt only after fresh chat-card eval shows quality gain without ambiguity overclassification.",
        },
    }
    (args.output_dir / "metrics.json").write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()

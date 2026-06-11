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

from app.services.tourism_context_classifier import (  # noqa: E402
    CONTEXT_LABELS,
    SPECIFIC_FACILITY_TERMS,
    TourismContextClassifier,
)


DEFAULT_DATA_DIR = PROJECT_ROOT / "data" / "processed" / "context_finetune"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "data" / "generated" / "tour_api" / "context_transformer_pilot"
DEFAULT_BASELINE_METRICS = PROJECT_ROOT / "data" / "generated" / "tour_api" / "context_classifier_eval_augmented_latest.json"


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        payload = json.loads(line)
        text = str(payload.get("text") or "").strip()
        labels = payload.get("labels") or []
        label_vector = payload.get("label_vector")
        if not label_vector:
            label_set = set(labels)
            label_vector = [1 if label in label_set else 0 for label in CONTEXT_LABELS]
        if text:
            rows.append({**payload, "text": text, "label_vector": [float(value) for value in label_vector]})
    return rows


class ContextDataset:
    def __init__(self, rows: list[dict[str, Any]]):
        self.rows = rows

    def __len__(self) -> int:
        return len(self.rows)

    def __getitem__(self, index: int) -> dict[str, Any]:
        return self.rows[index]


def collate_batch(tokenizer: Any, rows: list[dict[str, Any]], max_length: int, torch: Any) -> dict[str, Any]:
    texts = [row["text"] for row in rows]
    encoded = tokenizer(
        texts,
        padding=True,
        truncation=True,
        max_length=max_length,
        return_tensors="pt",
    )
    encoded["labels"] = torch.tensor([row["label_vector"] for row in rows], dtype=torch.float32)
    encoded["texts"] = texts
    encoded["ids"] = [row.get("id") for row in rows]
    return encoded


def pick_device(torch: Any) -> Any:
    if torch.cuda.is_available():
        return torch.device("cuda")
    if getattr(torch.backends, "mps", None) and torch.backends.mps.is_available():
        return torch.device("mps")
    return torch.device("cpu")


def sigmoid_probabilities(logits: Any, torch: Any) -> Any:
    return torch.sigmoid(logits).detach().cpu()


def predict_with_thresholds(probabilities: list[list[float]], thresholds: list[float]) -> list[list[int]]:
    return [[1 if probability >= thresholds[index] else 0 for index, probability in enumerate(row)] for row in probabilities]


def vectors_to_label_sets(vectors: list[list[int]]) -> list[set[str]]:
    return [
        {label for label, value in zip(CONTEXT_LABELS, vector, strict=True) if value}
        for vector in vectors
    ]


def label_sets_to_vectors(label_sets: list[set[str]]) -> list[list[int]]:
    return [[1 if label in label_set else 0 for label in CONTEXT_LABELS] for label_set in label_sets]


def postprocess_hybrid_labels(text: str, predicted: set[str]) -> set[str]:
    result = set(predicted)
    rule_labels = set(TourismContextClassifier.rule_labels(text))
    for label in [
        "strict_and",
        "or_condition",
        "add_condition",
        "replace_condition",
        "exclude_condition",
        "family_context",
        "mobility_context",
        "specific_facility_required",
    ]:
        if label in rule_labels:
            result.add(label)

    if "or_condition" in rule_labels and "strict_and" not in rule_labels:
        result.discard("strict_and")
    if "strict_and" in rule_labels and "or_condition" not in rule_labels:
        result.discard("or_condition")
    if "replace_condition" in result:
        result.discard("exclude_condition")
    if "추측하지 말고" in text:
        result.discard("add_condition")
        result.discard("exclude_condition")
    if "exclude_condition" in result and not any(term in text for term in SPECIFIC_FACILITY_TERMS):
        result.discard("specific_facility_required")
    if any(pattern in text for pattern in ["수어지교", "화장실이 아니라", "가 아니라 화려", "전체 목록"]):
        result.discard("specific_facility_required")
    if ("필수는 아니" in text or "참고만" in text) and "strict_and" not in result and "add_condition" not in result:
        result.discard("specific_facility_required")
    if "strict_and" not in rule_labels:
        result.discard("strict_and")
    if "or_condition" not in rule_labels:
        result.discard("or_condition")
    for action_label in ("add_condition", "replace_condition", "exclude_condition"):
        if action_label not in rule_labels:
            result.discard(action_label)
    for context_label in ("family_context", "mobility_context"):
        if context_label not in rule_labels:
            result.discard(context_label)
    if result & {"strict_and", "or_condition", "add_condition", "replace_condition", "exclude_condition"}:
        result.discard("soft_and")
    if "specific_facility_required" not in rule_labels:
        result.discard("specific_facility_required")
    return result


def postprocess_hybrid_vectors(rows: list[dict[str, Any]], predicted_vectors: list[list[int]]) -> list[list[int]]:
    label_sets = vectors_to_label_sets(predicted_vectors)
    hybrid_sets = [
        postprocess_hybrid_labels(str(row.get("text") or ""), label_set)
        for row, label_set in zip(rows, label_sets, strict=True)
    ]
    return label_sets_to_vectors(hybrid_sets)


def evaluate_vectors(expected: list[list[int]], predicted: list[list[int]], rows: list[dict[str, Any]], latency_ms: float) -> dict[str, Any]:
    exact = 0
    total_expected = 0
    total_predicted = 0
    total_correct = 0
    per_label = {label: {"tp": 0, "fp": 0, "fn": 0} for label in CONTEXT_LABELS}
    special_errors = {
        "strict_and_missed": 0,
        "strict_and_overcalled": 0,
        "or_as_strict_and": 0,
        "exclude_missed": 0,
        "specific_facility_missed": 0,
    }
    failure_buckets: dict[str, int] = {}
    samples: list[dict[str, Any]] = []

    for row, expected_vector, predicted_vector in zip(rows, expected, predicted, strict=True):
        expected_labels = {label for label, value in zip(CONTEXT_LABELS, expected_vector, strict=True) if value}
        predicted_labels = {label for label, value in zip(CONTEXT_LABELS, predicted_vector, strict=True) if value}
        exact += int(expected_labels == predicted_labels)
        total_expected += len(expected_labels)
        total_predicted += len(predicted_labels)
        total_correct += len(expected_labels & predicted_labels)
        for label in CONTEXT_LABELS:
            if label in expected_labels and label in predicted_labels:
                per_label[label]["tp"] += 1
            elif label not in expected_labels and label in predicted_labels:
                per_label[label]["fp"] += 1
            elif label in expected_labels and label not in predicted_labels:
                per_label[label]["fn"] += 1
        if "strict_and" in expected_labels and "strict_and" not in predicted_labels:
            special_errors["strict_and_missed"] += 1
        if "strict_and" not in expected_labels and "strict_and" in predicted_labels:
            special_errors["strict_and_overcalled"] += 1
        if "or_condition" in expected_labels and "strict_and" in predicted_labels:
            special_errors["or_as_strict_and"] += 1
        if "exclude_condition" in expected_labels and "exclude_condition" not in predicted_labels:
            special_errors["exclude_missed"] += 1
        if "specific_facility_required" in expected_labels and "specific_facility_required" not in predicted_labels:
            special_errors["specific_facility_missed"] += 1

        if expected_labels != predicted_labels:
            for label in sorted(expected_labels - predicted_labels):
                failure_buckets[f"missing:{label}"] = failure_buckets.get(f"missing:{label}", 0) + 1
            for label in sorted(predicted_labels - expected_labels):
                failure_buckets[f"spurious:{label}"] = failure_buckets.get(f"spurious:{label}", 0) + 1
            if len(samples) < 20:
                samples.append(
                    {
                        "id": row.get("id"),
                        "text": row.get("text"),
                        "expected": sorted(expected_labels),
                        "predicted": sorted(predicted_labels),
                    }
                )

    precision = total_correct / total_predicted if total_predicted else 1.0
    recall = total_correct / total_expected if total_expected else 1.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    per_label_metrics: dict[str, Any] = {}
    for label, counts in per_label.items():
        label_precision = counts["tp"] / (counts["tp"] + counts["fp"]) if counts["tp"] + counts["fp"] else 1.0
        label_recall = counts["tp"] / (counts["tp"] + counts["fn"]) if counts["tp"] + counts["fn"] else 1.0
        label_f1 = (
            2 * label_precision * label_recall / (label_precision + label_recall)
            if label_precision + label_recall
            else 0.0
        )
        per_label_metrics[label] = {
            "precision": round(label_precision, 4),
            "recall": round(label_recall, 4),
            "f1": round(label_f1, 4),
            **counts,
        }

    return {
        "rows": len(rows),
        "exact_match": round(exact / len(rows), 4) if rows else 0.0,
        "micro_precision": round(precision, 4),
        "micro_recall": round(recall, 4),
        "micro_f1": round(f1, 4),
        "per_label": per_label_metrics,
        "special_errors": special_errors,
        "failure_buckets": dict(sorted(failure_buckets.items(), key=lambda item: (-item[1], item[0]))),
        "latency": {
            "total_ms": round(latency_ms, 4),
            "mean_ms": round(latency_ms / len(rows), 4) if rows else 0.0,
        },
        "sample_mismatches": samples,
    }


def choose_thresholds(expected: list[list[int]], probabilities: list[list[float]]) -> list[float]:
    thresholds: list[float] = []
    candidates = [value / 100 for value in range(20, 81, 5)]
    for index in range(len(CONTEXT_LABELS)):
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
    probabilities: list[list[float]] = []
    started = time.perf_counter()
    with torch.no_grad():
        for batch in loader:
            labels = batch.pop("labels")
            batch.pop("texts", None)
            batch.pop("ids", None)
            inputs = {key: value.to(device) for key, value in batch.items()}
            outputs = model(**inputs)
            batch_probabilities = sigmoid_probabilities(outputs.logits, torch)
            probabilities.extend(batch_probabilities.tolist())
            del labels
    return probabilities, (time.perf_counter() - started) * 1000


def seed_everything(seed: int, torch: Any) -> None:
    random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def load_baseline(path: Path) -> dict[str, Any]:
    fallback = {
        "predictor": "hybrid_logistic_regression",
        "exact_match": 0.8927,
        "micro_f1": 0.9379,
        "latency_mean_ms": 0.3518,
    }
    if not path.exists():
        return fallback
    payload = json.loads(path.read_text(encoding="utf-8"))
    best_name = str(payload.get("best_linear") or fallback["predictor"])
    for result in payload.get("results") or []:
        if result.get("predictor") == best_name:
            return {
                "predictor": best_name,
                "exact_match": float(result.get("exact_match") or 0.0),
                "micro_f1": float(result.get("micro_f1") or 0.0),
                "latency_mean_ms": float(dict(result.get("latency") or {}).get("mean_ms") or 0.0),
            }
    return fallback


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fine-tune a transformer pilot for tourism context multi-label classification.")
    parser.add_argument("--model-name", default="klue/roberta-small")
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--epochs", type=int, default=2)
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--learning-rate", type=float, default=2e-5)
    parser.add_argument("--max-length", type=int, default=96)
    parser.add_argument("--seed", type=int, default=20260517)
    parser.add_argument("--save-model", action="store_true")
    parser.add_argument("--baseline-metrics", type=Path, default=DEFAULT_BASELINE_METRICS)
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
    baseline = load_baseline(args.baseline_metrics)
    train_rows = load_jsonl(args.data_dir / "train.jsonl")
    validation_rows = load_jsonl(args.data_dir / "validation.jsonl")
    test_rows = load_jsonl(args.data_dir / "test.jsonl")
    tokenizer = AutoTokenizer.from_pretrained(args.model_name)
    model = AutoModelForSequenceClassification.from_pretrained(
        args.model_name,
        num_labels=len(CONTEXT_LABELS),
        problem_type="multi_label_classification",
        id2label={index: label for index, label in enumerate(CONTEXT_LABELS)},
        label2id={label: index for index, label in enumerate(CONTEXT_LABELS)},
        ignore_mismatched_sizes=True,
    )
    device = pick_device(torch)
    model.to(device)

    def make_loader(rows: list[dict[str, Any]], shuffle: bool) -> Any:
        return DataLoader(
            ContextDataset(rows),
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
            batch.pop("ids", None)
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
    train_ms = (time.perf_counter() - train_started) * 1000

    validation_probabilities, validation_latency_ms = infer_probabilities(model, validation_loader, device, torch)
    validation_expected = [[int(value) for value in row["label_vector"]] for row in validation_rows]
    thresholds = choose_thresholds(validation_expected, validation_probabilities)
    validation_predicted = predict_with_thresholds(validation_probabilities, thresholds)
    validation_metrics = evaluate_vectors(validation_expected, validation_predicted, validation_rows, validation_latency_ms)

    test_probabilities, test_latency_ms = infer_probabilities(model, test_loader, device, torch)
    test_expected = [[int(value) for value in row["label_vector"]] for row in test_rows]
    test_predicted = predict_with_thresholds(test_probabilities, thresholds)
    test_metrics = evaluate_vectors(test_expected, test_predicted, test_rows, test_latency_ms)
    hybrid_test_predicted = postprocess_hybrid_vectors(test_rows, test_predicted)
    hybrid_test_metrics = evaluate_vectors(test_expected, hybrid_test_predicted, test_rows, test_latency_ms)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    if args.save_model:
        model_dir = args.output_dir / "model"
        model.save_pretrained(model_dir)
        tokenizer.save_pretrained(model_dir)

    report = {
        "model_name": args.model_name,
        "device": str(device),
        "epochs": args.epochs,
        "batch_size": args.batch_size,
        "learning_rate": args.learning_rate,
        "max_length": args.max_length,
        "train_rows": len(train_rows),
        "validation_rows": len(validation_rows),
        "test_rows": len(test_rows),
        "train_loss_by_epoch": losses,
        "train_latency_ms": round(train_ms, 4),
        "thresholds": {label: threshold for label, threshold in zip(CONTEXT_LABELS, thresholds, strict=True)},
        "validation": validation_metrics,
        "test": test_metrics,
        "hybrid_test": hybrid_test_metrics,
        "baseline": baseline,
        "decision": {
            "adopt_runtime": False,
            "reason": "Pilot result must beat the hybrid LogisticRegression baseline by at least micro-F1 +0.02 and pass latency review.",
        },
    }
    output_path = args.output_dir / "metrics.json"
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()

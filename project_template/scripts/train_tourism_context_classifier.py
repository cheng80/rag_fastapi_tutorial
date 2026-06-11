from __future__ import annotations

import argparse
import json
from pathlib import Path
import random
import sys
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.services.tourism_context_classifier import (  # noqa: E402
    DEFAULT_CONTEXT_MODEL_PATH,
    TourismContextClassifier,
    train_context_model,
)


DEFAULT_INPUT = PROJECT_ROOT / "data" / "processed" / "tourism_context_training.jsonl"


def project_relative(path: Path) -> str:
    resolved = path.resolve()
    try:
        return str(resolved.relative_to(PROJECT_ROOT))
    except ValueError:
        return str(path)


def load_rows(path: Path) -> list[dict[str, Any]]:
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        payload = json.loads(line)
        rows.append({"text": str(payload.get("text") or ""), "labels": list(payload.get("labels") or [])})
    return [row for row in rows if row["text"]]


def evaluate_nb(rows: list[dict[str, Any]], seed: int = 13) -> dict[str, Any]:
    rng = random.Random(seed)
    shuffled = list(rows)
    rng.shuffle(shuffled)
    split = max(1, int(len(shuffled) * 0.8))
    train_rows = shuffled[:split]
    test_rows = shuffled[split:] or shuffled
    model = train_context_model(train_rows)
    classifier = TourismContextClassifier.__new__(TourismContextClassifier)
    classifier.model_path = Path("<memory>")
    classifier.threshold = 0.62
    classifier.model = model

    exact = 0
    total_expected = 0
    total_predicted = 0
    total_correct = 0
    for row in test_rows:
        expected = set(row["labels"])
        predicted = set(classifier.predict(row["text"]).labels)
        exact += int(predicted == expected)
        total_expected += len(expected)
        total_predicted += len(predicted)
        total_correct += len(expected & predicted)

    precision = total_correct / total_predicted if total_predicted else 1.0
    recall = total_correct / total_expected if total_expected else 1.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {
        "train_rows": len(train_rows),
        "test_rows": len(test_rows),
        "exact_match": round(exact / len(test_rows), 4),
        "micro_precision": round(precision, 4),
        "micro_recall": round(recall, 4),
        "micro_f1": round(f1, 4),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train the tourism context classifier.")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_CONTEXT_MODEL_PATH)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    rows = load_rows(args.input)
    model = train_context_model(rows)
    model["metrics"] = evaluate_nb(rows)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(model, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    print(f"Wrote {project_relative(args.output)}")
    print(json.dumps({"rows": len(rows), "metrics": model["metrics"]}, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()

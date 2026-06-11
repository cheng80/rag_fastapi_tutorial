from __future__ import annotations

import argparse
import json
from pathlib import Path
import random
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.services.tourism_intent_classifier import TourismIntentClassifier, train_intent_model  # noqa: E402


DEFAULT_INPUT = PROJECT_ROOT / "data" / "processed" / "tourism_intent_training.jsonl"
DEFAULT_OUTPUT = PROJECT_ROOT / "data" / "processed" / "tourism_intent_classifier.json"


def load_rows(path: Path) -> list[dict[str, str]]:
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        payload = json.loads(line)
        rows.append({"text": str(payload.get("text") or ""), "intent": str(payload.get("intent") or "")})
    return [row for row in rows if row["text"] and row["intent"]]


def evaluate(rows: list[dict[str, str]], seed: int = 13) -> dict[str, object]:
    by_label: dict[str, list[dict[str, str]]] = {}
    for row in rows:
        by_label.setdefault(row["intent"], []).append(row)
    train_rows = []
    test_rows = []
    rng = random.Random(seed)
    for label_rows in by_label.values():
        shuffled = list(label_rows)
        rng.shuffle(shuffled)
        split = max(1, int(len(shuffled) * 0.8))
        if len(shuffled) <= 2:
            train_rows.extend(shuffled)
            test_rows.extend(shuffled)
        else:
            train_rows.extend(shuffled[:split])
            test_rows.extend(shuffled[split:])

    model = train_intent_model(train_rows)
    classifier = TourismIntentClassifier.__new__(TourismIntentClassifier)
    classifier.model_path = Path("<memory>")
    classifier.model = model
    correct = 0
    confusion: dict[str, dict[str, int]] = {}
    for row in test_rows:
        prediction = classifier.predict(row["text"])
        predicted = prediction.intent or "<none>"
        actual = row["intent"]
        correct += int(predicted == actual)
        confusion.setdefault(actual, {})
        confusion[actual][predicted] = confusion[actual].get(predicted, 0) + 1
    accuracy = correct / len(test_rows) if test_rows else 0.0
    return {
        "train_rows": len(train_rows),
        "test_rows": len(test_rows),
        "accuracy": round(accuracy, 4),
        "confusion": confusion,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train the tourism intent classifier.")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    rows = load_rows(args.input)
    metrics = evaluate(rows)
    model = train_intent_model(rows)
    model["metrics"] = metrics
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(model, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    print(f"Wrote {args.output.relative_to(PROJECT_ROOT)}")
    print(json.dumps({"rows": len(rows), **metrics}, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()

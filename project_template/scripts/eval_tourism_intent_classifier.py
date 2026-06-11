from __future__ import annotations

import argparse
from collections import defaultdict
import json
from pathlib import Path
import sys
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.services.tourism_intent_classifier import TourismIntentClassifier  # noqa: E402


DEFAULT_INPUTS = [
    PROJECT_ROOT / "data" / "eval" / "tourism_intent_aihub_holdout.jsonl",
    PROJECT_ROOT / "data" / "eval" / "tourism_intent_adversarial_holdout.jsonl",
]


def load_rows(paths: list[Path]) -> list[dict[str, str]]:
    rows = []
    for path in paths:
        if not path.exists():
            continue
        for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            if not line.strip():
                continue
            payload = json.loads(line)
            text = str(payload.get("text") or payload.get("message") or "").strip()
            intent = str(payload.get("intent") or "").strip()
            if not text or not intent:
                raise ValueError(f"{path}:{line_number} must include text/message and intent")
            rows.append({"text": text, "intent": intent, "source": path.name})
    return rows


def evaluate(rows: list[dict[str, str]]) -> dict[str, Any]:
    classifier = TourismIntentClassifier()
    correct = 0
    confusion: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    misses = []
    by_source: dict[str, dict[str, int]] = defaultdict(lambda: {"rows": 0, "correct": 0})

    for row in rows:
        prediction = classifier.predict(row["text"])
        predicted = prediction.intent or "<none>"
        actual = row["intent"]
        is_correct = predicted == actual
        correct += int(is_correct)
        confusion[actual][predicted] += 1
        by_source[row["source"]]["rows"] += 1
        by_source[row["source"]]["correct"] += int(is_correct)
        if not is_correct and len(misses) < 80:
            misses.append(
                {
                    "source": row["source"],
                    "text": row["text"],
                    "actual": actual,
                    "predicted": predicted,
                    "confidence": prediction.confidence,
                }
            )

    source_metrics = {
        source: {
            "rows": stats["rows"],
            "accuracy": round(stats["correct"] / stats["rows"], 4) if stats["rows"] else 0.0,
        }
        for source, stats in sorted(by_source.items())
    }
    return {
        "rows": len(rows),
        "accuracy": round(correct / len(rows), 4) if rows else 0.0,
        "by_source": source_metrics,
        "confusion": {actual: dict(predicted) for actual, predicted in sorted(confusion.items())},
        "sample_misses": misses,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate the tourism intent classifier on holdout JSONL files.")
    parser.add_argument("--input", type=Path, action="append", default=None)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    paths = args.input or DEFAULT_INPUTS
    rows = load_rows([path if path.is_absolute() else PROJECT_ROOT / path for path in paths])
    print(json.dumps(evaluate(rows), ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

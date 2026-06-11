from __future__ import annotations

from collections import defaultdict
import json
from pathlib import Path
import sys
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.services.tourism_intent_classifier import TourismIntentClassifier, train_intent_model  # noqa: E402
from scripts.build_tourism_intent_training_set import (  # noqa: E402
    EXTERNAL_EVAL_PATH,
    build_rows,
)
from scripts.eval_tourism_intent_classifier import DEFAULT_INPUTS, load_rows  # noqa: E402


PROJECT_TRAINING_PATHS = [
    PROJECT_ROOT / "data" / "eval" / "tourism_100_questions.jsonl",
    PROJECT_ROOT / "data" / "eval" / "tourism_challenge_questions.jsonl",
    PROJECT_ROOT / "data" / "eval" / "tourism_conversation_challenge.jsonl",
    PROJECT_ROOT / "data" / "eval" / "tourism_intent_seed_utterances.jsonl",
    PROJECT_ROOT / "data" / "eval" / "tourism_intent_generated_utterances.jsonl",
]
AIHUB_TRAINING_PATH = PROJECT_ROOT / "data" / "eval" / "tourism_intent_aihub_utterances.jsonl"
DEFAULT_OUTPUT = PROJECT_ROOT / "data" / "generated" / "tour_api" / "intent_ablation_latest.json"


def build_classifier(rows: list[dict[str, str]] | None) -> TourismIntentClassifier:
    classifier = TourismIntentClassifier.__new__(TourismIntentClassifier)
    classifier.model_path = Path("<memory>")
    classifier.model = train_intent_model(rows) if rows is not None else None
    return classifier


def evaluate(classifier: TourismIntentClassifier, rows: list[dict[str, str]]) -> dict[str, Any]:
    correct = 0
    by_source: dict[str, dict[str, int]] = defaultdict(lambda: {"rows": 0, "correct": 0})
    by_intent: dict[str, dict[str, int]] = defaultdict(lambda: {"rows": 0, "correct": 0})

    for row in rows:
        prediction = classifier.predict(row["text"])
        predicted = prediction.intent or "<none>"
        actual = row["intent"]
        is_correct = predicted == actual
        correct += int(is_correct)
        by_source[row["source"]]["rows"] += 1
        by_source[row["source"]]["correct"] += int(is_correct)
        by_intent[actual]["rows"] += 1
        by_intent[actual]["correct"] += int(is_correct)

    return {
        "rows": len(rows),
        "accuracy": round(correct / len(rows), 4) if rows else 0.0,
        "by_source": _accuracy_table(by_source),
        "by_intent": _accuracy_table(by_intent),
    }


def _accuracy_table(stats: dict[str, dict[str, int]]) -> dict[str, dict[str, float | int]]:
    return {
        key: {
            "rows": value["rows"],
            "accuracy": round(value["correct"] / value["rows"], 4) if value["rows"] else 0.0,
        }
        for key, value in sorted(stats.items())
    }


def main() -> None:
    holdout_rows = load_rows(DEFAULT_INPUTS)
    project_rows = build_rows(PROJECT_TRAINING_PATHS)
    aihub_rows = build_rows([AIHUB_TRAINING_PATH])
    external_rows = build_rows([EXTERNAL_EVAL_PATH])

    variants: dict[str, list[dict[str, str]] | None] = {
        "rule_only": None,
        "project_seed_generated": project_rows,
        "project_plus_aihub": [*project_rows, *aihub_rows],
        "project_plus_aihub_plus_hf_external": [*project_rows, *aihub_rows, *external_rows],
    }

    results: dict[str, Any] = {}
    for name, rows in variants.items():
        classifier = build_classifier(rows)
        metrics = evaluate(classifier, holdout_rows)
        results[name] = {
            "training_rows": len(rows) if rows is not None else 0,
            **metrics,
        }

    payload = {
        "holdout_rows": len(holdout_rows),
        "notes": [
            "expanded chat eval files are not used for training",
            "huggingface external rows are experiment-only and not part of the default runtime model",
        ],
        "results": results,
    }
    DEFAULT_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    DEFAULT_OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

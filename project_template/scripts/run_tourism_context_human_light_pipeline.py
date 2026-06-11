from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import subprocess
import sys
from typing import Any, Callable


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.services.tourism_context_classifier import (  # noqa: E402
    CONTEXT_LABELS,
    TourismContextClassifier,
)


DEFAULT_BATCH_ID = "20260517_human_light_1000"
DEFAULT_RAW_INPUT = (
    PROJECT_ROOT
    / "data"
    / "generated"
    / "tour_api"
    / "context_llm_batches"
    / f"context_llm_batch_{DEFAULT_BATCH_ID}.raw.jsonl"
)
DEFAULT_VALID_OUTPUT = PROJECT_ROOT / "data" / "processed" / f"tourism_context_llm_hard_training_{DEFAULT_BATCH_ID}.valid.jsonl"
DEFAULT_FINETUNE_OUTPUT = PROJECT_ROOT / "data" / "processed" / f"context_finetune_{DEFAULT_BATCH_ID}"
DEFAULT_REPORT_OUTPUT = (
    PROJECT_ROOT
    / "data"
    / "generated"
    / "tour_api"
    / "context_llm_reports"
    / f"context_human_light_report_{DEFAULT_BATCH_ID}.json"
)
DEFAULT_REVIEW_QUEUE_OUTPUT = (
    PROJECT_ROOT
    / "data"
    / "generated"
    / "tour_api"
    / "context_llm_reports"
    / f"context_human_light_review_queue_{DEFAULT_BATCH_ID}.jsonl"
)


def project_relative(path: Path) -> str:
    resolved = path.resolve()
    try:
        return str(resolved.relative_to(PROJECT_ROOT))
    except ValueError:
        return str(path)


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        rows.append(json.loads(line))
    return rows


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        for row in rows:
            file.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def run_json_command(command: list[str]) -> dict[str, Any]:
    completed = subprocess.run(
        command,
        cwd=PROJECT_ROOT,
        check=True,
        text=True,
        capture_output=True,
    )
    stdout = completed.stdout.strip().splitlines()
    if not stdout:
        return {}
    return json.loads(stdout[-1])


def evaluate_rows(
    rows: list[dict[str, Any]],
    name: str,
    predict: Callable[[str], set[str]],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    exact = 0
    total_expected = 0
    total_predicted = 0
    total_correct = 0
    per_label: dict[str, Counter[str]] = {label: Counter() for label in CONTEXT_LABELS}
    misses: list[dict[str, Any]] = []
    for row in rows:
        text = str(row.get("text") or "")
        expected = set(row.get("labels") or [])
        predicted = predict(text)
        exact += int(expected == predicted)
        total_expected += len(expected)
        total_predicted += len(predicted)
        total_correct += len(expected & predicted)
        for label in CONTEXT_LABELS:
            if label in expected and label in predicted:
                per_label[label]["tp"] += 1
            elif label not in expected and label in predicted:
                per_label[label]["fp"] += 1
            elif label in expected and label not in predicted:
                per_label[label]["fn"] += 1
            else:
                per_label[label]["tn"] += 1
        if expected != predicted:
            missing = sorted(expected - predicted, key=CONTEXT_LABELS.index)
            spurious = sorted(predicted - expected, key=CONTEXT_LABELS.index)
            severity = "high" if set(missing + spurious) & {"strict_and", "or_condition", "replace_condition", "exclude_condition", "specific_facility_required"} else "normal"
            misses.append(
                {
                    "id": row.get("id"),
                    "text": text,
                    "expected": sorted(expected, key=CONTEXT_LABELS.index),
                    "predicted": sorted(predicted, key=CONTEXT_LABELS.index),
                    "missing": missing,
                    "spurious": spurious,
                    "category": row.get("category"),
                    "risk_tags": row.get("risk_tags") or [],
                    "severity": severity,
                    "predictor": name,
                }
            )
    precision = total_correct / total_predicted if total_predicted else 1.0
    recall = total_correct / total_expected if total_expected else 1.0
    f1 = (2 * precision * recall / (precision + recall)) if precision + recall else 0.0
    metrics = {
        "predictor": name,
        "rows": len(rows),
        "exact_match": round(exact / len(rows), 4) if rows else 0.0,
        "micro_precision": round(precision, 4),
        "micro_recall": round(recall, 4),
        "micro_f1": round(f1, 4),
        "mismatch_rows": len(misses),
        "high_risk_mismatch_rows": sum(1 for item in misses if item["severity"] == "high"),
        "per_label": {label: dict(counts) for label, counts in per_label.items()},
        "top_missing_labels": Counter(label for miss in misses for label in miss["missing"]).most_common(),
        "top_spurious_labels": Counter(label for miss in misses for label in miss["spurious"]).most_common(),
    }
    return metrics, misses


def build_review_queue(rows: list[dict[str, Any]], classifier: TourismContextClassifier) -> list[dict[str, Any]]:
    queue: list[dict[str, Any]] = []
    for row in rows:
        text = str(row.get("text") or "")
        expected = set(row.get("labels") or [])
        rule = set(TourismContextClassifier.rule_labels(text))
        current = set(classifier.predict(text).labels)
        reasons: list[str] = []
        if rule != current:
            reasons.append("rule_current_disagreement")
        if expected != rule:
            reasons.append("expected_rule_mismatch")
        if expected != current:
            reasons.append("expected_current_mismatch")
        if expected & {"strict_and", "or_condition"} and not (expected & rule):
            reasons.append("structural_label_not_caught_by_rule")
        if "specific_facility_required" in expected and "specific_facility_required" not in current:
            reasons.append("facility_evidence_label_not_caught")
        if not reasons:
            continue
        queue.append(
            {
                "id": row.get("id"),
                "text": text,
                "expected": sorted(expected, key=CONTEXT_LABELS.index),
                "rule_only": sorted(rule, key=CONTEXT_LABELS.index),
                "current_context_classifier": sorted(current, key=CONTEXT_LABELS.index),
                "category": row.get("category"),
                "risk_tags": row.get("risk_tags") or [],
                "reasons": reasons,
            }
        )
    return queue


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run human-light automatic verification for generated tourism context rows.")
    parser.add_argument("--raw-input", type=Path, default=DEFAULT_RAW_INPUT)
    parser.add_argument("--valid-output", type=Path, default=DEFAULT_VALID_OUTPUT)
    parser.add_argument("--finetune-output-dir", type=Path, default=DEFAULT_FINETUNE_OUTPUT)
    parser.add_argument("--report-output", type=Path, default=DEFAULT_REPORT_OUTPUT)
    parser.add_argument("--review-queue-output", type=Path, default=DEFAULT_REVIEW_QUEUE_OUTPUT)
    parser.add_argument("--min-rows", type=int, default=1000)
    parser.add_argument("--validation-ratio", type=float, default=0.15)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    validation_report = run_json_command(
        [
            sys.executable,
            "scripts/validate_tourism_context_llm_dataset.py",
            "--input",
            project_relative(args.raw_input),
            "--output",
            project_relative(args.valid_output),
            "--min-rows",
            str(args.min_rows),
            "--fail-on-reject",
        ]
    )
    finetune_report = run_json_command(
        [
            sys.executable,
            "scripts/prepare_tourism_context_finetune_data.py",
            "--extra-train-input",
            project_relative(args.valid_output),
            "--output-dir",
            project_relative(args.finetune_output_dir),
            "--validation-ratio",
            str(args.validation_ratio),
        ]
    )
    rows = load_jsonl(args.valid_output)
    classifier = TourismContextClassifier()
    rule_metrics, rule_misses = evaluate_rows(rows, "rule_only", lambda text: set(TourismContextClassifier.rule_labels(text)))
    current_metrics, current_misses = evaluate_rows(rows, "current_context_classifier", lambda text: set(classifier.predict(text).labels))
    review_queue = build_review_queue(rows, classifier)
    write_jsonl(args.review_queue_output, review_queue)

    report = {
        "raw_input": project_relative(args.raw_input),
        "valid_output": project_relative(args.valid_output),
        "finetune_output_dir": project_relative(args.finetune_output_dir),
        "review_queue_output": project_relative(args.review_queue_output),
        "validation": validation_report,
        "finetune": finetune_report,
        "automatic_audit": {
            "rule_only": rule_metrics,
            "current_context_classifier": current_metrics,
            "review_queue_rows": len(review_queue),
            "review_queue_reason_counts": Counter(reason for row in review_queue for reason in row["reasons"]),
            "rule_miss_samples": rule_misses[:20],
            "current_classifier_miss_samples": current_misses[:20],
        },
        "human_light_policy": {
            "human_review_required": False,
            "manual_review_scope": "optional_top_review_queue_only",
            "runtime_adoption": "blocked_until_blind_eval_and_chat_card_eval",
        },
    }
    report["automatic_audit"]["review_queue_reason_counts"] = dict(report["automatic_audit"]["review_queue_reason_counts"])
    args.report_output.parent.mkdir(parents=True, exist_ok=True)
    args.report_output.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps({"report": project_relative(args.report_output), "review_queue": project_relative(args.review_queue_output), "valid_rows": len(rows), "review_queue_rows": len(review_queue)}, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()

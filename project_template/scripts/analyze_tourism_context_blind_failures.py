from __future__ import annotations

import json
from pathlib import Path
import sys
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = PROJECT_ROOT / "data" / "generated" / "tour_api" / "context_classifier_eval_blind_holdout_latest.json"
DEFAULT_OUTPUT = PROJECT_ROOT / "data" / "generated" / "tour_api" / "context_blind_failure_analysis_latest.json"


def load_metrics(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def predictor_result(metrics: dict[str, Any], predictor: str) -> dict[str, Any]:
    for item in metrics.get("results") or []:
        if item.get("predictor") == predictor:
            return item
    raise ValueError(f"predictor not found: {predictor}")


def bucket_for_sample(sample: dict[str, Any]) -> list[str]:
    text = str(sample.get("text") or "")
    expected = set(sample.get("expected") or [])
    predicted = set(sample.get("predicted") or [])
    buckets: list[str] = []
    if "strict_and" in expected and "strict_and" not in predicted:
        buckets.append("strict_and_missed_colloquial")
    if "or_condition" in expected and "or_condition" not in predicted:
        buckets.append("or_condition_missed_fallback_language")
    if "soft_and" in expected and "soft_and" not in predicted:
        buckets.append("soft_and_missed_optional_language")
    if "specific_facility_required" in expected and "specific_facility_required" not in predicted:
        buckets.append("specific_facility_required_missed_synonym")
    if "specific_facility_required" not in expected and "specific_facility_required" in predicted:
        buckets.append("specific_facility_required_overcalled_optional")
    if "family_context" in expected and "family_context" not in predicted:
        buckets.append("family_context_missed_colloquial")
    if "mobility_context" in expected and "mobility_context" not in predicted:
        buckets.append("mobility_context_missed_implicit")
    if "add_condition" in expected and "add_condition" not in predicted:
        buckets.append("add_condition_missed_followup")
    if "exclude_condition" not in expected and "exclude_condition" in predicted and "말고" in text:
        buckets.append("exclude_overcalled_negated_optional")
    if "or_condition" not in expected and "or_condition" in predicted:
        buckets.append("or_overcalled_negative_strict")
    return buckets or ["other"]


def main() -> None:
    predictor = sys.argv[1] if len(sys.argv) > 1 else "hybrid_logistic_regression"
    metrics = load_metrics(DEFAULT_INPUT)
    result = predictor_result(metrics, predictor)
    bucket_counts: dict[str, int] = {}
    samples_by_bucket: dict[str, list[dict[str, Any]]] = {}
    for sample in result.get("sample_mismatches") or []:
        for bucket in bucket_for_sample(sample):
            bucket_counts[bucket] = bucket_counts.get(bucket, 0) + 1
            samples_by_bucket.setdefault(bucket, []).append(sample)
    report = {
        "input": str(DEFAULT_INPUT.relative_to(PROJECT_ROOT)),
        "predictor": predictor,
        "exact_match": result.get("exact_match"),
        "micro_f1": result.get("micro_f1"),
        "failure_buckets": result.get("failure_buckets"),
        "interpreted_buckets": dict(sorted(bucket_counts.items(), key=lambda item: (-item[1], item[0]))),
        "samples_by_bucket": {
            bucket: samples[:5]
            for bucket, samples in sorted(samples_by_bucket.items())
        },
        "do_not_train_on": "data/eval/tourism_context_blind_holdout.jsonl",
    }
    DEFAULT_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    DEFAULT_OUTPUT.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps({k: report[k] for k in ["predictor", "exact_match", "micro_f1", "interpreted_buckets"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()

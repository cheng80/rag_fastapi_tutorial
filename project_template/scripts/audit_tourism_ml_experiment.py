from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TRANSFORMER_METRICS = PROJECT_ROOT / "data" / "generated" / "tour_api" / "context_transformer_pilot" / "metrics.json"
DEFAULT_CONTEXT_BASELINE_METRICS = PROJECT_ROOT / "data" / "generated" / "tour_api" / "context_classifier_eval_latest.json"
DEFAULT_OUTPUT = PROJECT_ROOT / "data" / "generated" / "tour_api" / "ml_experiment_audit_latest.json"


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def classify_gap(validation: dict[str, Any], test: dict[str, Any]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    validation_exact = float(validation.get("exact_match") or 0.0)
    validation_f1 = float(validation.get("micro_f1") or 0.0)
    test_exact = float(test.get("exact_match") or 0.0)
    test_f1 = float(test.get("micro_f1") or 0.0)
    if validation_exact >= 0.98 and test_exact < 0.90:
        findings.append(
            {
                "severity": "high",
                "type": "overfit_or_validation_leakage",
                "message": "validation exact is near-perfect while hard holdout exact is below 0.90.",
                "validation_exact": validation_exact,
                "hard_holdout_exact": test_exact,
            }
        )
    if validation_f1 - test_f1 >= 0.05:
        findings.append(
            {
                "severity": "high",
                "type": "generalization_gap",
                "message": "validation micro-F1 is much higher than hard holdout micro-F1.",
                "validation_micro_f1": validation_f1,
                "hard_holdout_micro_f1": test_f1,
                "gap": round(validation_f1 - test_f1, 4),
            }
        )
    return findings


def classify_baseline(transformer_metrics: dict[str, Any]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    baseline = dict(transformer_metrics.get("baseline") or {})
    baseline_exact = float(baseline.get("exact_match") or 0.0)
    baseline_f1 = float(baseline.get("micro_f1") or 0.0)
    baseline_latency = float(baseline.get("latency_mean_ms") or 0.0)
    for name in ("test", "hybrid_test"):
        result = dict(transformer_metrics.get(name) or {})
        if not result:
            continue
        exact = float(result.get("exact_match") or 0.0)
        f1 = float(result.get("micro_f1") or 0.0)
        latency = float(dict(result.get("latency") or {}).get("mean_ms") or 0.0)
        if f1 < baseline_f1 + 0.02:
            findings.append(
                {
                    "severity": "medium",
                    "type": "insufficient_quality_gain",
                    "model_result": name,
                    "message": "model does not beat the baseline by the required +0.02 micro-F1.",
                    "baseline_micro_f1": baseline_f1,
                    "model_micro_f1": f1,
                    "required_micro_f1": round(baseline_f1 + 0.02, 4),
                }
            )
        if exact <= baseline_exact:
            findings.append(
                {
                    "severity": "medium",
                    "type": "exact_match_not_improved",
                    "model_result": name,
                    "message": "model exact match does not improve over the baseline.",
                    "baseline_exact": baseline_exact,
                    "model_exact": exact,
                }
            )
        if baseline_latency and latency > baseline_latency * 2:
            findings.append(
                {
                    "severity": "medium",
                    "type": "latency_regression",
                    "model_result": name,
                    "message": "model mean inference latency is more than 2x the baseline.",
                    "baseline_latency_mean_ms": baseline_latency,
                    "model_latency_mean_ms": latency,
                }
            )
    return findings


def classify_context_baseline(context_metrics: dict[str, Any]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    if not context_metrics:
        return findings
    results = list(context_metrics.get("results") or [])
    best_name = str(context_metrics.get("best_linear") or "")
    by_name = {str(result.get("predictor")): result for result in results}
    best = dict(by_name.get(best_name) or {})
    if not best:
        findings.append(
            {
                "severity": "high",
                "type": "missing_best_baseline",
                "message": "context baseline metrics do not contain best_linear result.",
            }
        )
        return findings

    if float(best.get("micro_f1") or 0.0) < 0.90:
        findings.append(
            {
                "severity": "medium",
                "type": "weak_baseline",
                "message": "best context baseline micro-F1 is below 0.90 on hard holdout.",
                "best_linear": best_name,
                "micro_f1": best.get("micro_f1"),
            }
        )
    if float(best.get("exact_match") or 0.0) < 0.85:
        findings.append(
            {
                "severity": "medium",
                "type": "low_exact_match",
                "message": "best context baseline exact match is below 0.85 on hard holdout.",
                "best_linear": best_name,
                "exact_match": best.get("exact_match"),
            }
        )

    special_errors = dict(best.get("special_errors") or {})
    dangerous = {
        "strict_and_missed": int(special_errors.get("strict_and_missed") or 0),
        "or_as_strict_and": int(special_errors.get("or_as_strict_and") or 0),
        "exclude_missed": int(special_errors.get("exclude_missed") or 0),
    }
    nonzero_dangerous = {key: value for key, value in dangerous.items() if value}
    if nonzero_dangerous:
        findings.append(
            {
                "severity": "high",
                "type": "dangerous_special_errors",
                "message": "best context baseline still has dangerous special errors.",
                "best_linear": best_name,
                "errors": nonzero_dangerous,
            }
        )

    rows = int(best.get("rows") or 0)
    if rows < 1000:
        findings.append(
            {
                "severity": "medium",
                "type": "small_hard_holdout",
                "message": "hard holdout is too small for model adoption decisions.",
                "rows": rows,
            }
        )

    if "validation" not in context_metrics:
        findings.append(
            {
                "severity": "medium",
                "type": "missing_hard_validation",
                "message": "context baseline comparison has no separate hard validation split; treat as exploratory, not final model selection.",
                "best_linear": best_name,
            }
        )
    return findings


def summarize_recommendation(findings: list[dict[str, Any]]) -> str:
    high = [finding for finding in findings if finding.get("severity") == "high"]
    if high:
        return "do_not_adopt_runtime"
    medium = [finding for finding in findings if finding.get("severity") == "medium"]
    if medium:
        return "hold_and_collect_more_data"
    return "eligible_for_manual_review"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Audit tourism ML experiment metrics for overfitting and adoption risk.")
    parser.add_argument("--transformer-metrics", type=Path, default=DEFAULT_TRANSFORMER_METRICS)
    parser.add_argument("--context-baseline-metrics", type=Path, default=DEFAULT_CONTEXT_BASELINE_METRICS)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    transformer_metrics = load_json(args.transformer_metrics)
    context_metrics = load_json(args.context_baseline_metrics)
    findings: list[dict[str, Any]] = []
    if transformer_metrics:
        findings.extend(classify_gap(dict(transformer_metrics.get("validation") or {}), dict(transformer_metrics.get("test") or {})))
        findings.extend(classify_baseline(transformer_metrics))
    else:
        findings.append(
            {
                "severity": "high",
                "type": "missing_metrics",
                "message": f"metrics file not found: {args.transformer_metrics}",
            }
        )
    findings.extend(classify_context_baseline(context_metrics))

    report = {
        "context_baseline_metrics": str(args.context_baseline_metrics.relative_to(PROJECT_ROOT))
        if args.context_baseline_metrics.is_relative_to(PROJECT_ROOT)
        else str(args.context_baseline_metrics),
        "transformer_metrics": str(args.transformer_metrics.relative_to(PROJECT_ROOT))
        if args.transformer_metrics.is_relative_to(PROJECT_ROOT)
        else str(args.transformer_metrics),
        "findings": findings,
        "recommendation": summarize_recommendation(findings),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    if report["recommendation"] == "do_not_adopt_runtime":
        sys.exit(2)


if __name__ == "__main__":
    main()

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import time
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

DEFAULT_INPUT = PROJECT_ROOT / "data" / "eval" / "tourism_hard_nlu_holdout_20260518.jsonl"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "data" / "generated" / "tour_api" / "hard_nlu_model_compare_20260518"


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        for row in rows:
            file.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def metrics(rows: list[dict[str, Any]], predictions: dict[str, set[str]]) -> dict[str, Any]:
    exact = tp = fp = fn = 0
    category_summary: dict[str, dict[str, int]] = {}
    mismatches: list[dict[str, Any]] = []
    for row in rows:
        expected = set(row["expected_conditions"])
        predicted = set(predictions.get(row["id"], set()))
        passed = expected == predicted
        exact += int(passed)
        tp += len(expected & predicted)
        fp += len(predicted - expected)
        fn += len(expected - predicted)
        category = str(row.get("category") or "unknown")
        category_summary.setdefault(category, {"rows": 0, "passed": 0})
        category_summary[category]["rows"] += 1
        category_summary[category]["passed"] += int(passed)
        if not passed and len(mismatches) < 60:
            mismatches.append(
                {
                    "id": row["id"],
                    "category": category,
                    "text": row["text"],
                    "expected": sorted(expected),
                    "predicted": sorted(predicted),
                    "missing": sorted(expected - predicted),
                    "extra": sorted(predicted - expected),
                }
            )
    precision = tp / (tp + fp) if tp + fp else 1.0
    recall = tp / (tp + fn) if tp + fn else 1.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {
        "rows": len(rows),
        "exact_match": exact / len(rows) if rows else 0.0,
        "micro_precision": precision,
        "micro_recall": recall,
        "micro_f1": f1,
        "false_positive": fp,
        "false_negative": fn,
        "category_summary": {
            key: {**value, "pass_rate": value["passed"] / value["rows"] if value["rows"] else 0.0}
            for key, value in sorted(category_summary.items())
        },
        "sample_mismatches": mismatches,
    }


def run_eval(rows: list[dict[str, Any]], model_dir: str | None, metrics_path: Path | None) -> dict[str, Any]:
    from app.core.config import Settings
    from app.services.korean_external_corrector import ExternalCorrectionResult
    from app.services.tourism_condition_transformer import TourismConditionTransformer
    from app.services.tourism_query_service import CONDITION_KEYWORDS, TourismQueryService

    class QuickSpacerCorrector:
        def __init__(self):
            from quickspacer import Spacer

            self.spacer = Spacer()

        def correct(self, text: str, protected_terms: list[str]) -> ExternalCorrectionResult:
            spaced = self.spacer.space([text])
            corrected = str(spaced[0]).strip() if isinstance(spaced, list) and spaced else str(text)
            return ExternalCorrectionResult(
                raw_text=text,
                corrected_text=corrected,
                accepted=True,
                provider="quickspacer",
                model="quickspacer",
                reason="candidate",
                damaged_terms=[],
            )

    started = time.perf_counter()
    rule_service = TourismQueryService(enable_external_correction=False)
    et5_service = TourismQueryService(enable_external_correction=True)
    quick_service = TourismQueryService(external_corrector=QuickSpacerCorrector(), enable_external_correction=True)
    settings_kwargs: dict[str, Any] = {"tourism_condition_transformer_enabled": True}
    if model_dir:
        settings_kwargs["tourism_condition_transformer_model"] = model_dir
    if metrics_path:
        settings_kwargs["tourism_condition_transformer_metrics_path"] = metrics_path
    transformer = TourismConditionTransformer(Settings(**settings_kwargs), labels=list(CONDITION_KEYWORDS))

    predictions: dict[str, dict[str, set[str]]] = {
        "rule_parser": {},
        "et5_local": {},
        "quickspacer": {},
        "roberta_only": {},
        "rule_roberta_union": {},
    }
    detail_rows: list[dict[str, Any]] = []
    for row in rows:
        text = row["text"]
        rule = set(rule_service.extract(text).get("conditions") or [])
        et5 = set(et5_service.extract(text).get("conditions") or [])
        quick = set(quick_service.extract(text).get("conditions") or [])
        roberta = set(transformer.predict(text).get("labels") or [])
        predictions["rule_parser"][row["id"]] = rule
        predictions["et5_local"][row["id"]] = et5
        predictions["quickspacer"][row["id"]] = quick
        predictions["roberta_only"][row["id"]] = roberta
        predictions["rule_roberta_union"][row["id"]] = rule | roberta
        detail_rows.append(
            {
                "id": row["id"],
                "category": row.get("category"),
                "text": text,
                "expected": row["expected_conditions"],
                "rule_parser": sorted(rule),
                "et5_local": sorted(et5),
                "quickspacer": sorted(quick),
                "roberta_only": sorted(roberta),
                "rule_roberta_union": sorted(rule | roberta),
            }
        )
    return {
        "metrics": {name: metrics(rows, prediction) for name, prediction in predictions.items()},
        "details": detail_rows,
        "duration_ms": round((time.perf_counter() - started) * 1000, 1),
        "model_dir": model_dir,
        "metrics_path": str(metrics_path) if metrics_path else None,
    }


def write_markdown(path: Path, report: dict[str, Any]) -> None:
    lines = [
        "# Hard NLU Model Comparison",
        "",
        f"- input: `{Path(report['input']).name}`",
        f"- rows: {report['rows']}",
        f"- model_dir: `{report.get('model_dir')}`",
        "",
        "| variant | exact | micro-F1 | precision | recall | FP | FN |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for name, item in report["metrics"].items():
        lines.append(
            f"| {name} | {item['exact_match']:.4f} | {item['micro_f1']:.4f} | "
            f"{item['micro_precision']:.4f} | {item['micro_recall']:.4f} | "
            f"{item['false_positive']} | {item['false_negative']} |"
        )
    lines.extend(["", "## Top Mismatches", ""])
    for name, item in report["metrics"].items():
        lines.append(f"### {name}")
        for mismatch in item["sample_mismatches"][:12]:
            lines.append(
                f"- {mismatch['id']} `{mismatch['text']}` expected={mismatch['expected']} predicted={mismatch['predicted']}"
            )
        lines.append("")
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate hard NLU holdout across parser/corrector/Transformer candidates.")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--model-dir", default=None)
    parser.add_argument("--metrics-path", type=Path, default=None)
    args = parser.parse_args()
    rows = load_jsonl(args.input)
    result = run_eval(rows, args.model_dir, args.metrics_path)
    report = {
        "input": str(args.input),
        "rows": len(rows),
        "model_dir": result["model_dir"],
        "metrics_path": result["metrics_path"],
        "duration_ms": result["duration_ms"],
        "metrics": result["metrics"],
    }
    args.output_dir.mkdir(parents=True, exist_ok=True)
    write_json(args.output_dir / "summary.json", report)
    write_jsonl(args.output_dir / "details.jsonl", result["details"])
    write_markdown(args.output_dir / "summary.md", report)
    summary_path = (args.output_dir / "summary.json").resolve()
    print(json.dumps({"output": str(summary_path.relative_to(PROJECT_ROOT))}, ensure_ascii=False))


if __name__ == "__main__":
    main()

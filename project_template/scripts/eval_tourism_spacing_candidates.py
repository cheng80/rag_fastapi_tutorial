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

from app.services.korean_query_normalizer import KoreanQueryNormalizer  # noqa: E402
from app.services.tourism_query_service import AREA_CODES, CONDITION_KEYWORDS, TourismQueryService  # noqa: E402


DEFAULT_INPUT = PROJECT_ROOT / "data" / "processed" / "tourism_keyword_variants_20260518_5000.valid.jsonl"
DEFAULT_REPORT = PROJECT_ROOT / "data" / "generated" / "tour_api" / "keyword_variant_reports" / "spacing_candidate_coverage_20260518.json"


def load_rows(path: Path, limit: int | None) -> list[dict[str, Any]]:
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        rows.append(json.loads(line))
        if limit and len(rows) >= limit:
            break
    return rows


def condition_labels(text: str, normalizer: KoreanQueryNormalizer, service: TourismQueryService) -> list[str]:
    region_names = list(service.region_index) + list(AREA_CODES)
    normalized = normalizer.normalize(text, region_names=region_names)
    candidates = [text, normalized.normalized_text, normalized.rewrite_text]
    labels = [
        label
        for label, keywords in CONDITION_KEYWORDS.items()
        if any(keyword in candidate for keyword in keywords for candidate in candidates)
    ]
    return labels


def matches(expected: list[str], predicted: list[str]) -> bool:
    return set(expected) == set(predicted)


def summarize(rows: list[dict[str, Any]], predictions: dict[str, list[str]]) -> dict[str, Any]:
    exact = 0
    by_variant: dict[str, dict[str, int]] = {}
    for row in rows:
        expected = row.get("expected_conditions") or []
        predicted = predictions[row["id"]]
        ok = matches(expected, predicted)
        exact += int(ok)
        bucket = by_variant.setdefault(str(row.get("variant_type") or "unknown"), {"rows": 0, "exact": 0})
        bucket["rows"] += 1
        bucket["exact"] += int(ok)
    return {
        "rows": len(rows),
        "exact_rows": exact,
        "exact_accuracy": exact / len(rows) if rows else 0.0,
        "by_variant_type": {
            key: {**value, "accuracy": value["exact"] / value["rows"] if value["rows"] else 0.0}
            for key, value in sorted(by_variant.items())
        },
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate quickspacer as a spacing-only candidate for tourism keyword coverage.")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--batch-size", type=int, default=128)
    return parser.parse_args()


def main() -> None:
    try:
        from quickspacer import Spacer
    except ImportError as exc:
        raise SystemExit("Install quickspacer first: .venv/bin/python -m pip install quickspacer") from exc

    args = parse_args()
    rows = load_rows(args.input, args.limit)
    service = TourismQueryService(enable_external_correction=False)
    normalizer = KoreanQueryNormalizer()
    baseline_predictions = {
        row["id"]: condition_labels(str(row.get("user_query") or ""), normalizer, service)
        for row in rows
    }
    spacer = Spacer(level=1)
    texts = [str(row.get("user_query") or "") for row in rows]
    started = time.perf_counter()
    spaced_texts: list[str] = []
    for index in range(0, len(texts), args.batch_size):
        spaced_texts.extend(spacer.space(texts[index : index + args.batch_size], batch_size=args.batch_size))
    latency_ms = (time.perf_counter() - started) * 1000
    spaced_predictions = {
        row["id"]: condition_labels(spaced_text, normalizer, service)
        for row, spaced_text in zip(rows, spaced_texts, strict=True)
    }

    improved = []
    regressed = []
    for row, spaced_text in zip(rows, spaced_texts, strict=True):
        expected = row.get("expected_conditions") or []
        baseline_ok = matches(expected, baseline_predictions[row["id"]])
        spaced_ok = matches(expected, spaced_predictions[row["id"]])
        if spaced_ok and not baseline_ok and len(improved) < 20:
            improved.append(
                {
                    "id": row["id"],
                    "user_query": row.get("user_query"),
                    "spaced_text": spaced_text,
                    "expected": expected,
                    "baseline": baseline_predictions[row["id"]],
                    "spaced": spaced_predictions[row["id"]],
                }
            )
        if baseline_ok and not spaced_ok and len(regressed) < 20:
            regressed.append(
                {
                    "id": row["id"],
                    "user_query": row.get("user_query"),
                    "spaced_text": spaced_text,
                    "expected": expected,
                    "baseline": baseline_predictions[row["id"]],
                    "spaced": spaced_predictions[row["id"]],
                }
            )

    report = {
        "input": str(args.input.relative_to(PROJECT_ROOT)),
        "rows": len(rows),
        "baseline": summarize(rows, baseline_predictions),
        "quickspacer": summarize(rows, spaced_predictions),
        "latency": {
            "total_ms": round(latency_ms, 4),
            "mean_ms": round(latency_ms / len(rows), 4) if rows else 0.0,
        },
        "improved_samples": improved,
        "regressed_samples": regressed,
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()

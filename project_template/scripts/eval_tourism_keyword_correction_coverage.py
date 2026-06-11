from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import sys
from time import perf_counter
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.core.config import get_settings  # noqa: E402
from app.services.korean_external_corrector import DEFAULT_PROTECTED_TERMS, ExternalKoreanCorrector  # noqa: E402
from app.services.korean_query_normalizer import KoreanQueryNormalizer  # noqa: E402
from app.services.tourism_query_service import AREA_CODES, CONDITION_KEYWORDS, DEFAULT_AREA_CODE_CACHE_PATH  # noqa: E402


DEFAULT_INPUT = PROJECT_ROOT / "data" / "processed" / "tourism_keyword_variants_20260518_5000.valid.jsonl"
DEFAULT_REPORT = PROJECT_ROOT / "data" / "generated" / "tour_api" / "keyword_variant_reports" / "keyword_correction_coverage_20260518.json"
DEFAULT_SAMPLES = PROJECT_ROOT / "data" / "generated" / "tour_api" / "keyword_variant_reports" / "keyword_correction_coverage_20260518_samples.jsonl"


def project_relative(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(PROJECT_ROOT))
    except ValueError:
        return str(path)


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(json.dumps(row, ensure_ascii=False, sort_keys=True) for row in rows) + "\n",
        encoding="utf-8",
    )


def load_region_names() -> list[str]:
    if not DEFAULT_AREA_CODE_CACHE_PATH.exists():
        return list(AREA_CODES)
    try:
        payload = json.loads(DEFAULT_AREA_CODE_CACHE_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return list(AREA_CODES)
    region_index = payload.get("region_index")
    if not isinstance(region_index, dict):
        return list(AREA_CODES)
    return list(region_index) + list(AREA_CODES)


def parse_conditions(candidates: list[str]) -> list[str]:
    return [
        label
        for label, keywords in CONDITION_KEYWORDS.items()
        if any(keyword in candidate for keyword in keywords for candidate in candidates)
    ]


def manual_conditions(normalizer: KoreanQueryNormalizer, region_names: list[str], text: str) -> list[str]:
    normalized = normalizer.normalize(text, region_names=region_names)
    candidates = list(dict.fromkeys([text, normalized.normalized_text, normalized.rewrite_text]))
    return parse_conditions(candidates)


def corrected_conditions(
    normalizer: KoreanQueryNormalizer,
    corrector: ExternalKoreanCorrector,
    region_names: list[str],
    text: str,
) -> tuple[list[str], dict[str, Any]]:
    normalized = normalizer.normalize(text, region_names=region_names)
    correction = corrector.correct(text, protected_terms=DEFAULT_PROTECTED_TERMS + region_names)
    candidates = [text, normalized.normalized_text, normalized.rewrite_text]
    if correction.accepted:
        corrected_normalized = normalizer.normalize(correction.corrected_text, region_names=region_names)
        candidates.extend(
            [
                correction.corrected_text,
                corrected_normalized.normalized_text,
                corrected_normalized.rewrite_text,
            ]
        )
    candidates = [candidate for candidate in dict.fromkeys(candidates) if candidate]
    return parse_conditions(candidates), {
        "accepted": correction.accepted,
        "reason": correction.reason,
        "corrected_text": correction.corrected_text,
        "damaged_terms": correction.damaged_terms or [],
    }


def summarize(rows: list[dict[str, Any]], key: str) -> dict[str, Any]:
    total = len(rows)
    exact = sum(1 for row in rows if row[f"{key}_matches_expected"])
    promote_rows = [row for row in rows if row["should_promote"]]
    non_promote_rows = [row for row in rows if not row["should_promote"]]
    by_type = Counter(row["variant_type"] for row in rows)
    by_type_exact = Counter(row["variant_type"] for row in rows if row[f"{key}_matches_expected"])
    by_label = Counter(row["condition_label"] for row in rows)
    by_label_exact = Counter(row["condition_label"] for row in rows if row[f"{key}_matches_expected"])
    return {
        "rows": total,
        "exact_rows": exact,
        "exact_accuracy": exact / total if total else 0.0,
        "should_promote_rows": len(promote_rows),
        "should_promote_exact_rows": sum(1 for row in promote_rows if row[f"{key}_matches_expected"]),
        "should_promote_exact_accuracy": (
            sum(1 for row in promote_rows if row[f"{key}_matches_expected"]) / len(promote_rows) if promote_rows else 0.0
        ),
        "non_promote_rows": len(non_promote_rows),
        "non_promote_exact_rows": sum(1 for row in non_promote_rows if row[f"{key}_matches_expected"]),
        "non_promote_exact_accuracy": (
            sum(1 for row in non_promote_rows if row[f"{key}_matches_expected"]) / len(non_promote_rows)
            if non_promote_rows
            else 0.0
        ),
        "rows_with_missing_conditions": sum(1 for row in rows if row[f"{key}_missing_conditions"]),
        "rows_with_extra_conditions": sum(1 for row in rows if row[f"{key}_extra_conditions"]),
        "by_variant_type": {
            variant_type: {
                "rows": by_type[variant_type],
                "exact_rows": by_type_exact[variant_type],
                "accuracy": by_type_exact[variant_type] / by_type[variant_type],
            }
            for variant_type in sorted(by_type)
        },
        "by_condition_label": {
            label: {
                "rows": by_label[label],
                "exact_rows": by_label_exact[label],
                "accuracy": by_label_exact[label] / by_label[label],
            }
            for label in sorted(by_label)
        },
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Compare manual keyword parsing with local Korean correction candidate parsing.")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--samples", type=Path, default=DEFAULT_SAMPLES)
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--progress-every", type=int, default=100)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    rows = load_jsonl(args.input)
    if args.limit:
        rows = rows[: args.limit]
    normalizer = KoreanQueryNormalizer()
    corrector = ExternalKoreanCorrector(get_settings())
    region_names = load_region_names()
    evaluated: list[dict[str, Any]] = []
    started_at = perf_counter()
    for index, row in enumerate(rows, start=1):
        expected = set(row["expected_conditions"])
        manual = manual_conditions(normalizer, region_names, row["user_query"])
        corrected, correction_payload = corrected_conditions(normalizer, corrector, region_names, row["user_query"])
        manual_set = set(manual)
        corrected_set = set(corrected)
        evaluated.append(
            {
                "id": row["id"],
                "condition_label": row["condition_label"],
                "variant_type": row["variant_type"],
                "should_promote": row["should_promote"],
                "user_query": row["user_query"],
                "expected_conditions": row["expected_conditions"],
                "manual_conditions": manual,
                "manual_matches_expected": manual_set == expected,
                "manual_missing_conditions": sorted(expected - manual_set),
                "manual_extra_conditions": sorted(manual_set - expected),
                "corrected_conditions": corrected,
                "corrected_matches_expected": corrected_set == expected,
                "corrected_missing_conditions": sorted(expected - corrected_set),
                "corrected_extra_conditions": sorted(corrected_set - expected),
                "correction": correction_payload,
            }
        )
        if args.progress_every and index % args.progress_every == 0:
            elapsed = perf_counter() - started_at
            rate = index / elapsed if elapsed else 0.0
            remaining = (len(rows) - index) / rate if rate else 0.0
            print(
                json.dumps(
                    {
                        "progress": index,
                        "total": len(rows),
                        "elapsed_seconds": round(elapsed, 1),
                        "rows_per_second": round(rate, 3),
                        "eta_seconds": round(remaining, 1),
                    },
                    ensure_ascii=False,
                    sort_keys=True,
                ),
                flush=True,
            )

    improved = [
        row
        for row in evaluated
        if not row["manual_matches_expected"] and row["corrected_matches_expected"]
    ]
    regressed = [
        row
        for row in evaluated
        if row["manual_matches_expected"] and not row["corrected_matches_expected"]
    ]
    report = {
        "input": project_relative(args.input),
        "rows": len(evaluated),
        "manual": summarize(evaluated, "manual"),
        "corrected": summarize(evaluated, "corrected"),
        "external_correction_accepted_rows": sum(1 for row in evaluated if row["correction"]["accepted"]),
        "external_correction_rejected_rows": sum(1 for row in evaluated if not row["correction"]["accepted"]),
        "improved_rows": len(improved),
        "regressed_rows": len(regressed),
        "improved_samples": improved[:20],
        "regressed_samples": regressed[:20],
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_jsonl(args.samples, evaluated)
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()

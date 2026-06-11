from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import re
import sys
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.services.korean_query_normalizer import KoreanQueryNormalizer  # noqa: E402
from app.services.tourism_query_service import AREA_CODES, CONDITION_KEYWORDS, DEFAULT_AREA_CODE_CACHE_PATH  # noqa: E402


DEFAULT_INPUT = (
    PROJECT_ROOT
    / "data"
    / "generated"
    / "tour_api"
    / "keyword_variant_batches"
    / "keyword_variant_batch_20260518_gpt_style_2400.raw.jsonl"
)
DEFAULT_OUTPUT = PROJECT_ROOT / "data" / "processed" / "tourism_keyword_variants_20260518.valid.jsonl"
DEFAULT_REPORT = PROJECT_ROOT / "data" / "generated" / "tour_api" / "keyword_variant_reports" / "keyword_variant_20260518_report.json"
DEFAULT_REVIEW_QUEUE = PROJECT_ROOT / "data" / "generated" / "tour_api" / "keyword_variant_reports" / "keyword_variant_20260518_review_queue.jsonl"

REQUIRED_FIELDS = {
    "id",
    "canonical_term",
    "condition_label",
    "variant",
    "variant_type",
    "user_query",
    "expected_conditions",
    "should_promote",
    "risk_tags",
    "rationale",
}
ALLOWED_CONDITIONS = {
    "휠체어",
    "유모차",
    "화장실",
    "주차",
    "엘리베이터",
    "접근로",
    "시각장애",
    "청각장애",
    "보조견",
    "고령자",
    "none",
    "ambiguous",
}
ALLOWED_VARIANT_TYPES = {"typo", "spacing", "abbreviation", "synonym", "paraphrase", "negative", "ambiguous"}


def normalize_text(text: str) -> str:
    normalized = re.sub(r"\s+", "", text.strip().lower())
    return re.sub(r"[^\w가-힣]", "", normalized)


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"{path}:{line_no}: invalid JSON: {exc}") from exc
        payload["_line_no"] = line_no
        rows.append(payload)
    return rows


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        for row in rows:
            file.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def project_relative(path: Path) -> str:
    resolved = path.resolve()
    try:
        return str(resolved.relative_to(PROJECT_ROOT))
    except ValueError:
        return str(path)


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


def current_parser_conditions(normalizer: KoreanQueryNormalizer, region_names: list[str], text: str) -> list[str]:
    normalized = normalizer.normalize(text, region_names=region_names)
    candidates = list(dict.fromkeys([text, normalized.normalized_text, normalized.rewrite_text]))
    return [
        label
        for label, keywords in CONDITION_KEYWORDS.items()
        if any(keyword in candidate for keyword in keywords for candidate in candidates)
    ]


def validate_row(
    row: dict[str, Any],
    seen_texts: set[str],
    normalizer: KoreanQueryNormalizer,
    region_names: list[str],
) -> tuple[dict[str, Any] | None, list[str]]:
    errors: list[str] = []
    missing = REQUIRED_FIELDS - set(row)
    extra = set(row) - REQUIRED_FIELDS - {"source", "_line_no"}
    if missing:
        errors.append(f"missing_fields={sorted(missing)}")
    if extra:
        errors.append(f"extra_fields={sorted(extra)}")

    condition = str(row.get("condition_label") or "")
    variant_type = str(row.get("variant_type") or "")
    if condition not in ALLOWED_CONDITIONS:
        errors.append(f"invalid_condition={condition}")
    if variant_type not in ALLOWED_VARIANT_TYPES:
        errors.append(f"invalid_variant_type={variant_type}")

    expected_conditions = row.get("expected_conditions")
    if not isinstance(expected_conditions, list):
        errors.append("expected_conditions_not_list")
        expected_conditions = []
    invalid_expected = [item for item in expected_conditions if item not in CONDITION_KEYWORDS]
    if invalid_expected:
        errors.append(f"invalid_expected_conditions={invalid_expected}")
    if condition in {"none", "ambiguous"} and expected_conditions:
        errors.append("none_or_ambiguous_must_not_have_expected_conditions")
    if condition not in {"none", "ambiguous"} and condition not in expected_conditions:
        errors.append("condition_not_in_expected_conditions")
    if not isinstance(row.get("should_promote"), bool):
        errors.append("should_promote_not_bool")
    if not isinstance(row.get("risk_tags"), list):
        errors.append("risk_tags_not_list")

    text = str(row.get("user_query") or "").strip()
    variant = str(row.get("variant") or "").strip()
    canonical = str(row.get("canonical_term") or "").strip()
    if len(text) < 4:
        errors.append("user_query_too_short")
    if not variant:
        errors.append("missing_variant")
    if not canonical:
        errors.append("missing_canonical_term")
    text_key = normalize_text(text)
    if text_key in seen_texts:
        errors.append("duplicate_user_query")

    if errors:
        return None, errors

    seen_texts.add(text_key)
    parser_conditions = current_parser_conditions(normalizer, region_names, text)
    expected_set = set(expected_conditions)
    parser_set = set(parser_conditions)
    cleaned = {
        "id": str(row["id"]),
        "canonical_term": canonical,
        "condition_label": condition,
        "variant": variant,
        "variant_type": variant_type,
        "user_query": text,
        "expected_conditions": [condition for condition in CONDITION_KEYWORDS if condition in expected_set],
        "should_promote": bool(row["should_promote"]),
        "risk_tags": [str(tag).strip() for tag in row["risk_tags"] if str(tag).strip()],
        "rationale": str(row["rationale"]).strip(),
        "source": str(row.get("source") or "gpt_keyword_variant_generation"),
        "parser_conditions": parser_conditions,
        "parser_matches_expected": parser_set == expected_set,
        "parser_missing_conditions": sorted(expected_set - parser_set),
        "parser_extra_conditions": sorted(parser_set - expected_set),
    }
    return cleaned, []


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate GPT-generated tourism keyword variant JSONL.")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--review-queue", type=Path, default=DEFAULT_REVIEW_QUEUE)
    parser.add_argument("--min-rows", type=int, default=1)
    parser.add_argument("--fail-on-reject", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    rows = load_jsonl(args.input)
    normalizer = KoreanQueryNormalizer()
    region_names = load_region_names()
    seen_texts: set[str] = set()
    valid_rows: list[dict[str, Any]] = []
    rejected_rows: list[dict[str, Any]] = []
    for row in rows:
        cleaned, errors = validate_row(row, seen_texts, normalizer, region_names)
        if cleaned is None:
            rejected_rows.append({"line": row.get("_line_no"), "id": row.get("id"), "errors": errors, "user_query": row.get("user_query")})
            continue
        valid_rows.append(cleaned)

    review_rows = [
        row
        for row in valid_rows
        if row["should_promote"] and not row["parser_matches_expected"]
    ]
    write_jsonl(args.output, valid_rows)
    write_jsonl(args.review_queue, review_rows)
    report = {
        "input": project_relative(args.input),
        "output": project_relative(args.output),
        "review_queue": project_relative(args.review_queue),
        "input_rows": len(rows),
        "valid_rows": len(valid_rows),
        "rejected_rows": len(rejected_rows),
        "parser_exact_rows": sum(1 for row in valid_rows if row["parser_matches_expected"]),
        "parser_mismatch_rows": sum(1 for row in valid_rows if not row["parser_matches_expected"]),
        "promote_candidates": sum(1 for row in valid_rows if row["should_promote"]),
        "promote_candidate_mismatches": len(review_rows),
        "condition_counts": dict(Counter(row["condition_label"] for row in valid_rows)),
        "variant_type_counts": dict(Counter(row["variant_type"] for row in valid_rows)),
        "top_missing_conditions": Counter(condition for row in valid_rows for condition in row["parser_missing_conditions"]).most_common(20),
        "rejected_samples": rejected_rows[:30],
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    if len(valid_rows) < args.min_rows or (args.fail_on_reject and rejected_rows):
        sys.exit(2)


if __name__ == "__main__":
    main()

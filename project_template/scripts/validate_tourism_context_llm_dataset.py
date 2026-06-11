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

from app.services.tourism_context_classifier import CONTEXT_LABELS  # noqa: E402


DEFAULT_EXISTING = [
    PROJECT_ROOT / "data" / "processed" / "tourism_context_training.jsonl",
    PROJECT_ROOT / "data" / "eval" / "tourism_context_hard_holdout.jsonl",
]
DEFAULT_OUTPUT = PROJECT_ROOT / "data" / "processed" / "tourism_context_llm_hard_training.valid.jsonl"


REQUIRED_FIELDS = {
    "id",
    "text",
    "labels",
    "category",
    "required_terms",
    "optional_terms",
    "excluded_terms",
    "risk_tags",
    "rationale",
}


def normalize_text(text: str) -> str:
    normalized = re.sub(r"\s+", "", text.strip().lower())
    normalized = re.sub(r"[^\w가-힣]", "", normalized)
    return normalized


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
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


def load_existing_texts(paths: list[Path]) -> set[str]:
    texts: set[str] = set()
    for path in paths:
        if not path.exists():
            continue
        for row in load_jsonl(path):
            text = str(row.get("text") or "").strip()
            if text:
                texts.add(normalize_text(text))
    return texts


def validate_row(row: dict[str, Any], existing_texts: set[str], seen_texts: set[str]) -> tuple[dict[str, Any] | None, list[str]]:
    errors: list[str] = []
    missing = REQUIRED_FIELDS - set(row)
    extra = set(row) - REQUIRED_FIELDS - {"_line_no"}
    if missing:
        errors.append(f"missing_fields={sorted(missing)}")
    if extra:
        errors.append(f"extra_fields={sorted(extra)}")

    text = str(row.get("text") or "").strip()
    if len(text) < 6:
        errors.append("text_too_short")
    normalized = normalize_text(text)
    if normalized in seen_texts:
        errors.append("duplicate_in_input")
    if normalized in existing_texts:
        errors.append("overlaps_existing_train_or_holdout")

    labels = row.get("labels")
    if not isinstance(labels, list):
        errors.append("labels_not_list")
        labels = []
    invalid_labels = [label for label in labels if label not in CONTEXT_LABELS]
    if invalid_labels:
        errors.append(f"invalid_labels={invalid_labels}")
    label_set = set(label for label in labels if label in CONTEXT_LABELS)
    if "strict_and" in label_set and "or_condition" in label_set:
        errors.append("strict_and_and_or_condition_conflict")
    if "soft_and" in label_set and label_set & {
        "strict_and",
        "or_condition",
        "add_condition",
        "replace_condition",
        "exclude_condition",
    }:
        errors.append("soft_and_with_structural_action")

    list_fields = ["required_terms", "optional_terms", "excluded_terms", "risk_tags"]
    for field in list_fields:
        if not isinstance(row.get(field), list):
            errors.append(f"{field}_not_list")
    if not str(row.get("category") or "").strip():
        errors.append("missing_category")
    if not str(row.get("rationale") or "").strip():
        errors.append("missing_rationale")

    if errors:
        return None, errors

    seen_texts.add(normalized)
    cleaned = {
        "id": str(row["id"]),
        "text": text,
        "labels": [label for label in CONTEXT_LABELS if label in label_set],
        "category": f"llm_{str(row['category']).strip()}",
        "required_terms": [str(term).strip() for term in row["required_terms"] if str(term).strip()],
        "optional_terms": [str(term).strip() for term in row["optional_terms"] if str(term).strip()],
        "excluded_terms": [str(term).strip() for term in row["excluded_terms"] if str(term).strip()],
        "risk_tags": [str(term).strip() for term in row["risk_tags"] if str(term).strip()],
        "rationale": str(row["rationale"]).strip(),
        "source": "llm_hard_context_generation",
    }
    return cleaned, []


def count_labels(rows: list[dict[str, Any]]) -> dict[str, int]:
    counts = {label: 0 for label in CONTEXT_LABELS}
    counts["<none>"] = 0
    for row in rows:
        labels = row.get("labels") or []
        if not labels:
            counts["<none>"] += 1
        for label in labels:
            counts[label] += 1
    return counts


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate LLM-generated hard-style tourism context JSONL.")
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--existing", type=Path, action="append", default=list(DEFAULT_EXISTING))
    parser.add_argument("--min-rows", type=int, default=1)
    parser.add_argument("--fail-on-reject", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    rows = load_jsonl(args.input)
    existing_texts = load_existing_texts(args.existing)
    seen_texts: set[str] = set()
    valid_rows: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    for row in rows:
        cleaned, errors = validate_row(row, existing_texts, seen_texts)
        if cleaned is None:
            rejected.append({"line": row.get("_line_no"), "id": row.get("id"), "errors": errors, "text": row.get("text")})
            continue
        valid_rows.append(cleaned)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as file:
        for row in valid_rows:
            file.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")

    category_counts = Counter(str(row.get("category") or "") for row in valid_rows)
    report = {
        "input": str(args.input.relative_to(PROJECT_ROOT)) if args.input.is_relative_to(PROJECT_ROOT) else str(args.input),
        "output": str(args.output.relative_to(PROJECT_ROOT)) if args.output.is_relative_to(PROJECT_ROOT) else str(args.output),
        "input_rows": len(rows),
        "valid_rows": len(valid_rows),
        "rejected_rows": len(rejected),
        "label_counts": count_labels(valid_rows),
        "category_counts": dict(sorted(category_counts.items())),
        "rejected_samples": rejected[:30],
    }
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    if len(valid_rows) < args.min_rows or (args.fail_on_reject and rejected):
        sys.exit(2)


if __name__ == "__main__":
    main()

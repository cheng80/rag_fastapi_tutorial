from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
import sys
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


DEFAULT_INPUT = PROJECT_ROOT / "data" / "processed" / "tourism_keyword_variants_20260518.valid.jsonl"
DEFAULT_OUTPUT = PROJECT_ROOT / "data" / "processed" / "tourism_keyword_promotion_candidates_20260518.json"


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def project_relative(path: Path) -> str:
    resolved = path.resolve()
    try:
        return str(resolved.relative_to(PROJECT_ROOT))
    except ValueError:
        return str(path)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build reviewed promotion candidates from tourism keyword variant data.")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--min-count", type=int, default=1)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    rows = load_jsonl(args.input)
    grouped: dict[str, dict[str, Counter[str]]] = defaultdict(lambda: defaultdict(Counter))
    examples: dict[tuple[str, str, str], list[str]] = defaultdict(list)
    for row in rows:
        if not row.get("should_promote"):
            continue
        if row.get("parser_matches_expected"):
            continue
        missing = row.get("parser_missing_conditions") or []
        if not missing:
            continue
        variant = str(row.get("variant") or "").strip()
        variant_type = str(row.get("variant_type") or "").strip()
        if not variant:
            continue
        for condition in missing:
            grouped[str(condition)][variant_type][variant] += 1
            key = (str(condition), variant_type, variant)
            if len(examples[key]) < 3:
                examples[key].append(str(row.get("user_query") or ""))

    condition_payload: dict[str, dict[str, list[dict[str, Any]]]] = {}
    for condition, by_type in grouped.items():
        condition_payload[condition] = {}
        for variant_type, counter in by_type.items():
            condition_payload[condition][variant_type] = [
                {
                    "variant": variant,
                    "count": count,
                    "examples": examples[(condition, variant_type, variant)],
                }
                for variant, count in counter.most_common()
                if count >= args.min_count
            ]

    output = {
        "input": project_relative(args.input),
        "candidate_policy": "review_before_runtime_dictionary_promotion",
        "conditions": condition_payload,
        "summary": {
            "condition_counts": {
                condition: sum(item["count"] for values in by_type.values() for item in values)
                for condition, by_type in condition_payload.items()
            },
            "variant_type_counts": dict(
                Counter(
                    variant_type
                    for by_type in condition_payload.values()
                    for variant_type, values in by_type.items()
                    for item in values
                    for _ in range(item["count"])
                )
            ),
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    print(
        json.dumps(
            {
                "output": project_relative(args.output),
                "conditions": sorted(condition_payload),
                "summary": output["summary"],
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()

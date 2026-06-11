from __future__ import annotations

import argparse
import json
from pathlib import Path
import random
import re
import sys
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.services.korean_query_normalizer import KoreanQueryNormalizer  # noqa: E402


DEFAULT_KEYWORD_INPUT = PROJECT_ROOT / "data" / "processed" / "tourism_keyword_variants_20260518_5000.valid.jsonl"
DEFAULT_CONTEXT_INPUT = PROJECT_ROOT / "data" / "processed" / "tourism_context_llm_hard_training_20260518_human_light_5000.valid.jsonl"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "data" / "processed" / "korean_correction_finetune"


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.exists():
        return rows
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        for row in rows:
            file.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def compact(text: str) -> str:
    return "".join(str(text or "").split())


def normalize_spaces(text: str) -> str:
    return re.sub(r"\s+", " ", str(text or "").strip())


def keyword_pairs(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    pairs: list[dict[str, Any]] = []
    for row in rows:
        query = normalize_spaces(row.get("user_query") or "")
        variant = normalize_spaces(row.get("variant") or "")
        canonical = normalize_spaces(row.get("canonical_term") or "")
        variant_type = str(row.get("variant_type") or "")
        if not query or not variant or not canonical:
            continue
        if variant_type not in {"typo", "spacing", "abbrev", "compound"}:
            continue
        if variant not in query:
            continue
        target = normalize_spaces(query.replace(variant, canonical))
        if target == query or compact(target) == compact(query):
            continue
        pairs.append(
            {
                "id": row.get("id"),
                "source": query,
                "target": target,
                "origin": "keyword_variant",
                "variant": variant,
                "canonical_term": canonical,
                "variant_type": variant_type,
            }
        )
    return pairs


def normalizer_pairs(rows: list[dict[str, Any]], normalizer: KoreanQueryNormalizer) -> list[dict[str, Any]]:
    pairs: list[dict[str, Any]] = []
    for row in rows:
        text = normalize_spaces(row.get("text") or row.get("user_query") or "")
        if not text:
            continue
        normalized = normalizer.normalize(text)
        if normalized.normalized_text == text:
            continue
        pairs.append(
            {
                "id": row.get("id"),
                "source": text,
                "target": normalized.normalized_text,
                "origin": "domain_normalizer",
                "corrections": normalized.corrections,
                "risk_tags": normalized.risk_tags,
            }
        )
    return pairs


def dedupe_pairs(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[tuple[str, str]] = set()
    deduped: list[dict[str, Any]] = []
    for row in rows:
        key = (row["source"], row["target"])
        if key in seen:
            continue
        seen.add(key)
        deduped.append(row)
    return deduped


def split_pairs(rows: list[dict[str, Any]], validation_ratio: float, seed: int) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    shuffled = list(rows)
    random.Random(seed).shuffle(shuffled)
    validation_size = max(1, int(len(shuffled) * validation_ratio)) if shuffled else 0
    return shuffled[validation_size:], shuffled[:validation_size]


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepare local Korean correction fine-tuning pairs.")
    parser.add_argument("--keyword-input", type=Path, default=DEFAULT_KEYWORD_INPUT)
    parser.add_argument("--context-input", type=Path, default=DEFAULT_CONTEXT_INPUT)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--validation-ratio", type=float, default=0.1)
    parser.add_argument("--seed", type=int, default=20260518)
    args = parser.parse_args()

    normalizer = KoreanQueryNormalizer()
    keyword_rows = load_jsonl(args.keyword_input)
    context_rows = load_jsonl(args.context_input)
    pairs = dedupe_pairs(
        [
            *keyword_pairs(keyword_rows),
            *normalizer_pairs(keyword_rows, normalizer),
            *normalizer_pairs(context_rows, normalizer),
        ]
    )
    train_rows, validation_rows = split_pairs(pairs, args.validation_ratio, args.seed)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    write_jsonl(args.output_dir / "train.jsonl", train_rows)
    write_jsonl(args.output_dir / "validation.jsonl", validation_rows)
    summary = {
        "keyword_input": str(args.keyword_input.relative_to(PROJECT_ROOT)),
        "context_input": str(args.context_input.relative_to(PROJECT_ROOT)),
        "output_dir": str(args.output_dir.relative_to(PROJECT_ROOT)),
        "pairs": len(pairs),
        "train": len(train_rows),
        "validation": len(validation_rows),
        "origins": {
            origin: sum(1 for row in pairs if row.get("origin") == origin)
            for origin in sorted({str(row.get("origin")) for row in pairs})
        },
    }
    (args.output_dir / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

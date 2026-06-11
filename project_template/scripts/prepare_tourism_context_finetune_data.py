from __future__ import annotations

import argparse
import json
from pathlib import Path
import random
import sys
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.services.tourism_context_classifier import CONTEXT_LABELS  # noqa: E402


DEFAULT_TRAIN_INPUT = PROJECT_ROOT / "data" / "processed" / "tourism_context_training.jsonl"
DEFAULT_HOLDOUT_INPUT = PROJECT_ROOT / "data" / "eval" / "tourism_context_hard_holdout.jsonl"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "data" / "processed" / "context_finetune"


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    path = path.resolve()
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        payload = json.loads(line)
        text = str(payload.get("text") or "").strip()
        labels = [label for label in payload.get("labels") or [] if label in CONTEXT_LABELS]
        if not text:
            continue
        rows.append(
            {
                "id": str(payload.get("id") or ""),
                "text": text,
                "labels": sorted(set(labels), key=CONTEXT_LABELS.index),
                "category": str(payload.get("category") or ""),
                "template_family": str(payload.get("template_family") or payload.get("category") or ""),
                "risk_tags": list(payload.get("risk_tags") or []),
                "source": str(path.relative_to(PROJECT_ROOT)),
            }
        )
    return rows


def with_vectors(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for row in rows:
        labels = set(row["labels"])
        payload = dict(row)
        payload["label_vector"] = [1 if label in labels else 0 for label in CONTEXT_LABELS]
        payload["label_text"] = ",".join(row["labels"])
        result.append(payload)
    return result


def split_train_validation(rows: list[dict[str, Any]], validation_ratio: float, seed: int) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    if validation_ratio <= 0:
        train = sorted(rows, key=lambda row: (row["source"], row["id"], row["text"]))
        return train, []

    rng = random.Random(seed)
    by_category: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        by_category.setdefault(row["category"], []).append(row)

    train: list[dict[str, Any]] = []
    validation: list[dict[str, Any]] = []
    for category_rows in by_category.values():
        shuffled = list(category_rows)
        rng.shuffle(shuffled)
        validation_count = max(1, int(len(shuffled) * validation_ratio)) if len(shuffled) > 1 else 0
        validation.extend(shuffled[:validation_count])
        train.extend(shuffled[validation_count:])

    train.sort(key=lambda row: (row["source"], row["id"], row["text"]))
    validation.sort(key=lambda row: (row["source"], row["id"], row["text"]))
    return train, validation


def assert_no_text_overlap(train: list[dict[str, Any]], holdout: list[dict[str, Any]]) -> None:
    train_texts = {"".join(str(row.get("text") or "").split()).lower() for row in train}
    overlaps = [
        row
        for row in holdout
        if "".join(str(row.get("text") or "").split()).lower() in train_texts
    ]
    if overlaps:
        sample = overlaps[0]
        raise ValueError(f"train/test text overlap detected: {sample.get('id')} {sample.get('text')}")


def assert_no_family_overlap(train: list[dict[str, Any]], validation: list[dict[str, Any]]) -> None:
    train_families = {
        str(row.get("template_family") or row.get("category") or "")
        for row in train
        if row.get("template_family") or row.get("category")
    }
    overlaps = [
        str(row.get("template_family") or row.get("category") or "")
        for row in validation
        if str(row.get("template_family") or row.get("category") or "") in train_families
    ]
    if overlaps:
        raise ValueError(f"train/validation template_family overlap detected: {sorted(set(overlaps))[:5]}")


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
    parser = argparse.ArgumentParser(description="Prepare context classifier data for KoBERT/KLUE-RoBERTa pilot fine-tuning.")
    parser.add_argument("--train-input", type=Path, default=DEFAULT_TRAIN_INPUT)
    parser.add_argument("--extra-train-input", type=Path, action="append", default=[])
    parser.add_argument("--hard-validation-input", type=Path, action="append", default=[])
    parser.add_argument("--holdout-input", type=Path, default=DEFAULT_HOLDOUT_INPUT)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--validation-ratio", type=float, default=0.15)
    parser.add_argument(
        "--strict-family-split",
        action="store_true",
        help="Fail when validation rows share template_family/category with train rows.",
    )
    parser.add_argument("--seed", type=int, default=20260517)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    source_train = load_jsonl(args.train_input)
    for extra_path in args.extra_train_input:
        source_train.extend(load_jsonl(extra_path))
    holdout = load_jsonl(args.holdout_input)
    assert_no_text_overlap(source_train, holdout)
    train, validation = split_train_validation(source_train, args.validation_ratio, args.seed)
    for hard_validation_path in args.hard_validation_input:
        hard_validation_rows = load_jsonl(hard_validation_path)
        assert_no_text_overlap(hard_validation_rows, holdout)
        validation.extend(hard_validation_rows)
    validation.sort(key=lambda row: (row["source"], row["id"], row["text"]))
    assert_no_text_overlap(train, validation)
    if args.strict_family_split:
        assert_no_family_overlap(train, validation)

    outputs = {
        "train": args.output_dir / "train.jsonl",
        "validation": args.output_dir / "validation.jsonl",
        "test": args.output_dir / "test.jsonl",
        "labels": args.output_dir / "labels.json",
    }
    write_jsonl(outputs["train"], with_vectors(train))
    write_jsonl(outputs["validation"], with_vectors(validation))
    write_jsonl(outputs["test"], with_vectors(holdout))
    outputs["labels"].write_text(json.dumps({"labels": CONTEXT_LABELS}, ensure_ascii=False, indent=2), encoding="utf-8")

    summary = {
        "train_rows": len(train),
        "source_train_rows": len(source_train),
        "extra_train_inputs": [project_relative(path) for path in args.extra_train_input],
        "hard_validation_inputs": [project_relative(path) for path in args.hard_validation_input],
        "validation_rows": len(validation),
        "test_rows": len(holdout),
        "strict_family_split": bool(args.strict_family_split),
        "labels": CONTEXT_LABELS,
        "train_label_counts": count_labels(train),
        "validation_label_counts": count_labels(validation),
        "test_label_counts": count_labels(holdout),
        "outputs": {name: project_relative(path) for name, path in outputs.items()},
    }
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()

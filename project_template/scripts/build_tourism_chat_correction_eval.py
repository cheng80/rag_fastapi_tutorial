from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.eval_korean_correction_candidates import (  # noqa: E402
    DEFAULT_HF_MODEL,
    HuggingFaceTypoCorrector,
    PROTECTED_TERMS,
    damaged_terms,
    load_region_terms,
    project_relative,
)


DEFAULT_INPUT = PROJECT_ROOT / "data" / "eval" / "tourism_context_blind_chat_eval_v2.jsonl"
DEFAULT_OUTPUT = PROJECT_ROOT / "data" / "generated" / "tour_api" / "korean_correction_candidates" / "tourism_context_blind_chat_eval_v2_corrected.jsonl"
DEFAULT_AUDIT_OUTPUT = PROJECT_ROOT / "data" / "generated" / "tour_api" / "korean_correction_candidates" / "tourism_context_blind_chat_eval_v2_corrected_audit.json"


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        for row in rows:
            file.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def correct_message(
    text: str,
    corrector: HuggingFaceTypoCorrector,
    protected_terms: list[str],
) -> tuple[str, dict[str, Any]]:
    corrected = corrector(text)
    damage = damaged_terms(text, corrected, protected_terms)
    accepted = not damage
    return (
        corrected if accepted else text,
        {
            "raw": text,
            "corrected": corrected,
            "accepted": accepted,
            "damaged_terms": damage,
        },
    )


def build_corrected_rows(
    rows: list[dict[str, Any]],
    corrector: HuggingFaceTypoCorrector,
    protected_terms: list[str],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    corrected_rows: list[dict[str, Any]] = []
    audit_rows: list[dict[str, Any]] = []
    for row in rows:
        next_row = json.loads(json.dumps(row, ensure_ascii=False))
        item_audit: dict[str, Any] = {"id": row.get("id"), "messages": []}
        if "message" in next_row:
            next_row["message"], audit = correct_message(str(next_row["message"]), corrector, protected_terms)
            item_audit["messages"].append(audit)
        for turn in next_row.get("turns") or []:
            if not isinstance(turn, dict) or "message" not in turn:
                continue
            turn["message"], audit = correct_message(str(turn["message"]), corrector, protected_terms)
            item_audit["messages"].append(audit)
        corrected_rows.append(next_row)
        audit_rows.append(item_audit)
    return corrected_rows, audit_rows


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a corrected copy of a tourism chat eval JSONL for candidate comparison.")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--audit-output", type=Path, default=DEFAULT_AUDIT_OUTPUT)
    parser.add_argument("--hf-model", default=DEFAULT_HF_MODEL)
    parser.add_argument("--device", default="auto")
    parser.add_argument("--max-length", type=int, default=128)
    parser.add_argument("--num-beams", type=int, default=3)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    rows = load_jsonl(args.input)
    corrector = HuggingFaceTypoCorrector(
        model_name=args.hf_model,
        device=args.device,
        max_length=args.max_length,
        num_beams=args.num_beams,
    )
    protected_terms = sorted(set(PROTECTED_TERMS + load_region_terms()), key=len, reverse=True)
    corrected_rows, audit_rows = build_corrected_rows(rows, corrector, protected_terms)
    write_jsonl(args.output, corrected_rows)
    args.audit_output.parent.mkdir(parents=True, exist_ok=True)
    args.audit_output.write_text(
        json.dumps(
            {
                "input": project_relative(args.input),
                "output": project_relative(args.output),
                "model": args.hf_model,
                "rows": len(rows),
                "message_count": sum(len(row["messages"]) for row in audit_rows),
                "changed_messages": sum(1 for row in audit_rows for message in row["messages"] if message["raw"] != message["corrected"]),
                "accepted_messages": sum(1 for row in audit_rows for message in row["messages"] if message["accepted"]),
                "rejected_messages": sum(1 for row in audit_rows for message in row["messages"] if not message["accepted"]),
                "items": audit_rows,
            },
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "input": project_relative(args.input),
                "output": project_relative(args.output),
                "audit_output": project_relative(args.audit_output),
                "rows": len(rows),
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()

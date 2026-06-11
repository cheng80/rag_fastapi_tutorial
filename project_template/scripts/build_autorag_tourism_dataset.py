from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime
import json
from pathlib import Path
import re
import sys
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "data" / "processed" / "autorag_tourism"
DEFAULT_CORPUS_INPUTS = [
    PROJECT_ROOT / "data" / "raw" / "tourism_accessible",
    PROJECT_ROOT / "data" / "generated" / "tour_api" / "live_markdown",
]
DEFAULT_EVAL_INPUTS = [
    PROJECT_ROOT / "data" / "eval" / "tourism_20_questions.jsonl",
    PROJECT_ROOT / "data" / "eval" / "tourism_noisy_realistic_chat_eval_v1_200.jsonl",
]

CONDITION_TERMS = {
    "wheelchair": ["휠체어", "무장애", "장애인", "경사로", "출입통로", "접근로"],
    "family": ["가족", "아이", "어린이", "영유아", "유아", "아기"],
    "stroller": ["유모차", "유아차", "수유실", "기저귀", "영유아", "가족"],
    "elderly": ["고령자", "어르신", "노약자", "부모님", "휴식", "쉬어"],
    "guide_dog": ["보조견", "안내견"],
    "visual_impairment": ["시각장애", "점자", "점자블록", "촉지도", "음성안내", "오디오가이드"],
    "accessible_toilet": ["화장실", "장애인 화장실"],
    "accessible_parking": ["주차", "장애인 주차"],
    "parking": ["주차", "차댈", "차 댈"],
    "indoor": ["실내", "박물관", "전시관", "미술관", "체험관"],
    "elevator": ["엘리베이터", "엘베", "승강기", "리프트"],
    "hearing": ["수어", "수화", "자막", "문자안내", "영상안내", "청각장애"],
}

KOREAN_LABEL_TO_TERMS = {
    "휠체어": CONDITION_TERMS["wheelchair"],
    "유모차": CONDITION_TERMS["stroller"],
    "고령자": CONDITION_TERMS["elderly"],
    "주차": CONDITION_TERMS["parking"],
    "장애인 화장실": CONDITION_TERMS["accessible_toilet"],
    "엘리베이터": CONDITION_TERMS["elevator"],
    "수어": CONDITION_TERMS["hearing"],
    "보조견": CONDITION_TERMS["guide_dog"],
    "점자": CONDITION_TERMS["visual_impairment"],
}

KNOWN_REGION_TERMS = [
    "서울",
    "강남구",
    "강릉",
    "부산",
    "중구",
    "인천",
    "대전",
    "대구",
    "제주",
    "울산",
    "남구",
    "충북",
    "경기",
    "경기도",
    "강원",
    "강원특별자치도",
    "전북",
    "전북특별자치도",
    "전남",
    "전라남도",
    "경북",
    "경상북도",
    "경남",
    "경상남도",
    "충남",
    "충청남도",
    "서귀포",
    "서귀포시",
    "성남",
    "성남시",
    "부산진구",
]
SPECIFIC_REGION_TERMS = [region for region in KNOWN_REGION_TERMS if region.endswith(("구", "군", "시")) and region not in {"서울", "부산", "인천", "대전", "대구", "울산"}]
BROAD_REGION_TERMS = [region for region in KNOWN_REGION_TERMS if region not in SPECIFIC_REGION_TERMS]

REGION_ADDRESS_ALIASES = {
    "서울": ["서울특별시", "서울 "],
    "부산": ["부산광역시", "부산 "],
    "인천": ["인천광역시", "인천 "],
    "대전": ["대전광역시", "대전 "],
    "대구": ["대구광역시", "대구 "],
    "울산": ["울산광역시", "울산 "],
    "제주": ["제주특별자치도", "제주 "],
    "강원": ["강원특별자치도", "강원도", "강원 "],
    "강릉": ["강릉시", "강릉 "],
    "충북": ["충청북도", "충북 "],
    "충남": ["충청남도", "충남 "],
    "전북": ["전북특별자치도", "전라북도", "전북 "],
    "전남": ["전라남도", "전남 "],
    "경북": ["경상북도", "경북 "],
    "경남": ["경상남도", "경남 "],
    "경기": ["경기도", "경기 "],
    "경기도": ["경기도"],
    "강원특별자치도": ["강원특별자치도"],
    "전북특별자치도": ["전북특별자치도"],
    "전라남도": ["전라남도"],
    "경상북도": ["경상북도"],
    "경상남도": ["경상남도"],
    "충청남도": ["충청남도"],
}

SKIP_CATEGORY_FRAGMENTS = [
    "ambiguous",
    "clarification",
    "non_tourism",
    "wrong_premise",
    "no_results",
    "unsupported",
]


@dataclass
class CorpusRow:
    doc_id: str
    contents: str
    path: str
    metadata: dict[str, Any]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build AutoRAG qa.parquet and corpus.parquet from tourism markdown/eval assets.",
    )
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--corpus-input", action="append", type=Path, dest="corpus_inputs")
    parser.add_argument("--eval-input", action="append", type=Path, dest="eval_inputs")
    parser.add_argument("--max-eval-rows", type=int, default=80)
    parser.add_argument(
        "--min-ground-truth",
        type=int,
        default=1,
        help="Skip QA rows with fewer than this many matched corpus docs.",
    )
    return parser.parse_args()


def require_parquet_deps() -> Any:
    try:
        import pandas as pd
    except ModuleNotFoundError as exc:
        raise SystemExit(
            "pandas/pyarrow dependencies are missing. Install with: "
            ".venv/bin/python -m pip install -r requirements-autorag.txt"
        ) from exc
    try:
        import pyarrow  # noqa: F401
    except ModuleNotFoundError as exc:
        raise SystemExit(
            "pyarrow dependency is missing. Install with: "
            ".venv/bin/python -m pip install -r requirements-autorag.txt"
        ) from exc
    return pd


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.exists():
        return rows
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        rows.append(json.loads(line))
    return rows


def markdown_value(text: str, label: str) -> str:
    match = re.search(rf"^{re.escape(label)}:\s*(.+)$", text, flags=re.MULTILINE)
    return match.group(1).strip() if match else ""


def title_from_markdown(text: str, fallback: str) -> str:
    match = re.search(r"^#\s+(.+)$", text, flags=re.MULTILINE)
    return match.group(1).strip() if match else fallback


def normalize_doc_id(value: str, fallback: str) -> str:
    raw = value.strip() or fallback
    normalized = re.sub(r"[^0-9A-Za-z가-힣_.:-]+", "-", raw).strip("-")
    return normalized or fallback


def build_corpus(corpus_inputs: list[Path]) -> list[CorpusRow]:
    rows: list[CorpusRow] = []
    seen: set[str] = set()
    now = datetime.now()
    for input_dir in corpus_inputs:
        if not input_dir.exists():
            continue
        for path in sorted(input_dir.rglob("*.md")):
            text = path.read_text(encoding="utf-8").strip()
            if not text:
                continue
            content_id = markdown_value(text, "콘텐츠ID")
            title = markdown_value(text, "관광지명") or title_from_markdown(text, path.stem)
            address = markdown_value(text, "주소")
            source_url = markdown_value(text, "출처URL")
            doc_id = normalize_doc_id(content_id, path.stem)
            if doc_id in seen:
                doc_id = normalize_doc_id(f"{doc_id}-{path.stem}", path.stem)
            seen.add(doc_id)
            rows.append(
                CorpusRow(
                    doc_id=doc_id,
                    contents=text,
                    path=str(path.relative_to(PROJECT_ROOT)),
                    metadata={
                        "title": title,
                        "content_id": content_id,
                        "address": address,
                        "source_url": source_url,
                        "source_path": str(path.relative_to(PROJECT_ROOT)),
                        "last_modified_datetime": now,
                    },
                )
            )
    return rows


def flatten_eval_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    flattened: list[dict[str, Any]] = []
    for row in rows:
        turns = row.get("turns")
        if isinstance(turns, list):
            for index, turn in enumerate(turns, start=1):
                merged = {**row, **turn}
                merged["id"] = f"{row.get('id', 'ROW')}-T{index}"
                merged.pop("turns", None)
                flattened.append(merged)
        else:
            flattened.append(row)
    return flattened


def extract_regions(row: dict[str, Any]) -> list[str]:
    candidates: list[str] = []
    for key in ("expected_region", "message", "must_contain_answer_terms"):
        value = str(row.get(key) or "")
        for region in sorted(KNOWN_REGION_TERMS, key=len, reverse=True):
            if region in value:
                candidates.append(region)
    candidates = unique_preserve_order(candidates)
    return [
        region
        for region in candidates
        if not any(region != other and region in other for other in candidates)
    ]


def split_region_constraints(row: dict[str, Any]) -> tuple[list[str], list[str]]:
    regions = extract_regions(row)
    specific = [region for region in regions if region in SPECIFIC_REGION_TERMS]
    broad = [region for region in regions if region in BROAD_REGION_TERMS]
    return specific, broad


def expected_terms(row: dict[str, Any]) -> list[str]:
    terms: list[str] = []
    conditions = row.get("expected_conditions") or []
    if isinstance(conditions, str):
        conditions = [conditions]
    for condition in conditions:
        condition_text = str(condition)
        terms.extend(CONDITION_TERMS.get(condition_text, []))
        terms.extend(KOREAN_LABEL_TO_TERMS.get(condition_text, []))
        if condition_text and condition_text not in {"nearby", "source", "out_of_scope"}:
            terms.append(condition_text)
    for key in ("must_include_any_card_terms", "must_include_answer_any_terms"):
        value = row.get(key)
        if isinstance(value, list):
            for item in value:
                if isinstance(item, list):
                    terms.extend(str(term) for term in item)
                else:
                    terms.append(str(item))
    return unique_preserve_order([term for term in terms if term])


def unique_preserve_order(values: list[str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        if value not in seen:
            result.append(value)
            seen.add(value)
    return result


def region_in_address(region: str, address: str) -> bool:
    if not region or not address:
        return False
    aliases = REGION_ADDRESS_ALIASES.get(region)
    if aliases:
        return any(address.startswith(alias) if alias.endswith(" ") else alias in address for alias in aliases)
    return re.search(rf"(^|[^가-힣]){re.escape(region)}($|[^가-힣])", address) is not None


def score_doc(row: dict[str, Any], corpus: CorpusRow) -> int:
    haystack = f"{corpus.contents}\n{corpus.metadata.get('address', '')}\n{corpus.metadata.get('title', '')}"
    address = str(corpus.metadata.get("address") or "")
    score = 0
    specific_regions, broad_regions = split_region_constraints(row)
    terms = expected_terms(row)
    if specific_regions:
        specific_hits = sum(1 for region in specific_regions if region_in_address(region, address))
        if specific_hits == 0:
            return 0
        score += 5 + specific_hits
        broad_hits = sum(1 for region in broad_regions if region_in_address(region, address))
        if broad_regions and broad_hits == 0:
            return 0
        score += broad_hits
    elif broad_regions:
        broad_hits = sum(1 for region in broad_regions if region_in_address(region, address))
        if broad_hits == 0:
            return 0
        score += 4 + broad_hits
    if terms:
        score += sum(1 for term in terms if term in haystack)
    message = str(row.get("message") or "")
    if message:
        title = str(corpus.metadata.get("title") or "")
        if title and title in message:
            score += 3
    return score


def map_retrieval_gt(row: dict[str, Any], corpus_rows: list[CorpusRow], limit: int = 8) -> list[str]:
    scored = [(score_doc(row, corpus), corpus.doc_id) for corpus in corpus_rows]
    positive = [(score, doc_id) for score, doc_id in scored if score > 0]
    positive.sort(key=lambda item: (-item[0], item[1]))
    return [doc_id for _, doc_id in positive[:limit]]


def should_skip_eval_row(row: dict[str, Any]) -> bool:
    category = str(row.get("category") or "")
    expected_region = str(row.get("expected_region") or "")
    conditions = [str(item) for item in row.get("expected_conditions") or []]
    if row.get("expect_clarification") or row.get("expect_no_cards"):
        return True
    if "ambiguous" in expected_region:
        return True
    if any(fragment in category for fragment in SKIP_CATEGORY_FRAGMENTS):
        return True
    if any(condition in {"out_of_scope", "source"} for condition in conditions):
        return True
    return False


def build_qa_rows(eval_inputs: list[Path], corpus_rows: list[CorpusRow], max_rows: int, min_ground_truth: int) -> list[dict[str, Any]]:
    raw_eval_rows: list[dict[str, Any]] = []
    for path in eval_inputs:
        raw_eval_rows.extend(read_jsonl(path))
    qa_rows: list[dict[str, Any]] = []
    for row in flatten_eval_rows(raw_eval_rows):
        if should_skip_eval_row(row):
            continue
        query = str(row.get("message") or "").strip()
        if not query:
            continue
        retrieval_gt = map_retrieval_gt(row, corpus_rows)
        if len(retrieval_gt) < min_ground_truth:
            continue
        qa_rows.append(
            {
                "qid": str(row.get("id") or f"tourism-{len(qa_rows) + 1:04d}"),
                "query": query,
                "retrieval_gt": [retrieval_gt],
                "generation_gt": str(row.get("expected_behavior") or row.get("category") or "근거 있는 관광 카드 추천"),
                "metadata": {
                    "category": row.get("category"),
                    "scoring_focus": row.get("scoring_focus", []),
                    "source_eval_id": row.get("id"),
                },
            }
        )
        if len(qa_rows) >= max_rows:
            break
    return qa_rows


def write_summary(output_dir: Path, corpus_rows: list[CorpusRow], qa_rows: list[dict[str, Any]], skipped_inputs: list[str]) -> None:
    summary = {
        "corpus_rows": len(corpus_rows),
        "qa_rows": len(qa_rows),
        "skipped_inputs": skipped_inputs,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "notes": [
            "retrieval_gt is heuristic and should be manually reviewed before using results as final quality evidence.",
            "Use this dataset for retrieval pipeline screening, not for replacing /tourism/chat domain logic.",
        ],
    }
    (output_dir / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")


def write_review_report(output_dir: Path, corpus_rows: list[CorpusRow], qa_rows: list[dict[str, Any]]) -> None:
    corpus_by_id = {row.doc_id: row for row in corpus_rows}
    lines = [
        "# AutoRAG Tourism QA Mapping Review",
        "",
        "This report is generated from heuristic `retrieval_gt` mapping.",
        "Review suspicious rows before treating AutoRAG metrics as quality evidence.",
        "",
    ]
    for index, row in enumerate(qa_rows, start=1):
        gt_nested = row.get("retrieval_gt") or [[]]
        gt_ids = gt_nested[0] if gt_nested and isinstance(gt_nested[0], list) else []
        lines.extend(
            [
                f"## {index}. {row['qid']}",
                "",
                f"- Query: {row['query']}",
                f"- Category: {row.get('metadata', {}).get('category')}",
                f"- Ground truth count: {len(gt_ids)}",
                "",
                "| Rank | doc_id | Title | Address | Source path |",
                "|---:|---|---|---|---|",
            ]
        )
        for rank, doc_id in enumerate(gt_ids, start=1):
            corpus = corpus_by_id.get(str(doc_id))
            if corpus is None:
                lines.append(f"| {rank} | `{doc_id}` | missing | missing | missing |")
                continue
            title = str(corpus.metadata.get("title") or "")
            address = str(corpus.metadata.get("address") or "")
            source_path = str(corpus.metadata.get("source_path") or "")
            lines.append(
                f"| {rank} | `{doc_id}` | {title} | {address} | `{source_path}` |"
            )
        lines.append("")
    (output_dir / "qa_mapping_review.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    args = parse_args()
    pd = require_parquet_deps()
    corpus_inputs = args.corpus_inputs or DEFAULT_CORPUS_INPUTS
    eval_inputs = args.eval_inputs or DEFAULT_EVAL_INPUTS
    output_dir = args.output_dir
    if not output_dir.is_absolute():
        output_dir = PROJECT_ROOT / output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    corpus_rows = build_corpus(corpus_inputs)
    if not corpus_rows:
        raise SystemExit("No tourism markdown corpus rows found.")
    qa_rows = build_qa_rows(eval_inputs, corpus_rows, args.max_eval_rows, args.min_ground_truth)
    if not qa_rows:
        raise SystemExit("No QA rows matched corpus docs. Lower --min-ground-truth or inspect eval/corpus coverage.")

    corpus_df = pd.DataFrame(
        [
            {
                "doc_id": row.doc_id,
                "contents": row.contents,
                "path": row.path,
                "metadata": row.metadata,
            }
            for row in corpus_rows
        ]
    ).reset_index(drop=True)
    qa_df = pd.DataFrame(qa_rows).reset_index(drop=True)
    corpus_df.to_parquet(output_dir / "corpus.parquet", index=False)
    qa_df.to_parquet(output_dir / "qa.parquet", index=False)
    write_summary(output_dir, corpus_rows, qa_rows, [str(path) for path in corpus_inputs + eval_inputs if not path.exists()])
    write_review_report(output_dir, corpus_rows, qa_rows)
    print(f"Wrote {len(corpus_rows)} corpus rows and {len(qa_rows)} QA rows to {output_dir.relative_to(PROJECT_ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

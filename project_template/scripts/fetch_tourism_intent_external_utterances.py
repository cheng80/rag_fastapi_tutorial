from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from urllib.parse import urlencode
from urllib.request import urlopen


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


DEFAULT_OUTPUT = PROJECT_ROOT / "data" / "eval" / "tourism_intent_external_utterances.jsonl"
HF_CLINC_BASE = "https://huggingface.co/datasets/neuralfoundry-coder/clinc150-ko/resolve/main"
HF_DATASET_ROWS = "https://datasets-server.huggingface.co/rows"


def fetch_text(url: str) -> str:
    with urlopen(url, timeout=30) as response:
        return response.read().decode("utf-8")


def fetch_json(url: str) -> dict:
    return json.loads(fetch_text(url))


def infer_project_intent(text: str) -> str | None:
    compact = " ".join(text.strip().split())
    if not compact or len(compact) < 3:
        return None
    lowered = compact.lower()
    if any(keyword in compact for keyword in ["출처", "근거", "원자료", "어디서", "자료"]):
        return "ask_source"
    if any(keyword in compact for keyword in ["더 보여", "더 알려", "다른", "추가", "나머지", "전체", "전부", "계속"]):
        return "show_more"
    if any(keyword in compact for keyword in ["최신", "최근", "현재", "업데이트", "새로", "다시 조회"]):
        return "live_topup"
    if any(keyword in compact for keyword in ["실시간", "가격", "요금", "비용", "예약", "취소", "환불", "영업", "운영 시간", "전화", "병원", "응급실", "날씨", "재고", "대기"]):
        return "unsupported_request"
    if any(keyword in compact for keyword in ["말고", "빼고", "제외", "대신", "아니고"]):
        region_hits = sum(1 for region in ["서울", "부산", "대구", "인천", "광주", "대전", "제주", "강릉", "속초", "전주"] if region in compact)
        condition_hits = sum(1 for term in ["휠체어", "유모차", "아이", "어르신", "주차", "화장실", "실내", "시장", "호텔", "카페", "식당"] if term in compact)
        if region_hits >= 2:
            return "change_region"
        if condition_hits >= 2:
            return "replace_condition"
        return "exclude_preference"
    if any(keyword in compact for keyword in ["좁혀", "쪽만", "만 보여", "중심", "범위"]):
        return "narrow_region"
    if compact.split()[0] in {"중구", "동구", "서구", "남구", "북구", "고성군", "강서구"}:
        return "clarify_region"
    if any(keyword in compact for keyword in ["있는 곳", "가능한 곳", "좋은 곳", "편한 곳", "되는 곳", "확인되는 곳"]):
        return "add_condition"
    if any(keyword in compact for keyword in ["관광", "여행", "장소", "가볼", "갈만", "갈 만", "추천", "주변", "근처", "찾아"]):
        return "recommend_places"
    if any(keyword in lowered for keyword in ["travel", "trip", "hotel", "restaurant", "tour", "place"]):
        return "recommend_places"
    return None


def load_clinc_rows(max_rows: int) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for split in ["train", "validation", "test"]:
        url = f"{HF_CLINC_BASE}/data/clinc150_ko_{split}_20260112_135130.jsonl"
        try:
            content = fetch_text(url)
        except Exception:
            continue
        for line in content.splitlines():
            if not line.strip():
                continue
            payload = json.loads(line)
            text = str(payload.get("text") or payload.get("utterance") or "").strip()
            intent = infer_project_intent(text)
            if intent:
                rows.append({"text": text, "intent": intent, "source": "neuralfoundry-coder/clinc150-ko"})
            if len(rows) >= max_rows:
                return rows
    return rows


def load_dataset_server_rows(dataset: str, split: str, text_field: str, max_rows: int, page_size: int = 100) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    offset = 0
    while len(rows) < max_rows:
        query = urlencode({"dataset": dataset, "config": "default", "split": split, "offset": offset, "length": page_size})
        try:
            payload = fetch_json(f"{HF_DATASET_ROWS}?{query}")
        except Exception:
            break
        batch = payload.get("rows") or []
        if not batch:
            break
        for item in batch:
            row = item.get("row") or {}
            text = str(row.get(text_field) or "").strip()
            intent = infer_project_intent(text)
            if intent:
                rows.append({"text": text, "intent": intent, "source": dataset})
                if len(rows) >= max_rows:
                    break
        offset += page_size
    return rows


def load_kosgd_rows(max_rows: int) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for index in range(1, 35):
        url = f"https://huggingface.co/datasets/AIWORKX/KoSGD/resolve/main/data/test/dialogues_{index:03d}.json"
        try:
            payload = fetch_json(url)
        except Exception:
            continue
        dialogues = payload if isinstance(payload, list) else payload.get("dialogues") or []
        for dialogue in dialogues:
            turns = dialogue.get("turns") or []
            for turn in turns:
                if turn.get("speaker") not in {None, "USER", "user"}:
                    continue
                text = str(turn.get("utterance") or "").strip()
                intent = infer_project_intent(text)
                if intent:
                    rows.append({"text": text, "intent": intent, "source": "AIWORKX/KoSGD"})
                    if len(rows) >= max_rows:
                        return rows
    return rows


def deduplicate(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    result = []
    seen: set[tuple[str, str]] = set()
    for row in rows:
        key = (row["text"], row["intent"])
        if key in seen:
            continue
        seen.add(key)
        result.append(row)
    return result


def write_jsonl(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        for row in rows:
            file.write(json.dumps(row, ensure_ascii=False) + "\n")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fetch weakly-mapped public external utterances for tourism intent data.")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--max-clinc", type=int, default=5000)
    parser.add_argument("--max-3i4k", type=int, default=5000)
    parser.add_argument("--max-kosgd", type=int, default=5000)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    rows = []
    rows.extend(load_clinc_rows(args.max_clinc))
    rows.extend(load_dataset_server_rows("wicho/kor_3i4k", "train", "text", args.max_3i4k))
    rows.extend(load_kosgd_rows(args.max_kosgd))
    rows = deduplicate(rows)
    write_jsonl(args.output, rows)
    counts: dict[str, int] = {}
    sources: dict[str, int] = {}
    for row in rows:
        counts[row["intent"]] = counts.get(row["intent"], 0) + 1
        sources[row["source"]] = sources.get(row["source"], 0) + 1
    print(f"Wrote {len(rows)} rows to {args.output.relative_to(PROJECT_ROOT)}")
    print(json.dumps({"intent_counts": counts, "source_counts": sources}, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()

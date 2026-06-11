from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

DEFAULT_EVAL_PATHS = [
    PROJECT_ROOT / "data" / "eval" / "tourism_100_questions.jsonl",
    PROJECT_ROOT / "data" / "eval" / "tourism_challenge_questions.jsonl",
    PROJECT_ROOT / "data" / "eval" / "tourism_conversation_challenge.jsonl",
    PROJECT_ROOT / "data" / "eval" / "tourism_intent_seed_utterances.jsonl",
    PROJECT_ROOT / "data" / "eval" / "tourism_intent_generated_utterances.jsonl",
    PROJECT_ROOT / "data" / "eval" / "tourism_intent_aihub_utterances.jsonl",
]
EXTERNAL_EVAL_PATH = PROJECT_ROOT / "data" / "eval" / "tourism_intent_external_utterances.jsonl"
DEFAULT_OUTPUT = PROJECT_ROOT / "data" / "processed" / "tourism_intent_training.jsonl"


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
    if not path.exists():
        return rows
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def infer_intent(message: str, *, turn_index: int = 1, previous_message: str | None = None) -> str:
    text = message.strip()
    if any(keyword in text for keyword in ["더 보기", "더보기", "더 보여", "더 많이", "전체", "전부", "20곳", "20개"]):
        return "show_more"
    if "최신 정보" in text:
        return "live_topup"
    if any(keyword in text for keyword in ["출처", "근거"]):
        return "ask_source"
    if any(keyword in text for keyword in ["지하철역 바로 연결", "실시간", "혼잡도", "가격", "대여 가격", "응급실", "병원", "약국"]):
        return "unsupported_request"
    if any(keyword in text for keyword in ["말고", "빼고", "제외", "아닌"]):
        if _looks_like_region_switch(text):
            return "change_region"
        if any(keyword in text for keyword in ["휠체어", "유모차", "유아차", "점자", "보조견", "안내견"]):
            return "replace_condition"
        return "exclude_preference"
    if any(keyword in text for keyword in ["좁혀", "쪽으로", "동구로", "서구로", "중구로", "남구로", "북구로"]):
        return "narrow_region"
    if turn_index > 1 and any(keyword in text for keyword in ["있는 곳", "있는 곳만", "위주", "장애인", "주차", "화장실", "엘리베이터", "점자", "수어", "자막", "경사로", "동선"]):
        return "add_condition"
    if any(keyword in text for keyword in ["동구", "서구", "중구", "남구", "북구", "고성군"]) and not any(
        area in text for area in ["서울", "부산", "대구", "인천", "광주", "대전", "울산", "강원", "경남", "경북"]
    ):
        return "clarify_region"
    return "recommend_places"


def _looks_like_region_switch(text: str) -> bool:
    areas = ["서울", "부산", "대구", "인천", "광주", "대전", "울산", "세종", "제주", "경기", "강원", "충북", "충남", "전북", "전남", "경북", "경남"]
    return sum(1 for area in areas if area in text) >= 2


def build_rows(eval_paths: list[Path]) -> list[dict[str, str]]:
    result = []
    seen = set()
    for path in eval_paths:
        for item in load_jsonl(path):
            turns = item.get("turns")
            if isinstance(turns, list):
                previous = None
                for index, turn in enumerate(turns, start=1):
                    message = str(turn.get("message") or "").strip()
                    if not message:
                        continue
                    intent = infer_intent(message, turn_index=index, previous_message=previous)
                    key = (message, intent)
                    if key not in seen:
                        result.append({"text": message, "intent": intent, "source": path.name, "item_id": str(item.get("id") or "")})
                        seen.add(key)
                    previous = message
            else:
                message = str(item.get("message") or "").strip()
                if not message and item.get("text"):
                    message = str(item.get("text") or "").strip()
                if not message:
                    continue
                intent = str(item.get("intent") or "").strip() or infer_intent(message)
                key = (message, intent)
                if key not in seen:
                    result.append({"text": message, "intent": intent, "source": path.name, "item_id": str(item.get("id") or "")})
                    seen.add(key)
    return result


def write_jsonl(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        for row in rows:
            file.write(json.dumps(row, ensure_ascii=False) + "\n")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build the tourism intent training set.")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--include-external",
        action="store_true",
        help="Include weakly mapped external public utterances. Use for experiments only; default training excludes them.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    output = args.output if args.output.is_absolute() else PROJECT_ROOT / args.output
    paths = [*DEFAULT_EVAL_PATHS]
    if args.include_external:
        paths.append(EXTERNAL_EVAL_PATH)
    rows = build_rows(paths)
    write_jsonl(output, rows)
    counts = {}
    for row in rows:
        counts[row["intent"]] = counts.get(row["intent"], 0) + 1
    print(f"Wrote {len(rows)} rows to {output.relative_to(PROJECT_ROOT)}")
    print(json.dumps(counts, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()

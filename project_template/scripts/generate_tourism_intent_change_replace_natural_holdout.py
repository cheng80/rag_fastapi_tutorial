from __future__ import annotations

import json
from pathlib import Path
import random
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

DEFAULT_OUTPUT = PROJECT_ROOT / "data" / "eval" / "tourism_intent_change_replace_natural_holdout.jsonl"


def _variants(texts: list[str], rng: random.Random, prefixes: list[str] | None = None) -> list[str]:
    prefixes = prefixes or ["", "아까 거에서 ", "방금 결과 말고 ", "음 ", "이번엔 ", "가능하면 ", "부모님이랑 갈 건데 "]
    suffixes = ["", "요", " 부탁", " 다시", " 가능해", " 알려줘", "?"]
    result = []
    for text in texts:
        for prefix in prefixes:
            for suffix in suffixes:
                result.append(" ".join(f"{prefix}{text}{suffix}".split()))
    rng.shuffle(result)
    return result


def _take(
    intent: str,
    texts: list[str],
    count: int,
    rng: random.Random,
    seen: set[str],
    prefixes: list[str] | None = None,
) -> list[dict[str, str]]:
    rows = []
    for text in _variants(texts, rng, prefixes=prefixes):
        if text in seen:
            continue
        seen.add(text)
        rows.append({"text": text, "intent": intent, "source": "change_replace_natural_holdout"})
        if len(rows) >= count:
            return rows
    raise RuntimeError(f"{intent} generated only {len(rows)} rows")


def generate_rows(seed: int = 20260516) -> list[dict[str, str]]:
    rng = random.Random(seed)
    seen: set[str] = set()
    rows: list[dict[str, str]] = []

    change_texts = [
        "서울 말고 부산으로",
        "부산 중구 말고 서울 중구로",
        "제주도 말고 강릉으로 바꿀래",
        "그 지역 말고 다른 데 찾아줘",
        "전에 말한 지역 말고 딴 곳으로",
        "지역을 다시 고를게",
        "지역 변경할래",
        "이번에는 경상도 여행이요",
        "이번엔 여수로 가보자",
        "다음엔 전주 가고 싶어",
        "지금 여기 말고 광주 지역은",
        "강원도로 검색해 줘",
        "부산에서 다른 곳으로 옮겨줘",
        "대구 지역으로 다시 볼래",
        "경북 쪽으로 바꿔서 추천",
        "전남 쪽으로 바꿔서 알려줘",
        "충청북도 쪽으로 바꿔서 보여줘",
        "강릉으로 갈아탈게",
        "속초 쪽으로 바꿔",
        "제주시 후보 말고 서귀포시 후보",
    ]
    followup_prefixes = ["", "아까 거에서 ", "방금 결과 말고 ", "음 ", "이번엔 "]
    neutral_prefixes = ["", "음 ", "가능하면 ", "부모님이랑 갈 건데 "]
    rows.extend(_take("change_region", change_texts, 180, rng, seen, prefixes=followup_prefixes))

    replace_texts = [
        "유모차 말고 휠체어로",
        "휠체어 말고 유모차로",
        "시장 위주 말고 산책 위주",
        "실내 말고 야외로 볼래",
        "주차보다 장애인 화장실을 우선해줘",
        "대중교통 말고 자가용 기준으로",
        "박물관 말고 공원 위주로",
        "식당 기준 말고 관광지 접근성 기준으로",
        "가이드 투어 말고 자유 여행 코스",
        "장애인 편의시설 말고 노약자 편의시설",
        "오전 투어 말고 오후 투어로",
        "버스 투어 말고 도보 투어로",
        "역사 유적지 말고 자연 경관 좋은 곳",
        "조용한 곳 말고 활기찬 시장 같은 데",
        "아기 의자 대신 유아용 카시트",
        "휠체어 조건 취소하고 유모차로",
        "시장 조건 빼고 박물관으로",
        "무료 입장 말고 유료라도 좋은 데",
    ]
    rows.extend(_take("replace_condition", replace_texts, 180, rng, seen, prefixes=followup_prefixes))

    exclude_texts = [
        "시장은 빼고 추천",
        "카페는 이번에 안 갈래",
        "호텔이나 숙박은 제외",
        "놀이공원은 안 가고 싶어",
        "아이들과 가서 술집은 빼줘",
        "유흥 시설은 전부 빼줘",
        "전통 시장은 됐어",
        "키즈카페나 놀이방 있는 곳은 사양할게",
        "테마파크는 이번엔 안 가려고",
        "패밀리 레스토랑은 추천 안 해줘도 돼",
        "먹자골목 느낌은 빼줘",
        "쇼핑몰 성격은 제외",
    ]
    rows.extend(_take("exclude_preference", exclude_texts, 100, rng, seen, prefixes=neutral_prefixes))

    add_texts = [
        "장애인 화장실 있는 곳도 봐줘",
        "유모차 끌기 좋은 길인가요",
        "수유실 있는 관광지 중심으로",
        "점자블록 설치된 곳으로",
        "주차 공간 넓은 곳으로",
        "보조견 동반 가능한 곳",
        "경사로 확인되는 곳",
        "기저귀 갈 곳 있는 데",
    ]
    rows.extend(_take("add_condition", add_texts, 70, rng, seen, prefixes=neutral_prefixes))

    show_more_texts = [
        "다른 곳도 알려줘",
        "다음 추천 보여줘",
        "더 많은 여행지 추천해줘",
        "남은 정보도 보여줘",
        "다른 선택지는 없나",
        "다음 페이지로 넘어가줘",
    ]
    rows.extend(_take("show_more", show_more_texts, 40, rng, seen, prefixes=["", "아까 거에서 ", "방금 결과에서 ", "음 "]))

    recommend_texts = [
        "서울 여행 정보 알려줘",
        "경북 여행 추천 좀",
        "부산 쪽 관광지 찾아줘",
        "대전 명소는 뭐가 있어",
        "제주도 가볼만한 곳",
        "강원도 여행 계획 중인데 관광지 추천",
    ]
    rows.extend(_take("recommend_places", recommend_texts, 30, rng, seen, prefixes=["", "음 ", "가능하면 ", "부모님이랑 갈 건데 "]))

    rows.sort(key=lambda row: (row["intent"], row["text"]))
    return rows


def main() -> None:
    rows = generate_rows()
    DEFAULT_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with DEFAULT_OUTPUT.open("w", encoding="utf-8") as file:
        for row in rows:
            file.write(json.dumps(row, ensure_ascii=False) + "\n")
    counts: dict[str, int] = {}
    for row in rows:
        counts[row["intent"]] = counts.get(row["intent"], 0) + 1
    print(f"Wrote {len(rows)} rows to {DEFAULT_OUTPUT.relative_to(PROJECT_ROOT)}")
    print(json.dumps(counts, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()

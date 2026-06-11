from __future__ import annotations

import json
from pathlib import Path
import random
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

DEFAULT_OUTPUT = PROJECT_ROOT / "data" / "eval" / "tourism_intent_region_clarify_natural_holdout.jsonl"


def _variants(texts: list[str], rng: random.Random) -> list[str]:
    prefixes = ["", "혹시 ", "음 ", "저기 ", "아이랑 가는데 ", "부모님이랑 ", "이번 여행 ", "대충 "]
    suffixes = ["", "?", "요", " 알려줘", " 좀", " 가능해", " 부탁", " 다시"]
    result = []
    for text in texts:
        for prefix in prefixes:
            for suffix in suffixes:
                candidate = " ".join(f"{prefix}{text}{suffix}".split())
                result.append(candidate)
    rng.shuffle(result)
    return result


def _take(intent: str, texts: list[str], count: int, rng: random.Random, seen: set[str]) -> list[dict[str, str]]:
    selected = []
    for text in _variants(texts, rng):
        if text in seen:
            continue
        seen.add(text)
        selected.append({"text": text, "intent": intent, "source": "region_clarify_natural_holdout"})
        if len(selected) >= count:
            return selected
    raise RuntimeError(f"{intent} generated only {len(selected)} rows")


def generate_rows(seed: int = 20260516) -> list[dict[str, str]]:
    rng = random.Random(seed)
    seen: set[str] = set()
    rows: list[dict[str, str]] = []

    clarify_texts = [
        "중구라면 어디 중구 말하는 거야",
        "중구만 치면 너무 많지 않아",
        "중구 여행지 찾아줘",
        "중구 관광 정보",
        "중구 휠체어 가능한 데",
        "중구 유모차 갈만한 곳",
        "중구 쪽이라고만 하면 알아",
        "중구 맛집 말고 볼거리",
        "중구 주차 편한 관광지",
        "중구 장애인 화장실 있는 곳",
        "동구 여행지",
        "동구 관광지 어디",
        "동구면 어느 광역시인지 물어봐야 하지",
        "동구 휠체어 되는 데",
        "동구 아이랑 갈 데",
        "동구쪽 무장애",
        "서구 관광지",
        "서구라고만 하면 어디 서구야",
        "서구 유모차 가능",
        "서구 부모님 모시고 갈 곳",
        "남구 여행 정보",
        "남구만 말했는데 찾아줄 수 있어",
        "남구 휠체어 관광",
        "남구 쪽 볼거리",
        "북구 관광지 추천",
        "북구면 대구인지 광주인지 모르겠네",
        "북구 가족 여행",
        "북구 무장애 명소",
        "강서구 여행",
        "강서구는 서울인지 부산인지",
        "강서구 아이랑 갈 곳",
        "강서구 휠체어 관광지",
        "고성군 가볼만한 곳",
        "고성군은 강원도 경남 둘 다 있지",
        "고성군 유모차 가능한 곳",
        "고성군 관광 정보 찾아줘",
        "중구 쪽으로 가려는데 지역 먼저 확인해야겠지",
        "동구 근처라고 했는데 어느 동구인지",
        "북구 쪽이면 어디 북구 기준이야",
        "고성군이라고만 하면 애매하지",
    ]
    rows.extend(_take("clarify_region", clarify_texts, 300, rng, seen))

    recommend_texts = [
        "서울 중구 여행지",
        "서울 중구 휠체어 가능한 관광지",
        "서울 중구 유모차 갈만한 곳",
        "부산 중구 볼거리",
        "부산 중구 관광 정보",
        "부산 중구 시장 말고 관광지",
        "대구 동구 여행지",
        "대구 동구 아이랑 갈 곳",
        "인천 서구 무장애 관광",
        "광주 남구 관광지",
        "광주 남구 휠체어 가능한 곳",
        "대전 동구 여행 정보",
        "울산 북구 가볼만한 곳",
        "경남 고성군 여행지",
        "경남 고성군 유모차 관광",
        "강원 고성군 관광지",
        "강원 고성군 휠체어 갈만한 곳",
        "서울 강서구 가족 여행",
        "부산 강서구 볼거리",
        "청주 서원구 여행지",
    ]
    rows.extend(_take("recommend_places", recommend_texts, 140, rng, seen))

    narrow_texts = [
        "아까 말한 데서 서울 중구만",
        "부산 중구 카드만 남겨줘",
        "대구 동구 쪽으로 좁혀",
        "인천 서구 안에서만 다시",
        "광주 남구 위주로만",
        "대전 동구 후보만",
        "울산 북구로 범위 줄여",
        "경남 고성군 쪽만 볼래",
        "강원 고성군 근처 후보로",
        "서울 강서구 쪽으로만",
        "부산 강서구 안에서",
        "중구 중에서도 서울 중구만",
        "고성군 중 강원 고성군으로 좁혀",
        "방금 목록에서 부산 중구만 다시",
        "아까 지역 중 경남 고성군 위주",
        "서울 중구 아닌 건 빼고",
    ]
    rows.extend(_take("narrow_region", narrow_texts, 100, rng, seen))

    change_texts = [
        "중구 말고 부산 중구로 바꿔",
        "고성군 말고 강원 고성군으로",
        "서울 중구 말고 부산 중구",
        "지역을 부산 중구로 다시 선택",
        "이번엔 경남 고성군으로 바꿀래",
        "동구 말고 대구 동구로 봐줘",
        "강서구는 됐고 서울 강서구",
        "전에 말한 곳 말고 광주 남구",
    ]
    rows.extend(_take("change_region", change_texts, 60, rng, seen))

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

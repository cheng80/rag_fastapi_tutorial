from __future__ import annotations

from itertools import product
import json
from pathlib import Path
import random
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

DEFAULT_OUTPUT = PROJECT_ROOT / "data" / "eval" / "tourism_intent_hard_holdout.jsonl"
DEFAULT_ROWS_PER_INTENT = 90


def _rows(intent: str, templates: list[str], slots: dict[str, list[str]]) -> list[dict[str, str]]:
    result = []
    for template in templates:
        names = [part.split("}", 1)[0] for part in template.split("{")[1:]]
        values = [slots[name] for name in names]
        for combo in product(*values):
            text = template.format(**dict(zip(names, combo, strict=True)))
            result.append({"text": " ".join(text.split()), "intent": intent})
    return result


def _surface_variants(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    prefixes = ["", "혹시 ", "방금 결과에서 ", "아까 말한 조건 기준으로 ", "가능하면 "]
    suffixes = ["", " 부탁해", " 가능할까", " 다시 봐줘", " 알려줘"]
    result = []
    for row in rows:
        for prefix in prefixes:
            for suffix in suffixes:
                result.append({"text": " ".join(f"{prefix}{row['text']}{suffix}".split()), "intent": row["intent"]})
    return result


def generate_rows(rows_per_intent: int = DEFAULT_ROWS_PER_INTENT, seed: int = 20260516) -> list[dict[str, str]]:
    rng = random.Random(seed)
    specs = {
        "show_more": (
            [
                "목록이 남았으면 {phrase}",
                "현재 카드 다음 {count}도 {phrase}",
                "방금 결과 말고 {phrase}",
                "같은 조건으로 {count} 더",
                "아까 보여준 카드 이어서 {phrase}",
                "전체 목록 중 아직 안 나온 곳 {phrase}",
            ],
            {
                "phrase": ["더 보여줘", "나머지도 보여줘", "계속 보여줘", "추가 후보 보여줘", "다른 후보도 보여줘", "있는 만큼 보여줘"],
                "count": ["3곳", "5곳", "10곳", "몇 군데", "가능한 만큼"],
            },
        ),
        "live_topup": (
            [
                "{fresh} 기준으로 더 찾아줘",
                "지금 가지고 있는 것 말고 {action}",
                "카드가 적으면 {action}",
                "최근에 추가된 곳 있으면 {action}",
                "현재 확인 가능한 자료로 {action}",
                "새로 확인해서 후보를 {action}",
            ],
            {
                "fresh": ["최신", "최근", "오늘", "현재", "방금"],
                "action": ["보강해줘", "추가 확인해줘", "새로 조회해줘", "더 찾아줘", "다시 찾아줘"],
            },
        ),
        "unsupported_request": (
            [
                "{topic} 지금 알 수 있어",
                "{topic} 기준으로 정렬해줘",
                "{topic} 되는 곳만 골라줘",
                "{topic}까지 계산해서 추천해줘",
                "{topic} 확인되는 곳만 보여줘",
                "{topic} 제일 좋은 순서로 보여줘",
            ],
            {
                "topic": [
                    "실시간 혼잡도",
                    "오늘 영업 여부",
                    "입장료",
                    "예약 가능 시간",
                    "주차장 빈자리",
                    "휠체어 대여 재고",
                    "택시비",
                    "버스 번호",
                    "버스 소요시간",
                    "날씨",
                    "약국 거리",
                    "응급실 거리",
                    "전화번호",
                ],
            },
        ),
        "clarify_region": (
            [
                "{ambiguous} {need} 관광지 찾아줘",
                "{ambiguous}에서 {need} 갈 곳",
                "{ambiguous} 기준으로 {need} 여행지 추천",
                "{ambiguous} 쪽 {need} 볼거리 알려줘",
                "{ambiguous} 여행 정보",
                "{ambiguous} 가족 여행지",
            ],
            {
                "ambiguous": ["중구", "동구", "서구", "남구", "북구", "강서구", "고성군"],
                "need": ["휠체어 가능한", "유모차 가능한", "주차 되는", "장애인 화장실 있는", "아이랑 갈 만한"],
            },
        ),
        "narrow_region": (
            [
                "{qualified} 쪽으로만 좁혀줘",
                "{qualified} 안에서만 다시 보여줘",
                "아까 지역 중 {qualified} 위주로",
                "범위를 {qualified}까지 줄여줘",
                "{qualified} 카드만 남겨줘",
            ],
            {
                "qualified": [
                    "부산 중구",
                    "서울 중구",
                    "대구 동구",
                    "광주 북구",
                    "강원 고성군",
                    "경남 고성군",
                    "제주 애월",
                    "창원 진해구",
                    "성남 분당구",
                ],
            },
        ),
        "change_region": (
            [
                "{old} 말고 {new}로 바꿔줘",
                "{old}는 됐고 {new}에서 다시 찾아줘",
                "지역을 {new}로 다시 선택할게",
                "이번엔 {new} 기준으로 바꿔",
                "{old} 후보 말고 {new} 후보",
            ],
            {
                "old": ["서울 중구", "부산 중구", "제주시", "서귀포시", "강릉", "강원 고성군"],
                "new": ["부산 중구", "서울 중구", "서귀포시", "제주시", "속초", "경남 고성군"],
            },
        ),
        "replace_condition": (
            [
                "{old} 말고 {new} 기준으로 바꿔줘",
                "{old}는 빼고 {new} 되는 곳",
                "{old}보다 {new}를 우선해줘",
                "{old} 조건 취소하고 {new}로 다시",
                "{old} 위주 말고 {new} 위주",
            ],
            {
                "old": ["유모차", "휠체어", "주차", "실내", "시장", "식당", "대중교통"],
                "new": ["휠체어", "장애인 화장실", "유모차", "박물관", "산책", "보조견", "엘리베이터"],
            },
        ),
        "add_condition": (
            [
                "그중 {condition}도 되는 곳",
                "같은 지역에서 {condition} 확인되는 곳",
                "{condition} 조건을 추가해줘",
                "방금 후보에 {condition}까지 봐줘",
            ],
            {
                "condition": ["장애인 화장실", "엘리베이터", "수유실", "점자블록", "보조견 동반", "장애인 주차", "경사로"],
            },
        ),
        "exclude_preference": (
            [
                "{excluded}은 빼고 보여줘",
                "{excluded} 말고 관광지로만",
                "{excluded} 느낌은 제외해줘",
                "추천에서 {excluded} 성격은 빼줘",
            ],
            {
                "excluded": ["숙소", "호텔", "식당", "카페", "시장", "쇼핑몰", "먹자골목"],
            },
        ),
        "ask_source": (
            [
                "이 정보 {source}가 뭐야",
                "{source}도 같이 보여줘",
                "방금 카드 {source} 확인하고 싶어",
                "접근성 정보 {source} 남겨줘",
            ],
            {
                "source": ["출처", "근거", "원자료", "자료 기준", "확인 자료"],
            },
        ),
        "recommend_places": (
            [
                "{region} {condition} 관광지 추천",
                "{region}에서 {persona}랑 갈 곳",
                "{region} 여행 정보 알려줘",
                "{region} {preference} 위주로 볼거리 찾아줘",
            ],
            {
                "region": ["서울 강남구", "부산 중구", "제주시", "서귀포시", "강릉", "전주", "대전 유성구"],
                "condition": ["휠체어 가능한", "유모차 가능한", "장애인 화장실 있는", "주차 되는"],
                "persona": ["아이", "부모님", "휠체어 이용자", "유모차 가족"],
                "preference": ["박물관", "공원", "산책", "실내", "시장 말고"],
            },
        ),
    }
    output: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for intent, (templates, slots) in specs.items():
        candidates = _surface_variants(_rows(intent, templates, slots))
        rng.shuffle(candidates)
        selected = 0
        for row in candidates:
            if row["intent"] == "replace_condition" and reuses_same_condition(row["text"]):
                continue
            if row["intent"] == "change_region" and reuses_same_region(row["text"]):
                continue
            key = (row["text"], row["intent"])
            if key in seen:
                continue
            seen.add(key)
            row["source"] = "hard_holdout"
            output.append(row)
            selected += 1
            if selected >= rows_per_intent:
                break
        if selected < rows_per_intent:
            raise RuntimeError(f"{intent} only generated {selected} rows")
    output.sort(key=lambda row: (row["intent"], row["text"]))
    return output


def reuses_same_condition(text: str) -> bool:
    pairs = [("유모차", "유모차"), ("휠체어", "휠체어"), ("주차", "주차")]
    return any(text.count(left) > 1 and left == right for left, right in pairs)


def reuses_same_region(text: str) -> bool:
    pairs = ["서울 중구", "부산 중구", "제주시", "서귀포시", "강원 고성군"]
    return any(text.count(region) > 1 for region in pairs)


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

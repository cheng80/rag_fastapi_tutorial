from __future__ import annotations

from itertools import product
import json
from pathlib import Path
import random
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

DEFAULT_OUTPUT = PROJECT_ROOT / "data" / "eval" / "tourism_intent_adversarial_holdout.jsonl"
DEFAULT_ROWS_PER_INTENT = 220


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
    prefixes = ["", "혹시 ", "가능하면 ", "방금 목록 기준으로 ", "아까 추천에서 ", "지금 조건이면 "]
    suffixes = ["", " 부탁해", " 해줘", " 알려줘", " 가능할까"]
    result = []
    for row in rows:
        for prefix in prefixes:
            for suffix in suffixes:
                text = " ".join(f"{prefix}{row['text']}{suffix}".split())
                result.append({"text": text, "intent": row["intent"]})
    return result


def generate_rows(rows_per_intent: int = DEFAULT_ROWS_PER_INTENT, seed: int = 20260517) -> list[dict[str, str]]:
    rng = random.Random(seed)
    specs = {
        "recommend_places": (
            [
                "{region} {persona} {place_type} 어디가 괜찮을까",
                "{region}에서 {persona}랑 갈 {place_type} 골라줘",
                "{region} {condition} {place_type} 몇 군데만",
                "{region} 여행인데 {preference} 쪽으로 잡아줘",
            ],
            {
                "region": ["서울 강남구", "부산 중구", "제주시", "서귀포시", "강릉", "전주", "속초", "대전 유성구"],
                "persona": ["휠체어 이용자", "유모차 끄는 가족", "부모님", "아이", "보조견 동반자"],
                "place_type": ["볼거리", "관광지", "산책 코스", "실내 명소", "가족 여행지"],
                "condition": ["장애인 화장실 있는", "계단 부담 적은", "유모차로 움직이기 쉬운", "주차 가능한"],
                "preference": ["박물관", "공원", "시장 말고 관광지", "실내", "산책"],
            },
        ),
        "add_condition": (
            [
                "그중 {condition} 확인되는 데만 추려줘",
                "아까 후보에서 {condition} 괜찮은 곳 위주로",
                "{condition} 때문에 다시 걸러줘",
                "같은 지역에서 {condition}도 봐줘",
            ],
            {
                "condition": ["휠체어 동선", "장애인 화장실", "수유실", "유모차 이동", "장애인 주차", "점자블록", "수어 안내", "보조견 동반", "버스 정류장 접근", "엘리베이터"],
            },
        ),
        "replace_condition": (
            [
                "{old} 조건은 빼고 {new} 기준으로 다시",
                "이번엔 {old}보다 {new}를 우선해줘",
                "{old} 말한 건 취소하고 {new} 되는 곳",
                "{old} 위주 말고 {new} 위주로 바꿔",
            ],
            {
                "old": ["유모차", "주차", "시장", "실내", "휠체어", "어르신", "대중교통"],
                "new": ["휠체어", "장애인 화장실", "산책", "박물관", "유모차", "엘리베이터", "보조견"],
            },
        ),
        "exclude_preference": (
            [
                "{excluded}은 빼고 볼거리만",
                "{excluded} 느낌은 제외해줘",
                "{excluded} 말고 관광지로만 다시",
                "추천 중 {excluded} 성격은 빼줘",
            ],
            {
                "excluded": ["숙소", "호텔", "펜션", "식당", "카페", "먹자골목", "시장", "상가", "쇼핑몰", "예약 시설"],
            },
        ),
        "change_region": (
            [
                "{old}는 아니고 {new}로 바꿔줘",
                "{old} 말고 {new}에서 다시 찾아줘",
                "지역을 {old}에서 {new}로 변경",
                "{old} 후보는 됐고 {new} 기준으로",
            ],
            {
                "old": ["서울 중구", "부산 중구", "제주시", "강릉", "광주", "강원 고성군", "대구 동구"],
                "new": ["부산 중구", "서울 중구", "서귀포시", "속초", "광주광역시 북구", "경남 고성군", "대전 동구"],
            },
        ),
        "narrow_region": (
            [
                "{district}만 남겨서 다시 보여줘",
                "{district} 쪽 후보로 줄여줘",
                "범위를 {district} 안으로 좁혀",
                "아까 지역 중 {district} 위주로",
            ],
            {
                "district": ["중구", "동구", "서구", "해운대구", "강남구", "종로구", "마산합포구", "진해구", "분당구", "수성구"],
            },
        ),
        "clarify_region": (
            [
                "{ambiguous} {condition} 관광지",
                "{ambiguous}에서 아이랑 갈 곳",
                "{ambiguous} 기준으로 무장애 추천",
                "{ambiguous} 쪽 볼거리 알려줘",
            ],
            {
                "ambiguous": ["중구", "동구", "서구", "남구", "북구", "강서구", "고성군", "광산구"],
                "condition": ["휠체어 가능한", "유모차 가능한", "주차 되는", "장애인 화장실 있는"],
            },
        ),
        "show_more": (
            [
                "아까 카드 말고 {more}",
                "{amount} 정도 더 이어서",
                "목록이 남았으면 {more}",
                "지금 결과 다음 것도 보여줘",
            ],
            {
                "more": ["더 꺼내줘", "나머지도 줘", "계속 보여줘", "추가 후보 보여줘", "다른 후보도"],
                "amount": ["5곳", "10곳", "가능한 만큼", "전체", "있는 만큼"],
            },
        ),
        "live_topup": (
            [
                "{fresh} 기준으로 더 확인해줘",
                "지금 자료로 {action}",
                "저장된 결과가 적으면 {action}",
                "새로 올라온 정보가 있으면 반영해줘",
            ],
            {
                "fresh": ["오늘", "현재", "최근", "방금", "최신 자료"],
                "action": ["다시 찾아줘", "추가 확인해줘", "새로 조회해줘", "보강해줘"],
            },
        ),
        "ask_source": (
            [
                "이 카드 {source}가 뭐야",
                "{source}도 같이 확인하고 싶어",
                "방금 답변은 어떤 자료 기준이야",
                "접근성 정보 {source} 남겨줘",
            ],
            {
                "source": ["근거", "출처", "원자료", "확인 자료", "자료명"],
            },
        ),
        "unsupported_request": (
            [
                "{topic} 지금 알 수 있어?",
                "{topic} 기준으로 정렬해줘",
                "{topic} 되는 곳만 골라줘",
                "{topic}까지 같이 계산해줘",
            ],
            {
                "topic": ["입장료", "예약 가능 시간", "오늘 영업 여부", "실시간 혼잡도", "주차장 빈자리", "택시비", "버스 번호", "버스 소요시간", "렌터카 전화번호", "약국 거리", "날씨"],
            },
        ),
    }
    output = []
    seen: set[tuple[str, str]] = set()
    for intent, (templates, slots) in specs.items():
        candidates = _surface_variants(_rows(intent, templates, slots))
        rng.shuffle(candidates)
        selected = 0
        for row in candidates:
            if row["intent"] == "change_region" and any(
                duplicated in row["text"]
                for duplicated in [
                    "부산 중구 말고 부산 중구",
                    "부산 중구는 아니고 부산 중구",
                    "서울 중구 말고 서울 중구",
                    "서울 중구는 아니고 서울 중구",
                ]
            ):
                continue
            key = (row["text"], row["intent"])
            if key in seen:
                continue
            seen.add(key)
            row["source"] = "adversarial_holdout"
            output.append(row)
            selected += 1
            if selected >= rows_per_intent:
                break
    output.sort(key=lambda row: (row["intent"], row["text"]))
    return output


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

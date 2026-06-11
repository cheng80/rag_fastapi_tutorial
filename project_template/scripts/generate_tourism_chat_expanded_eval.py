from __future__ import annotations

from itertools import product
import json
from pathlib import Path
import random
import sys
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

SINGLE_OUTPUT = PROJECT_ROOT / "data" / "eval" / "tourism_expanded_questions.jsonl"
CONVERSATION_OUTPUT = PROJECT_ROOT / "data" / "eval" / "tourism_expanded_conversation_challenge.jsonl"


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        for row in rows:
            file.write(json.dumps(row, ensure_ascii=False) + "\n")


def generate_single_questions(seed: int = 20260517) -> list[dict[str, Any]]:
    rng = random.Random(seed)
    rows: list[dict[str, Any]] = []

    regions = [
        ("서울", "서울"),
        ("부산", "부산"),
        ("대구", "대구"),
        ("대전", "대전"),
        ("제주시", "제주시"),
        ("서귀포시", "서귀포시"),
        ("강릉", "강릉"),
        ("전주", "전주"),
        ("부산 중구", "부산 중구"),
        ("서울 강남구", "서울 강남구"),
    ]
    conditions = [
        ("휠체어로 갈 수 있는", ["휠체어", "장애인"]),
        ("유모차로 움직이기 좋은", ["유모차", "수유실", "영유아", "기저귀", "어린이", "가족"]),
        ("장애인 화장실 정보가 있는", ["화장실"]),
        ("장애인 주차가 확인되는", ["주차"]),
        ("어르신과 천천히 둘러보기 좋은", ["휠체어", "장애인", "경사로", "접근"]),
    ]
    preferences = [
        ("실내 박물관이나 전시관", ["박물관", "전시관", "미술관", "체험관", "도서관", "갤러리"]),
        ("공원이나 산책하기 좋은 곳", ["공원", "산책", "정원", "숲"]),
        ("시장이나 먹거리 위주", ["시장", "먹거리", "식당", "음식"]),
        ("조용히 볼거리 위주", ["공원", "산책", "정원", "박물관", "전시", "숲", "생태", "한적", "조용"]),
    ]

    for index, ((region, answer_term), (condition, card_terms)) in enumerate(product(regions, conditions), start=1):
        rows.append(
            {
                "id": f"TEQ{index:03d}",
                "category": "expanded_condition",
                "message": f"{region}에서 {condition} 관광지 추천해줘",
                "min_cards": 1,
                "max_cards": 5,
                "must_contain_answer_terms": [answer_term],
                "must_include_any_card_terms": [card_terms],
                "scoring_focus": ["지역 유지", "조건 근거 카드"],
            }
        )

    offset = len(rows)
    low_coverage_preferences = {
        ("전주", "실내 박물관이나 전시관"),
        ("전주", "조용히 볼거리 위주"),
        ("제주시", "조용히 볼거리 위주"),
        ("전주", "공원이나 산책하기 좋은 곳"),
        ("강릉", "조용히 볼거리 위주"),
    }
    for index, ((region, answer_term), (preference, card_terms)) in enumerate(product(regions[:8], preferences), start=1):
        row = {
            "id": f"TEQ{offset + index:03d}",
            "category": "expanded_preference",
            "message": f"{region}에서 {preference}로 무장애 관광지 골라줘",
            "max_cards": 5,
            "must_contain_answer_terms": [answer_term],
            "scoring_focus": ["선호 조건 랭킹", "지역 유지"],
        }
        if (region, preference) in low_coverage_preferences:
            row.pop("must_contain_answer_terms", None)
            row.update(
                {
                    "expect_no_cards": True,
                    "must_include_answer_any_terms": ["조건에 맞는 관광지를 확인하지 못했습니다", "조건에 맞는"],
                }
            )
        else:
            row.update({"min_cards": 1, "must_include_any_card_terms": [card_terms]})
        rows.append(row)

    ambiguous = ["중구", "동구", "서구", "남구", "북구", "강서구", "고성군"]
    offset = len(rows)
    for index, region in enumerate(ambiguous * 8, start=1):
        rows.append(
            {
                "id": f"TEQ{offset + index:03d}",
                "category": "expanded_ambiguous_region",
                "message": f"{region}에서 휠체어 가능한 관광지 추천해줘",
                "expect_clarification": True,
                "expect_no_cards": True,
                "must_include_answer_any_terms": ["어느 지역", "구체적으로", region],
                "scoring_focus": ["모호 지역 확인", "잘못된 지역 추천 금지"],
            }
        )

    unsupported_topics = [
        "입장료가 제일 싼 곳",
        "오늘 영업 중인 곳",
        "실시간 혼잡도 낮은 곳",
        "주차장 빈자리 있는 곳",
        "버스 번호와 소요시간",
        "예약 가능한 시간",
        "휠체어 대여 가격",
        "렌터카 전화번호",
        "약국 가까운 관광지",
        "날씨에 맞춰 갈 곳",
    ]
    offset = len(rows)
    for index, topic in enumerate(unsupported_topics * 8, start=1):
        rows.append(
            {
                "id": f"TEQ{offset + index:03d}",
                "category": "expanded_unsupported",
                "message": f"{topic} 알려줘",
                "expect_no_cards": True,
                "must_include_answer_any_terms": ["현재 MVP", "확인된 데이터", "추천하지 않겠습니다", "지역과 접근성 조건"],
                "scoring_focus": ["서비스 범위 밖 질문 거절", "추측 금지"],
            }
        )

    negative_templates = [
        ("서울", "식당이나 카페 말고 휠체어 관광지", ["식당", "카페", "맛집", "레스토랑"], "서울"),
        ("부산 중구", "시장 말고 조용히 볼 곳", ["시장", "먹자골목"], "부산 중구"),
        ("제주시", "숙박이나 호텔 말고 아이랑 갈 관광지", ["호텔", "숙박", "리조트", "펜션"], "제주시"),
        ("대구", "쇼핑몰이나 상가 말고 박물관 쪽", ["쇼핑몰", "상가", "백화점"], "대구"),
    ]
    offset = len(rows)
    for index, (region, phrase, forbidden, answer_term) in enumerate(negative_templates * 14, start=1):
        rows.append(
            {
                "id": f"TEQ{offset + index:03d}",
                "category": "expanded_negative_preference",
                "message": f"{region}에서 {phrase} 추천해줘",
                "min_cards": 0,
                "max_cards": 5,
                "must_contain_answer_terms": [answer_term],
                "must_not_include_card_terms": [forbidden],
                "scoring_focus": ["제외 조건 반영"],
            }
        )

    rng.shuffle(rows)
    for index, row in enumerate(rows, start=1):
        row["id"] = f"TEQ{index:03d}"
    return rows


def generate_conversations(seed: int = 20260518) -> list[dict[str, Any]]:
    rng = random.Random(seed)
    base_regions = [
        ("서울", "서울", "중구", "서울 중구"),
        ("부산", "부산", "중구", "부산 중구"),
        ("대구", "대구", "중구", "대구 중구"),
        ("제주시", "제주시", "제주시", "제주시"),
        ("강릉", "강릉", "강릉", "강릉"),
    ]
    rows: list[dict[str, Any]] = []

    for region, answer_term, district, narrowed in base_regions:
        rows.extend(
            [
                {
                    "category": "expanded_more_followup",
                    "turns": [
                        {"message": f"{region}에서 휠체어 관광지 추천해줘", "min_cards": 1, "max_cards": 5, "must_contain_answer_terms": [answer_term]},
                        {"message": "더 보여줘", "min_cards": 1, "max_cards": 100, "must_contain_answer_terms": [answer_term], "must_include_any_card_terms": [["휠체어", "장애인"]]},
                    ],
                },
                {
                    "category": "expanded_add_condition_followup",
                    "turns": [
                        {"message": f"{region}에서 관광지 추천해줘", "min_cards": 1, "must_contain_answer_terms": [answer_term]},
                        {"message": "그중 장애인 화장실 확인되는 곳", "min_cards": 1, "max_cards": 5, "must_contain_answer_terms": [answer_term], "must_include_any_card_terms": [["화장실"]]},
                    ],
                },
                {
                    "category": "expanded_replace_condition_followup",
                    "turns": [
                        {"message": f"{region}에서 유모차 가능한 관광지 추천해줘", "min_cards": 1, "must_contain_answer_terms": [answer_term]},
                        {"message": "유모차 말고 휠체어 기준으로 다시", "min_cards": 1, "max_cards": 5, "must_contain_answer_terms": [answer_term], "must_include_any_card_terms": [["휠체어", "장애인"]]},
                    ],
                },
                {
                    "category": "expanded_exclude_followup",
                    "turns": [
                        {"message": f"{region}에서 아이랑 갈 곳 추천해줘", "min_cards": 1, "must_contain_answer_terms": [answer_term]},
                        {"message": "숙박이나 호텔은 빼고", "min_cards": 1, "max_cards": 5, "must_contain_answer_terms": [answer_term], "must_not_include_card_terms": [["호텔", "숙박", "리조트", "펜션"]]},
                    ],
                },
                {
                    "category": "expanded_narrow_followup",
                    "turns": [
                        {"message": f"{region}에서 휠체어 관광지 추천해줘", "min_cards": 1, "must_contain_answer_terms": [answer_term]},
                        {"message": f"{district}로 좁혀줘", "min_cards": 0, "max_cards": 5, "must_contain_answer_terms": [narrowed]},
                    ],
                },
            ]
        )

    switches = [
        ("부산 중구", "부산 중구", "서울 중구", "서울 중구", "부산광역시 중구"),
        ("서울 중구", "서울 중구", "부산 중구", "부산 중구", "서울특별시 중구"),
        ("제주시", "제주시", "서귀포시", "서귀포시", "제주시"),
        ("강릉", "강릉", "속초", "속초", "강릉"),
    ]
    for old_region, old_term, new_region, new_term, forbidden in switches * 8:
        rows.append(
            {
                "category": "expanded_region_switch_followup",
                "turns": [
                    {"message": f"{old_region}에서 휠체어 관광지 추천해줘", "min_cards": 1, "must_contain_answer_terms": [old_term]},
                    {"message": f"{old_region} 말고 {new_region}로 다시", "min_cards": 1, "max_cards": 5, "must_contain_answer_terms": [new_term], "must_not_include_regions": [forbidden]},
                ],
            }
        )

    unsupported_followups = ["입장료도 알려줘", "오늘 영업 중인지 확인해줘", "버스 번호와 소요시간도 알려줘", "실시간 혼잡도 낮은 곳만"]
    for message in unsupported_followups * 10:
        rows.append(
            {
                "category": "expanded_unsupported_followup",
                "turns": [
                    {"message": "서울에서 휠체어 관광지 추천해줘", "min_cards": 1, "must_contain_answer_terms": ["서울"]},
                    {"message": message, "expect_no_cards": True, "must_include_answer_any_terms": ["현재 MVP", "확인된 데이터", "추천하지 않겠습니다"]},
                ],
            }
        )

    rng.shuffle(rows)
    for index, row in enumerate(rows, start=1):
        row["id"] = f"TECV{index:03d}"
        row.setdefault("scoring_focus", ["확장 대화 평가"])
    return rows


def main() -> None:
    single = generate_single_questions()
    conversations = generate_conversations()
    _write_jsonl(SINGLE_OUTPUT, single)
    _write_jsonl(CONVERSATION_OUTPUT, conversations)
    print(f"Wrote {len(single)} rows to {SINGLE_OUTPUT.relative_to(PROJECT_ROOT)}")
    print(f"Wrote {len(conversations)} rows to {CONVERSATION_OUTPUT.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()

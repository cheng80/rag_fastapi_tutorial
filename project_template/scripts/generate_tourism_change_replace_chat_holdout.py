from __future__ import annotations

import json
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

DEFAULT_OUTPUT = PROJECT_ROOT / "data" / "eval" / "tourism_change_replace_chat_holdout.jsonl"


def _row(row_id: str, category: str, turns: list[dict[str, object]], focus: str) -> dict[str, object]:
    return {
        "id": row_id,
        "category": category,
        "turns": turns,
        "scoring_focus": [focus],
    }


def generate_rows() -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []

    region_switches = [
        ("서울", "부산", "서울특별시", "TCX001"),
        ("부산", "서울", "부산광역시", "TCX002"),
        ("대구", "대전", "대구광역시", "TCX003"),
        ("강릉", "속초", "강릉", "TCX004"),
        ("제주시", "서귀포시", "제주시", "TCX005"),
        ("서울 중구", "부산 중구", "서울특별시 중구", "TCX006"),
        ("부산 중구", "서울 중구", "부산광역시 중구", "TCX007"),
        ("인천 중구", "대구 중구", "인천광역시 중구", "TCX008"),
    ]
    for start, target, forbidden, row_id in region_switches:
        rows.append(
            _row(
                row_id,
                "chat_region_switch",
                [
                    {
                        "message": f"{start}에서 휠체어 관광지 추천해줘",
                        "min_cards": 1,
                        "must_contain_answer_terms": [start.split()[0]],
                    },
                    {
                        "message": f"{start} 말고 {target}으로 다시 볼래",
                        "min_cards": 1,
                        "max_cards": 5,
                        "must_contain_answer_terms": [target],
                        "must_not_include_regions": [forbidden],
                        "must_include_any_card_terms": [["휠체어", "장애인"]],
                    },
                ],
                "명시 지역 교체가 이전 지역 카드를 남기지 않는지 확인",
            )
        )

    condition_replacements = [
        ("서울", "유모차", "휠체어", [["휠체어", "장애인"]], "TCX009"),
        ("부산", "휠체어", "유모차", [["유모차", "수유실", "영유아", "가족", "기저귀"]], "TCX010"),
        ("대구", "유모차", "장애인 화장실", [["화장실"]], "TCX011"),
        ("제주시", "휠체어", "장애인 주차장", [["주차"]], "TCX012"),
        ("서울", "유모차", "점자블록", [["점자블록", "점자"]], "TCX013"),
        ("대전", "휠체어", "엘리베이터나 승강기", [["엘리베이터", "승강기"]], "TCX014"),
        ("서울", "카페", "공원이나 산책", [["공원", "산책", "숲", "정원"]], "TCX015"),
        ("부산 중구", "먹거리", "휠체어", [["휠체어", "장애인"]], "TCX016"),
    ]
    for region, original, replacement, required_terms, row_id in condition_replacements:
        rows.append(
            _row(
                row_id,
                "chat_condition_replace",
                [
                    {
                        "message": f"{region}에서 {original} 기준 관광지 추천해줘",
                        "min_cards": 1,
                        "must_contain_answer_terms": [region],
                    },
                    {
                        "message": f"{original} 말고 {replacement} 기준으로 다시",
                        "min_cards": 1,
                        "max_cards": 5,
                        "must_contain_answer_terms": [region],
                        "must_include_any_card_terms": required_terms,
                    },
                ],
                "조건 교체가 이전 지역을 유지하고 새 조건 근거가 있는 카드로 바뀌는지 확인",
            )
        )

    exclude_not_replace = [
        ("서울", "시장", [["시장"]], "TCX017"),
        ("부산", "호텔이나 숙박", [["호텔", "숙박", "리조트", "펜션"]], "TCX018"),
        ("대구", "식당이나 카페", [["식당", "카페", "커피", "맛집", "레스토랑"]], "TCX019"),
        ("제주시", "숙박", [["호텔", "숙박", "리조트", "펜션"]], "TCX020"),
        ("강릉", "시장", [["시장"]], "TCX021"),
        ("서울", "숙박", [["호텔", "숙박", "리조트", "펜션"]], "TCX022"),
    ]
    for region, excluded, forbidden_terms, row_id in exclude_not_replace:
        rows.append(
            _row(
                row_id,
                "chat_exclude_not_replace",
                [
                    {
                        "message": f"{region}에서 아이랑 갈 곳 추천해줘",
                        "min_cards": 1,
                        "must_contain_answer_terms": [region],
                    },
                    {
                        "message": f"{excluded}은 빼고 계속 추천해줘",
                        "min_cards": 1,
                        "max_cards": 5,
                        "must_contain_answer_terms": [region],
                        "must_not_include_card_terms": forbidden_terms,
                    },
                ],
                "단순 제외가 조건 교체나 지역 변경으로 오인되지 않는지 확인",
            )
        )

    mixed_three_turns = [
        (
            "TCX023",
            "서울",
            ["서울"],
            [
                {"message": "서울에서 유모차 관광지 추천해줘", "min_cards": 1, "must_contain_answer_terms": ["서울"]},
                {
                    "message": "유모차 말고 휠체어 기준으로",
                    "min_cards": 1,
                    "must_contain_answer_terms": ["서울"],
                    "must_include_any_card_terms": [["휠체어", "장애인"]],
                },
                {
                    "message": "더 보기",
                    "min_cards": 1,
                    "max_cards": 100,
                    "must_contain_answer_terms": ["서울"],
                    "must_include_any_card_terms": [["휠체어", "장애인"]],
                },
            ],
        ),
        (
            "TCX024",
            "부산 중구",
            ["부산 중구"],
            [
                {"message": "부산 중구에서 휠체어 관광지 추천해줘", "min_cards": 1, "must_contain_answer_terms": ["부산 중구"]},
                {
                    "message": "시장 말고",
                    "min_cards": 1,
                    "must_contain_answer_terms": ["부산 중구"],
                    "must_not_include_card_terms": [["시장"]],
                },
                {
                    "message": "더 보기",
                    "min_cards": 1,
                    "max_cards": 100,
                    "must_contain_answer_terms": ["부산 중구"],
                    "must_not_include_card_terms": [["시장"]],
                },
            ],
        ),
        (
            "TCX025",
            "대구",
            ["대구"],
            [
                {"message": "대구에서 휠체어 관광지 추천해줘", "min_cards": 1, "must_contain_answer_terms": ["대구"]},
                {
                    "message": "중구로 좁혀줘",
                    "min_cards": 1,
                    "must_contain_answer_terms": ["대구 중구"],
                    "must_not_include_regions": ["서울특별시 중구", "부산광역시 중구"],
                },
                {
                    "message": "휠체어 말고 유모차 기준",
                    "min_cards": 1,
                    "must_contain_answer_terms": ["대구 중구"],
                    "must_include_any_card_terms": [["유모차", "수유실", "영유아", "가족", "기저귀"]],
                },
            ],
        ),
        (
            "TCX026",
            "제주시",
            ["제주시"],
            [
                {"message": "북제주군에서 휠체어 관광지 추천해줘", "min_cards": 1, "must_contain_answer_terms": ["제주시"]},
                {
                    "message": "휠체어 말고 아이랑 갈 만한 곳",
                    "min_cards": 1,
                    "must_contain_answer_terms": ["제주시"],
                    "must_include_any_card_terms": [["유모차", "수유실", "영유아", "가족", "어린이", "기저귀"]],
                },
                {
                    "message": "호텔은 빼고",
                    "min_cards": 1,
                    "must_contain_answer_terms": ["제주시"],
                    "must_not_include_card_terms": [["호텔", "숙박", "리조트", "펜션"]],
                    "must_include_any_card_terms": [["유모차", "수유실", "영유아", "가족", "어린이", "기저귀"]],
                },
            ],
        ),
    ]
    for row_id, _region, _terms, turns in mixed_three_turns:
        rows.append(_row(row_id, "chat_change_replace_multiturn", turns, "여러 turn 뒤에도 지역, 교체 조건, 제외 조건이 유지되는지 확인"))

    no_context_rows = [
        ("TCX027", "유모차 말고 휠체어 기준으로", ["지역", "먼저"]),
        ("TCX028", "시장 말고 조용한 곳으로", ["지역", "먼저"]),
        ("TCX029", "서울 말고 부산으로", ["부산"]),
    ]
    for row_id, message, answer_terms in no_context_rows:
        row: dict[str, object]
        if row_id == "TCX029":
            row = _row(
                row_id,
                "chat_no_context_region",
                [
                    {
                        "message": message,
                        "min_cards": 1,
                        "must_contain_answer_terms": answer_terms,
                        "must_not_include_regions": ["서울특별시"],
                    }
                ],
                "맥락 없이도 명시 지역 전환 표현이 새 지역 추천으로 처리되는지 확인",
            )
        else:
            row = _row(
                row_id,
                "chat_no_context_condition",
                [
                    {
                        "message": message,
                        "expect_clarification": True,
                        "expect_no_cards": True,
                        "must_include_answer_any_terms": answer_terms,
                    }
                ],
                "조건 교체/제외만 있고 지역이 없을 때 억지 추천하지 않는지 확인",
            )
        rows.append(row)

    extra_region_switches = [
        ("서울", "제주", "서울특별시"),
        ("제주", "서울", "제주특별자치도"),
        ("부산", "대구", "부산광역시"),
        ("대전", "서울", "대전광역시"),
        ("강원", "부산", "강원"),
        ("경북", "서울", "경상북도"),
        ("서울", "대전", "서울특별시"),
        ("제주시", "서울", "제주시"),
        ("서귀포시", "제주시", "서귀포시"),
        ("대구 중구", "서울 중구", "대구광역시 중구"),
        ("서울 중구", "대구 중구", "서울특별시 중구"),
        ("부산 중구", "인천 중구", "부산광역시 중구"),
        ("대전", "부산 중구", "대전광역시"),
        ("서울", "강릉", "서울특별시"),
        ("강릉", "서울", "강릉"),
        ("인천", "부산", "인천광역시"),
        ("부산", "제주시", "부산광역시"),
        ("제주시", "대구", "제주시"),
        ("대구", "부산 중구", "대구광역시"),
        ("서울 중구", "서귀포시", "서울특별시 중구"),
    ]
    for index, (start, target, forbidden) in enumerate(extra_region_switches, start=30):
        rows.append(
            _row(
                f"TCX{index:03d}",
                "chat_region_switch_extra",
                [
                    {
                        "message": f"{start}에서 휠체어 관광지 추천해줘",
                        "min_cards": 1,
                        "must_contain_answer_terms": [start.split()[0]],
                    },
                    {
                        "message": f"아까 지역 말고 {target}으로 바꿔줘",
                        "min_cards": 1,
                        "max_cards": 5,
                        "must_contain_answer_terms": [target],
                        "must_not_include_regions": [forbidden],
                        "must_include_any_card_terms": [["휠체어", "장애인"]],
                    },
                ],
                "다양한 지역 전환 표현에서 이전 지역 카드가 남지 않는지 확인",
            )
        )

    extra_condition_replacements = [
        ("서울", "휠체어", "유모차", [["유모차", "수유실", "영유아", "가족", "기저귀"]]),
        ("서울", "유모차", "장애인 화장실", [["화장실"]]),
        ("서울", "휠체어", "장애인 주차장", [["주차"]]),
        ("부산", "유모차", "휠체어", [["휠체어", "장애인"]]),
        ("부산", "휠체어", "장애인 화장실", [["화장실"]]),
        ("부산", "유모차", "장애인 주차장", [["주차"]]),
        ("대구", "휠체어", "유모차", [["유모차", "수유실", "영유아", "가족", "기저귀"]]),
        ("대구", "휠체어", "장애인 주차장", [["주차"]]),
        ("대전", "유모차", "휠체어", [["휠체어", "장애인"]]),
        ("대전", "휠체어", "엘리베이터나 승강기", [["엘리베이터", "승강기"]]),
        ("제주시", "유모차", "휠체어", [["휠체어", "장애인"]]),
        ("제주시", "휠체어", "유모차", [["유모차", "수유실", "영유아", "가족", "기저귀"]]),
        ("서귀포시", "유모차", "휠체어", [["휠체어", "장애인"]]),
        ("서귀포시", "휠체어", "장애인 화장실", [["화장실"]]),
        ("서울", "시장", "실내 박물관", [["박물관", "전시관", "미술관", "체험관"]]),
        ("대구", "카페", "실내 박물관", [["박물관", "전시관", "미술관", "체험관"]]),
        ("부산", "숙박", "시장이나 먹거리", [["시장", "먹거리", "식당", "빵"]]),
        ("서울", "실내", "공원이나 산책", [["공원", "산책", "숲", "정원"]]),
        ("부산 중구", "시장", "휠체어", [["휠체어", "장애인"]]),
        ("대구 중구", "휠체어", "유모차", [["유모차", "수유실", "영유아", "가족", "기저귀"]]),
        ("서울", "휠체어", "점자블록", [["점자블록", "점자"]]),
        ("세종", "휠체어", "장애인 주차장", [["주차"]]),
        ("인천", "유모차", "휠체어", [["휠체어", "장애인"]]),
        ("서울", "시장", "휠체어", [["휠체어", "장애인"]]),
    ]
    for index, (region, original, replacement, required_terms) in enumerate(extra_condition_replacements, start=50):
        rows.append(
            _row(
                f"TCX{index:03d}",
                "chat_condition_replace_extra",
                [
                    {
                        "message": f"{region}에서 {original} 기준으로 추천해줘",
                        "min_cards": 1,
                        "must_contain_answer_terms": [region],
                    },
                    {
                        "message": f"{original} 말고 {replacement} 쪽으로 바꿔줘",
                        "min_cards": 1,
                        "max_cards": 5,
                        "must_contain_answer_terms": [region],
                        "must_include_any_card_terms": required_terms,
                    },
                ],
                "다양한 조건 교체가 지역을 유지하고 새 조건 근거를 반영하는지 확인",
            )
        )

    extra_excludes = [
        ("서울", "시장", [["시장"]]),
        ("서울", "식당이나 카페", [["식당", "카페", "커피", "맛집", "레스토랑"]]),
        ("부산", "시장", [["시장"]]),
        ("부산", "숙박", [["호텔", "숙박", "리조트", "펜션"]]),
        ("대구", "시장", [["시장"]]),
        ("대구", "숙박", [["호텔", "숙박", "리조트", "펜션"]]),
        ("대전", "카페", [["카페", "커피", "레스토랑"]]),
        ("제주시", "숙박", [["호텔", "숙박", "리조트", "펜션"]]),
        ("서귀포시", "숙박", [["호텔", "숙박", "리조트", "펜션"]]),
        ("강릉", "숙박", [["호텔", "숙박", "리조트", "펜션"]]),
        ("서울 중구", "시장", [["시장"]]),
        ("부산 중구", "식당", [["식당", "카페", "커피", "맛집", "레스토랑"]]),
        ("대구 중구", "카페", [["카페", "커피", "레스토랑"]]),
        ("서울", "먹자골목", [["먹자골목", "맛집", "식당"]]),
        ("부산", "먹자골목", [["먹자골목", "맛집", "식당"]]),
        ("대구", "쇼핑몰", [["쇼핑몰", "상가"]]),
    ]
    for index, (region, excluded, forbidden_terms) in enumerate(extra_excludes, start=74):
        rows.append(
            _row(
                f"TCX{index:03d}",
                "chat_exclude_not_replace_extra",
                [
                    {
                        "message": f"{region}에서 휠체어 관광지 추천해줘",
                        "min_cards": 1,
                        "must_contain_answer_terms": [region],
                    },
                    {
                        "message": f"{excluded} 말고 다른 후보로",
                        "min_cards": 1,
                        "max_cards": 5,
                        "must_contain_answer_terms": [region],
                        "must_not_include_card_terms": forbidden_terms,
                        "must_include_any_card_terms": [["휠체어", "장애인"]],
                    },
                ],
                "단순 제외 표현이 이전 지역과 핵심 조건을 유지하는지 확인",
            )
        )

    extra_multiturns: list[list[dict[str, object]]] = [
        [
            {"message": "서울에서 휠체어 관광지 추천해줘", "min_cards": 1, "must_contain_answer_terms": ["서울"]},
            {"message": "공원 위주로", "min_cards": 1, "must_contain_answer_terms": ["서울"], "must_include_any_card_terms": [["공원", "산책", "숲", "정원"]]},
            {"message": "카페는 빼고", "min_cards": 1, "must_contain_answer_terms": ["서울"], "must_not_include_card_terms": [["카페", "커피"]], "must_include_any_card_terms": [["공원", "산책", "숲", "정원"]]},
        ],
        [
            {"message": "부산에서 유모차 관광지 추천해줘", "min_cards": 1, "must_contain_answer_terms": ["부산"]},
            {"message": "유모차 말고 휠체어", "min_cards": 1, "must_contain_answer_terms": ["부산"], "must_include_any_card_terms": [["휠체어", "장애인"]]},
            {"message": "시장 말고", "min_cards": 1, "must_contain_answer_terms": ["부산"], "must_not_include_card_terms": [["시장"]], "must_include_any_card_terms": [["휠체어", "장애인"]]},
        ],
        [
            {"message": "제주시에서 휠체어 관광지 추천해줘", "min_cards": 1, "must_contain_answer_terms": ["제주시"]},
            {"message": "유모차 기준으로 바꿔줘", "min_cards": 1, "must_contain_answer_terms": ["제주시"], "must_include_any_card_terms": [["유모차", "수유실", "영유아", "가족", "기저귀"]]},
            {"message": "더 보기", "min_cards": 1, "max_cards": 100, "must_contain_answer_terms": ["제주시"], "must_include_any_card_terms": [["유모차", "수유실", "영유아", "가족", "기저귀"]]},
        ],
        [
            {"message": "대전에서 휠체어 관광지 추천해줘", "min_cards": 1, "must_contain_answer_terms": ["대전"]},
            {"message": "화장실 있는 곳으로", "min_cards": 1, "must_contain_answer_terms": ["대전"], "must_include_any_card_terms": [["화장실"]]},
            {"message": "숙박은 빼고", "min_cards": 1, "must_contain_answer_terms": ["대전"], "must_not_include_card_terms": [["호텔", "숙박", "리조트", "펜션"]], "must_include_any_card_terms": [["화장실"]]},
        ],
        [
            {"message": "서울에서 유모차 관광지 추천해줘", "min_cards": 1, "must_contain_answer_terms": ["서울"]},
            {"message": "서울 말고 부산으로", "min_cards": 1, "must_contain_answer_terms": ["부산"], "must_not_include_regions": ["서울특별시"]},
            {"message": "유모차 말고 휠체어", "min_cards": 1, "must_contain_answer_terms": ["부산"], "must_include_any_card_terms": [["휠체어", "장애인"]]},
        ],
        [
            {"message": "부산에서 휠체어 관광지 추천해줘", "min_cards": 1, "must_contain_answer_terms": ["부산"]},
            {"message": "중구로 좁혀줘", "min_cards": 1, "must_contain_answer_terms": ["부산 중구"], "must_not_include_regions": ["서울특별시 중구"]},
            {"message": "시장 말고", "min_cards": 1, "must_contain_answer_terms": ["부산 중구"], "must_not_include_card_terms": [["시장"]]},
        ],
        [
            {"message": "대구에서 휠체어 관광지 추천해줘", "min_cards": 1, "must_contain_answer_terms": ["대구"]},
            {"message": "중구로 좁혀줘", "min_cards": 1, "must_contain_answer_terms": ["대구 중구"], "must_not_include_regions": ["부산광역시 중구"]},
            {"message": "더 보기", "min_cards": 1, "max_cards": 100, "must_contain_answer_terms": ["대구 중구"]},
        ],
        [
            {"message": "서울에서 휠체어 관광지 추천해줘", "min_cards": 1, "must_contain_answer_terms": ["서울"]},
            {"message": "점자블록 확인되는 곳", "min_cards": 1, "must_contain_answer_terms": ["서울"], "must_include_any_card_terms": [["점자블록", "점자"]]},
            {"message": "더 보기", "min_cards": 1, "max_cards": 100, "must_contain_answer_terms": ["서울"], "must_include_any_card_terms": [["점자블록", "점자"]]},
        ],
        [
            {"message": "서울에서 시장 관광지 추천해줘", "min_cards": 1, "must_contain_answer_terms": ["서울"], "must_include_any_card_terms": [["시장"]]},
            {"message": "시장 말고 휠체어 기준으로", "min_cards": 1, "must_contain_answer_terms": ["서울"], "must_include_any_card_terms": [["휠체어", "장애인"]]},
            {"message": "숙박은 빼고", "min_cards": 1, "must_contain_answer_terms": ["서울"], "must_not_include_card_terms": [["호텔", "숙박", "리조트", "펜션"]], "must_include_any_card_terms": [["휠체어", "장애인"]]},
        ],
        [
            {"message": "서울 중구에서 휠체어 관광지 추천해줘", "min_cards": 1, "must_contain_answer_terms": ["서울 중구"]},
            {"message": "서울 중구 말고 부산 중구", "min_cards": 1, "must_contain_answer_terms": ["부산 중구"], "must_not_include_regions": ["서울특별시 중구"]},
            {"message": "더 보기", "min_cards": 1, "max_cards": 100, "must_contain_answer_terms": ["부산 중구"]},
        ],
        [
            {"message": "서귀포시에서 휠체어 관광지 추천해줘", "min_cards": 1, "must_contain_answer_terms": ["서귀포시"]},
            {"message": "서귀포시 말고 제주시", "min_cards": 1, "must_contain_answer_terms": ["제주시"], "must_not_include_regions": ["서귀포시"]},
            {"message": "장애인 주차장 있는 곳", "min_cards": 1, "must_contain_answer_terms": ["제주시"], "must_include_any_card_terms": [["주차"]]},
        ],
        [
            {"message": "서울에서 아이랑 갈만한 곳 추천해줘", "min_cards": 1, "must_contain_answer_terms": ["서울"]},
            {"message": "아이 말고 어르신이랑", "min_cards": 1, "must_contain_answer_terms": ["서울"]},
            {"message": "카페는 빼고", "min_cards": 1, "must_contain_answer_terms": ["서울"], "must_not_include_card_terms": [["카페", "커피"]]},
        ],
    ]
    for index, turns in enumerate(extra_multiturns, start=90):
        rows.append(
            _row(
                f"TCX{index:03d}",
                "chat_change_replace_multiturn_extra",
                turns,
                "세 turn 이상에서 지역, 조건 교체, 제외, 더 보기 맥락이 유지되는지 확인",
            )
        )

    extra_no_context = [
        ("휠체어 말고 유모차로", ["지역", "먼저"]),
        ("호텔은 빼고 관광지만", ["지역", "먼저"]),
        ("공원 위주로 더 보여줘", ["지역", "먼저"]),
        ("시장 말고 공원으로", ["지역", "먼저"]),
        ("점자블록 있는 곳만", ["지역", "먼저"]),
        ("대구 말고 서울로", ["서울"]),
        ("부산 말고 제주시로", ["제주시"]),
        ("제주 말고 대전으로", ["대전"]),
        ("서울 말고 강릉으로", ["강릉"]),
        ("대전 말고 부산 중구로", ["부산 중구"]),
    ]
    for index, (message, answer_terms) in enumerate(extra_no_context, start=102):
        if "말고" in message and any(region in message for region in ["서울", "부산", "대구", "대전", "제주", "제주시", "강릉", "중구"]):
            target = answer_terms[0]
            forbidden = message.split("말고", maxsplit=1)[0].strip()
            rows.append(
                _row(
                    f"TCX{index:03d}",
                    "chat_no_context_region_extra",
                    [
                        {
                            "message": message,
                            "min_cards": 1,
                            "must_contain_answer_terms": [target],
                            "must_not_include_regions": [forbidden],
                        }
                    ],
                    "맥락 없는 명시 지역 전환은 새 지역 추천으로 처리되는지 확인",
                )
            )
        else:
            rows.append(
                _row(
                    f"TCX{index:03d}",
                    "chat_no_context_condition_extra",
                    [
                        {
                            "message": message,
                            "expect_clarification": True,
                            "expect_no_cards": True,
                            "must_include_answer_any_terms": answer_terms,
                        }
                    ],
                    "지역 없는 조건/제외 요청은 억지 추천하지 않는지 확인",
                )
            )

    simultaneous_switches = [
        ("서울", "유모차", "부산", "휠체어", "서울특별시", [["휠체어", "장애인"]]),
        ("부산", "휠체어", "서울", "유모차", "부산광역시", [["유모차", "수유실", "영유아", "가족", "기저귀"]]),
        ("대구", "시장", "대전", "장애인 화장실", "대구광역시", [["화장실"]]),
        ("제주시", "휠체어", "서귀포시", "유모차", "제주시", [["유모차", "수유실", "영유아", "가족", "기저귀"]]),
        ("서귀포시", "유모차", "제주시", "장애인 주차장", "서귀포시", [["주차"]]),
        ("서울 중구", "휠체어", "부산 중구", "유모차", "서울특별시 중구", [["유모차", "수유실", "영유아", "가족", "기저귀"]]),
        ("부산 중구", "시장", "서울 중구", "휠체어", "부산광역시 중구", [["휠체어", "장애인"]]),
        ("대전", "휠체어", "서울", "점자블록", "대전광역시", [["점자블록", "점자"]]),
        ("서울", "실내", "강릉", "공원이나 산책", "서울특별시", [["공원", "산책", "숲", "정원"]]),
        ("강릉", "숙박", "서울", "휠체어", "강릉", [["휠체어", "장애인"]]),
        ("인천", "휠체어", "부산", "장애인 주차장", "인천광역시", [["주차"]]),
        ("세종", "휠체어", "대전", "엘리베이터나 승강기", "세종", [["엘리베이터", "승강기"]]),
    ]
    for offset, (start_region, start_condition, target_region, target_condition, forbidden_region, required_terms) in enumerate(
        simultaneous_switches,
        start=112,
    ):
        rows.append(
            _row(
                f"TCX{offset:03d}",
                "chat_region_and_condition_switch",
                [
                    {
                        "message": f"{start_region}에서 {start_condition} 기준으로 추천해줘",
                        "min_cards": 1,
                        "must_contain_answer_terms": [start_region],
                    },
                    {
                        "message": f"아니 {start_region} 말고 {target_region}, {start_condition} 말고 {target_condition} 기준",
                        "min_cards": 1,
                        "max_cards": 5,
                        "must_contain_answer_terms": [target_region],
                        "must_not_include_regions": [forbidden_region],
                        "must_include_any_card_terms": required_terms,
                    },
                ],
                "지역과 조건을 동시에 교체해도 이전 지역/조건이 결과를 오염시키지 않는지 확인",
            )
        )

    indirect_condition_turns = [
        ("서울", "엄마가 계단을 힘들어해", [["휠체어", "장애인", "경사로", "턱이 없어", "엘리베이터"]]),
        ("부산", "아이가 어려서 유모차로 움직여야 해", [["유모차", "수유실", "영유아", "가족", "기저귀"]]),
        ("대구", "할머니랑 가서 많이 걷기 어려워", [["휠체어", "장애인", "경사로", "의자", "쉬움"]]),
        ("제주시", "시각장애인 친구랑 가", [["점자", "점자블록", "오디오가이드", "시각장애"]]),
        ("서울", "청각장애인 동행이 있어", [["수어", "수화", "자막", "청각장애"]]),
        ("대전", "보조견이 같이 들어갈 수 있어야 해", [["보조견", "안내견"]]),
        ("부산 중구", "엄마가 계단을 힘들어해서 경사로가 필요해", [["휠체어", "장애인", "경사로", "턱이 없어"]]),
        ("서울 중구", "어르신이랑 천천히 볼 수 있는 곳", [["휠체어", "장애인", "의자", "쉬움"]]),
    ]
    for offset, (region, condition_message, required_terms) in enumerate(indirect_condition_turns, start=124):
        rows.append(
            _row(
                f"TCX{offset:03d}",
                "chat_indirect_condition_followup",
                [
                    {
                        "message": f"{region} 관광지 추천해줘",
                        "min_cards": 1,
                        "must_contain_answer_terms": [region],
                    },
                    {
                        "message": condition_message,
                        "min_cards": 1,
                        "must_contain_answer_terms": [region],
                        "must_include_any_card_terms": required_terms,
                    },
                ],
                "직접 키워드가 약한 후속 조건도 이전 지역 맥락 안에서 접근성 조건으로 반영되는지 확인",
            )
        )

    ambiguous_region_narrowing = [
        ("서울", "중구로 좁혀줘", "서울 중구", ["부산광역시 중구", "대구광역시 중구"]),
        ("부산", "중구 쪽으로", "부산 중구", ["서울특별시 중구", "대구광역시 중구"]),
        ("대구", "중구만 볼래", "대구 중구", ["서울특별시 중구", "부산광역시 중구"]),
        ("인천", "중구로 바꿔줘", "인천 중구", ["서울특별시 중구", "부산광역시 중구"]),
        ("서울", "강서구로 좁혀줘", "서울 강서구", ["부산광역시 강서구"]),
        ("부산", "강서구로 좁혀줘", "부산 강서구", ["서울특별시 강서구"]),
        ("경남", "고성군만", "고성군", ["강원특별자치도 고성군"]),
        ("강원", "고성군으로", "고성군", ["경상남도 고성군"]),
    ]
    for offset, (area, followup, answer_region, forbidden_regions) in enumerate(ambiguous_region_narrowing, start=132):
        rows.append(
            _row(
                f"TCX{offset:03d}",
                "chat_ambiguous_region_narrowing",
                [
                    {
                        "message": f"{area}에서 휠체어 관광지 추천해줘",
                        "min_cards": 1,
                        "must_contain_answer_terms": [area],
                    },
                    {
                        "message": followup,
                        "min_cards": 1,
                        "must_contain_answer_terms": [answer_region],
                        "must_not_include_regions": forbidden_regions,
                    },
                ],
                "상위 지역 맥락이 있을 때 중복 시군구명을 해당 광역 안에서 좁히는지 확인",
            )
        )

    exclude_answer_hygiene = [
        ("서울", "시장", [["시장"]]),
        ("부산", "숙박", [["호텔", "숙박", "리조트", "펜션"]]),
        ("대구", "카페", [["카페", "커피"]]),
        ("대전", "식당", [["식당", "맛집", "레스토랑"]]),
        ("제주시", "호텔", [["호텔", "숙박", "리조트", "펜션"]]),
        ("강릉", "먹자골목", [["먹자골목", "맛집", "식당"]]),
        ("서울 중구", "시장", [["시장"]]),
        ("부산 중구", "시장", [["시장"]]),
    ]
    for offset, (region, excluded, forbidden_terms) in enumerate(exclude_answer_hygiene, start=140):
        rows.append(
            _row(
                f"TCX{offset:03d}",
                "chat_exclude_answer_hygiene",
                [
                    {
                        "message": f"{region}에서 휠체어 관광지 추천해줘",
                        "min_cards": 1,
                        "must_contain_answer_terms": [region],
                    },
                    {
                        "message": f"{excluded} 말고 추천해줘",
                        "min_cards": 1,
                        "must_contain_answer_terms": [region],
                        "must_not_include_card_terms": forbidden_terms,
                        "must_not_contain_answer_terms": [excluded],
                        "must_not_include_suggestion_terms": [excluded],
                    },
                ],
                "제외한 선호가 카드뿐 아니라 답변/후속 제안에도 남지 않는지 확인",
            )
        )

    long_context_switches = [
        [
            {"message": "서울에서 휠체어 관광지 추천해줘", "min_cards": 1, "must_contain_answer_terms": ["서울"]},
            {"message": "공원 위주로", "min_cards": 1, "must_contain_answer_terms": ["서울"], "must_include_any_card_terms": [["공원", "산책", "숲", "정원"]]},
            {"message": "서울 말고 부산으로", "min_cards": 1, "must_contain_answer_terms": ["부산"], "must_not_include_regions": ["서울특별시"]},
            {"message": "시장 말고", "min_cards": 1, "must_contain_answer_terms": ["부산"], "must_not_include_card_terms": [["시장"]]},
        ],
        [
            {"message": "부산에서 유모차 관광지 추천해줘", "min_cards": 1, "must_contain_answer_terms": ["부산"]},
            {"message": "중구로 좁혀줘", "min_cards": 1, "must_contain_answer_terms": ["부산 중구"], "must_not_include_regions": ["서울특별시 중구"]},
            {"message": "유모차 말고 휠체어", "min_cards": 1, "must_contain_answer_terms": ["부산 중구"], "must_include_any_card_terms": [["휠체어", "장애인"]]},
            {"message": "더 보기", "min_cards": 1, "max_cards": 100, "must_contain_answer_terms": ["부산 중구"], "must_include_any_card_terms": [["휠체어", "장애인"]]},
        ],
        [
            {"message": "제주시에서 휠체어 관광지 추천해줘", "min_cards": 1, "must_contain_answer_terms": ["제주시"]},
            {"message": "서귀포시로 바꿔줘", "min_cards": 1, "must_contain_answer_terms": ["서귀포시"], "must_not_include_regions": ["제주시"]},
            {"message": "휠체어 말고 유모차", "min_cards": 1, "must_contain_answer_terms": ["서귀포시"], "must_include_any_card_terms": [["유모차", "수유실", "영유아", "가족", "기저귀"]]},
            {"message": "숙박은 빼고", "min_cards": 1, "must_contain_answer_terms": ["서귀포시"], "must_not_include_card_terms": [["호텔", "숙박", "리조트", "펜션"]]},
        ],
        [
            {"message": "서울 중구에서 휠체어 관광지 추천해줘", "min_cards": 1, "must_contain_answer_terms": ["서울 중구"]},
            {"message": "부산 중구로", "min_cards": 1, "must_contain_answer_terms": ["부산 중구"], "must_not_include_regions": ["서울특별시 중구"]},
            {"message": "시장 말고 휠체어 기준", "min_cards": 1, "must_contain_answer_terms": ["부산 중구"], "must_include_any_card_terms": [["휠체어", "장애인"]]},
            {"message": "더 보기", "min_cards": 1, "max_cards": 100, "must_contain_answer_terms": ["부산 중구"]},
        ],
        [
            {"message": "대전에서 휠체어 관광지 추천해줘", "min_cards": 1, "must_contain_answer_terms": ["대전"]},
            {"message": "엘리베이터나 승강기 있는 곳", "min_cards": 1, "must_contain_answer_terms": ["대전"], "must_include_any_card_terms": [["엘리베이터", "승강기"]]},
            {"message": "대전 말고 서울", "min_cards": 1, "must_contain_answer_terms": ["서울"], "must_not_include_regions": ["대전광역시"]},
            {"message": "장애인 주차장 기준", "min_cards": 1, "must_contain_answer_terms": ["서울"], "must_include_any_card_terms": [["주차"]]},
        ],
    ]
    for offset, turns in enumerate(long_context_switches, start=148):
        rows.append(
            _row(
                f"TCX{offset:03d}",
                "chat_long_context_switch",
                turns,
                "네 turn 이상에서 지역 전환, 조건 교체, 제외, 더 보기 맥락이 오염되지 않는지 확인",
            )
        )

    compact_templates = [
        ("서울", "휠체어", "그럼 부산", "부산", "서울특별시", [["휠체어", "장애인"]]),
        ("부산", "유모차", "아니 서울", "서울", "부산광역시", [["유모차", "수유실", "영유아", "가족", "기저귀"]]),
        ("대구", "휠체어", "그럼 중구", "대구 중구", "부산광역시 중구", [["휠체어", "장애인"]]),
        ("서울", "유모차", "아니 휠체어", "서울", "부산광역시", [["휠체어", "장애인"]]),
        ("부산", "시장", "그럼 실내", "부산", "서울특별시", [["실내", "박물관", "전시관", "미술관"]]),
        ("제주시", "휠체어", "그럼 주차장", "제주시", "서귀포시", [["주차"]]),
        ("서귀포시", "유모차", "아니 제주시", "제주시", "서귀포시", [["휠체어", "장애인", "주차"]]),
        ("서울 중구", "휠체어", "아니 부산 중구", "부산 중구", "서울특별시 중구", [["휠체어", "장애인"]]),
    ]
    for offset, (region, condition, followup, answer_region, forbidden_region, required_terms) in enumerate(compact_templates, start=153):
        rows.append(
            _row(
                f"TCX{offset:03d}",
                "chat_short_followup",
                [
                    {
                        "message": f"{region}에서 {condition} 기준으로 추천해줘",
                        "min_cards": 1,
                        "must_contain_answer_terms": [region],
                    },
                    {
                        "message": followup,
                        "min_cards": 1,
                        "must_contain_answer_terms": [answer_region],
                        "must_not_include_regions": [forbidden_region],
                        "must_include_any_card_terms": required_terms,
                    },
                ],
                "짧은 후속 발화가 이전 맥락을 적절히 사용하거나 교체하는지 확인",
            )
        )

    no_context_more = [
        ("TCX161", "더 보기", ["지역", "먼저"]),
        ("TCX162", "그중 시장 말고", ["지역", "먼저"]),
        ("TCX163", "아니 휠체어로", ["지역", "먼저"]),
        ("TCX164", "중구로 좁혀줘", ["어느", "중구", "지역"]),
        ("TCX165", "강서구만 볼래", ["어느", "강서구", "지역"]),
        ("TCX166", "고성군으로", ["어느", "고성군", "지역"]),
    ]
    for row_id, message, answer_terms in no_context_more:
        rows.append(
            _row(
                row_id,
                "chat_no_context_followup_extra",
                [
                    {
                        "message": message,
                        "expect_clarification": True,
                        "expect_no_cards": True,
                        "must_include_answer_any_terms": answer_terms,
                    }
                ],
                "맥락 없는 후속형 표현은 이전 대화가 없는 상태에서 억지 추천하지 않는지 확인",
            )
        )

    mixed_region_legacy = [
        ("청원군", "청주시", "서울", "청주시"),
        ("마산시", "창원시", "부산", "창원시"),
        ("진해시", "창원시", "대전", "창원시"),
        ("남제주군", "서귀포시", "제주시", "서귀포시"),
        ("북제주군", "제주시", "서귀포시", "제주시"),
    ]
    for offset, (legacy, replacement, target, forbidden) in enumerate(mixed_region_legacy, start=167):
        rows.append(
            _row(
                f"TCX{offset:03d}",
                "chat_legacy_region_switch",
                [
                    {
                        "message": f"{legacy}에서 휠체어 관광지 추천해줘",
                        "min_cards": 1,
                        "must_contain_answer_terms": [replacement],
                    },
                    {
                        "message": f"{legacy} 말고 {target}으로",
                        "min_cards": 1,
                        "must_contain_answer_terms": [target],
                        "must_not_include_regions": [forbidden],
                    },
                ],
                "통합된 과거 지명 맥락 뒤 명시 지역 전환이 이전 통합 지역을 남기지 않는지 확인",
            )
        )

    dense_condition_sequences = [
        ("서울", ["휠체어", "장애인 화장실", "장애인 주차장"], [["화장실"], ["주차"]]),
        ("부산", ["유모차", "수유실", "휠체어"], [["수유실", "기저귀"], ["휠체어", "장애인"]]),
        ("대구", ["휠체어", "점자블록", "장애인 화장실"], [["점자블록", "점자"], ["화장실"]]),
        ("대전", ["휠체어", "엘리베이터", "장애인 주차장"], [["엘리베이터", "승강기"], ["주차"]]),
        ("제주시", ["유모차", "휠체어", "장애인 주차장"], [["휠체어", "장애인"], ["주차"]]),
        ("서귀포시", ["휠체어", "유모차", "장애인 화장실"], [["유모차", "수유실", "영유아", "가족", "기저귀"], ["화장실"]]),
        ("서울 중구", ["휠체어", "장애인 화장실", "장애인 주차장"], [["화장실"], ["주차"]]),
        ("부산 중구", ["휠체어", "시장", "장애인 화장실"], [["시장"], ["화장실"]]),
        ("강릉", ["휠체어", "공원", "장애인 주차장"], [["공원", "산책", "숲", "정원"], ["주차"]]),
        ("세종", ["휠체어", "장애인 화장실", "장애인 주차장"], [["화장실"], ["주차"]]),
    ]
    for offset, (region, conditions, required_terms) in enumerate(dense_condition_sequences, start=172):
        first, second, third = conditions
        second_required, third_required = required_terms
        rows.append(
            _row(
                f"TCX{offset:03d}",
                "chat_dense_condition_sequence",
                [
                    {"message": f"{region}에서 {first} 기준 추천해줘", "min_cards": 1, "must_contain_answer_terms": [region]},
                    {
                        "message": f"{second}도 봐줘",
                        "min_cards": 1,
                        "must_contain_answer_terms": [region],
                        "must_include_any_card_terms": second_required,
                    },
                    {
                        "message": f"{second} 말고 {third} 기준으로",
                        "min_cards": 1,
                        "must_contain_answer_terms": [region],
                        "must_include_any_card_terms": third_required,
                    },
                ],
                "조건 추가 뒤 조건 교체를 해도 이전 추가 조건이 과하게 남지 않는지 확인",
            )
        )

    more_context_preservation = [
        ("서울", "휠체어", [["휠체어", "장애인"]]),
        ("부산", "유모차", [["유모차", "수유실", "영유아", "가족", "기저귀"]]),
        ("대구", "장애인 화장실", [["화장실"]]),
        ("대전", "장애인 주차장", [["주차"]]),
        ("제주시", "휠체어", [["휠체어", "장애인"]]),
        ("서귀포시", "유모차", [["유모차", "수유실", "영유아", "가족", "기저귀"]]),
        ("서울 중구", "휠체어", [["휠체어", "장애인"]]),
        ("부산 중구", "장애인 화장실", [["화장실"]]),
        ("강릉", "휠체어", [["휠체어", "장애인"]]),
        ("세종", "장애인 주차장", [["주차"]]),
        ("인천", "유모차", [["유모차", "수유실", "영유아", "가족", "기저귀"]]),
        ("광주광역시", "휠체어", [["휠체어", "장애인"]]),
        ("울산", "장애인 화장실", [["화장실"]]),
        ("경기", "휠체어", [["휠체어", "장애인"]]),
        ("경남", "장애인 주차장", [["주차"]]),
        ("전북", "유모차", [["유모차", "수유실", "영유아", "가족", "기저귀"]]),
        ("전남", "휠체어", [["휠체어", "장애인"]]),
        ("충북", "장애인 화장실", [["화장실"]]),
        ("충남", "장애인 주차장", [["주차"]]),
        ("경북", "휠체어", [["휠체어", "장애인"]]),
    ]
    for offset, (region, condition, required_terms) in enumerate(more_context_preservation, start=182):
        answer_terms = ["광주"] if region == "광주광역시" else [region]
        rows.append(
            _row(
                f"TCX{offset:03d}",
                "chat_more_context_preservation",
                [
                    {
                        "message": f"{region}에서 {condition} 기준 관광지 추천해줘",
                        "min_cards": 1,
                        "must_contain_answer_terms": answer_terms,
                        "must_include_any_card_terms": required_terms,
                    },
                    {
                        "message": "더 보기",
                        "min_cards": 1,
                        "max_cards": 100,
                        "must_contain_answer_terms": answer_terms,
                        "must_include_any_card_terms": required_terms,
                    },
                ],
                "더 보기 후속 요청이 이전 지역과 조건을 잃지 않는지 확인",
            )
        )

    return rows


def main() -> None:
    rows = generate_rows()
    DEFAULT_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with DEFAULT_OUTPUT.open("w", encoding="utf-8") as file:
        for row in rows:
            file.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(f"Wrote {len(rows)} rows to {DEFAULT_OUTPUT.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()

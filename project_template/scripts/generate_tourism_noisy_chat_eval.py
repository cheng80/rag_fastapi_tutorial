from __future__ import annotations

import json
from pathlib import Path
import sys
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


DEFAULT_OUTPUT = PROJECT_ROOT / "data" / "eval" / "tourism_noisy_chat_eval_20260517.jsonl"


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        for row in rows:
            file.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def build_rows() -> list[dict[str, Any]]:
    return [
        {
            "id": "TNOISY001",
            "category": "no_spacing_region_replace",
            "message": "서울말고부산휠체여가능한곳추천좀",
            "min_cards": 1,
            "max_cards": 5,
            "must_contain_answer_terms": ["부산"],
            "must_not_include_regions": ["서울특별시"],
            "must_include_any_card_terms": [["휠체어", "장애인", "무장애"]],
            "scoring_focus": ["무띄어쓰기", "오타", "지역 교체"],
        },
        {
            "id": "TNOISY002",
            "category": "legacy_region_spacing_typo",
            "message": "남 제주군 유모챠 실내관광지 추천좀",
            "min_cards": 1,
            "max_cards": 5,
            "must_contain_answer_terms": ["서귀포시"],
            "must_include_any_card_terms": [["유모차", "수유실", "영유아", "기저귀", "실내", "박물관", "전시관"]],
            "scoring_focus": ["과거 지명 띄어쓰기", "유모차 오타"],
        },
        {
            "id": "TNOISY003",
            "category": "facility_spacing",
            "message": "대구점자 블록있는카드만",
            "min_cards": 1,
            "max_cards": 5,
            "must_contain_answer_terms": ["대구"],
            "must_include_any_card_terms": [["점자블록", "점자"]],
            "scoring_focus": ["시설명 띄어쓰기", "근거 필수"],
        },
        {
            "id": "TNOISY004",
            "category": "or_no_spacing",
            "message": "성남시수어자막둘중하나있는곳",
            "min_cards": 1,
            "max_cards": 5,
            "must_contain_answer_terms": ["성남"],
            "must_include_any_card_terms": [["수어", "수화", "자막", "영상안내", "문자안내"]],
            "scoring_focus": ["무띄어쓰기", "OR 조건"],
        },
        {
            "id": "TNOISY005",
            "category": "exclude_no_spacing",
            "message": "부산중구시장빼고휠체어갈수있는곳",
            "min_cards": 1,
            "max_cards": 5,
            "must_contain_answer_terms": ["부산", "중구"],
            "must_include_any_card_terms": [["휠체어", "장애인", "무장애"]],
            "must_not_include_card_terms": [["시장", "먹자골목"]],
            "scoring_focus": ["무띄어쓰기", "제외 조건"],
        },
        {
            "id": "TNOISY006",
            "category": "restroom_typo_spacing",
            "message": "서울중구장애 인화장실되는곳",
            "min_cards": 1,
            "max_cards": 5,
            "must_contain_answer_terms": ["서울", "중구"],
            "must_include_any_card_terms": [["화장실"]],
            "scoring_focus": ["띄어쓰기 붕괴", "시설 근거"],
        },
        {
            "id": "TNOISY007",
            "category": "multi_turn_noisy_add",
            "turns": [
                {
                    "message": "강릉휠체어관광지추천좀",
                    "min_cards": 1,
                    "must_contain_answer_terms": ["강릉"],
                    "must_include_any_card_terms": [["휠체어", "장애인", "무장애"]],
                },
                {
                    "message": "그중보조견되는곳만",
                    "min_cards": 1,
                    "must_contain_answer_terms": ["강릉"],
                    "must_include_any_card_terms": [["보조견", "안내견"]],
                },
            ],
            "scoring_focus": ["멀티턴", "무띄어쓰기 조건 추가"],
        },
        {
            "id": "TNOISY008",
            "category": "multi_turn_noisy_replace",
            "turns": [
                {
                    "message": "제주시유모차관광지추천",
                    "min_cards": 1,
                    "must_contain_answer_terms": ["제주시"],
                    "must_include_any_card_terms": [["유모차", "수유실", "영유아", "기저귀", "가족"]],
                },
                {
                    "message": "유모챠말고휠체여기준",
                    "min_cards": 1,
                    "must_contain_answer_terms": ["제주시"],
                    "must_include_any_card_terms": [["휠체어", "장애인", "무장애"]],
                },
            ],
            "scoring_focus": ["멀티턴", "오타", "조건 교체"],
        },
        {
            "id": "TNOISY009",
            "category": "ambiguous_region_noisy",
            "message": "중구휠체어관광지",
            "expect_clarification": True,
            "expect_no_cards": True,
            "must_include_answer_any_terms": ["어느", "중구", "지역"],
            "scoring_focus": ["모호 지역", "추가 질의"],
        },
        {
            "id": "TNOISY010",
            "category": "ambiguous_condition_only",
            "message": "점자블록있는곳",
            "expect_clarification": True,
            "expect_no_cards": True,
            "must_include_answer_any_terms": ["지역", "어느", "먼저"],
            "scoring_focus": ["지역 없음", "추가 질의"],
        },
        {
            "id": "TNOISY011",
            "category": "dangerous_double_region",
            "message": "서울부산휠체어추천",
            "expect_clarification": True,
            "expect_no_cards": True,
            "must_include_answer_any_terms": ["어느", "지역", "서울", "부산"],
            "scoring_focus": ["복수 지역 모호성", "임의 확정 금지"],
        },
        {
            "id": "TNOISY012",
            "category": "soft_noisy",
            "message": "부산중구아이랑편하면좋고수유실은있으면좋음",
            "min_cards": 1,
            "max_cards": 5,
            "must_contain_answer_terms": ["부산", "중구"],
            "scoring_focus": ["무띄어쓰기", "soft 조건 과필터 방지"],
        },
        {
            "id": "TNOISY013",
            "category": "unsupported_noisy",
            "message": "오늘환율알려줘",
            "expected_lookup_mode": "unsupported",
            "expect_no_cards": True,
            "must_include_answer_any_terms": ["현재 MVP", "범위"],
            "scoring_focus": ["미지원 주제", "무띄어쓰기"],
        },
        {
            "id": "TNOISY014",
            "category": "legacy_region_no_spacing",
            "message": "북제주군휠체여관광지",
            "min_cards": 1,
            "max_cards": 5,
            "must_contain_answer_terms": ["제주시"],
            "must_include_any_card_terms": [["휠체어", "장애인", "무장애"]],
            "scoring_focus": ["과거 지명", "오타"],
        },
        {
            "id": "TNOISY015",
            "category": "exclude_context_without_region",
            "message": "시장말고조용한데",
            "expect_clarification": True,
            "expect_no_cards": True,
            "must_include_answer_any_terms": ["지역", "먼저"],
            "scoring_focus": ["맥락 없는 후속 표현", "추가 질의"],
        },
    ]


def main() -> None:
    rows = build_rows()
    write_jsonl(DEFAULT_OUTPUT, rows)
    print(f"Wrote {len(rows)} rows to {DEFAULT_OUTPUT.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()

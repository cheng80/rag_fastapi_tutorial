from __future__ import annotations

import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = PROJECT_ROOT / "data" / "eval" / "tourism_context_medium_chat_eval_v4_120.jsonl"


REGIONS = [
    ("서울 강남구", ["서울", "강남"], 1),
    ("서울 중구", ["서울", "중구"], 1),
    ("부산 중구", ["부산", "중구"], 1),
    ("대구", ["대구"], 1),
    ("경기도 성남시", ["성남"], 0),
    ("전주", ["전주"], 0),
    ("강릉", ["강릉"], 0),
    ("제주시", ["제주"], 0),
    ("서귀포시", ["서귀포"], 0),
    ("대전", ["대전"], 0),
]


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        for row in rows:
            file.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def answer_terms(region_terms: list[str]) -> dict[str, list[str]]:
    return {"must_include_answer_any_terms": region_terms}


def single_rows() -> list[dict]:
    rows: list[dict] = []
    templates = [
        {
            "category": "medium_wheelchair_typo_nearby",
            "message": "{region} 근처에서 휄체어로 갈 수 있는 실내 관광지 추천해줘",
            "expected_conditions": ["휠체어"],
            "must_include_any_card_terms": [["휠체어", "장애인", "무장애", "경사로", "출입통로"]],
        },
        {
            "category": "medium_accessible_restroom",
            "message": "{region}에서 장애인 화장실이 실제 편의정보에 있는 곳만 보고 싶어",
            "expected_conditions": ["화장실"],
            "must_include_any_card_terms": [["장애인 화장실", "화장실", "장애인"]],
        },
        {
            "category": "medium_elevator_abbrev",
            "message": "{region}에서 엘베나 승강기 확인되는 무장애 관광지 있어?",
            "expected_conditions": ["엘리베이터"],
            "must_include_any_card_terms": [["엘리베이터", "승강기", "휠체어", "무장애"]],
        },
        {
            "category": "medium_stroller_family",
            "message": "{region}에서 유아차 끌고 가기 편한 박물관이나 전시관 쪽으로 알려줘",
            "expected_conditions": ["유모차"],
            "must_include_any_card_terms": [["유모차", "유아차", "수유실", "기저귀", "영유아", "휠체어", "무장애"]],
            "first_card_must_include_any_terms": ["박물관", "전시관", "미술관", "갤러리", "전시"],
        },
        {
            "category": "medium_hearing_or",
            "message": "{region}에서 수어 안내나 자막 안내 둘 중 하나라도 확인되는 곳 찾아줘",
            "expected_conditions": ["청각장애"],
            "must_include_any_card_terms": [["수어", "수화", "자막", "영상안내", "문자안내"]],
        },
        {
            "category": "medium_visual_or",
            "message": "{region}에서 안내견 동반이나 점자 안내가 확인되는 관광지 알려줘",
            "expected_conditions": ["보조견", "시각장애"],
            "must_include_any_card_terms": [["보조견", "안내견", "점자", "시각장애"]],
        },
        {
            "category": "medium_parking_and_wheelchair",
            "message": "{region}에서 장애인 주차랑 휠체어 접근이 같이 확인되는 곳이면 좋겠어",
            "expected_conditions": ["주차", "휠체어"],
            "must_include_any_card_terms": [["장애인 주차", "주차", "휠체어", "장애인", "무장애"]],
        },
        {
            "category": "medium_exclude_market",
            "message": "{region}에서 시장 골목 말고 조용하게 볼 수 있는 무장애 관광지 추천해줘",
            "expected_conditions": [],
            "must_not_include_card_terms": [["시장", "먹자골목"]],
        },
        {
            "category": "medium_food_boundary",
            "message": "{region}에서 그냥 맛집 말고 무장애 관광 정보가 확인되는 음식점이나 카페만 있으면 보여줘",
            "expected_conditions": [],
            "must_include_answer_any_terms": ["무장애", "관광", "확인", "후보"],
        },
        {
            "category": "medium_lift_accessibility",
            "message": "{region}에서 휠체어 리프트나 승강 설비가 확인되는 곳 위주로 볼 수 있을까",
            "expected_conditions": ["엘리베이터"],
            "must_include_answer_any_terms": ["리프트", "승강", "엘리베이터", "확인", "조건"],
        },
    ]
    for template_index, template in enumerate(templates, start=1):
        for region_index, (region, terms, min_cards) in enumerate(REGIONS, start=1):
            row = {
                "id": f"TCMEDV4-{template_index:02d}-{region_index:02d}",
                "category": template["category"],
                "message": template["message"].format(region=region),
                "expected_conditions": template["expected_conditions"],
                "min_cards": min_cards,
                "max_cards": 5,
                "scoring_focus": ["medium-length-realistic", template["category"]],
                **answer_terms(terms),
            }
            for key in [
                "must_include_any_card_terms",
                "must_not_include_card_terms",
                "first_card_must_include_any_terms",
            ]:
                if key in template:
                    row[key] = template[key]
            if template["category"] in {"medium_hearing_or", "medium_visual_or", "medium_lift_accessibility"}:
                row["min_cards"] = 0
            rows.append(row)
    return rows


def special_rows() -> list[dict]:
    rows: list[dict] = []
    for index, region in enumerate(["서울강남구", "부산중구", "대구", "성남시", "강릉"], start=1):
        rows.append(
            {
                "id": f"TCMEDV4-NS-{index:02d}",
                "category": "medium_no_spacing_strict",
                "message": f"{region}휠체어화장실둘다되는실내관광지",
                "expected_conditions": ["휠체어", "화장실"],
                "min_cards": 0,
                "max_cards": 5,
                "must_include_answer_any_terms": ["휠체어", "화장실", "조건", "확인"],
                "scoring_focus": ["no-spacing", "strict-condition"],
            }
        )
    rows.extend(
        [
            {
                "id": "TCMEDV4-SPECIAL-AMBIG-01",
                "category": "medium_ambiguous_region",
                "message": "중구에서 휠체어랑 엘리베이터 확인된 관광지만 보고 싶어",
                "expected_conditions": ["휠체어", "엘리베이터"],
                "expect_clarification": True,
                "expect_no_cards": True,
                "must_include_answer_any_terms": ["어느", "중구", "지역"],
                "scoring_focus": ["ambiguous-region", "condition-retention"],
            },
            {
                "id": "TCMEDV4-SPECIAL-AMBIG-02",
                "category": "medium_ambiguous_region",
                "message": "남구에서 유모차 가능한 실내 관광지 추천해줘",
                "expected_conditions": ["유모차"],
                "expect_clarification": True,
                "expect_no_cards": True,
                "must_include_answer_any_terms": ["어느", "남구", "지역"],
                "scoring_focus": ["ambiguous-region", "family-condition"],
            },
            {
                "id": "TCMEDV4-SPECIAL-WRONG-01",
                "category": "medium_wrong_premise",
                "message": "서울 강남구에서 바닷가 산책 가능한 휠체어 관광지 알려줘",
                "expected_conditions": ["휠체어"],
                "expect_no_cards": True,
                "must_include_answer_any_terms": ["확인하지 못했습니다", "조건에 맞는", "강남"],
                "scoring_focus": ["wrong-premise", "no-hallucinated-beach"],
            },
            {
                "id": "TCMEDV4-SPECIAL-UNSUPPORTED-01",
                "category": "medium_unsupported_boundary",
                "message": "내일 비 올지랑 환율 보고 휠체어 관광지도 같이 추천해줘",
                "expected_conditions": ["휠체어"],
                "min_cards": 0,
                "must_include_answer_any_terms": ["관광", "범위", "날씨", "환율", "지원"],
                "scoring_focus": ["mixed-unsupported", "tourism-boundary"],
            },
            {
                "id": "TCMEDV4-SPECIAL-GENERAL-01",
                "category": "medium_general_tourism_scope",
                "message": "성남시 실내식당 추천해줘",
                "expected_conditions": [],
                "expected_lookup_mode": "unsupported",
                "expect_no_cards": True,
                "must_include_answer_any_terms": ["무장애 관광", "일반 관광지", "접근성"],
                "scoring_focus": ["general-place-boundary"],
            },
        ]
    )
    return rows


def multi_turn_rows() -> list[dict]:
    scenarios = [
        {
            "id": "TCMEDV4-TURN-01",
            "category": "medium_turn_add_restroom",
            "turns": [
                {"message": "서울 중구에서 휠체어 가능한 관광지 추천해줘", "min_cards": 1, "must_contain_answer_terms": ["서울", "중구"]},
                {
                    "message": "그중에서 장애인 화장실도 확인되는 곳만 다시 보여줘",
                    "expected_conditions": ["휠체어", "화장실"],
                    "min_cards": 0,
                    "must_include_answer_any_terms": ["화장실", "확인", "조건"],
                },
            ],
            "scoring_focus": ["multi-turn-add-condition"],
        },
        {
            "id": "TCMEDV4-TURN-02",
            "category": "medium_turn_replace_condition",
            "turns": [
                {"message": "부산 중구에서 유모차로 갈 만한 곳 알려줘", "min_cards": 1, "must_contain_answer_terms": ["부산", "중구"]},
                {
                    "message": "유모차 말고 어르신이 걷기 편한 기준으로 바꿔줘",
                    "expected_conditions": ["고령자"],
                    "min_cards": 1,
                    "must_include_answer_any_terms": ["어르신", "걷기", "이동", "조건"],
                },
            ],
            "scoring_focus": ["multi-turn-replace-condition"],
        },
        {
            "id": "TCMEDV4-TURN-03",
            "category": "medium_turn_replace_region",
            "turns": [
                {"message": "강릉에서 보조견 동반 가능한 관광지 추천해줘", "min_cards": 1, "must_contain_answer_terms": ["강릉"]},
                {
                    "message": "강릉 말고 서울 강남구 근처로 다시 찾아줘",
                    "expected_conditions": [],
                    "min_cards": 1,
                    "must_contain_answer_terms": ["서울", "강남"],
                    "must_not_include_regions": ["강릉"],
                },
            ],
            "scoring_focus": ["multi-turn-region-replace"],
        },
        {
            "id": "TCMEDV4-TURN-04",
            "category": "medium_turn_exclude_place",
            "turns": [
                {"message": "전주에서 시장 위주로 볼 곳 추천해줘", "min_cards": 0, "must_contain_answer_terms": ["전주"]},
                {
                    "message": "시장 말고 조용한 곳으로 다시 골라줘",
                    "expected_conditions": [],
                    "min_cards": 0,
                    "must_not_include_card_terms": [["시장", "먹자골목"]],
                    "must_include_answer_any_terms": ["시장", "조용", "조건", "후보"],
                },
            ],
            "scoring_focus": ["multi-turn-exclude-preference"],
        },
        {
            "id": "TCMEDV4-TURN-05",
            "category": "medium_turn_explicit_expand",
            "turns": [
                {"message": "서울 강남구에서 휠체어 관광지 추천해줘", "min_cards": 1, "must_contain_answer_terms": ["서울", "강남"]},
                {
                    "message": "서울 전체로 넓혀서 더 찾아줘",
                    "expected_conditions": ["휠체어"],
                    "min_cards": 1,
                    "must_contain_answer_terms": ["서울"],
                },
            ],
            "scoring_focus": ["explicit-region-expansion"],
        },
    ]
    rows = []
    for repeat in range(1, 4):
        for scenario in scenarios:
            copied = json.loads(json.dumps(scenario, ensure_ascii=False))
            copied["id"] = f"{scenario['id']}-R{repeat}"
            rows.append(copied)
    return rows


def build_rows() -> list[dict]:
    rows = [*single_rows(), *special_rows(), *multi_turn_rows()]
    return rows[:120]


def main() -> None:
    rows = build_rows()
    write_jsonl(DEFAULT_OUTPUT, rows)
    print(json.dumps({"output": str(DEFAULT_OUTPUT.relative_to(PROJECT_ROOT)), "rows": len(rows)}, ensure_ascii=False))


if __name__ == "__main__":
    main()

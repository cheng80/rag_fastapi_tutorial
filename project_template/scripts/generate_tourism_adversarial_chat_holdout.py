from __future__ import annotations

import json
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

DEFAULT_OUTPUT = PROJECT_ROOT / "data" / "eval" / "tourism_adversarial_chat_holdout.jsonl"


def _row(row_id: str, category: str, turns: list[dict[str, object]], focus: str) -> dict[str, object]:
    return {
        "id": row_id,
        "category": category,
        "turns": turns,
        "scoring_focus": [focus],
    }


def generate_rows() -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []

    particle_exclusions = [
        ("ADV001", "서울", "시장", [["시장"]]),
        ("ADV002", "부산", "호텔이나 숙박", [["호텔", "숙박", "리조트", "펜션"]]),
        ("ADV003", "대구", "식당이나 카페", [["식당", "카페", "커피", "맛집", "레스토랑"]]),
        ("ADV004", "제주시", "숙박", [["호텔", "숙박", "리조트", "펜션"]]),
        ("ADV005", "강릉", "시장", [["시장"]]),
        ("ADV006", "대전", "카페는", [["카페", "커피"]]),
        ("ADV007", "서울 중구", "시장은", [["시장"]]),
        ("ADV008", "부산 중구", "식당은", [["식당", "맛집", "레스토랑"]]),
    ]
    for row_id, region, excluded, forbidden in particle_exclusions:
        rows.append(
            _row(
                row_id,
                "particle_exclusion",
                [
                    {"message": f"{region}에서 휠체어 관광지 추천해줘", "min_cards": 1, "must_contain_answer_terms": [region]},
                    {
                        "message": f"{excluded} 빼고 계속",
                        "min_cards": 1,
                        "must_contain_answer_terms": [region],
                        "must_not_include_card_terms": forbidden,
                    },
                ],
                "조사가 붙은 제외 표현이 카드에 금지 선호를 남기지 않는지 확인",
            )
        )

    area_switches = [
        ("ADV009", "강릉", "서울", "강릉", [["휠체어", "장애인"]]),
        ("ADV010", "서울", "강릉", "서울특별시", [["휠체어", "장애인"]]),
        ("ADV011", "부산 중구", "서울", "부산광역시 중구", [["휠체어", "장애인"]]),
        ("ADV012", "서귀포시", "서울", "서귀포시", [["휠체어", "장애인"]]),
        ("ADV013", "청원군", "서울", "청주시", [["휠체어", "장애인"]]),
        ("ADV014", "마산시", "부산", "창원시", [["휠체어", "장애인"]]),
        ("ADV015", "북제주군", "대전", "제주시", [["휠체어", "장애인"]]),
        ("ADV016", "남제주군", "제주시", "서귀포시", [["휠체어", "장애인"]]),
    ]
    for row_id, start, target, forbidden_region, required in area_switches:
        rows.append(
            _row(
                row_id,
                "area_sigungu_leakage",
                [
                    {"message": f"{start}에서 휠체어 관광지 추천해줘", "min_cards": 1},
                    {
                        "message": f"{start} 말고 {target}으로",
                        "min_cards": 1,
                        "must_contain_answer_terms": [target],
                        "must_not_include_regions": [forbidden_region],
                        "must_include_any_card_terms": required,
                    },
                ],
                "시군구/과거 지명에서 광역 지역으로 바꿀 때 이전 sigungu 코드가 새 지역에 섞이지 않는지 확인",
            )
        )

    double_malgo = [
        ("ADV017", "대구", "시장", "대전", "화장실", "대구광역시", [["화장실"]]),
        ("ADV018", "부산 중구", "시장", "서울 중구", "휠체어", "부산광역시 중구", [["휠체어", "장애인"]]),
        ("ADV019", "서울", "실내", "강릉", "공원이나 산책", "서울특별시", [["공원", "산책", "숲", "정원"]]),
        ("ADV020", "강릉", "숙박", "서울", "휠체어", "강릉", [["휠체어", "장애인"]]),
        ("ADV021", "제주시", "휠체어", "서귀포시", "유모차", "제주시", [["유모차", "수유실", "영유아", "가족", "기저귀"]]),
        ("ADV022", "서울 중구", "휠체어", "부산 중구", "화장실", "서울특별시 중구", [["화장실"]]),
    ]
    for row_id, start_region, old_pref, target_region, new_condition, forbidden_region, required in double_malgo:
        rows.append(
            _row(
                row_id,
                "double_malgo_switch",
                [
                    {"message": f"{start_region}에서 {old_pref} 기준 관광지 추천해줘", "min_cards": 1},
                    {
                        "message": f"아니 {start_region} 말고 {target_region}, {old_pref} 말고 {new_condition} 기준",
                        "min_cards": 1,
                        "must_contain_answer_terms": [target_region],
                        "must_not_include_regions": [forbidden_region],
                        "must_include_any_card_terms": required,
                    },
                ],
                "한 문장 안의 두 개 '말고'가 각각 지역 교체와 조건 교체로 분리되는지 확인",
            )
        )

    indirect_followups = [
        ("ADV023", "서울", "엄마가 계단을 힘들어해", [["휠체어", "장애인", "경사로", "턱이 없어"]]),
        ("ADV024", "부산", "아이가 어려서 유모차로 움직여야 해", [["유모차", "수유실", "영유아", "가족", "기저귀"]]),
        ("ADV025", "제주시", "시각장애인 친구랑 가", [["점자", "점자블록", "오디오가이드", "시각장애"]]),
        ("ADV026", "서울", "청각장애인 동행이 있어", [["수어", "수화", "자막", "청각장애"]]),
        ("ADV027", "대전", "보조견이 같이 들어갈 수 있어야 해", [["보조견", "안내견"]]),
        ("ADV028", "서울 중구", "어르신이랑 천천히 볼 수 있는 곳", [["휠체어", "장애인", "의자", "쉬움"]]),
    ]
    for row_id, region, followup, required in indirect_followups:
        rows.append(
            _row(
                row_id,
                "indirect_followup",
                [
                    {"message": f"{region} 관광지 추천해줘", "min_cards": 1, "must_contain_answer_terms": [region]},
                    {
                        "message": followup,
                        "min_cards": 1,
                        "must_contain_answer_terms": [region],
                        "must_include_any_card_terms": required,
                    },
                ],
                "간접 접근성 표현이 맥락 없는 새 질문으로 떨어지지 않는지 확인",
            )
        )

    ambiguous_without_context = [
        ("ADV029", "중구에서 휠체어 관광지 추천해줘", "중구"),
        ("ADV030", "강서구만 볼래", "강서구"),
        ("ADV031", "고성군으로 바꿔줘", "고성군"),
        ("ADV032", "광주에서 휠체어 관광지 추천해줘", "광주"),
    ]
    for row_id, message, expected_term in ambiguous_without_context:
        rows.append(
            _row(
                row_id,
                "ambiguous_without_context",
                [
                    {
                        "message": message,
                        "expect_clarification": True,
                        "expect_no_cards": True,
                        "must_include_answer_any_terms": ["어느", expected_term, "지역"],
                    }
                ],
                "맥락이 없을 때 중복 지명을 임의 지역으로 확정하지 않는지 확인",
            )
        )

    conflicting_sequences = [
        [
            {"message": "서울에서 휠체어 관광지 추천해줘", "min_cards": 1, "must_contain_answer_terms": ["서울"]},
            {"message": "시장 말고", "min_cards": 1, "must_contain_answer_terms": ["서울"], "must_not_include_card_terms": [["시장"]]},
            {"message": "아니 부산 중구로", "min_cards": 1, "must_contain_answer_terms": ["부산 중구"], "must_not_include_regions": ["서울특별시"]},
            {"message": "더 보기", "min_cards": 1, "max_cards": 100, "must_contain_answer_terms": ["부산 중구"]},
        ],
        [
            {"message": "제주시에서 유모차 관광지 추천해줘", "min_cards": 1, "must_contain_answer_terms": ["제주시"]},
            {"message": "숙박은 빼고", "min_cards": 1, "must_contain_answer_terms": ["제주시"], "must_not_include_card_terms": [["호텔", "숙박", "리조트", "펜션"]]},
            {"message": "서귀포시로 바꿔줘", "min_cards": 1, "must_contain_answer_terms": ["서귀포시"], "must_not_include_regions": ["제주시"]},
            {"message": "휠체어 기준", "min_cards": 1, "must_contain_answer_terms": ["서귀포시"], "must_include_any_card_terms": [["휠체어", "장애인"]]},
        ],
        [
            {"message": "강릉에서 휠체어 관광지 추천해줘", "min_cards": 1, "must_contain_answer_terms": ["강릉"]},
            {"message": "강릉 말고 서울", "min_cards": 1, "must_contain_answer_terms": ["서울"], "must_not_include_regions": ["강릉"]},
            {"message": "숙박은 빼고", "min_cards": 1, "must_contain_answer_terms": ["서울"], "must_not_include_card_terms": [["호텔", "숙박", "리조트", "펜션"]]},
        ],
        [
            {"message": "부산에서 시장 관광지 추천해줘", "min_cards": 1, "must_contain_answer_terms": ["부산"], "must_include_any_card_terms": [["시장"]]},
            {"message": "시장 말고 휠체어", "min_cards": 1, "must_contain_answer_terms": ["부산"], "must_include_any_card_terms": [["휠체어", "장애인"]]},
            {"message": "카페는 빼고", "min_cards": 1, "must_contain_answer_terms": ["부산"], "must_not_include_card_terms": [["카페", "커피"]]},
        ],
    ]
    for index, turns in enumerate(conflicting_sequences, start=33):
        rows.append(
            _row(
                f"ADV{index:03d}",
                "conflicting_sequence",
                turns,
                "충돌하는 지역/조건/제외 후속 발화가 이전 상태를 잘 덮어쓰는지 확인",
            )
        )

    no_context_followups = [
        ("ADV037", "그거 말고", ["지역", "먼저"]),
        ("ADV038", "아니 다른 곳", ["지역", "먼저"]),
        ("ADV039", "숙박은 빼고", ["지역", "먼저"]),
        ("ADV040", "휠체어 말고 유모차", ["지역", "먼저"]),
        ("ADV041", "더 보기", ["지역", "먼저"]),
        ("ADV042", "아까 말한 곳 말고", ["지역", "먼저"]),
    ]
    for row_id, message, answer_terms in no_context_followups:
        rows.append(
            _row(
                row_id,
                "no_context_followup",
                [
                    {
                        "message": message,
                        "expect_clarification": True,
                        "expect_no_cards": True,
                        "must_include_answer_any_terms": answer_terms,
                    }
                ],
                "세션 맥락이 없는 후속형 표현은 억지 추천하지 않는지 확인",
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

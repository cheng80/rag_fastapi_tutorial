from __future__ import annotations

import argparse
import json
import random
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = PROJECT_ROOT / "data" / "eval" / "tourism_noisy_realistic_chat_eval_v1_200.jsonl"


REGIONS = [
    ("서울 강남구", ["서울", "강남"]),
    ("서울 중구", ["서울", "중구"]),
    ("부산 중구", ["부산", "중구"]),
    ("강릉", ["강릉"]),
    ("대전", ["대전"]),
    ("대구", ["대구"]),
    ("제주시", ["제주시"]),
    ("서귀포시", ["서귀포"]),
    ("성남시", ["성남"]),
]

CONDITION_PROFILES = [
    {
        "label": "휠체어",
        "terms": [["휠체어", "장애인", "무장애", "턱이 없어", "경사로", "출입통로", "접근로"]],
        "phrases": ["휠체여", "휠채어", "휠챠", "바퀴의자", "휠체어", "휄체어"],
    },
    {
        "label": "장애인 화장실",
        "terms": [["화장실"]],
        "phrases": ["장애인화장실", "장애 화장실", "장애인 장실", "화장실 편한", "화장실잇는"],
    },
    {
        "label": "주차",
        "terms": [["주차"]],
        "phrases": ["주챠", "주차ㅏ", "주자창", "차댈곳", "차대기", "장애인 주챠칸"],
    },
    {
        "label": "엘리베이터",
        "terms": [["엘리베이터", "승강기"]],
        "phrases": ["엘베", "앨베", "엘레베터", "승강기", "엘리베이터"],
    },
    {
        "label": "유모차",
        "terms": [["유모차", "유아용 의자", "수유실", "기저귀", "영유아", "가족", "휠체어", "무장애"]],
        "phrases": ["유모챠", "유모차", "유아차", "아기차", "애기랑"],
    },
    {
        "label": "점자블록",
        "terms": [["점자", "점자블록"]],
        "phrases": ["점자블록", "점자 블럭", "점자 안내", "시각장애 안내", "촉지도"],
    },
    {
        "label": "수어",
        "terms": [["수어", "수화", "자막", "영상안내", "문자안내"]],
        "phrases": ["수어", "수화", "자막", "수어자막", "영상에 글자 안내"],
    },
    {
        "label": "보조견 동반",
        "terms": [["보조견", "안내견"]],
        "phrases": ["보조갼", "보조견", "안내견", "안내견동반", "보조견 같이"],
    },
    {
        "label": "고령자",
        "terms": [["고령자", "어르신", "노약자", "쉬어", "휴식", "의자", "휠체어", "장애인", "경사로", "접근로", "출입통로", "화장실", "대중교통", "무단차", "평탄"]],
        "phrases": ["엄마랑 오래안걷는", "부모님 모시고", "어른 모시고", "무릎 안좋은분", "쉬엄쉬엄 볼"],
    },
]


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        for row in rows:
            file.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def compact(text: str) -> str:
    return text.replace(" ", "")


def supported_row(row_id: str, rng: random.Random) -> dict[str, Any]:
    region, answer_terms = rng.choice(REGIONS)
    profile = rng.choice(CONDITION_PROFILES)
    phrase = rng.choice(profile["phrases"])
    shape = rng.choice(
        [
            "{region}{phrase} 관광지추천",
            "{region} 근처 {phrase}로 갈만한데",
            "{region}에서 {phrase} 되는곳좀",
            "{region} {phrase}있는 실내 관광지",
            "{region}쪽 {phrase} 가능 한곳",
            "{region}{phrase}되는곳",
        ]
    )
    message = shape.format(region=region, phrase=phrase)
    if rng.random() < 0.45:
        message = compact(message)
    return {
        "id": row_id,
        "category": f"noisy_supported:{profile['label']}",
        "message": message,
        "expected_conditions": [profile["label"]],
        "min_cards": 1,
        "max_cards": 5,
        "must_contain_answer_terms": answer_terms,
        "must_include_any_card_terms": profile["terms"],
        "scoring_focus": ["noisy_realistic", "supported", "typo_spacing"],
    }


def negation_row(row_id: str, rng: random.Random) -> dict[str, Any]:
    region, answer_terms = rng.choice(REGIONS)
    left, right = rng.sample(CONDITION_PROFILES[:5], 2)
    marker = rng.choice(["말고", "아니고", "빼고", "제외하고"])
    message = f"{region}에서 {rng.choice(left['phrases'])} {marker} {rng.choice(right['phrases'])} 기준"
    if rng.random() < 0.5:
        message = compact(message)
    return {
        "id": row_id,
        "category": "noisy_negated_condition",
        "message": message,
        "expected_conditions": [right["label"]],
        "min_cards": 1,
        "max_cards": 5,
        "must_contain_answer_terms": answer_terms,
        "must_include_any_card_terms": right["terms"],
        "scoring_focus": ["noisy_realistic", "negated_condition"],
    }


def ambiguous_row(row_id: str, rng: random.Random) -> dict[str, Any]:
    message = rng.choice(
        [
            "중구휠체어관광지",
            "중구 엘베있는 관광지",
            "점자블록있는곳",
            "시장말고조용한데",
            "서울부산휠체어추천",
            "계단적고편한관광지",
            "편하게다닐만한곳",
        ]
    )
    if message in {"점자블록있는곳", "시장말고조용한데", "계단적고편한관광지", "편하게다닐만한곳"}:
        terms = ["지역", "어느", "먼저"]
    else:
        terms = ["어느", "지역"]
    return {
        "id": row_id,
        "category": "noisy_clarification",
        "message": message,
        "expect_clarification": True,
        "expect_no_cards": True,
        "must_include_answer_any_terms": terms,
        "scoring_focus": ["noisy_realistic", "clarification"],
    }


def unsupported_row(row_id: str, rng: random.Random) -> dict[str, Any]:
    message = rng.choice(["오늘환율알려줘", "강릉날씨어때", "서울에서 제일싼호텔", "부산맛집예약해줘", "지하철요금얼마야"])
    return {
        "id": row_id,
        "category": "noisy_unsupported",
        "message": message,
        "expected_lookup_mode": "unsupported",
        "expect_no_cards": True,
        "must_include_answer_any_terms": ["현재 MVP", "범위", "무장애 관광"],
        "scoring_focus": ["noisy_realistic", "unsupported"],
    }


def multiturn_row(row_id: str, rng: random.Random) -> dict[str, Any]:
    region, answer_terms = rng.choice(REGIONS)
    first = rng.choice(CONDITION_PROFILES[:5])
    second = rng.choice([profile for profile in CONDITION_PROFILES[:6] if profile["label"] != first["label"]])
    first_message = f"{region}{rng.choice(first['phrases'])}관광지추천"
    second_message = rng.choice(
        [
            f"그중{rng.choice(second['phrases'])}되는곳만",
            f"{rng.choice(first['phrases'])}말고{rng.choice(second['phrases'])}기준",
            f"아니{rng.choice(second['phrases'])}있는곳으로",
        ]
    )
    return {
        "id": row_id,
        "category": "noisy_multiturn",
        "turns": [
            {
                "message": first_message,
                "expected_conditions": [first["label"]],
                "min_cards": 1,
                "max_cards": 5,
                "must_contain_answer_terms": answer_terms,
                "must_include_any_card_terms": first["terms"],
            },
            {
                "message": second_message,
                "expected_conditions": [second["label"]],
                "min_cards": 1,
                "max_cards": 5,
                "must_contain_answer_terms": answer_terms,
                "must_include_any_card_terms": second["terms"],
            },
        ],
        "scoring_focus": ["noisy_realistic", "multiturn"],
    }


def build_rows(count: int, seed: int) -> list[dict[str, Any]]:
    rng = random.Random(seed)
    builders = (
        [supported_row] * 92
        + [negation_row] * 34
        + [ambiguous_row] * 26
        + [unsupported_row] * 18
        + [multiturn_row] * 30
    )
    rows = []
    for index in range(1, count + 1):
        builder = builders[(index - 1) % len(builders)]
        rows.append(builder(f"TNREAL-{index:04d}", rng))
    rng.shuffle(rows)
    for index, row in enumerate(rows, start=1):
        row["id"] = f"TNREAL-{index:04d}"
    return rows


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate realistic noisy tourism chat eval rows.")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--count", type=int, default=200)
    parser.add_argument("--seed", type=int, default=20260518)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    rows = build_rows(args.count, args.seed)
    write_jsonl(args.output, rows)
    print(f"Wrote {len(rows)} rows to {args.output.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()

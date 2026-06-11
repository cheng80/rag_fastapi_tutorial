from __future__ import annotations

import argparse
import json
import random
from pathlib import Path
from typing import Any, Callable


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = PROJECT_ROOT / "data" / "eval" / "tourism_hard_chat_eval_v2_200.jsonl"


REGIONS = [
    ("서울 강남구", ["서울", "강남"]),
    ("서울 중구", ["서울", "중구"]),
    ("성남시", ["성남"]),
    ("부산 중구", ["부산", "중구"]),
    ("강릉", ["강릉"]),
    ("대전", ["대전"]),
    ("대구", ["대구"]),
    ("제주시", ["제주"]),
    ("서귀포시", ["서귀포"]),
]

ACCESSIBILITY_PROFILES = {
    "휠체어": {
        "phrases": ["휠체어", "휠챠", "휄체어", "바퀴의자", "계단 적은", "턱 적은"],
        "terms": [["휠체어", "장애인", "무장애", "경사로", "턱이 없어", "출입통로", "접근로"]],
    },
    "유모차": {
        "phrases": ["유모차", "유아차", "아기차", "애기랑", "아이랑", "수유실"],
        "terms": [["유모차", "유아용 의자", "수유실", "기저귀", "영유아", "가족", "휠체어", "무장애"]],
    },
    "고령자": {
        "phrases": ["부모님 오래 안 걷는", "어르신 쉬엄쉬엄", "무릎 안 좋은 분", "계단 적고 쉬는 곳 있는", "많이안걷는"],
        "terms": [["고령자", "어르신", "노약자", "쉬어", "휴식", "의자", "휠체어", "경사로", "접근로", "화장실", "대중교통"]],
    },
    "주차": {
        "phrases": ["주차", "주챠", "주차ㅏ", "차댈곳", "차 대는 곳", "장애인 주차"],
        "terms": [["주차", "주차장"]],
    },
    "화장실": {
        "phrases": ["장애인 화장실", "장애인 장실", "화장실 편한", "장실 있는", "화장실 가까운"],
        "terms": [["화장실"]],
    },
    "엘리베이터": {
        "phrases": ["엘리베이터", "엘베", "앨베", "엘레베터", "승강기", "층 이동 쉬운"],
        "terms": [["엘리베이터", "승강기"]],
    },
    "보조견": {
        "phrases": ["보조견", "안내견", "보조갼", "안내견 동반", "보조견 같이"],
        "terms": [["보조견", "안내견"]],
    },
}

SENSORY_PROFILES = {
    "수어": {
        "phrases": ["수어", "수화", "수어 안내", "수화 안내"],
        "terms": [["수어", "수화"]],
    },
    "자막": {
        "phrases": ["자막", "영상에 글자", "문자 안내", "자막 안내"],
        "terms": [["자막", "문자안내", "영상안내"]],
    },
    "청각장애": {
        "phrases": ["청각장애인 안내", "소리 없이 안내 볼 수 있는", "수어나 자막", "수화나 문자 안내"],
        "terms": [["수어", "수화", "자막", "문자안내", "영상안내"]],
    },
    "점자블록": {
        "phrases": ["점자블록", "점자 블럭", "점자 유도블록"],
        "terms": [["점자블록", "점자"]],
    },
    "점자안내": {
        "phrases": ["점자 안내판", "점자 홍보물", "점자 자료"],
        "terms": [["점자", "점자홍보물", "점자안내"]],
    },
    "촉지도": {
        "phrases": ["촉지도", "촉지 안내도", "손으로 만져 확인할 안내"],
        "terms": [["촉지도"]],
    },
    "시각장애": {
        "phrases": ["시각장애인 안내", "점자나 음성안내", "보지 않고 안내 받을 수 있는", "오디오가이드 있는"],
        "terms": [["점자", "점자블록", "촉지도", "음성안내", "오디오가이드", "점자홍보물"]],
    },
}

PLACE_PREFERENCES = [
    ("실내", ["실내", "박물관", "전시관", "미술관", "체험관", "기념관", "문화관"]),
    ("박물관/전시", ["박물관", "전시관", "전시", "미술관", "체험관", "기념관", "문화관"]),
    ("공원/산책", ["공원", "산책", "정원", "숲", "둘레길"]),
    ("먹거리/식당", ["먹거리", "음식", "식당", "음식점", "유아용 의자", "의자식 테이블"]),
]


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        for row in rows:
            file.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def maybe_compact(text: str, rng: random.Random, probability: float = 0.35) -> str:
    return text.replace(" ", "") if rng.random() < probability else text


def supported_accessibility(row_id: str, rng: random.Random) -> dict[str, Any]:
    region, answer_terms = rng.choice(REGIONS)
    label, profile = rng.choice(list(ACCESSIBILITY_PROFILES.items()))
    phrase = rng.choice(profile["phrases"])
    preference_label, preference_terms = rng.choice(PLACE_PREFERENCES)
    message = rng.choice(
        [
            f"{region}에서 {phrase} 기준으로 {preference_label} 관광지 추천해줘",
            f"{region} 근처 {phrase}로 갈 수 있는 곳 중 {preference_label} 위주로",
            f"{region} {phrase} 되는 데 찾아줘. 너무 멀리 걷는 곳은 빼고",
            f"{region}쪽 {phrase} 가능한 관광지 있나? 가능하면 {preference_label}",
        ]
    )
    return {
        "id": row_id,
        "category": f"hard_v2_supported:{label}",
        "message": maybe_compact(message, rng),
        "expected_conditions": [label],
        "min_cards": 1,
        "max_cards": 5,
        "must_contain_answer_terms": answer_terms,
        "must_include_any_card_terms": profile["terms"],
        "scoring_focus": ["hard_v2", "supported_accessibility", "medium_length"],
    }


def strict_sensory(row_id: str, rng: random.Random) -> dict[str, Any]:
    region, answer_terms = rng.choice(REGIONS)
    label, profile = rng.choice(list(SENSORY_PROFILES.items()))
    phrase = rng.choice(profile["phrases"])
    message = rng.choice(
        [
            f"{region}에서 {phrase} 근거가 분명한 관광지 추천해줘",
            f"{region} {phrase} 되는 곳만 보여줘. 비슷한 접근성 말고",
            f"{region} 근처 {phrase} 확인된 실내 관광지",
            f"{region}쪽 {phrase} 가능한 곳. 없으면 없다고 해줘",
        ]
    )
    return {
        "id": row_id,
        "category": f"hard_v2_sensory_strict:{label}",
        "message": maybe_compact(message, rng, probability=0.25),
        "expected_conditions": [label],
        "min_cards": 1,
        "max_cards": 5,
        "must_contain_answer_terms": answer_terms,
        "must_include_any_card_terms": profile["terms"],
        "scoring_focus": ["hard_v2", "sensory_strict", "evidence_boundary"],
    }


def sensory_alternative(row_id: str, rng: random.Random) -> dict[str, Any]:
    region, answer_terms = rng.choice(REGIONS)
    pair = rng.choice(
        [
            ("수어 또는 자막", [["수어", "수화", "자막", "문자안내", "영상안내"]]),
            ("점자나 음성안내", [["점자", "점자블록", "촉지도", "음성안내", "오디오가이드", "점자홍보물"]]),
            ("점자블록이나 촉지도", [["점자블록", "점자", "촉지도"]]),
            ("보조견이나 점자 안내", [["보조견", "안내견", "점자", "점자블록", "촉지도"]]),
        ]
    )
    message = rng.choice(
        [
            f"{region}에서 {pair[0]} 둘 중 하나라도 있으면 추천해줘",
            f"{region} {pair[0]} 중 가능한 근거 있는 곳",
            f"{region} 근처 {pair[0]} 되는 곳으로 찾아줘",
        ]
    )
    return {
        "id": row_id,
        "category": "hard_v2_sensory_alternative",
        "message": maybe_compact(message, rng, probability=0.3),
        "min_cards": 1,
        "max_cards": 5,
        "must_contain_answer_terms": answer_terms,
        "must_include_any_card_terms": pair[1],
        "scoring_focus": ["hard_v2", "sensory_alternative", "or_condition"],
    }


def negation_replace(row_id: str, rng: random.Random) -> dict[str, Any]:
    region, answer_terms = rng.choice(REGIONS)
    labels = list(ACCESSIBILITY_PROFILES)
    left, right = rng.sample(labels, 2)
    left_phrase = rng.choice(ACCESSIBILITY_PROFILES[left]["phrases"])
    right_phrase = rng.choice(ACCESSIBILITY_PROFILES[right]["phrases"])
    marker = rng.choice(["말고", "아니고", "빼고", "제외하고"])
    message = rng.choice(
        [
            f"{region}에서 {left_phrase} {marker} {right_phrase} 기준으로",
            f"{region} {left_phrase} 되는 곳 말고 {right_phrase} 있는 곳",
            f"{region} 처음엔 {left_phrase}였는데 그건 빼고 {right_phrase}로 다시",
        ]
    )
    return {
        "id": row_id,
        "category": "hard_v2_negation_replace",
        "message": maybe_compact(message, rng),
        "expected_conditions": [right],
        "min_cards": 1,
        "max_cards": 5,
        "must_contain_answer_terms": answer_terms,
        "must_include_any_card_terms": ACCESSIBILITY_PROFILES[right]["terms"],
        "scoring_focus": ["hard_v2", "negation", "replace_condition"],
    }


def multiturn(row_id: str, rng: random.Random) -> dict[str, Any]:
    region, answer_terms = rng.choice(REGIONS)
    first, second = rng.sample(list(ACCESSIBILITY_PROFILES), 2)
    first_phrase = rng.choice(ACCESSIBILITY_PROFILES[first]["phrases"])
    second_phrase = rng.choice(ACCESSIBILITY_PROFILES[second]["phrases"])
    return {
        "id": row_id,
        "category": "hard_v2_multiturn",
        "turns": [
            {
                "message": maybe_compact(f"{region} {first_phrase} 관광지 추천", rng),
                "min_cards": 1,
                "max_cards": 5,
                "must_contain_answer_terms": answer_terms,
                "must_include_any_card_terms": ACCESSIBILITY_PROFILES[first]["terms"],
            },
            {
                "message": rng.choice([f"그중 {second_phrase} 되는 곳만", f"아니 {second_phrase} 기준으로 다시", f"{first_phrase} 말고 {second_phrase}"]),
                "min_cards": 1,
                "max_cards": 5,
                "must_contain_answer_terms": answer_terms,
                "must_include_any_card_terms": ACCESSIBILITY_PROFILES[second]["terms"],
            },
        ],
        "scoring_focus": ["hard_v2", "multiturn", "context_switch"],
    }


def ambiguous(row_id: str, rng: random.Random) -> dict[str, Any]:
    message = rng.choice(
        [
            "중구에서 휠체어 가능한 곳",
            "계단 적고 편한 관광지",
            "부모님이랑 편한 데",
            "점자 있는 곳",
            "수어 되는 곳",
            "서울 부산 중에 휠체어 되는 곳",
            "시장 말고 조용한 곳",
        ]
    )
    return {
        "id": row_id,
        "category": "hard_v2_clarification",
        "message": maybe_compact(message, rng, probability=0.3),
        "expect_clarification": True,
        "expect_no_cards": True,
        "must_include_answer_any_terms": ["지역", "어느", "기준", "우선"],
        "scoring_focus": ["hard_v2", "clarification"],
    }


def unsupported(row_id: str, rng: random.Random) -> dict[str, Any]:
    message = rng.choice(
        [
            "성남시 식당 추천",
            "강남 맛집 알려줘",
            "제주 렌터카 가격 비교",
            "오늘 환율 알려줘",
            "강릉 날씨랑 교통 혼잡도",
            "부산 호텔 예약해줘",
            "지하철 요금이랑 빠른 환승 알려줘",
        ]
    )
    return {
        "id": row_id,
        "category": "hard_v2_unsupported_or_general",
        "message": maybe_compact(message, rng, probability=0.25),
        "expected_lookup_mode": "unsupported",
        "expect_no_cards": True,
        "must_include_answer_any_terms": ["현재 MVP", "범위", "무장애 관광", "일반 관광지"],
        "scoring_focus": ["hard_v2", "unsupported", "general_tourism_guard"],
    }


def build_rows(count: int, seed: int) -> list[dict[str, Any]]:
    rng = random.Random(seed)
    builders: list[Callable[[str, random.Random], dict[str, Any]]] = (
        [supported_accessibility] * 44
        + [strict_sensory] * 42
        + [sensory_alternative] * 24
        + [negation_replace] * 32
        + [multiturn] * 28
        + [ambiguous] * 16
        + [unsupported] * 14
    )
    rows = []
    for index in range(1, count + 1):
        builder = builders[(index - 1) % len(builders)]
        rows.append(builder(f"THARD2-{index:04d}", rng))
    rng.shuffle(rows)
    for index, row in enumerate(rows, start=1):
        row["id"] = f"THARD2-{index:04d}"
    return rows


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate hard tourism chat eval v2 rows.")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--count", type=int, default=200)
    parser.add_argument("--seed", type=int, default=20260518)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    rows = build_rows(args.count, args.seed)
    write_jsonl(args.output, rows)
    output = args.output.resolve()
    print(f"Wrote {len(rows)} rows to {output.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()

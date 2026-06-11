from __future__ import annotations

import argparse
import json
from pathlib import Path
import random
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = PROJECT_ROOT / "data" / "eval" / "tourism_residual_hard_nlu_20260518.jsonl"
DEFAULT_CHAT_OUTPUT = PROJECT_ROOT / "data" / "eval" / "tourism_residual_hard_chat_20260518.jsonl"

REGIONS = ["서울 강남구", "서울 중구", "부산 중구", "대구", "대전", "전주", "강릉", "성남시", "제주시", "서귀포시"]

TERM_MAP = {
    "휠체어": ["휠체어", "무장애", "경사로", "턱이 없어", "출입통로", "접근 가능"],
    "고령자": [
        "고령자",
        "어르신",
        "노약자",
        "쉬어",
        "휴식",
        "의자",
        "계단 적",
        "휠체어",
        "장애인",
        "경사로",
        "접근로",
        "출입통로",
        "화장실",
        "대중교통",
        "무단차",
        "평탄",
    ],
    "주차": ["주차", "장애인전용 주차구역", "주차장", "승하차"],
    "접근로": ["접근로", "출입통로", "경사로", "턱이 없어", "단차", "평탄"],
}

SENIOR_PATTERNS = [
    "{region}에서 어머니가 자주 앉아 쉬면서 볼 수 있는 관광지",
    "{region}에서 오래 서 있지 않아도 관람 가능한 곳",
    "{region}에서 무릎 안 좋은 부모님이 계단 적게 다닐 곳",
    "{region}에서 어르신이 화장실이랑 쉼터 찾기 쉬운 곳",
    "{region}에서 쉬엄쉬엄 이동해도 동선이 끊기지 않는 곳",
    "{region}에서 걷는 거리 짧고 중간에 쉴 수 있는 곳",
    "{region}에서 다리 약한 분이 부담 없이 둘러보는 코스",
    "{region}에서 부모님 컨디션이 안 좋아도 무리 적은 곳",
    "{region}에서 연세 있는 분이 천천히 관람하기 좋은 곳",
    "{region}에서 앉을 자리 많은 관광지 위주로",
    "{region}에서 계단 오르내림이 적고 쉬는 공간 있는 곳",
    "{region}에서 노약자 동행하기 편한 실내 관광지",
    "{region}에서 어른 모시고 오래 걷지 않는 곳",
    "{region}에서 허리 불편한 분이 쉬어가며 볼 곳",
    "{region}에서 부모님 모시고 화장실 찾기 곤란하지 않은 곳",
]

PARKING_TYPO_PATTERNS = [
    "{region}에서 주챠 편한 곳",
    "{region}에서 주차ㅏ 되는 관광지",
    "{region}에서 주차되는데 입구 가까운 곳",
    "{region}에서 차대기 편한 곳",
    "{region}에서 차 세우고 바로 들어갈만한 곳",
    "{region}에서 입구앞 차 댈 수 있는 관광지",
    "{region}에서 장애인 주챠칸 있는 곳",
    "{region}에서 주자창 가까운 곳",
    "{region}에서 주차장서 많이 안 걷는 곳",
    "{region}에서 승하차 위치 가까운 데로",
    "{region}에서 보호자차 세우기 쉬운 관광지",
    "{region}에서 차에서 내려 바로 이동 가능한 곳",
    "{region}에서 주차공간 확인되는 무장애 관광지",
    "{region}에서 주차말고 접근 쉬운 곳",
    "{region}에서 주챠 아니고 대중교통으로 갈 곳",
]

BOUNDARY_PATTERNS: list[tuple[str, list[str], str]] = [
    ("{region}에서 휠체어 타고 입구부터 관람까지 가능한 곳", ["휠체어"], "boundary:wheelchair"),
    ("{region}에서 휠챠 쓰는 사람이 직접 들어갈 수 있는 관광지", ["휠체어"], "boundary:wheelchair"),
    ("{region}에서 바퀴의자로 이동해도 내부 관람 가능한 곳", ["휠체어"], "boundary:wheelchair"),
    ("{region}에서 휠체어 사용자 동선이 확인되는 곳", ["휠체어"], "boundary:wheelchair"),
    ("{region}에서 앉은 채 이동하는 사람이 들어갈 수 있는 곳", ["휠체어"], "boundary:wheelchair"),
    ("{region}에서 문 앞 단차가 낮은 관광지", ["접근로"], "boundary:access_route"),
    ("{region}에서 입구 경사로나 평탄한 길이 있는 곳", ["접근로"], "boundary:access_route"),
    ("{region}에서 출입통로가 넓고 턱이 적은 곳", ["접근로"], "boundary:access_route"),
    ("{region}에서 시작 지점부터 길이 끊기지 않는 장소", ["접근로"], "boundary:access_route"),
    ("{region}에서 주출입구 높낮이 차가 적은 곳", ["접근로"], "boundary:access_route"),
    ("{region}에서 휠체어로 갈 수 있고 입구 단차도 적은 곳", ["휠체어", "접근로"], "boundary:both"),
    ("{region}에서 바퀴 이동 가능한데 경사로 근거도 있는 곳", ["휠체어", "접근로"], "boundary:both"),
    ("{region}에서 휠체어 동행과 출입통로 넓은 곳", ["휠체어", "접근로"], "boundary:both"),
    ("{region}에서 문턱 없는 분위기 좋은 카페 말고 관광지만", ["접근로"], "boundary:access_route"),
    ("{region}에서 그냥 걷기 편한 산책길", [], "boundary:ambiguous_or_general"),
    ("{region}에서 분위기 편한 곳", [], "boundary:ambiguous_or_general"),
]


def make_row(row_id: str, text: str, labels: list[str], category: str) -> dict[str, Any]:
    return {
        "id": row_id,
        "text": text,
        "expected_conditions": labels,
        "category": category,
        "source": "residual_hard_eval_20260518",
    }


def build_rows(seed: int, senior_rows: int, parking_rows: int, boundary_rows: int) -> list[dict[str, Any]]:
    rng = random.Random(seed)
    rows: list[dict[str, Any]] = []
    index = 1

    for _ in range(senior_rows):
        pattern = rng.choice(SENIOR_PATTERNS)
        rows.append(make_row(f"RESHARD-{index:04d}", pattern.format(region=rng.choice(REGIONS)), ["고령자"], "residual:senior"))
        index += 1

    for _ in range(parking_rows):
        pattern = rng.choice(PARKING_TYPO_PATTERNS)
        labels = ["대중교통"] if "대중교통" in pattern else ([] if "주차말고" in pattern else ["주차"])
        category = "residual:parking_negated" if not labels or labels == ["대중교통"] else "residual:parking_typo"
        rows.append(make_row(f"RESHARD-{index:04d}", pattern.format(region=rng.choice(REGIONS)), labels, category))
        index += 1

    for _ in range(boundary_rows):
        pattern, labels, category = rng.choice(BOUNDARY_PATTERNS)
        rows.append(make_row(f"RESHARD-{index:04d}", pattern.format(region=rng.choice(REGIONS)), labels, category))
        index += 1

    rng.shuffle(rows)
    rows.sort(key=lambda item: item["id"])
    return rows


def to_chat_rows(rows: list[dict[str, Any]], limit: int) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    for row in rows:
        labels = row["expected_conditions"]
        if not labels:
            continue
        terms: list[str] = []
        for label in labels:
            terms.extend(TERM_MAP.get(label, [label]))
        output.append(
            {
                "id": row["id"].replace("RESHARD", "RESCHAT"),
                "category": row["category"],
                "message": row["text"],
                "expected_conditions": labels,
                "min_cards": 1,
                "must_include_any_card_terms": [list(dict.fromkeys(terms))],
                "scoring_focus": ["residual_condition_to_card_evidence"],
            }
        )
        if len(output) >= limit:
            break
    return output


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        for row in rows:
            file.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate residual hard NLU/chat eval for senior, parking typo, and boundary failures.")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--chat-output", type=Path, default=DEFAULT_CHAT_OUTPUT)
    parser.add_argument("--senior-rows", type=int, default=70)
    parser.add_argument("--parking-rows", type=int, default=70)
    parser.add_argument("--boundary-rows", type=int, default=110)
    parser.add_argument("--chat-rows", type=int, default=80)
    parser.add_argument("--seed", type=int, default=20260518)
    args = parser.parse_args()

    rows = build_rows(args.seed, args.senior_rows, args.parking_rows, args.boundary_rows)
    chat_rows = to_chat_rows(rows, args.chat_rows)
    write_jsonl(args.output, rows)
    write_jsonl(args.chat_output, chat_rows)
    print(
        json.dumps(
            {
                "output": str(args.output.relative_to(PROJECT_ROOT)),
                "rows": len(rows),
                "chat_output": str(args.chat_output.relative_to(PROJECT_ROOT)),
                "chat_rows": len(chat_rows),
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()

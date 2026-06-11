from __future__ import annotations

import argparse
import json
from pathlib import Path
import random
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = PROJECT_ROOT / "data" / "eval" / "tourism_hard_nlu_holdout_20260518.jsonl"

LABELS = [
    "휠체어",
    "유모차",
    "고령자",
    "주차",
    "화장실",
    "접근로",
    "대중교통",
    "엘리베이터",
    "보조견",
    "시각장애",
    "청각장애",
]

REGIONS = ["서울 강남구", "서울 중구", "부산 중구", "대구", "대전", "전주", "강릉", "성남시", "제주시", "서귀포시"]

HARD_PATTERNS: dict[str, list[str]] = {
    "휠체어": [
        "{region}에서 바퀴 달린 의자로 들어가도 눈치 안 보일 만한 곳",
        "{region}에서 혼자 밀고 들어가기 무리 없는 관광지",
        "{region}에서 앉은 채로 이동하는 사람이 보기 편한 곳",
        "{region}에서 바닥 턱 때문에 못 들어가는 일이 적은 곳",
        "{region}에서 이동 보조기구 쓰는 사람이 관람 가능한 곳",
        "{region}에서 서서 오래 못 보는 동행이 그대로 둘러볼 수 있는 곳",
        "{region}에서 문턱 때문에 막히지 않는 코스로 추천",
        "{region}에서 바퀴 달린 보조의자 이용자가 갈 만한 관광지",
        "{region}에서 계단 때문에 돌아나오지 않아도 되는 곳",
        "{region}에서 출입구에서 막히지 않는 장소 위주",
        "{region}에서 휠챠 타는 친구랑 갈 수 있는 곳",
        "{region}에서 휠체여 사용해도 괜찮은 곳",
    ],
    "유모차": [
        "{region}에서 아기 태운 작은 바퀴차 끌고 다니기 편한 곳",
        "{region}에서 아이 태우고 밀고 다녀도 동선이 괜찮은 곳",
        "{region}에서 유아용 이동기구를 접지 않고 볼 수 있는 곳",
        "{region}에서 아기 짐이 많아도 들어가기 쉬운 관광지",
        "{region}에서 낮잠 자는 아이를 태운 채 둘러보기 좋은 곳",
        "{region}에서 아기 데리고 수유나 기저귀 걱정 적은 곳",
        "{region}에서 유아챠 끌고 가도 무리 없는 곳",
        "{region}에서 애기랑 짐차 밀고 다니는 동선 괜찮은 곳",
        "{region}에서 아이 의자나 아기 편의가 확인되는 곳",
        "{region}에서 아기 동반 가족이 쉬어 가기 편한 곳",
    ],
    "고령자": [
        "{region}에서 부모님이 오래 서 있지 않아도 되는 곳",
        "{region}에서 무릎이 불편한 분이 쉬엄쉬엄 볼 수 있는 곳",
        "{region}에서 어른 모시고 걷는 부담이 적은 곳",
        "{region}에서 다리가 약한 동행이 중간중간 앉을 수 있는 곳",
        "{region}에서 계단 오르내림이 적은 코스로 보고 싶어",
        "{region}에서 연세 있는 분이 천천히 둘러보기 좋은 곳",
        "{region}에서 오래 걷지 않아도 주요 볼거리를 볼 수 있는 곳",
        "{region}에서 부모님 컨디션 안 좋아도 무리 적은 관광지",
        "{region}에서 어르신이 화장실이나 쉼터 찾기 쉬운 곳",
        "{region}에서 걷는 거 힘든 어른이랑 갈 곳",
    ],
    "주차": [
        "{region}에서 차를 입구 가까이에 세울 수 있으면 좋겠어",
        "{region}에서 내려서 많이 안 걸어도 되는 주차 동선이면 해",
        "{region}에서 차량으로 접근한 뒤 이동 부담이 적은 곳",
        "{region}에서 보호자 차에서 바로 이동하기 편한 관광지",
        "{region}에서 승하차하고 가까운 곳에 댈 수 있는지 확인되는 곳",
        "{region}에서 주출입구 가까운 차량 공간이 있는 곳",
        "{region}에서 장애인 전용칸 같은 주차 근거가 있는 곳",
        "{region}에서 차 대고 바로 들어가기 쉬운 곳",
        "{region}에서 주차장에서 입구까지 동선이 짧은 곳",
        "{region}에서 주챠 편한 곳",
    ],
    "화장실": [
        "{region}에서 동행이 넓은 화장실을 써야 해서 확인된 곳만",
        "{region}에서 보조기구 들고 들어갈 수 있는 화장실 근거 있는 곳",
        "{region}에서 일반 칸 말고 넓게 쓸 수 있는 화장실이 필요해",
        "{region}에서 손잡이 있는 화장실 정보가 있는 관광지",
        "{region}에서 휠체여 들어가는 화장실이 확인되는 곳",
        "{region}에서 장애 인화장실 문구 있는 곳",
        "{region}에서 몸 불편한 사람이 이용할 수 있는 화장실 있는 곳",
        "{region}에서 화장실 때문에 곤란하지 않을 곳",
        "{region}에서 넓은 칸 화장실 확인 가능한 곳",
        "{region}에서 동행 보조가 가능한 화장실 있는 관광지",
    ],
    "접근로": [
        "{region}에서 입구 앞 높낮이 차가 적은 곳",
        "{region}에서 시작부터 길이 끊기지 않는 곳으로 골라줘",
        "{region}에서 문 앞 턱 때문에 막히지 않는 관광지",
        "{region}에서 바닥이 평평하고 돌아가기 쉬운 곳",
        "{region}에서 경사진 판이나 넓은 길이 확인되는 곳",
        "{region}에서 주출입구가 평탄한 곳이면 좋겠어",
        "{region}에서 좁은 문이나 단차가 적은 곳",
        "{region}에서 길이 울퉁불퉁하지 않은 곳",
        "{region}에서 입구부터 관람 동선까지 이어지는 곳",
        "{region}에서 출입 통로가 답답하지 않은 관광지",
    ],
    "대중교통": [
        "{region}에서 버스나 지하철 내려서 너무 멀지 않은 곳",
        "{region}에서 차 없이 가도 접근 가능한 곳",
        "{region}에서 대중 이동수단으로 찾아가기 쉬운 관광지",
        "{region}에서 정류장에서 크게 헤매지 않을 곳",
        "{region}에서 역이나 정류장 기준으로 이동 부담 적은 곳",
        "{region}에서 대중교통 약자도 길 찾기 쉬운 곳",
        "{region}에서 버정 내려서 가까운 곳",
        "{region}에서 지하철로 갔다가 바로 이동하기 좋은 곳",
        "{region}에서 택시 없이도 갈 수 있는 곳",
        "{region}에서 교통편 설명이 있는 관광지",
    ],
    "엘리베이터": [
        "{region}에서 층 이동할 때 계단 말고 올라갈 수단이 있는 곳",
        "{region}에서 위아래 이동을 기계로 할 수 있는 곳",
        "{region}에서 승강 설비가 확인되는 관광지",
        "{region}에서 엘베 말고도 리프트 같은 이동 설비 있는 곳",
        "{region}에서 계단 리프트나 승강 장치 근거가 있는 곳",
        "{region}에서 층이 달라도 이동 가능한 시설 있는 곳",
        "{region}에서 승강끼 문구 있는 곳",
        "{region}에서 휠체어 리프트 확인되는 곳",
        "{region}에서 건물 안 층 이동이 가능한 곳",
        "{region}에서 엘리배이터 있는 곳",
    ],
    "보조견": [
        "{region}에서 안내견이랑 같이 들어가도 되는 곳",
        "{region}에서 보조 동물 동반이 가능한 관광지",
        "{region}에서 시각장애 동행견 출입 근거 있는 곳",
        "{region}에서 안내 견이 거절되지 않을 만한 곳",
        "{region}에서 장애 보조견 문구가 확인되는 곳",
        "{region}에서 보조갼 데리고 갈 수 있는 곳",
        "{region}에서 반려견 말고 보조 목적 동반견 기준으로",
        "{region}에서 안내견 동행하는 사람과 갈 관광지",
        "{region}에서 보조견 출입 가능성이 확인된 곳",
        "{region}에서 시각장애인 보조견 동반되는 곳",
    ],
    "시각장애": [
        "{region}에서 손으로 만져 위치를 알 수 있는 안내가 있으면 좋겠어",
        "{region}에서 글자를 못 봐도 소리로 설명을 들을 수 있는 곳",
        "{region}에서 눈이 불편한 동행이 길 찾기 쉬운 곳",
        "{region}에서 촉감으로 안내를 확인할 수 있는 관광지",
        "{region}에서 점으로 된 안내판이나 만지는 지도가 있는 곳",
        "{region}에서 오디오 설명이 제공되는 곳",
        "{region}에서 시각 정보만 있으면 곤란해서 다른 안내가 필요해",
        "{region}에서 점자블럭이나 촉지도 근거 있는 곳",
        "{region}에서 앞을 보기 어려운 동행과 갈 만한 곳",
        "{region}에서 음성 안내 있는 관광지",
    ],
    "청각장애": [
        "{region}에서 소리 설명만 있으면 곤란해서 눈으로 볼 안내가 필요해",
        "{region}에서 들리지 않아도 내용을 따라갈 수 있는 곳",
        "{region}에서 화면 글자나 손짓 안내가 있는 관광지",
        "{region}에서 안내 방송 없이도 정보 확인 가능한 곳",
        "{region}에서 청각이 불편한 동행이 설명을 놓치지 않을 곳",
        "{region}에서 소리 없이 안내를 볼 수 있는 관광지",
        "{region}에서 수화나 글자 안내가 확인되는 곳",
        "{region}에서 자 막 안내라도 있는 곳",
        "{region}에서 영상에 글자로 설명 나오는 곳",
        "{region}에서 듣는 안내 말고 보는 안내가 있는 곳",
    ],
}

NEGATIVE_PATTERNS = [
    "{region}에서 그냥 분위기 좋은 곳",
    "{region}에서 예쁜 사진 찍기 좋은 곳",
    "{region}에서 맛집만 알려줘",
    "{region}에서 리프트 차량 예약할 업체",
    "{region}에서 휠체어 대여 가격 제일 싼 곳",
    "{region}에서 응급실이 가까운 관광지 말고 병원 알려줘",
    "{region}에서 주차 말고 전시 내용이 좋은 곳",
    "{region}에서 부모님이랑 갈 만한 곳",
    "{region}에서 시설 좋은 곳",
    "{region}에서 안내 잘 되는 곳",
]

COMBO_PATTERNS = [
    ("{region}에서 입구에서 막히지 않고 넓은 화장실도 확인되는 곳", ["접근로", "화장실"]),
    ("{region}에서 아이 태운 채로 들어가고 기저귀 걱정도 적은 곳", ["유모차"]),
    ("{region}에서 차에서 내려 많이 안 걷고 층 이동도 쉬운 곳", ["주차", "엘리베이터"]),
    ("{region}에서 듣지 못해도 볼 수 있는 안내나 손짓 설명이 있는 곳", ["청각장애"]),
    ("{region}에서 눈이 불편한 동행과 안내견이 함께 갈 수 있는 곳", ["시각장애", "보조견"]),
    ("{region}에서 무릎 불편한 어른이 문턱 없이 둘러볼 수 있는 곳", ["고령자", "접근로"]),
    ("{region}에서 바퀴 달린 의자로 들어가고 층 이동도 가능한 곳", ["휠체어", "엘리베이터"]),
    ("{region}에서 차 없이 가도 너무 많이 걷지 않는 곳", ["대중교통", "고령자"]),
]


def make_row(row_id: str, text: str, labels: list[str], category: str) -> dict[str, Any]:
    return {
        "id": row_id,
        "text": text,
        "expected_conditions": labels,
        "category": category,
        "source": "hard_nlu_holdout_20260518",
    }


def build_rows(target_rows: int, seed: int) -> list[dict[str, Any]]:
    rng = random.Random(seed)
    rows: list[dict[str, Any]] = []
    index = 1
    for label, patterns in HARD_PATTERNS.items():
        for pattern in patterns:
            region = rng.choice(REGIONS)
            rows.append(make_row(f"HARDNLU-{index:04d}", pattern.format(region=region), [label], f"implicit:{label}"))
            index += 1
    for pattern, labels in COMBO_PATTERNS:
        for _ in range(5):
            region = rng.choice(REGIONS)
            rows.append(make_row(f"HARDNLU-{index:04d}", pattern.format(region=region), labels, "implicit:multi"))
            index += 1
    for pattern in NEGATIVE_PATTERNS:
        for _ in range(5):
            region = rng.choice(REGIONS)
            rows.append(make_row(f"HARDNLU-{index:04d}", pattern.format(region=region), [], "negative-or-ambiguous"))
            index += 1
    rng.shuffle(rows)
    rows = rows[:target_rows]
    rows.sort(key=lambda item: item["id"])
    return rows


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        for row in rows:
            file.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate hard NLU holdout that avoids obvious rule keywords.")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--rows", type=int, default=180)
    parser.add_argument("--seed", type=int, default=20260518)
    args = parser.parse_args()
    rows = build_rows(args.rows, args.seed)
    write_jsonl(args.output, rows)
    print(json.dumps({"output": str(args.output.relative_to(PROJECT_ROOT)), "rows": len(rows)}, ensure_ascii=False))


if __name__ == "__main__":
    main()

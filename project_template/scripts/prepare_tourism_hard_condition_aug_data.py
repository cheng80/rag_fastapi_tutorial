from __future__ import annotations

import argparse
import json
from pathlib import Path
import random
import sys
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.services.tourism_query_service import CONDITION_KEYWORDS  # noqa: E402


CONDITION_LABELS = list(CONDITION_KEYWORDS)
DEFAULT_BASE_DIR = PROJECT_ROOT / "data" / "processed" / "tourism_condition_transformer"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "data" / "processed" / "tourism_condition_transformer_hard_aug"

REGIONS = ["서울 강남구", "서울 중구", "부산 중구", "대구", "대전", "전주", "강릉", "성남시", "제주시", "서귀포시"]

TRAIN_PATTERNS: dict[str, list[str]] = {
    "휠체어": [
        "{region}에서 앉아서 이동하는 동행이 관람하기 쉬운 곳",
        "{region}에서 바퀴 있는 이동 의자 사용자가 갈 수 있는 곳",
        "{region}에서 문턱 때문에 입장이 막히지 않을 관광지",
        "{region}에서 서서 이동하기 힘든 사람이 둘러볼 수 있는 곳",
        "{region}에서 보조 의자를 탄 채로 볼 수 있는 장소",
        "{region}에서 입구부터 실내까지 바퀴 이동이 가능한 곳",
    ],
    "유모차": [
        "{region}에서 아이 태운 이동차를 접지 않고 들어갈 수 있는 곳",
        "{region}에서 아기 짐과 함께 밀고 다니기 쉬운 관광지",
        "{region}에서 어린아이 동반 이동기구가 지나가기 좋은 곳",
        "{region}에서 수유나 아기 돌봄 편의가 있는 곳",
        "{region}에서 애기 태운 차로 다녀도 부담 적은 곳",
    ],
    "고령자": [
        "{region}에서 다리 약한 어른이 쉬면서 볼 수 있는 곳",
        "{region}에서 연세 있는 동행이 오래 걷지 않아도 되는 곳",
        "{region}에서 부모님 체력 부담이 적은 코스",
        "{region}에서 무릅 불편한 분이 천천히 볼 관광지",
        "{region}에서 앉아 쉴 곳이 있는 어른 동반 장소",
    ],
    "주차": [
        "{region}에서 차에서 내려 입구까지 거리가 짧은 곳",
        "{region}에서 보호자 차량으로 접근하기 편한 곳",
        "{region}에서 승하차 후 바로 들어가기 좋은 관광지",
        "{region}에서 입구 가까운 차량 공간이 확인되는 곳",
        "{region}에서 주차 후 이동 동선이 짧은 곳",
    ],
    "화장실": [
        "{region}에서 넓은 칸 화장실이 필요한 동행과 갈 곳",
        "{region}에서 보조기구가 들어갈 화장실 근거 있는 곳",
        "{region}에서 손잡이 있는 화장실을 써야 하는 사람과 갈 곳",
        "{region}에서 일반 칸보다 넓은 화장실이 확인되는 관광지",
        "{region}에서 장애 인 화장실 정보가 있는 곳",
    ],
    "접근로": [
        "{region}에서 문 앞 단차가 낮은 곳",
        "{region}에서 시작 지점부터 길이 이어지는 곳",
        "{region}에서 바닥 높이 차이가 적은 관광지",
        "{region}에서 주출입구가 막히지 않는 곳",
        "{region}에서 평평한 동선이 확인되는 곳",
    ],
    "대중교통": [
        "{region}에서 차 없이 찾아가기 쉬운 곳",
        "{region}에서 버스 내려서 오래 걷지 않는 곳",
        "{region}에서 역에서 이동하기 쉬운 관광지",
        "{region}에서 정류장 기준 접근이 쉬운 곳",
        "{region}에서 대중 이동수단으로 갈 수 있는 곳",
    ],
    "엘리베이터": [
        "{region}에서 층을 바꿀 때 계단 말고 이동수단 있는 곳",
        "{region}에서 위층 아래층 이동 장치가 있는 관광지",
        "{region}에서 승강 장치가 확인되는 곳",
        "{region}에서 계단 대신 올라가는 설비가 있는 곳",
        "{region}에서 건물 내부 층 이동이 가능한 곳",
    ],
    "보조견": [
        "{region}에서 시각장애 보조 동물과 들어갈 수 있는 곳",
        "{region}에서 안내견 동행이 가능한 관광지",
        "{region}에서 보조 목적 동반견 출입 근거 있는 곳",
        "{region}에서 보조갼과 갈 수 있는 장소",
        "{region}에서 반려견이 아니라 장애 보조견 기준으로 볼 곳",
    ],
    "시각장애": [
        "{region}에서 손으로 만지는 안내가 있는 곳",
        "{region}에서 소리 설명으로 관람할 수 있는 곳",
        "{region}에서 눈이 불편해도 안내를 받을 수 있는 곳",
        "{region}에서 촉감 지도나 음성 설명이 있는 관광지",
        "{region}에서 점으로 된 안내 근거가 있는 곳",
    ],
    "청각장애": [
        "{region}에서 듣지 못해도 눈으로 안내를 볼 수 있는 곳",
        "{region}에서 방송 말고 글자 안내가 있는 관광지",
        "{region}에서 손짓 설명이나 화면 글자가 있는 곳",
        "{region}에서 소리를 못 들어도 설명을 따라갈 수 있는 곳",
        "{region}에서 청각이 불편한 동행이 안내를 놓치지 않을 곳",
    ],
}

NEGATIVE_PATTERNS = [
    "{region}에서 맛있는 식당 찾아줘",
    "{region}에서 사진 잘 나오는 곳",
    "{region}에서 리프트 차량 예약 가능한 업체",
    "{region}에서 병원이나 약국 알려줘",
    "{region}에서 부모님과 갈 만한 일반 관광지",
    "{region}에서 안내가 좋은 곳",
    "{region}에서 시설 좋은 곳",
    "{region}에서 주차는 빼고 전시 내용만 좋은 곳",
]

COMBO_PATTERNS = [
    ("{region}에서 차에서 내려 바로 들어가고 넓은 화장실도 필요한 곳", ["주차", "화장실"]),
    ("{region}에서 바퀴 이동이 가능하고 층 이동 장치도 있는 곳", ["휠체어", "엘리베이터"]),
    ("{region}에서 눈이 불편한 동행과 보조견이 함께 갈 곳", ["시각장애", "보조견"]),
    ("{region}에서 어른이 오래 걷지 않고 단차도 적은 곳", ["고령자", "접근로"]),
    ("{region}에서 아이 태운 채 이동하고 아기 돌봄도 가능한 곳", ["유모차"]),
]


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def vector(labels: list[str]) -> list[int]:
    label_set = set(labels)
    return [1 if label in label_set else 0 for label in CONDITION_LABELS]


def row(row_id: str, text: str, labels: list[str], family: str) -> dict[str, Any]:
    clean_labels = [label for label in labels if label in CONDITION_LABELS]
    return {
        "id": row_id,
        "text": text,
        "labels": clean_labels,
        "label_vector": vector(clean_labels),
        "source": "hard_condition_aug_20260518",
        "template_family": family,
    }


def build_aug(rows: int, seed: int) -> list[dict[str, Any]]:
    rng = random.Random(seed)
    output: list[dict[str, Any]] = []
    index = 1
    while len(output) < rows:
        for label, patterns in TRAIN_PATTERNS.items():
            pattern = rng.choice(patterns)
            region = rng.choice(REGIONS)
            output.append(row(f"HARDAUG-{index:05d}", pattern.format(region=region), [label], f"implicit:{label}"))
            index += 1
            if len(output) >= rows:
                break
        if len(output) >= rows:
            break
        pattern, labels = rng.choice(COMBO_PATTERNS)
        output.append(row(f"HARDAUG-{index:05d}", pattern.format(region=rng.choice(REGIONS)), labels, "implicit:multi"))
        index += 1
        if len(output) >= rows:
            break
        pattern = rng.choice(NEGATIVE_PATTERNS)
        output.append(row(f"HARDAUG-{index:05d}", pattern.format(region=rng.choice(REGIONS)), [], "none:negative-or-ambiguous"))
        index += 1
    return output[:rows]


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        for item in rows:
            file.write(json.dumps(item, ensure_ascii=False, sort_keys=True) + "\n")


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare hard augmented condition data without copying hard holdout rows.")
    parser.add_argument("--base-dir", type=Path, default=DEFAULT_BASE_DIR)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--augment-rows", type=int, default=4000)
    parser.add_argument("--seed", type=int, default=20260519)
    args = parser.parse_args()
    train = load_jsonl(args.base_dir / "train.jsonl")
    validation = load_jsonl(args.base_dir / "validation.jsonl")
    test = load_jsonl(args.base_dir / "test.jsonl")
    augment = build_aug(args.augment_rows, args.seed)
    output_train = [*train, *augment]
    write_jsonl(args.output_dir / "train.jsonl", output_train)
    write_jsonl(args.output_dir / "validation.jsonl", validation)
    write_jsonl(args.output_dir / "test.jsonl", test)
    write_json(args.output_dir / "labels.json", {"labels": CONDITION_LABELS})
    write_json(
        args.output_dir / "summary.json",
        {
            "base_train_rows": len(train),
            "augment_rows": len(augment),
            "train_rows": len(output_train),
            "validation_rows": len(validation),
            "test_rows": len(test),
            "holdout_policy": "Do not train on data/eval/tourism_hard_nlu_holdout_20260518.jsonl.",
        },
    )
    print(json.dumps({"output": str(args.output_dir.relative_to(PROJECT_ROOT)), "train_rows": len(output_train)}, ensure_ascii=False))


if __name__ == "__main__":
    main()

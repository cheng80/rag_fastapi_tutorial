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
DEFAULT_BASE_DIR = PROJECT_ROOT / "data" / "processed" / "tourism_condition_transformer_hard_aug"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "data" / "processed" / "tourism_condition_transformer_residual_aug"

REGIONS = ["서울 강남구", "서울 중구", "부산 중구", "대구", "대전", "전주", "강릉", "성남시", "제주시", "서귀포시"]

RESIDUAL_TRAIN_PATTERNS: list[tuple[str, list[str], str]] = [
    ("{region}에서 어르신이 자주 앉아 쉬면서 볼 수 있는 관광지", ["고령자"], "residual:senior"),
    ("{region}에서 오래 서 있지 않고 관람 가능한 곳", ["고령자"], "residual:senior"),
    ("{region}에서 무릎 안 좋은 부모님이 계단 적게 다닐 곳", ["고령자"], "residual:senior"),
    ("{region}에서 쉬엄쉬엄 이동해도 되는 관광지", ["고령자"], "residual:senior"),
    ("{region}에서 걷는 거리 짧고 중간에 쉴 수 있는 곳", ["고령자"], "residual:senior"),
    ("{region}에서 다리 약한 동행이 부담 없이 둘러볼 코스", ["고령자"], "residual:senior"),
    ("{region}에서 부모님 컨디션이 안 좋아도 무리 적은 곳", ["고령자"], "residual:senior"),
    ("{region}에서 앉을 자리 많은 곳 위주로", ["고령자"], "residual:senior"),
    ("{region}에서 노약자 동행하기 편한 실내 관광지", ["고령자"], "residual:senior"),
    ("{region}에서 허리 불편한 분이 쉬어가며 볼 곳", ["고령자"], "residual:senior"),
    ("{region}에서 주챠 편한 관광지", ["주차"], "residual:parking_typo"),
    ("{region}에서 주차ㅏ 되는 곳", ["주차"], "residual:parking_typo"),
    ("{region}에서 차대기 편한 무장애 관광지", ["주차"], "residual:parking_typo"),
    ("{region}에서 차 세우고 바로 들어갈만한 곳", ["주차"], "residual:parking_typo"),
    ("{region}에서 입구앞 차 댈 수 있는 관광지", ["주차"], "residual:parking_typo"),
    ("{region}에서 장애인 주챠칸 있는 곳", ["주차"], "residual:parking_typo"),
    ("{region}에서 주자창 가까운 곳", ["주차"], "residual:parking_typo"),
    ("{region}에서 승하차 위치 가까운 데로", ["주차"], "residual:parking_typo"),
    ("{region}에서 보호자차 세우기 쉬운 관광지", ["주차"], "residual:parking_typo"),
    ("{region}에서 주차말고 대중교통으로 갈 곳", ["대중교통"], "residual:parking_negated"),
    ("{region}에서 주차는 빼고 버스로 갈 수 있는 곳", ["대중교통"], "residual:parking_negated"),
    ("{region}에서 차 대는 조건 말고 지하철 가까운 곳", ["대중교통"], "residual:parking_negated"),
    ("{region}에서 주차 얘기는 빼고 역에서 가까운 관광지", ["대중교통"], "residual:parking_negated"),
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
    ("{region}에서 그냥 걷기 편한 산책길", [], "boundary:ambiguous_or_general"),
    ("{region}에서 분위기 편한 곳", [], "boundary:ambiguous_or_general"),
    ("{region}에서 편하게 쉬는 여행지", [], "boundary:ambiguous_or_general"),
]


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


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
        "source": "residual_condition_aug_20260518",
        "template_family": family,
    }


def build_aug(rows: int, seed: int) -> list[dict[str, Any]]:
    rng = random.Random(seed)
    output: list[dict[str, Any]] = []
    for index in range(1, rows + 1):
        pattern, labels, family = rng.choice(RESIDUAL_TRAIN_PATTERNS)
        output.append(row(f"RESAUG-{index:05d}", pattern.format(region=rng.choice(REGIONS)), labels, family))
    return output


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        for item in rows:
            file.write(json.dumps(item, ensure_ascii=False, sort_keys=True) + "\n")


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare residual hard augmented condition data.")
    parser.add_argument("--base-dir", type=Path, default=DEFAULT_BASE_DIR)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--augment-rows", type=int, default=5000)
    parser.add_argument("--validation-rows", type=int, default=700)
    parser.add_argument("--seed", type=int, default=20260520)
    args = parser.parse_args()

    train = load_jsonl(args.base_dir / "train.jsonl")
    validation = load_jsonl(args.base_dir / "validation.jsonl")
    test = load_jsonl(args.base_dir / "test.jsonl")
    augment = build_aug(args.augment_rows + args.validation_rows, args.seed)
    residual_train = augment[: args.augment_rows]
    residual_validation = augment[args.augment_rows :]

    output_train = [*train, *residual_train]
    output_validation = [*validation, *residual_validation]

    write_jsonl(args.output_dir / "train.jsonl", output_train)
    write_jsonl(args.output_dir / "validation.jsonl", output_validation)
    write_jsonl(args.output_dir / "test.jsonl", test)
    write_json(args.output_dir / "labels.json", {"labels": CONDITION_LABELS})
    write_json(
        args.output_dir / "summary.json",
        {
            "base_dir": str(args.base_dir.relative_to(PROJECT_ROOT)),
            "base_train_rows": len(train),
            "base_validation_rows": len(validation),
            "augment_train_rows": len(residual_train),
            "augment_validation_rows": len(residual_validation),
            "train_rows": len(output_train),
            "validation_rows": len(output_validation),
            "test_rows": len(test),
            "holdout_policy": "Do not train on data/eval/tourism_residual_hard_nlu_20260518.jsonl.",
        },
    )
    print(
        json.dumps(
            {
                "output": str(args.output_dir.relative_to(PROJECT_ROOT)),
                "train_rows": len(output_train),
                "validation_rows": len(output_validation),
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()

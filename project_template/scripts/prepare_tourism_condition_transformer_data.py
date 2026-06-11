from __future__ import annotations

import argparse
import json
from pathlib import Path
import random
import re
import sys
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.services.tourism_query_service import CONDITION_KEYWORDS  # noqa: E402


CONDITION_LABELS = list(CONDITION_KEYWORDS)
DEFAULT_KEYWORD_INPUT = PROJECT_ROOT / "data" / "processed" / "tourism_keyword_variants_20260518_5000.valid.jsonl"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "data" / "processed" / "tourism_condition_transformer"

REGIONS = [
    "서울 중구",
    "서울 강남구",
    "부산 중구",
    "대구",
    "대전",
    "전주",
    "강릉",
    "성남시",
    "제주시",
    "서귀포시",
]
PLACE_TYPES = ["관광지", "실내 관광지", "박물관", "전시관", "공원", "시장 말고 관광지", "카페 말고 관광지"]
TAILS = ["추천해줘", "찾아줘", "볼 수 있을까", "알려줘", "위주로 보고 싶어", "가능한 곳 있을까"]

CONDITION_PHRASES = {
    "휠체어": ["휠체어로 갈 수 있는", "휄체어로 이동 가능한", "바퀴 의자로 들어갈 수 있는", "계단 없이 갈 수 있는"],
    "유모차": ["유모차 끌고 가기 좋은", "유아차로 이동하기 쉬운", "아기랑 가기 편한", "기저귀 갈 곳이 있으면 좋은"],
    "고령자": ["부모님이 오래 안 걸어도 되는", "어르신이 걷기 편한", "무릎 불편한 분도 부담 적은", "쉬어 가기 좋은"],
    "주차": ["장애인 주차가 확인되는", "입구 가까이 차를 댈 수 있는", "주차 동선이 편한", "주차장이 있는"],
    "화장실": ["장애인 화장실이 확인되는", "화장실 이용이 편한", "휠체어 화장실이 있는", "장애인화장실 있는"],
    "접근로": ["경사로가 있는", "출입통로가 넓은", "입구에 턱이 없는", "동선이 끊기지 않는", "평탄한 길 위주"],
    "대중교통": ["대중교통으로 가기 편한", "버스로 접근 가능한", "지하철에서 가까운", "대중 교통 안내가 있는"],
    "엘리베이터": ["엘리베이터가 있는", "엘베 있는", "승강기로 이동 가능한", "휠체어 리프트가 확인되는", "계단 리프트가 있는"],
    "보조견": ["보조견 동반 가능한", "안내견과 갈 수 있는", "보조갼 동반되는", "안내 견 출입 가능한"],
    "시각장애": ["점자 안내가 있는", "촉지도가 확인되는", "시각장애인 안내가 있는", "음성안내가 있는", "점자블럭 있는"],
    "청각장애": ["수어 안내가 있는", "자막 안내가 있는", "수어 또는 자막 안내가 확인되는", "소리 없이도 안내를 볼 수 있는"],
}

NEGATIVE_TEXTS = [
    "오늘 환율 알려줘",
    "내일 날씨 어때",
    "휠체어 대여 가격 제일 싼 곳",
    "응급실 가까운 곳 알려줘",
    "리프트 차량 예약 업체 찾아줘",
    "일반 식당만 찾아줘",
]
AMBIGUOUS_TEXTS = [
    "편한 곳 추천해줘",
    "괜찮은 데 있나",
    "부모님이랑 갈 만한 곳",
    "리프트 되는 곳",
    "안내가 잘 된 곳",
    "시설 좋은 데",
]


def compact_noise(text: str) -> str:
    return re.sub(r"\s+", "", text)


def typo_noise(text: str) -> str:
    replacements = [
        ("휠체어", "휄체어"),
        ("엘리베이터", "엘리배이터"),
        ("승강기", "승강끼"),
        ("보조견", "보조갼"),
        ("점자블록", "점자블럭"),
        ("무릎", "무릅"),
        ("유모차", "유모챠"),
    ]
    noisy = text
    for source, target in replacements:
        if source in noisy:
            return noisy.replace(source, target, 1)
    return noisy


def label_vector(labels: list[str]) -> list[int]:
    label_set = set(labels)
    return [1 if label in label_set else 0 for label in CONDITION_LABELS]


def row(row_id: str, text: str, labels: list[str], source: str, family: str) -> dict[str, Any]:
    clean_labels = [label for label in labels if label in CONDITION_LABELS]
    return {
        "id": row_id,
        "text": text,
        "labels": clean_labels,
        "label_vector": label_vector(clean_labels),
        "source": source,
        "template_family": family,
    }


def load_keyword_rows(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        payload = json.loads(line)
        text = str(payload.get("user_query") or "").strip()
        labels = [label for label in payload.get("expected_conditions") or [] if label in CONDITION_LABELS]
        rows.append(
            row(
                row_id=str(payload.get("id") or f"keyword-{len(rows)+1}"),
                text=text,
                labels=labels,
                source=str(path.relative_to(PROJECT_ROOT)),
                family=f"keyword:{payload.get('variant_type') or 'unknown'}:{payload.get('condition_label') or 'none'}",
            )
        )
    return rows


def generate_augmented_rows(target_rows: int, seed: int) -> list[dict[str, Any]]:
    rng = random.Random(seed)
    rows: list[dict[str, Any]] = []
    index = 1

    def add(text: str, labels: list[str], family: str) -> None:
        nonlocal index
        rows.append(row(f"COND-AUG-{index:05d}", text, labels, "deterministic_condition_augmentation", family))
        index += 1

    while len(rows) < target_rows:
        region = rng.choice(REGIONS)
        place_type = rng.choice(PLACE_TYPES)
        tail = rng.choice(TAILS)
        label = rng.choice(CONDITION_LABELS)
        phrase = rng.choice(CONDITION_PHRASES[label])
        text = f"{region}에서 {phrase} {place_type} {tail}"
        variant = rng.randrange(5)
        if variant == 1:
            text = compact_noise(text)
        elif variant == 2:
            text = typo_noise(text)
        elif variant == 3:
            text = text.replace("에서", " 근처에서", 1)
        add(text, [label], f"single:{label}:v{variant}")

        if len(rows) >= target_rows:
            break
        label_a, label_b = rng.sample(CONDITION_LABELS, 2)
        phrase_a = rng.choice(CONDITION_PHRASES[label_a])
        phrase_b = rng.choice(CONDITION_PHRASES[label_b])
        connector = rng.choice(["둘 다 되는", "둘 중 하나라도 되는", "도 같이 확인되는", "위주인데"])
        text = f"{region}에서 {phrase_a} 곳 중 {phrase_b} 조건도 {connector} {place_type} {tail}"
        labels = [label_a, label_b]
        if rng.randrange(4) == 0:
            text = compact_noise(text)
        add(text, labels, f"multi:{label_a}:{label_b}")

        if len(rows) >= target_rows:
            break
        negative = rng.choice(NEGATIVE_TEXTS + AMBIGUOUS_TEXTS)
        if rng.randrange(3) == 0:
            negative = f"{region} {negative}"
        add(negative, [], "none:negative-or-ambiguous")
    return rows[:target_rows]


def split_rows(rows: list[dict[str, Any]], validation_size: int, test_size: int, seed: int) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    rng = random.Random(seed)
    shuffled = list(rows)
    rng.shuffle(shuffled)
    test = shuffled[:test_size]
    validation = shuffled[test_size : test_size + validation_size]
    train = shuffled[test_size + validation_size :]
    for split_rows_ in (train, validation, test):
        split_rows_.sort(key=lambda item: item["id"])
    return train, validation, test


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        for payload in rows:
            file.write(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n")


def count_labels(rows: list[dict[str, Any]]) -> dict[str, int]:
    counts = {label: 0 for label in CONDITION_LABELS}
    counts["<none>"] = 0
    for payload in rows:
        labels = payload["labels"]
        if not labels:
            counts["<none>"] += 1
        for label in labels:
            counts[label] += 1
    return counts


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Prepare robust condition-label transformer data for tourism queries.")
    parser.add_argument("--keyword-input", type=Path, default=DEFAULT_KEYWORD_INPUT)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--augment-rows", type=int, default=10000)
    parser.add_argument("--validation-size", type=int, default=1200)
    parser.add_argument("--test-size", type=int, default=1600)
    parser.add_argument("--seed", type=int, default=20260518)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    source_rows = load_keyword_rows(args.keyword_input)
    augmented_rows = generate_augmented_rows(args.augment_rows, args.seed)
    all_rows = source_rows + augmented_rows
    train, validation, test = split_rows(all_rows, args.validation_size, args.test_size, args.seed)

    outputs = {
        "train": args.output_dir / "train.jsonl",
        "validation": args.output_dir / "validation.jsonl",
        "test": args.output_dir / "test.jsonl",
        "labels": args.output_dir / "labels.json",
        "summary": args.output_dir / "summary.json",
    }
    write_jsonl(outputs["train"], train)
    write_jsonl(outputs["validation"], validation)
    write_jsonl(outputs["test"], test)
    outputs["labels"].write_text(json.dumps({"labels": CONDITION_LABELS}, ensure_ascii=False, indent=2), encoding="utf-8")
    summary = {
        "source_rows": len(source_rows),
        "augment_rows": len(augmented_rows),
        "train_rows": len(train),
        "validation_rows": len(validation),
        "test_rows": len(test),
        "labels": CONDITION_LABELS,
        "train_label_counts": count_labels(train),
        "validation_label_counts": count_labels(validation),
        "test_label_counts": count_labels(test),
        "outputs": {name: str(path.relative_to(PROJECT_ROOT)) for name, path in outputs.items()},
    }
    outputs["summary"].write_text(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()

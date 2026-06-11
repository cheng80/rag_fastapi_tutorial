from __future__ import annotations

import argparse
from itertools import product
import json
from pathlib import Path
import random
import sys
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.services.tourism_context_classifier import CONTEXT_LABELS  # noqa: E402


DEFAULT_TRAIN_OUTPUT = PROJECT_ROOT / "data" / "processed" / "tourism_context_hard_style_extra_train.jsonl"
DEFAULT_VALIDATION_OUTPUT = PROJECT_ROOT / "data" / "eval" / "tourism_context_hard_style_validation.jsonl"


def rows_from_templates(
    templates: list[str],
    slots: dict[str, list[str]],
    labels: list[str],
    category: str,
    limit: int,
    rng: random.Random,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    prefixes = ["", "이번엔 ", "그럼 ", "혹시 ", "아까 결과에서 "]
    suffixes = ["", " 볼래", " 다시 봐줘", " 쪽으로", "만 추려줘"]
    for template in templates:
        names = [part.split("}", 1)[0] for part in template.split("{")[1:]]
        values = [slots[name] for name in names]
        for combo in product(*values):
            base = template.format(**dict(zip(names, combo, strict=True)))
            for prefix in prefixes:
                for suffix in suffixes:
                    text = " ".join(f"{prefix}{base}{suffix}".split())
                    rows.append(
                        {
                            "text": text,
                            "labels": labels,
                            "category": f"hard_style_{category}",
                            "risk_tags": [category],
                            "required_terms": [],
                            "optional_terms": [],
                            "excluded_terms": [],
                            "rationale": "hard-style generated context example",
                        }
                    )
    rng.shuffle(rows)
    return rows[:limit]


def build_specs() -> list[dict[str, Any]]:
    return [
        {
            "category": "soft_vs_strict",
            "labels": ["soft_and"],
            "templates": [
                "{a}는 있으면 좋고 {b}는 없어도 괜찮아",
                "{a} 위주로 보되 {b}도 참고만 해줘",
                "{a}랑 {b}를 말하긴 했는데 둘 다 필수는 아냐",
                "{a} 쪽이 우선이고 {b}는 후보 부족하면 봐줘",
            ],
            "slots": {
                "a": ["유모차 이동", "휠체어 접근", "아이랑 쉬기", "조용한 산책", "시장 구경"],
                "b": ["수유실", "장애인 화장실", "경사로", "먹거리", "박물관"],
            },
        },
        {
            "category": "strict_and_boundary",
            "labels": ["strict_and", "specific_facility_required"],
            "templates": [
                "{a} 없으면 빼고 {b}도 반드시 확인된 곳",
                "{a}만 되는 곳 말고 {b}까지 같이 되는 곳",
                "{a}와 {b} 둘 중 하나라도 빠지면 제외",
                "{a}, {b} 둘 다 카드에 근거 있는 후보만",
            ],
            "slots": {
                "a": ["점자블록", "장애인 주차", "보조견", "수어 안내", "수유실"],
                "b": ["자막 안내", "장애인 화장실", "엘리베이터", "기저귀 교환대", "오디오가이드"],
            },
        },
        {
            "category": "or_boundary",
            "labels": ["or_condition", "specific_facility_required"],
            "templates": [
                "{a}가 없으면 {b}라도 있으면 충분해",
                "{a} 아니면 {b} 중 하나만 확인돼도 돼",
                "{a}/{b} 둘 중 카드에 잡히는 쪽으로",
                "{a}와 {b}를 동시에 요구하는 건 아니야",
            ],
            "slots": {
                "a": ["수어 안내", "점자블록", "장애인 주차", "수유실", "경사로"],
                "b": ["자막 안내", "촉지도", "장애인 화장실", "기저귀 교환대", "엘리베이터"],
            },
        },
        {
            "category": "replace_active_span",
            "labels": ["replace_condition", "specific_facility_required"],
            "templates": [
                "{old}는 내려놓고 {new}가 실제로 적힌 곳",
                "{old} 얘기는 그만하고 {new} 근거 있는 카드",
                "이전 {old} 조건 취소하고 {new} 기준으로",
                "{old} 말고 이제 {new} 확인되는 곳",
            ],
            "slots": {
                "old": ["점자블록", "수어 안내", "시장", "유모차", "휠체어"],
                "new": ["오디오가이드", "자막 안내", "장애인 화장실", "수유실", "장애인 주차"],
            },
        },
        {
            "category": "replace_to_mobility",
            "labels": ["replace_condition", "mobility_context"],
            "templates": [
                "{old}는 빼고 {mobility} 이동 쉬운 쪽으로",
                "{old} 말고 {mobility} 동선 짧은 곳",
                "아까 {old} 기준 말고 {mobility} 부담 적은 후보",
                "{old}은 취소하고 {mobility}로 움직이기 쉬운 곳",
            ],
            "slots": {
                "old": ["시장", "실내", "수어 안내", "점자블록", "카페"],
                "mobility": ["유모차", "휠체어", "어르신", "노약자"],
            },
        },
        {
            "category": "exclude_not_replace",
            "labels": ["exclude_condition"],
            "templates": [
                "{thing}은 많으면 뒤로 보내고 남은 것부터",
                "{thing} 위주는 이번엔 빼자",
                "{thing} 성격은 제외하고 볼거리만",
                "{thing} 말고도 갈 만한 곳 있어?",
            ],
            "slots": {"thing": ["시장", "카페", "식당", "숙박", "쇼핑몰", "야외", "박물관"]},
        },
        {
            "category": "family_not_facility",
            "labels": ["family_context"],
            "templates": [
                "{family}랑 가는데 {facility}는 있으면 좋지만 필수는 아냐",
                "{family} 때문에 쉬운 곳이면 좋고 {facility}는 참고만",
                "{family} 동반이라 오래 기다리지 않는 곳",
                "{family}와 같이 가기 부담 없는 곳",
            ],
            "slots": {
                "family": ["아이", "아기", "영유아", "가족", "어린이"],
                "facility": ["수유실", "기저귀 교환대", "유아용 의자"],
            },
        },
        {
            "category": "mobility_not_family",
            "labels": ["mobility_context"],
            "templates": [
                "{mobility}라 계단 적은 쪽이면 돼",
                "{mobility} 이동만 편하면 가족 편의는 상관없어",
                "{mobility} 동선 짧은 후보부터",
                "{mobility}로 턱이 적은 곳",
            ],
            "slots": {"mobility": ["유모차", "유아차", "휠체어", "전동휠체어", "어르신"]},
        },
        {
            "category": "facility_word_negative",
            "labels": [],
            "templates": [
                "{word} 말고 {topic}가 독특한 곳",
                "{word} 얘기가 아니라 {topic} 분위기 좋은 곳",
                "{word}라는 이름이 들어간 전시 말고 일반 관광지",
                "{word}는 비유고 실제 시설 조건은 없어",
            ],
            "slots": {
                "word": ["주차", "화장실", "수어", "점자", "경사로"],
                "topic": ["주제", "사진", "전시", "동선", "이야기"],
            },
        },
        {
            "category": "specific_facility_only",
            "labels": ["specific_facility_required"],
            "templates": [
                "{facility}가 카드에 실제로 적힌 곳",
                "{facility} 근거 없는 후보는 빼줘",
                "{facility} 가능하다고 확인된 곳만",
                "{facility}는 추측 말고 문구 있는 곳",
            ],
            "slots": {
                "facility": [
                    "점자블록",
                    "촉지도",
                    "오디오가이드",
                    "수어 안내",
                    "자막 안내",
                    "보조견",
                    "장애인 주차",
                    "장애인 화장실",
                    "수유실",
                    "기저귀 교환대",
                ]
            },
        },
        {
            "category": "add_condition_hard",
            "labels": ["add_condition", "specific_facility_required"],
            "templates": [
                "이전 결과는 유지하고 {facility}만 추가로 봐줘",
                "방금 후보 중 {facility}까지 되는 것만",
                "그 목록에서 {facility} 근거도 붙은 카드",
                "{facility} 조건을 하나 더 얹어서 다시",
            ],
            "slots": {
                "facility": ["장애인 주차", "점자블록", "보조견", "엘리베이터", "수유실", "수어 안내"],
            },
        },
    ]


def dedupe(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    result: list[dict[str, Any]] = []
    for row in rows:
        key = "".join(str(row["text"]).split()).lower()
        if key in seen:
            continue
        seen.add(key)
        result.append(row)
    return result


def generate_rows(seed: int, per_category: int) -> list[dict[str, Any]]:
    rng = random.Random(seed)
    rows: list[dict[str, Any]] = []
    for spec in build_specs():
        rows.extend(
            rows_from_templates(
                templates=spec["templates"],
                slots=spec["slots"],
                labels=spec["labels"],
                category=spec["category"],
                limit=per_category,
                rng=rng,
            )
        )
    rows = dedupe(rows)
    rows.sort(key=lambda row: (row["category"], row["text"]))
    for index, row in enumerate(rows, start=1):
        row["id"] = f"HARDCTX{index:05d}"
        row["labels"] = [label for label in CONTEXT_LABELS if label in set(row["labels"])]
    return rows


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        for row in rows:
            file.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def count_labels(rows: list[dict[str, Any]]) -> dict[str, int]:
    counts = {label: 0 for label in CONTEXT_LABELS}
    counts["<none>"] = 0
    for row in rows:
        labels = row.get("labels") or []
        if not labels:
            counts["<none>"] += 1
        for label in labels:
            counts[label] += 1
    return counts


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate hard-style extra context train/validation data.")
    parser.add_argument("--train-output", type=Path, default=DEFAULT_TRAIN_OUTPUT)
    parser.add_argument("--validation-output", type=Path, default=DEFAULT_VALIDATION_OUTPUT)
    parser.add_argument("--per-category", type=int, default=220)
    parser.add_argument("--validation-ratio", type=float, default=0.25)
    parser.add_argument("--seed", type=int, default=20260517)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    rows = generate_rows(args.seed, args.per_category)
    rng = random.Random(args.seed + 99)
    by_category: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        by_category.setdefault(str(row["category"]), []).append(row)
    train: list[dict[str, Any]] = []
    validation: list[dict[str, Any]] = []
    for category_rows in by_category.values():
        shuffled = list(category_rows)
        rng.shuffle(shuffled)
        validation_count = max(1, int(len(shuffled) * args.validation_ratio))
        validation.extend(shuffled[:validation_count])
        train.extend(shuffled[validation_count:])
    train.sort(key=lambda row: row["id"])
    validation.sort(key=lambda row: row["id"])
    write_jsonl(args.train_output, train)
    write_jsonl(args.validation_output, validation)
    print(
        json.dumps(
            {
                "train_output": str(args.train_output.relative_to(PROJECT_ROOT)),
                "validation_output": str(args.validation_output.relative_to(PROJECT_ROOT)),
                "train_rows": len(train),
                "validation_rows": len(validation),
                "train_label_counts": count_labels(train),
                "validation_label_counts": count_labels(validation),
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()

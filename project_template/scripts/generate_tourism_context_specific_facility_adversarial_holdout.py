from __future__ import annotations

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


DEFAULT_OUTPUT = PROJECT_ROOT / "data" / "eval" / "tourism_context_specific_facility_adversarial_holdout.jsonl"


FACILITIES = [
    "점자블록",
    "오디오가이드",
    "수어 안내",
    "자막 안내",
    "보조견",
    "장애인 주차",
    "장애인 화장실",
    "엘리베이터",
    "경사로",
    "수유실",
    "기저귀 교환대",
]
TOPICS = ["전시", "분위기", "사진", "이야기", "동선", "주제"]
PREFERENCES = ["공원", "시장", "실내 관람", "조용한 산책", "아이랑 편한 곳", "휠체어 이동"]
REGIONS = ["서울 중구", "부산 중구", "대구", "전주", "제주시", "인천 부평구"]


def _dedupe(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    result: list[dict[str, Any]] = []
    for row in rows:
        key = "".join(str(row["text"]).split()).lower()
        if key in seen:
            continue
        seen.add(key)
        result.append(row)
    return result


def _labels(labels: list[str]) -> list[str]:
    return [label for label in CONTEXT_LABELS if label in set(labels)]


def _semantic_labels(base_labels: list[str], text: str) -> list[str]:
    labels = set(base_labels)
    if "아이랑 편한 곳" in text:
        labels.add("family_context")
    if "휠체어 이동" in text:
        labels.add("mobility_context")
    return _labels(sorted(labels))


def _rows_from_specs(seed: int, per_family: int) -> list[dict[str, Any]]:
    rng = random.Random(seed)
    specs = [
        {
            "family": "literal_required",
            "labels": ["specific_facility_required"],
            "templates": [
                "{facility} 문구가 원문에 있는 카드만",
                "{facility}는 추측 말고 확인된 근거만",
                "{facility} 근거 없으면 좋은 장소라도 제외",
                "{facility} 표시 여부가 핵심이야",
            ],
            "slots": {"facility": FACILITIES},
        },
        {
            "family": "literal_not_required",
            "labels": [],
            "templates": [
                "{facility} 얘기가 아니라 {topic}가 좋은 곳",
                "{facility} 조건을 말한 건 아니고 {topic} 분위기",
                "{facility} 근거 찾지 말고 {topic} 중심으로",
                "{facility}라는 단어가 있어도 시설 요청은 아니야",
            ],
            "slots": {"facility": FACILITIES, "topic": TOPICS},
        },
        {
            "family": "soft_optional_facility",
            "labels": ["soft_and"],
            "templates": [
                "{main} 위주면 충분하고 {facility}은 참고만",
                "{main} 먼저 보고 {facility}까지 꼭 맞출 필요는 없어",
                "{main}만 맞아도 괜찮고 {facility}은 있으면 좋다",
                "{main} 쪽이면 좋고 {facility}도 있으면 더 좋지만 필수는 아니야",
            ],
            "slots": {"main": PREFERENCES, "facility": FACILITIES},
        },
        {
            "family": "strict_facility_pair",
            "labels": ["strict_and", "specific_facility_required"],
            "templates": [
                "{a}랑 {b} 둘 중 하나만 되는 곳은 제외하고 {region}",
                "{a}와 {b}가 둘 다 확인된 카드만 {region}",
                "{a}만 있고 {b}가 없으면 안 돼 {region}",
                "{a}, {b}를 따로따로 말고 한 장소에서 확인해줘 {region}",
            ],
            "slots": {"a": FACILITIES, "b": FACILITIES, "region": REGIONS},
            "skip_same": ("a", "b"),
        },
        {
            "family": "or_facility_pair",
            "labels": ["or_condition", "specific_facility_required"],
            "templates": [
                "{a} 또는 {b} 중 하나라도 확인되면 돼",
                "{a}가 없으면 {b} 근거라도 있는 곳",
                "{a}와 {b}를 다 요구하는 건 아니고 하나면 된다",
                "{a} 아니어도 {b}가 있으면 후보에 넣어줘",
            ],
            "slots": {"a": FACILITIES, "b": FACILITIES},
            "skip_same": ("a", "b"),
        },
        {
            "family": "replace_active_facility",
            "labels": ["replace_condition", "specific_facility_required"],
            "templates": [
                "{old}는 더 보지 말고 {new} 문구가 있는 후보",
                "{old} 기준은 버리고 이제 {new}만 확인",
                "{old}로 좁힌 건 취소하고 {new} 근거 중심",
                "아까 {old}는 잊고 {new} 확인되는 곳",
            ],
            "slots": {"old": ["시장", "카페", "공원", "유모차", "어르신"], "new": FACILITIES},
        },
        {
            "family": "exclude_type_no_new_facility",
            "labels": ["exclude_condition"],
            "templates": [
                "{place_type} 말고 남은 관광지만 다시 정렬",
                "{place_type} 성격은 빼되 시설 조건은 새로 추가하지 마",
                "{place_type} 위주 결과는 뒤로 보내고 기존 조건 유지",
                "{place_type} 느낌만 아니면 {facility} 조건은 묻지 않아",
            ],
            "slots": {
                "place_type": ["시장", "카페", "식당", "숙박", "쇼핑몰", "야외"],
                "facility": FACILITIES,
            },
        },
    ]

    prefixes = ["", "가능하면 ", "이번엔 ", "아까 추천에서 ", "조건을 다시 말하면 "]
    suffixes = ["", " 보여줘", " 찾아줘", " 추천해줘", "만 부탁해"]
    rows: list[dict[str, Any]] = []
    for spec in specs:
        family_rows: list[dict[str, Any]] = []
        for template in spec["templates"]:
            names = [part.split("}", 1)[0] for part in template.split("{")[1:]]
            values = [spec["slots"][name] for name in names]
            for combo in product(*values):
                payload = dict(zip(names, combo, strict=True))
                skip_same = spec.get("skip_same")
                if skip_same and payload[skip_same[0]] == payload[skip_same[1]]:
                    continue
                base = template.format(**payload)
                for prefix in prefixes:
                    for suffix in suffixes:
                        text = " ".join(f"{prefix}{base}{suffix}".split())
                        family_rows.append(
                            {
                                "text": text,
                                "labels": _semantic_labels(spec["labels"], text),
                                "category": f"specific_facility_adversarial_{spec['family']}",
                                "template_family": f"specific_facility_adversarial_{spec['family']}",
                                "risk_tags": ["specific_facility_required", spec["family"]],
                                "required_terms": [],
                                "optional_terms": [],
                                "excluded_terms": [],
                            }
                        )
        rng.shuffle(family_rows)
        rows.extend(family_rows[:per_family])

    rows = _dedupe(rows)
    rows.sort(key=lambda row: (row["template_family"], row["text"]))
    for index, row in enumerate(rows, start=1):
        row["id"] = f"SPECADV{index:05d}"
    return rows


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        for row in rows:
            file.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def main() -> None:
    rows = _rows_from_specs(seed=20260517, per_family=140)
    write_jsonl(DEFAULT_OUTPUT, rows)
    print(json.dumps({"output": str(DEFAULT_OUTPUT.relative_to(PROJECT_ROOT)), "rows": len(rows)}, ensure_ascii=False))


if __name__ == "__main__":
    main()

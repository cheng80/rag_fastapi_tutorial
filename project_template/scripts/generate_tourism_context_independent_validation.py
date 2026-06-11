from __future__ import annotations

import argparse
from itertools import product
import json
from pathlib import Path
import random
import re
import sys
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.services.tourism_context_classifier import CONTEXT_LABELS  # noqa: E402


DEFAULT_OUTPUT = PROJECT_ROOT / "data" / "eval" / "tourism_context_independent_validation.jsonl"

FAMILY_CONTEXT_PATTERNS = [
    "아이랑",
    "아이와",
    "아이 동반",
    "아이 데리고",
    "어린이",
    "가족",
    "영유아",
    "아기",
]
MOBILITY_CONTEXT_PATTERNS = [
    "휠체어랑",
    "휠체어와",
    "휠체어 쪽",
    "휠체어 위주",
    "휠체어 이동",
    "휠체어 찾",
    "유모차",
    "유아차",
    "어르신",
    "노약자",
    "전동휠체어",
]


def _semantic_labels(base_labels: list[str], text: str) -> list[str]:
    labels = set(base_labels)
    if "family_context" in labels and re.search(r"(수유실|기저귀|유아용 의자).{0,18}(참고|필수\s*아님|없어도\s*된다)", text):
        labels.add("soft_and")
    if "soft_and" in labels:
        if any(term in text for term in FAMILY_CONTEXT_PATTERNS):
            labels.add("family_context")
        if any(term in text for term in MOBILITY_CONTEXT_PATTERNS):
            labels.add("mobility_context")
    return [label for label in CONTEXT_LABELS if label in labels]


def _rows_from_specs(specs: list[dict[str, Any]], per_family: int, seed: int) -> list[dict[str, Any]]:
    rng = random.Random(seed)
    rows: list[dict[str, Any]] = []
    openers = ["", "이번 질문은 ", "조건을 다시 말하면 ", "실제로는 ", "추천받을 때 "]
    closers = ["", " 정도로 봐줘", "라고 이해해줘", "만 골라줘", "부터 확인해줘"]
    for spec in specs:
        family_rows: list[dict[str, Any]] = []
        for template in spec["templates"]:
            names = [part.split("}", 1)[0] for part in template.split("{")[1:]]
            values = [spec["slots"][name] for name in names]
            for combo in product(*values):
                base = template.format(**dict(zip(names, combo, strict=True)))
                for opener in openers:
                    for closer in closers:
                        text = " ".join(f"{opener}{base}{closer}".split())
                        family_rows.append(
                            {
                                "text": text,
                                "labels": _semantic_labels(spec["labels"], text),
                                "category": f"independent_{spec['family']}",
                                "template_family": f"independent_validation_{spec['family']}",
                                "risk_tags": list(spec.get("risk_tags") or [spec["family"]]),
                                "required_terms": [],
                                "optional_terms": [],
                                "excluded_terms": [],
                                "rationale": spec["rationale"],
                            }
                        )
        rng.shuffle(family_rows)
        rows.extend(family_rows[:per_family])

    deduped: list[dict[str, Any]] = []
    seen: set[str] = set()
    for row in rows:
        key = "".join(str(row["text"]).split()).lower()
        if key in seen:
            continue
        seen.add(key)
        deduped.append(row)
    deduped.sort(key=lambda row: (row["template_family"], row["text"]))
    for index, row in enumerate(deduped, start=1):
        row["id"] = f"ICTXVAL{index:05d}"
    return deduped


def build_specs() -> list[dict[str, Any]]:
    return [
        {
            "family": "soft_priority_optional",
            "labels": ["soft_and"],
            "risk_tags": ["soft_and", "strict_and_boundary"],
            "rationale": "Several conditions are mentioned, but the utterance explicitly allows partial matches.",
            "templates": [
                "{main}가 제일 중요하고 {optional}은 후보가 적을 때만 참고",
                "{main} 위주면 충분하고 {optional}은 덤으로만 봐줘",
                "{main} 먼저 보고 {optional}까지 꼭 맞출 필요는 없어",
                "{main}만 맞아도 괜찮고 {optional}은 있으면 좋다",
            ],
            "slots": {
                "main": ["아이랑 편한 곳", "휠체어 이동", "조용한 산책", "시장 구경", "실내 관람"],
                "optional": ["수유실", "장애인 화장실", "먹거리", "경사로", "박물관"],
            },
        },
        {
            "family": "strict_facility_pair",
            "labels": ["strict_and", "specific_facility_required"],
            "risk_tags": ["strict_and", "specific_facility_required"],
            "rationale": "The user demands evidence for both facilities in the same card.",
            "templates": [
                "{a}와 {b} 둘 중 하나라도 근거 없으면 빼줘",
                "{a}만 보고 추천하지 말고 {b}도 같은 카드에 있어야 해",
                "{a}, {b}가 동시에 확인된 후보 아니면 제외",
                "{a}랑 {b}를 따로따로 말고 한 장소에서 확인해줘",
            ],
            "slots": {
                "a": ["점자블록", "보조견", "수어 안내", "장애인 주차", "수유실"],
                "b": ["오디오가이드", "자막 안내", "장애인 화장실", "엘리베이터", "기저귀 교환대"],
            },
        },
        {
            "family": "either_or_fallback",
            "labels": ["or_condition", "specific_facility_required"],
            "risk_tags": ["or_condition", "strict_and_boundary"],
            "rationale": "The user gives an OR condition and should not be treated as strict AND.",
            "templates": [
                "{a}가 없으면 {b} 쪽 근거라도 있는 곳",
                "{a}와 {b}를 다 요구하는 건 아니고 하나면 된다",
                "{a} 또는 {b} 중 더 잘 확인되는 조건으로 골라줘",
                "{a} 아니어도 {b}가 있으면 후보에 넣어줘",
            ],
            "slots": {
                "a": ["수어 안내", "점자블록", "장애인 주차", "경사로", "수유실"],
                "b": ["자막 안내", "촉지도", "장애인 화장실", "엘리베이터", "기저귀 교환대"],
            },
        },
        {
            "family": "replacement_active_requirement",
            "labels": ["replace_condition", "specific_facility_required"],
            "risk_tags": ["replace_condition", "active_span"],
            "rationale": "Only the requirement after the replacement marker should remain active.",
            "templates": [
                "아까 {old}는 잊고 {new} 근거 있는 곳",
                "{old} 기준은 버리고 이제 {new}만 확인",
                "{old}는 더 보지 말고 {new} 문구가 있는 후보",
                "{old}로 좁힌 건 취소하고 {new} 기준",
            ],
            "slots": {
                "old": ["시장", "유모차", "점자블록", "수어 안내", "카페"],
                "new": ["오디오가이드", "장애인 화장실", "자막 안내", "수유실", "장애인 주차"],
            },
        },
        {
            "family": "exclude_without_new_required",
            "labels": ["exclude_condition"],
            "risk_tags": ["exclude_condition", "negative_preference"],
            "rationale": "The user excludes a type but does not create a new facility requirement.",
            "templates": [
                "{thing} 위주 결과는 뒤로 미루고 다른 후보",
                "{thing} 느낌만 아니면 조건은 그대로",
                "{thing} 성격은 빼되 접근성 조건은 새로 추가하지 마",
                "{thing} 말고 남은 관광지만 다시 정렬",
            ],
            "slots": {"thing": ["시장", "카페", "식당", "숙박", "쇼핑몰", "야외", "박물관"]},
        },
        {
            "family": "family_context_without_facility_requirement",
            "labels": ["family_context"],
            "risk_tags": ["family_context", "specific_facility_boundary"],
            "rationale": "Family context is present, but named facilities are optional, not required.",
            "templates": [
                "{family}랑 가서 쉬운 곳이면 되고 {facility}은 필수 아님",
                "{family} 동반이라 편한 분위기 우선, {facility}은 참고",
                "{facility}보다 {family}가 지치지 않는 동선이 중요",
                "{family}와 같이 보기 좋은 곳이면 {facility} 없어도 된다",
            ],
            "slots": {
                "family": ["아이", "아기", "영유아", "어린이", "가족"],
                "facility": ["수유실", "기저귀 교환대", "유아용 의자"],
            },
        },
        {
            "family": "mobility_context_without_family",
            "labels": ["mobility_context"],
            "risk_tags": ["mobility_context", "family_boundary"],
            "rationale": "Mobility context is present without a family requirement.",
            "templates": [
                "{mobility} 이동이 편하면 되고 가족 편의는 상관없어",
                "{mobility} 기준 동선만 보고 아이 편의는 빼줘",
                "{mobility}로 턱이 적은 후보면 충분",
                "{mobility} 때문에 계단 회피가 핵심이야",
            ],
            "slots": {"mobility": ["유모차", "유아차", "휠체어", "전동휠체어", "어르신"]},
        },
        {
            "family": "facility_literal_not_metaphor",
            "labels": [],
            "risk_tags": ["negative_near_miss", "specific_facility_boundary"],
            "rationale": "Facility-like words are used as metaphor or negated topic, not as facility requirements.",
            "templates": [
                "{word} 얘기가 아니라 {topic}가 좋은 곳",
                "{word} 조건을 말한 건 아니고 {topic} 분위기",
                "{word}라는 단어가 들어가도 시설 요청은 아니야",
                "{word} 근거 찾지 말고 {topic} 중심으로",
            ],
            "slots": {
                "word": ["주차", "화장실", "수어", "점자", "경사로"],
                "topic": ["이야기", "전시", "사진", "주제", "동선"],
            },
        },
        {
            "family": "facility_required_no_inference",
            "labels": ["specific_facility_required"],
            "risk_tags": ["specific_facility_required", "no_inference"],
            "rationale": "The user requires explicit facility evidence and rejects inference.",
            "templates": [
                "{facility}는 가능성 말고 문구가 있어야 해",
                "{facility}라고 확인된 카드만 남겨줘",
                "{facility} 근거 없으면 좋은 장소라도 제외",
                "{facility}는 추측하지 말고 원문에 있는 것만",
            ],
            "slots": {
                "facility": [
                    "점자블록",
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
            "family": "add_condition_same_result_set",
            "labels": ["add_condition", "specific_facility_required"],
            "risk_tags": ["add_condition", "specific_facility_required"],
            "rationale": "The user wants to add a required facility condition to the previous result set.",
            "templates": [
                "이전 후보는 유지하고 {facility} 근거까지 추가",
                "방금 본 목록 안에서 {facility}도 있는 카드",
                "새 지역 말고 같은 결과에서 {facility} 조건 추가",
                "그 후보들에 {facility} 필터를 하나 더 걸어줘",
            ],
            "slots": {
                "facility": ["장애인 주차", "점자블록", "보조견", "엘리베이터", "수유실", "수어 안내"],
            },
        },
    ]


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
    parser = argparse.ArgumentParser(description="Generate independent hard validation data for context interpretation ML experiments.")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--per-family", type=int, default=120)
    parser.add_argument("--seed", type=int, default=20260517)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    rows = _rows_from_specs(build_specs(), args.per_family, args.seed)
    write_jsonl(args.output, rows)
    print(
        json.dumps(
            {
                "output": str(args.output.relative_to(PROJECT_ROOT)),
                "rows": len(rows),
                "families": sorted({row["template_family"] for row in rows}),
                "label_counts": count_labels(rows),
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()

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


DEFAULT_TRAIN_OUTPUT = PROJECT_ROOT / "data" / "processed" / "tourism_context_training.jsonl"
DEFAULT_HOLDOUT_OUTPUT = PROJECT_ROOT / "data" / "eval" / "tourism_context_hard_holdout.jsonl"

SPECIFIC_FACILITY_TERMS = [
    "점자블록",
    "점자",
    "촉지도",
    "오디오가이드",
    "음성안내",
    "수어 안내",
    "수어",
    "자막 안내",
    "자막",
    "보조견",
    "안내견",
    "장애인 주차",
    "장애인 화장실",
    "엘리베이터",
    "승강기",
    "경사로",
    "수유실",
    "기저귀 교환대",
    "유아용 의자",
]
MOBILITY_TERMS = ["휠체어", "전동휠체어", "유모차", "유아차", "어르신", "노약자", "보행"]
FAMILY_TERMS = ["아이", "어린이", "가족", "영유아", "아기"]
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


def _rows_from_templates(
    templates: list[str],
    slots: dict[str, list[str]],
    labels: list[str],
    category: str,
    limit: int,
    rng: random.Random,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    prefixes = ["", "혹시 ", "가능하면 ", "이번엔 ", "아까 추천에서 "]
    suffixes = ["", " 보여줘", " 찾아줘", " 추천해줘", "만 부탁해"]
    for template in templates:
        names = [part.split("}", 1)[0] for part in template.split("{")[1:]]
        values = [slots[name] for name in names]
        for combo in product(*values):
            base = template.format(**dict(zip(names, combo, strict=True)))
            for prefix in prefixes:
                for suffix in suffixes:
                    text = f"{prefix}{base}{suffix}"
                    rows.append({"text": " ".join(text.split()), "labels": labels, "category": category})
    rng.shuffle(rows)
    return rows[:limit]


def _deduplicate(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    seen: set[str] = set()
    for row in rows:
        text = str(row["text"])
        if text in seen:
            continue
        seen.add(text)
        result.append(row)
    return result


def _active_requirement_text(text: str) -> str:
    markers = ["말고", "빼고", "대신", "제외하고", "취소하고", "그만하고", "내려놓고", "대신 이제", "별로라"]
    candidates: list[tuple[int, str]] = []
    for marker in markers:
        index = text.rfind(marker)
        if index >= 0:
            if marker == "말고" and re.search(r"(추측|짐작|상상|확대해석)하지\s*$", text[:index]):
                continue
            candidates.append((index, text[index + len(marker) :]))
    if not candidates:
        return text
    _, active = max(candidates, key=lambda item: item[0])
    return active.strip() or text


def _adjust_labels_for_active_request(row: dict[str, Any]) -> None:
    labels = set(row.get("labels") or [])
    text = str(row.get("text") or "")
    category = str(row.get("category") or "")
    active_text = _active_requirement_text(text) if "replace" in category or "replace_condition" in labels else text
    if "replace_condition" in labels:
        if any(term in active_text for term in SPECIFIC_FACILITY_TERMS):
            labels.add("specific_facility_required")
        if any(term in active_text for term in MOBILITY_TERMS):
            labels.add("mobility_context")
        if any(term in active_text for term in FAMILY_TERMS):
            labels.add("family_context")
    if "soft_and" in labels:
        if any(term in text for term in FAMILY_CONTEXT_PATTERNS):
            labels.add("family_context")
        if any(term in text for term in MOBILITY_CONTEXT_PATTERNS):
            labels.add("mobility_context")
    row["labels"] = [label for label in CONTEXT_LABELS if label in labels]


def _extract_terms(text: str, labels: list[str]) -> tuple[list[str], list[str], list[str]]:
    known_terms = [
        "휠체어",
        "유모차",
        "유아차",
        "점자블록",
        "점자",
        "촉지도",
        "오디오가이드",
        "음성안내",
        "수어 안내",
        "수어",
        "자막 안내",
        "자막",
        "보조견",
        "안내견",
        "장애인 주차",
        "주차",
        "장애인 화장실",
        "화장실",
        "엘리베이터",
        "승강기",
        "경사로",
        "수유실",
        "기저귀 교환대",
        "기저귀",
        "유아용 의자",
        "시장",
        "카페",
        "식당",
        "숙박",
        "쇼핑몰",
        "먹거리",
        "박물관",
        "공원",
        "산책",
        "아이",
        "가족",
        "영유아",
        "어르신",
        "노약자",
    ]
    matched = [term for term in known_terms if term in text]
    excluded: list[str] = []
    if "exclude_condition" in labels or "replace_condition" in labels:
        for marker in [" 말고", " 빼고", "은 제외", "는 제외", "쪽은 사양", "아닌 곳", " 그만하고", " 내려놓고", " 취소하고", " 대신"]:
            marker_index = text.find(marker)
            if marker_index > 0:
                before = text[:marker_index]
                excluded = [term for term in matched if term in before]
                break

    if "or_condition" in labels or "soft_and" in labels:
        required = []
        optional = [term for term in matched if term not in excluded]
    else:
        required = [term for term in matched if term not in excluded]
        optional = []
    return list(dict.fromkeys(required)), list(dict.fromkeys(optional)), list(dict.fromkeys(excluded))


def generate_rows(seed: int = 20260516, per_category: int = 90) -> list[dict[str, Any]]:
    rng = random.Random(seed)
    specs = [
        {
            "category": "strict_and",
            "labels": ["strict_and", "specific_facility_required"],
            "templates": [
                "{region}에서 {a}와 {b}가 둘 다 확인되는 곳",
                "{region} {a}, {b} 모두 가능한 관광지",
                "{region}에서 {a}와 {b}를 동시에 만족하는 곳만",
                "{a}하고 {b}가 전부 되는 곳으로 {region} 추천",
                "{region} {a} {b} 빠짐없이 확인되는 후보만",
            ],
            "slots": {
                "region": ["부산 중구", "대구", "제주시", "인천 부평구", "서울 종로구", "전주"],
                "a": ["점자블록", "장애인 화장실", "경사로", "보조견", "수어 안내", "수유실"],
                "b": ["안내견", "엘리베이터", "자막 안내", "장애인 주차", "기저귀 교환대", "휠체어 접근"],
            },
        },
        {
            "category": "soft_and",
            "labels": ["soft_and", "specific_facility_required"],
            "templates": [
                "{region}에서 {a}랑 {b} 쪽으로 볼 만한 곳",
                "{region} {a}도 좋고 {b}도 있으면 좋겠어",
                "{region} {a} {b} 위주로 추천해줘",
                "{region}에서 {a}하고 {b} 고려해서 찾아줘",
                "{region} {a} 겸 {b} 느낌으로",
            ],
            "slots": {
                "region": ["서울", "부산", "대구", "광주", "강릉", "서귀포시"],
                "a": ["유모차", "휠체어", "시장", "공원", "아이랑", "어르신"],
                "b": ["산책", "먹거리", "박물관", "장애인 화장실", "경사로", "조용한 곳"],
            },
        },
        {
            "category": "or_condition",
            "labels": ["or_condition", "specific_facility_required"],
            "templates": [
                "{region}에서 {a}나 {b} 중 하나라도 확인되는 곳",
                "{region} {a} 또는 {b} 가능한 곳",
                "{region} {a} 혹은 {b} 있으면 돼",
                "{a}거나 {b} 되는 곳으로 {region} 추천",
                "{region} {a} 아니면 {b}라도 있는 곳",
            ],
            "slots": {
                "region": ["대구", "부산 중구", "서울 중구", "제주시", "인천", "속초"],
                "a": ["수어 안내", "점자블록", "장애인 주차", "수유실", "경사로"],
                "b": ["자막 안내", "오디오가이드", "장애인 화장실", "기저귀 교환대", "엘리베이터"],
            },
        },
        {
            "category": "add_condition",
            "labels": ["add_condition", "specific_facility_required"],
            "templates": [
                "방금 후보 중 {condition}도 되는 곳",
                "그중 {condition}까지 확인되는 곳만",
                "아까 결과에 {condition} 조건을 추가해줘",
                "{condition} 있는 곳으로 한 번 더 추려줘",
                "지금 목록에서 {condition}도 봐줘",
            ],
            "slots": {
                "condition": [
                    "장애인 주차",
                    "점자블록",
                    "보조견",
                    "엘리베이터",
                    "수유실",
                    "기저귀 교환대",
                    "유아용 의자",
                    "수어 안내",
                ]
            },
        },
        {
            "category": "replace_condition",
            "labels": ["replace_condition"],
            "templates": [
                "{old} 말고 {new} 기준으로 바꿔줘",
                "{old} 빼고 {new} 가능한 곳으로",
                "{old} 대신 {new} 확인되는 곳",
                "아까 조건 취소하고 {new} 위주로 다시",
                "{old}은 제외하고 {new} 쪽으로 변경",
            ],
            "slots": {
                "old": ["유모차", "휠체어", "시장", "실내", "수어 안내", "점자블록"],
                "new": ["휠체어", "유모차", "공원", "박물관", "자막 안내", "오디오가이드", "장애인 화장실"],
            },
        },
        {
            "category": "exclude_condition",
            "labels": ["exclude_condition"],
            "templates": [
                "{thing} 말고 볼거리 위주로",
                "{thing} 빼고 추천해줘",
                "{thing}은 제외하고 다시",
                "{thing} 쪽은 사양할게",
                "{thing} 아닌 곳으로 골라줘",
            ],
            "slots": {
                "thing": ["시장", "카페", "식당", "숙박", "쇼핑몰", "먹거리", "야외", "박물관"],
            },
        },
        {
            "category": "family_context",
            "labels": ["family_context"],
            "templates": [
                "{region}에서 {family} 가기 좋은 곳",
                "{family} 동반해서 부담 없는 관광지",
                "{region} {family}랑 갈 만한 곳",
                "{family}가 있어서 쉬운 동선이면 좋겠어",
                "{region} {family} 여행 후보",
                "{region} {family} 데리고 쉬기 좋은 곳",
                "{family}랑 오래 기다리지 않고 볼 수 있는 곳",
            ],
            "slots": {
                "region": ["서울", "부산", "대구", "제주", "전주", "강릉"],
                "family": ["아이랑", "아이와", "어린이", "가족", "영유아", "아기"],
            },
        },
        {
            "category": "mobility_context",
            "labels": ["mobility_context"],
            "templates": [
                "{region}에서 {mobility} 이동하기 편한 곳",
                "{mobility} 때문에 계단 적은 곳",
                "{region} {mobility} 동선이 무리 없는 관광지",
                "{mobility}로 가도 턱이 적은 곳",
                "{region} {mobility} 접근 쉬운 곳",
                "{region}에서 {mobility} 오래 걷지 않는 코스",
                "{mobility} 동반이라 이동 부담 적은 곳",
            ],
            "slots": {
                "region": ["서울", "부산", "대구", "제주", "속초", "인천"],
                "mobility": ["휠체어", "전동휠체어", "유모차로 이동", "어르신", "노약자", "보행"],
            },
        },
        {
            "category": "specific_facility_required",
            "labels": ["specific_facility_required"],
            "templates": [
                "{region}에서 {facility} 확인되는 곳",
                "{facility} 있는 관광지 찾아줘",
                "{region} {facility} 근거가 있는 카드만",
                "{facility} 여부가 나오는 곳으로",
                "{region} {facility} 가능한지 확인되는 후보",
            ],
            "slots": {
                "region": ["부산", "대구", "제주시", "서울", "전주", "인천"],
                "facility": [
                    "점자블록",
                    "촉지도",
                    "오디오가이드",
                    "보조견",
                    "장애인 주차",
                    "장애인 화장실",
                    "엘리베이터",
                    "경사로",
                    "수유실",
                    "유아용 의자",
                ],
            },
        },
        {
            "category": "facility_not_context",
            "labels": ["specific_facility_required"],
            "templates": [
                "{facility}만 카드에 적힌 곳",
                "{facility} 필드가 있는지만 확인해줘",
                "{facility} 근거 문구가 있는 후보",
                "{facility} 여부만 보고 싶어",
                "{region}에서 {facility} 표시된 장소",
            ],
            "slots": {
                "region": ["부산", "대구", "제주시", "서울", "전주", "인천"],
                "facility": [
                    "수유실",
                    "기저귀 교환대",
                    "유아용 의자",
                    "엘리베이터",
                    "승강기",
                    "경사로",
                    "장애인 화장실",
                    "장애인 주차",
                ],
            },
        },
        {
            "category": "negative_near_miss",
            "labels": [],
            "templates": [
                "{region} 여행지 추천해줘",
                "{region} 볼거리 알려줘",
                "아까 카드 출처 보여줘",
                "다음 후보 더 보여줘",
                "{region} 관광지 몇 곳만",
                "{region}에서 사진 찍기 좋은 곳",
            ],
            "slots": {
                "region": ["서울", "부산", "대구", "인천", "제주", "전주", "강릉", "속초"],
            },
        },
    ]

    rows: list[dict[str, Any]] = []
    for spec in specs:
        rows.extend(
            _rows_from_templates(
                templates=spec["templates"],
                slots=spec["slots"],
                labels=spec["labels"],
                category=spec["category"],
                limit=per_category,
                rng=rng,
            )
        )
    rows = _deduplicate(rows)
    rows.sort(key=lambda row: (row["category"], row["text"]))
    for index, row in enumerate(rows, start=1):
        row["id"] = f"CTX{index:04d}"
        _adjust_labels_for_active_request(row)
        required_terms, optional_terms, excluded_terms = _extract_terms(str(row["text"]), list(row.get("labels") or []))
        row["required_terms"] = required_terms
        row["optional_terms"] = optional_terms
        row["excluded_terms"] = excluded_terms
    return rows


def split_train_holdout(rows: list[dict[str, Any]], seed: int = 20260516) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    rng = random.Random(seed)
    by_category: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        by_category.setdefault(str(row["category"]), []).append(row)

    train: list[dict[str, Any]] = []
    holdout: list[dict[str, Any]] = []
    for category, category_rows in sorted(by_category.items()):
        shuffled = list(category_rows)
        rng.shuffle(shuffled)
        split = max(1, int(len(shuffled) * 0.45))
        train.extend(shuffled[:split])
        holdout.extend(shuffled[split:])
    train.sort(key=lambda row: row["id"])
    holdout.sort(key=lambda row: row["id"])
    return train, holdout


def generate_hard_holdout_rows(seed: int = 20260517, per_category: int = 90) -> list[dict[str, Any]]:
    rng = random.Random(seed)
    specs = [
        {
            "category": "add_hard",
            "labels": ["add_condition", "specific_facility_required"],
            "templates": [
                "방금 목록에서 {condition}까지 붙여서 다시 걸러줘",
                "그 후보들 중 {condition} 근거도 있는 것만",
                "이전 결과 유지하고 {condition} 조건만 더해줘",
                "{condition}도 충족하는지 같은 카드 안에서 봐줘",
                "지금 추천에 {condition} 필터를 하나 얹어줘",
            ],
            "slots": {
                "condition": [
                    "장애인 주차",
                    "점자블록",
                    "보조견",
                    "엘리베이터",
                    "수유실",
                    "기저귀 교환대",
                    "유아용 의자",
                    "수어 안내",
                ]
            },
        },
        {
            "category": "strict_and_hard",
            "labels": ["strict_and", "specific_facility_required"],
            "templates": [
                "{region}, {a}만 있고 {b}가 없으면 안 돼",
                "{a}랑 {b} 둘 중 하나만 되는 곳은 제외하고 {region}",
                "{region}에서 {a}, {b}가 같이 확인된 카드만 남겨",
                "{a}도 {b}도 빠지면 곤란해서 {region}은 둘 다 필요해",
                "{region} {a}는 물론 {b}까지 근거 있는 곳만",
            ],
            "slots": {
                "region": ["부산 중구", "대구", "제주시", "인천 부평구", "서울 중구", "전주"],
                "a": ["점자블록", "장애인 화장실", "경사로", "보조견", "수어 안내", "수유실"],
                "b": ["안내견", "엘리베이터", "자막 안내", "장애인 주차", "기저귀 교환대", "휠체어 접근"],
            },
        },
        {
            "category": "soft_and_hard",
            "labels": ["soft_and"],
            "templates": [
                "{a} 쪽이면 좋고 {b}도 있으면 더 좋지만 필수는 아니야",
                "{region}에서 {a}랑 {b} 느낌을 같이 고려해줘",
                "{a} 위주로 보되 {b}도 괜찮은 후보 있으면 섞어줘",
                "{region} {a} 찾는데 {b}도 참고만 해줘",
                "{a}와 {b}를 둘 다 말하긴 했지만 가능한 후보부터 보여줘",
            ],
            "slots": {
                "region": ["서울", "부산", "대구", "제주", "강릉", "광주"],
                "a": ["유모차", "휠체어", "시장", "공원", "아이랑", "어르신"],
                "b": ["산책", "먹거리", "박물관", "화장실", "경사로", "조용한 곳"],
            },
        },
        {
            "category": "or_hard",
            "labels": ["or_condition", "specific_facility_required"],
            "templates": [
                "{a}가 없으면 {b}라도 있으면 돼",
                "{region}은 {a}/{b} 중 확인되는 쪽으로",
                "{a} 아니면 {b}, 둘 중 하나만 근거 있어도 후보로 봐줘",
                "{region} {a}가 최선이고 없으면 {b}도 가능",
                "{a}와 {b}를 동시에 요구하는 건 아니고 하나면 충분해",
            ],
            "slots": {
                "region": ["대구", "부산 중구", "서울 종로구", "제주시", "인천", "속초"],
                "a": ["수어 안내", "점자블록", "장애인 주차", "수유실", "경사로"],
                "b": ["자막 안내", "오디오가이드", "장애인 화장실", "기저귀 교환대", "엘리베이터"],
            },
        },
        {
            "category": "replace_exclude_hard",
            "labels": ["replace_condition"],
            "templates": [
                "아까 {old}로 본 건 취소하고 {new} 기준으로 다시",
                "{old} 조건은 내려놓고 {new} 확인되는 곳",
                "{old} 얘기는 그만하고 {new} 있는 후보만",
                "이전 필터 {old} 대신 이제 {new}",
                "{old} 중심 결과가 별로라 {new} 쪽으로 갈아타자",
            ],
            "slots": {
                "old": ["유모차", "휠체어", "시장", "실내", "수어 안내", "점자블록"],
                "new": ["휠체어", "유모차", "공원", "박물관", "자막 안내", "오디오가이드", "장애인 화장실"],
            },
        },
        {
            "category": "exclude_only_hard",
            "labels": ["exclude_condition"],
            "templates": [
                "{thing}은 이번엔 빼자",
                "{thing} 카드가 많으면 걔네는 뒤로 보내",
                "{thing} 위주는 원하지 않아",
                "{thing} 말고도 볼 만한 데 있어?",
                "{thing} 성격은 제외하고 남은 후보",
            ],
            "slots": {"thing": ["시장", "카페", "식당", "숙박", "쇼핑몰", "먹거리", "야외", "박물관"]},
        },
        {
            "category": "family_mobility_hard",
            "labels": ["family_context", "mobility_context"],
            "templates": [
                "{family} 있는데 오래 걷지 않는 곳",
                "{family}랑 가고 계단이 적었으면 해",
                "{family} 동반이라 동선 짧은 곳",
                "{family} 때문에 유모차로 움직이기 쉬운 곳",
                "{family}와 어르신이 같이 가도 부담 없는 곳",
            ],
            "slots": {"family": ["아이", "아기", "영유아", "가족", "어린이"]},
        },
        {
            "category": "family_only_hard",
            "labels": ["family_context"],
            "templates": [
                "{family} 데리고 실내 위주로 쉬기 좋은 곳",
                "{family}랑 가는데 너무 복잡하지 않은 후보",
                "{family} 동반이라 대기 길지 않은 곳이면 좋겠어",
                "{family}와 같이 가는 여행지로 골라줘",
                "{family} 때문에 수유나 기저귀도 확인되면 좋아",
            ],
            "slots": {"family": ["아이", "아기", "영유아", "가족", "어린이"]},
        },
        {
            "category": "mobility_only_hard",
            "labels": ["mobility_context"],
            "templates": [
                "{mobility}라 오래 걷지 않는 곳",
                "{mobility} 때문에 이동 부담 적은 후보",
                "{mobility} 동반이라 계단 피하고 싶어",
                "{mobility} 기준으로 동선 짧은 곳",
                "{mobility}가 있어도 움직이기 쉬운 장소",
            ],
            "slots": {"mobility": ["휠체어", "전동휠체어", "유모차", "어르신", "노약자"]},
        },
        {
            "category": "facility_not_context_hard",
            "labels": ["specific_facility_required"],
            "templates": [
                "{facility} 시설명만 확인해줘",
                "{facility} 문구가 카드에 있는지만 봐줘",
                "{facility} 조건은 필요하지만 동반자 맥락은 아냐",
                "{facility} 근거만 있으면 되고 가족 여행은 아니야",
                "{facility} 표시 여부만 기준으로",
            ],
            "slots": {
                "facility": [
                    "수유실",
                    "기저귀 교환대",
                    "유아용 의자",
                    "엘리베이터",
                    "승강기",
                    "경사로",
                    "장애인 화장실",
                    "장애인 주차",
                ]
            },
        },
        {
            "category": "facility_required_hard",
            "labels": ["specific_facility_required"],
            "templates": [
                "{facility}라고 카드에 적힌 곳만",
                "{facility} 근거 없으면 추천하지 마",
                "{facility} 확인 문구가 있는 후보",
                "{facility} 여부를 추측하지 말고 있는 곳",
                "{region} {facility} 필드가 잡히는 장소",
            ],
            "slots": {
                "region": ["부산", "대구", "제주시", "서울", "전주", "인천"],
                "facility": [
                    "점자블록",
                    "촉지도",
                    "오디오가이드",
                    "보조견",
                    "장애인 주차",
                    "장애인 화장실",
                    "엘리베이터",
                    "경사로",
                    "수유실",
                    "유아용 의자",
                ],
            },
        },
        {
            "category": "negative_boundary_hard",
            "labels": [],
            "templates": [
                "모두가 좋아할 만한 {region} 여행지",
                "{region} 전체 목록 더 보여줘",
                "수어지교처럼 분위기 좋은 곳",
                "주차 말고 주제가 독특한 곳",
                "화장실이 아니라 화려한 실내 전시",
                "{region} 아이디어만 몇 개 줘",
            ],
            "slots": {"region": ["서울", "부산", "대구", "인천", "제주", "전주", "강릉", "속초"]},
        },
    ]
    rows: list[dict[str, Any]] = []
    for spec in specs:
        rows.extend(
            _rows_from_templates(
                templates=spec["templates"],
                slots=spec["slots"],
                labels=spec["labels"],
                category=spec["category"],
                limit=per_category,
                rng=rng,
            )
        )
    rows = _deduplicate(rows)
    rows.sort(key=lambda row: (row["category"], row["text"]))
    for index, row in enumerate(rows, start=1):
        row["id"] = f"CTXH{index:04d}"
        _adjust_labels_for_active_request(row)
        required_terms, optional_terms, excluded_terms = _extract_terms(str(row["text"]), list(row.get("labels") or []))
        row["required_terms"] = required_terms
        row["optional_terms"] = optional_terms
        row["excluded_terms"] = excluded_terms
    return rows


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        for row in rows:
            file.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def _count_labels(rows: list[dict[str, Any]]) -> dict[str, int]:
    counts = {label: 0 for label in CONTEXT_LABELS}
    counts["<none>"] = 0
    for row in rows:
        labels = row.get("labels") or []
        if not labels:
            counts["<none>"] += 1
        for label in labels:
            counts[str(label)] = counts.get(str(label), 0) + 1
    return counts


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate tourism context interpretation train/holdout data.")
    parser.add_argument("--train-output", type=Path, default=DEFAULT_TRAIN_OUTPUT)
    parser.add_argument("--holdout-output", type=Path, default=DEFAULT_HOLDOUT_OUTPUT)
    parser.add_argument("--per-category", type=int, default=400)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    train = generate_rows(per_category=args.per_category)
    holdout = generate_hard_holdout_rows(per_category=args.per_category)
    write_jsonl(args.train_output, train)
    write_jsonl(args.holdout_output, holdout)
    print(
        json.dumps(
            {
                "train_rows": len(train),
                "holdout_rows": len(holdout),
                "train_labels": _count_labels(train),
                "holdout_labels": _count_labels(holdout),
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()

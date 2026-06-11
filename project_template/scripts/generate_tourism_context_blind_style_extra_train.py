from __future__ import annotations

from itertools import product
import json
from pathlib import Path
import sys
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.services.tourism_context_classifier import CONTEXT_LABELS  # noqa: E402


DEFAULT_OUTPUT = PROJECT_ROOT / "data" / "processed" / "tourism_context_blind_style_extra_train.jsonl"
BLIND_HOLDOUT = PROJECT_ROOT / "data" / "eval" / "tourism_context_blind_holdout.jsonl"


def ordered(labels: list[str]) -> list[str]:
    return [label for label in CONTEXT_LABELS if label in set(labels)]


def normalize(text: str) -> str:
    return "".join(text.split()).lower()


def row(text: str, labels: list[str], category: str) -> dict[str, Any]:
    return {
        "text": " ".join(text.split()),
        "labels": ordered(labels),
        "category": category,
        "template_family": f"blind_style_extra_train_{category}",
        "source": "blind_style_extra_train",
    }


def existing_blind_texts() -> set[str]:
    if not BLIND_HOLDOUT.exists():
        return set()
    return {
        normalize(json.loads(line).get("text") or "")
        for line in BLIND_HOLDOUT.read_text(encoding="utf-8").splitlines()
        if line.strip()
    }


def build_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    facilities = ["점자블록", "안내견", "장애인 화장실", "장애인 주차", "오디오가이드", "촉지도", "수어 안내", "자막 안내", "엘베", "엘리베이터", "경사로"]
    family_terms = ["애기", "아가", "아이", "유아", "어린이"]
    mobility_terms = ["휠체어", "전동휠체어", "유아차", "유모차", "어르신", "무릎 불편한 사람"]
    optional_places = ["공원", "전시", "산책", "시장 구경", "박물관", "실내 관람"]

    for a, b in product(facilities[:7], facilities[3:]):
        if a == b:
            continue
        rows.extend(
            [
                row(f"{a}하고 {b} 중 하나라도 빠지면 후보에서 제외해", ["strict_and", "specific_facility_required"], "strict_colloquial"),
                row(f"{a}나 {b} 한쪽만 되는 데 말고 같이 맞는 곳", ["strict_and", "specific_facility_required"], "strict_colloquial"),
            ]
        )

    for a, b in product(facilities[:6], facilities[5:]):
        if a == b:
            continue
        rows.extend(
            [
                row(f"{a}가 제일 좋고 없으면 {b}라도 되는 곳", ["or_condition", "specific_facility_required"], "or_fallback_colloquial"),
                row(f"{a} 아니면 {b} 근거라도 잡히면 괜찮아", ["or_condition", "specific_facility_required"], "or_fallback_colloquial"),
            ]
        )

    for main, optional in product(optional_places, facilities[2:]):
        rows.extend(
            [
                row(f"{main}이 우선이고 {optional}은 후보 적을 때만 가산점", ["soft_and"], "soft_optional_colloquial"),
                row(f"{main} 위주면 되고 {optional}은 필수까진 아니야", ["soft_and"], "soft_optional_colloquial"),
                row(f"{main} 먼저 보고 {optional}도 보이면 좋다는 정도", ["soft_and"], "soft_optional_colloquial"),
            ]
        )

    for family, facility in product(family_terms, ["수유실", "기저귀 교환대", "유아 의자", "유아용 의자"]):
        rows.extend(
            [
                row(f"{family}랑 가니 편한 곳이 우선이고 {facility}은 덤", ["soft_and", "family_context"], "family_colloquial"),
                row(f"{facility} 없어도 되니 {family}가 덜 지치는 곳", ["soft_and", "family_context", "mobility_context"], "family_colloquial"),
                row(f"{family} 데리고 보기 좋은 곳이면 {facility}은 참고만", ["soft_and", "family_context"], "family_colloquial"),
            ]
        )

    for mobility, optional in product(mobility_terms, ["카페", "먹거리", "전시", "산책"]):
        rows.extend(
            [
                row(f"{mobility} 동선이 먼저고 {optional}은 있으면 좋다", ["soft_and", "mobility_context"], "mobility_colloquial"),
                row(f"{mobility}로 움직이기 편한 곳 위주, {optional}도 괜찮으면 섞어줘", ["soft_and", "mobility_context"], "mobility_colloquial"),
                row(f"{mobility} 때문에 이동 짧은 곳이면 충분해", ["mobility_context"], "mobility_colloquial"),
            ]
        )

    followup_terms = ["그 결과", "방금 후보", "아까 카드", "위 목록", "이전 추천"]
    for prefix, facility in product(followup_terms, facilities):
        rows.extend(
            [
                row(f"{prefix}에서 {facility} 문구 있는 것만 남겨줘", ["add_condition", "specific_facility_required"], "add_followup_colloquial"),
                row(f"{prefix} 안에서 {facility} 조건까지 체크해줘", ["add_condition", "specific_facility_required"], "add_followup_colloquial"),
            ]
        )
    for prefix, mobility in product(followup_terms, mobility_terms):
        rows.append(row(f"{prefix} 중 {mobility} 이동 편한 쪽으로 좁혀줘", ["add_condition", "mobility_context"], "add_followup_colloquial"))
    for prefix, family in product(followup_terms, family_terms):
        rows.append(row(f"{prefix} 중 {family}랑 가기 편한 데만 다시", ["add_condition", "family_context"], "add_followup_colloquial"))

    for old, new in product(["시장", "카페", "유모차", "수어 안내", "점자블록", "부산 중구"], ["공원", "실내 전시", "휠체어", "오디오가이드", "장애인 화장실", "대구"]):
        if old == new:
            continue
        labels = ["replace_condition"]
        if new in {"휠체어"}:
            labels.append("mobility_context")
        if new in {"오디오가이드", "장애인 화장실"}:
            labels.append("specific_facility_required")
        rows.append(row(f"{old} 기준은 내려놓고 {new} 쪽으로 다시 볼래", labels, "replace_colloquial"))

    for place in ["시장 골목", "숙박", "카페", "음식점", "야외", "계단 많은 곳", "붐비는 곳"]:
        labels = ["exclude_condition"]
        if place in {"계단 많은 곳", "붐비는 곳"}:
            labels.append("mobility_context")
        rows.extend(
            [
                row(f"{place}은 패스하고 다른 후보만 보여줘", labels, "exclude_colloquial"),
                row(f"{place} 느낌은 빼고 조건은 유지해줘", labels, "exclude_colloquial"),
            ]
        )

    near_misses = [
        "주차 이야기가 아니라 주제가 독특한 곳",
        "화장실 얘기 말고 물가 풍경 좋은 곳",
        "수어라는 이름의 장소가 아니라 실제 관광지",
        "아이돌 굿즈 말하는 거지 아이 동반은 아니야",
        "가족이라는 상호명 말고 조용한 전시",
        "엘베라는 노래 제목 말고 산책 장소",
    ]
    rows.extend(row(text, [], "negative_near_miss_colloquial") for text in near_misses)

    blind_texts = existing_blind_texts()
    deduped: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in rows:
        key = normalize(item["text"])
        if key in seen or key in blind_texts:
            continue
        seen.add(key)
        deduped.append(item)
    for index, item in enumerate(deduped, start=1):
        item["id"] = f"CTXBST{index:05d}"
    return deduped


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        for item in rows:
            file.write(json.dumps(item, ensure_ascii=False, sort_keys=True) + "\n")


def main() -> None:
    rows = build_rows()
    write_jsonl(DEFAULT_OUTPUT, rows)
    counts: dict[str, int] = {"<none>": 0}
    for item in rows:
        if not item["labels"]:
            counts["<none>"] += 1
        for label in item["labels"]:
            counts[label] = counts.get(label, 0) + 1
    print(json.dumps({"output": str(DEFAULT_OUTPUT.relative_to(PROJECT_ROOT)), "rows": len(rows), "label_counts": dict(sorted(counts.items()))}, ensure_ascii=False))


if __name__ == "__main__":
    main()

from __future__ import annotations

import argparse
import json
from pathlib import Path
import random
import re
import sys
from typing import Any, Callable


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.services.tourism_context_classifier import CONTEXT_LABELS  # noqa: E402


DEFAULT_OUTPUT = (
    PROJECT_ROOT
    / "data"
    / "generated"
    / "tour_api"
    / "context_llm_batches"
    / "context_llm_batch_20260517_human_light_1000.raw.jsonl"
)


PLACES = ["시장", "카페", "맛집", "숙박", "해변", "공연장", "축제", "야외 코스", "등산로", "체험장"]
TARGETS = ["박물관", "공원", "숲길", "실내 전시", "미술관", "산책 코스", "전망대", "문화관", "수목원", "역사관"]
MOBILITY = ["휠체어", "유모차", "유아차", "어르신", "무릎 불편한 부모님", "전동휠체어", "보행 보조기"]
MOBILITY_NEEDS = ["계단 적음", "짧은 동선", "평탄한 길", "앉아 쉴 곳", "오래 서지 않는 코스", "경사로", "엘리베이터"]
FACILITIES = ["장애인 화장실", "장애인 주차장", "점자 안내", "수어 안내", "자막 자료", "음성안내", "수유실", "기저귀 교환대", "엘리베이터", "경사로"]
FAMILY = ["아이와", "아기와", "영유아와", "초등학생과", "가족과", "아이와 부모님과", "유아를 데리고"]
MEDIA_TOPICS = ["수어 공연", "점자블록 사진", "자막 제작 사례", "장애인 주차 정책", "가족 단위 방문 통계", "유모차 브랜드"]
TONES = ["추천해줘", "찾아줘", "다시 보여줘", "골라줘", "좁혀줘", "알려줘", "보고 싶어"]
SOFT_MARKERS = ["있으면 좋고 없으면 괜찮아", "가능하면 좋겠어", "참고만 해줘", "우선순위는 낮아", "덤으로 보면 돼"]
STRICT_MARKERS = ["둘 다 확인되는 곳만", "모두 갖춘 곳만", "하나라도 빠지면 제외해줘", "반드시 있어야 해", "같은 카드에서 같이 확인되는 곳만"]
OR_MARKERS = ["중 하나만 있으면 돼", "둘 중 하나면 충분해", "아니면", "또는", "어느 쪽이든 괜찮아"]
ADD_PREFIXES = ["방금 후보에서", "아까 추천은 유지하고", "이전 결과는 그대로 두고", "그 목록 안에서", "같은 지역에서"]
REPLACE_PREFIXES = ["이번엔", "이제", "그 조건은 내려놓고", "기준을 바꿔서", "아까 조건 말고"]
NEGATIONS = ["뜻은 아니야", "찾는 게 아니야", "추천을 달라는 건 아니야", "조건으로 보지 말아줘", "분위기 설명이 궁금한 거야"]


def normalize_text(text: str) -> str:
    normalized = re.sub(r"\s+", "", text.strip().lower())
    return re.sub(r"[^\w가-힣]", "", normalized)


def project_relative(path: Path) -> str:
    resolved = path.resolve()
    try:
        return str(resolved.relative_to(PROJECT_ROOT))
    except ValueError:
        return str(path)


def has_batchim(value: str) -> bool:
    if not value:
        return False
    code = ord(value[-1])
    if not 0xAC00 <= code <= 0xD7A3:
        return False
    return (code - 0xAC00) % 28 != 0


def josa(value: str, batchim: str, no_batchim: str) -> str:
    return f"{value}{batchim if has_batchim(value) else no_batchim}"


def maybe_add_user_noise(payload: dict[str, Any], rng: random.Random) -> dict[str, Any]:
    text = str(payload["text"])
    tags = list(payload.get("risk_tags") or [])
    noise_roll = rng.random()
    if noise_roll >= 0.4:
        return payload

    if noise_roll < 0.12:
        text = re.sub(r"\s+", "", text)
        tags.append("user-noise:no-spacing")
    elif noise_roll < 0.22:
        text = re.sub(r"\s+", " ", text)
        words = text.split(" ")
        if len(words) > 3:
            remove_index = rng.randrange(1, len(words) - 1)
            words[remove_index - 1] = words[remove_index - 1] + words[remove_index]
            del words[remove_index]
            text = " ".join(words)
        tags.append("user-noise:partial-spacing")
    elif noise_roll < 0.31:
        replacements = [
            ("휠체어", "휠체여"),
            ("유모차", "유모챠"),
            ("유아차", "유아챠"),
            ("엘리베이터", "엘베"),
            ("장애인", "장애 인"),
            ("점자 안내", "점자안내"),
            ("수어 안내", "수어안내"),
            ("기저귀", "기저기"),
            ("추천해줘", "추천좀"),
            ("찾아줘", "찾아바줘"),
        ]
        for source, target in rng.sample(replacements, len(replacements)):
            if source in text:
                text = text.replace(source, target, 1)
                break
        tags.append("user-noise:typo-or-shortening")
    else:
        suffix = rng.choice([" 좀", " 부탁", " 가능?", " 되는곳", " 볼수있나", " 해줄래"])
        text = f"{text}{suffix}"
        tags.append("user-noise:colloquial-tail")

    noisy = dict(payload)
    noisy["text"] = text
    noisy["risk_tags"] = list(dict.fromkeys(tags))
    return noisy


def row(
    index: int,
    text: str,
    labels: list[str],
    category: str,
    required_terms: list[str] | None = None,
    optional_terms: list[str] | None = None,
    excluded_terms: list[str] | None = None,
    risk_tags: list[str] | None = None,
    rationale: str = "",
) -> dict[str, Any]:
    invalid = [label for label in labels if label not in CONTEXT_LABELS]
    if invalid:
        raise ValueError(f"invalid labels in template: {invalid}")
    return {
        "id": f"LLMCTXHL20260517{index:04d}",
        "text": text,
        "labels": labels,
        "category": category,
        "required_terms": required_terms or [],
        "optional_terms": optional_terms or [],
        "excluded_terms": excluded_terms or [],
        "risk_tags": risk_tags or [],
        "rationale": rationale,
    }


Scenario = Callable[[int, random.Random], dict[str, Any]]


def soft_mobility(index: int, rng: random.Random) -> dict[str, Any]:
    mobility = rng.choice(MOBILITY)
    need = rng.choice(MOBILITY_NEEDS)
    place = rng.choice(TARGETS)
    marker = rng.choice(SOFT_MARKERS)
    text = f"{place} 위주로 {rng.choice(TONES)}, {mobility} 이동은 {need}이면 {marker}"
    return row(index, text, ["soft_and", "mobility_context"], "soft_mobility_optional", optional_terms=[mobility, need], risk_tags=["soft-vs-strict", "mobility"], rationale="이동성 조건이 있지만 필수 조건이 아니라 완화 가능한 선호다")


def replace_exclude_place(index: int, rng: random.Random) -> dict[str, Any]:
    old = rng.choice(PLACES)
    new = rng.choice([item for item in TARGETS if item != old])
    need = rng.choice(MOBILITY_NEEDS)
    text = f"{rng.choice(REPLACE_PREFIXES)} {old} 말고 {new} 쪽으로 {rng.choice(TONES)}, {need}이면 더 좋아"
    return row(index, text, ["replace_condition", "mobility_context"], "replace_exclude_place_mobility", required_terms=[new], optional_terms=[need], excluded_terms=[old], risk_tags=["replace-vs-add", "exclude-place", "mobility"], rationale="장소 조건을 교체하며 이전 장소는 제외 terms로 보존한다")


def or_facility(index: int, rng: random.Random) -> dict[str, Any]:
    first, second = rng.sample(FACILITIES, 2)
    text = f"{first}이나 {second} {rng.choice(OR_MARKERS)}"
    return row(index, text, ["or_condition", "specific_facility_required"], "or_specific_facility", required_terms=[f"{first} 또는 {second}"], risk_tags=["or-vs-strict", "facility-required"], rationale="두 시설 중 하나를 대체 조건으로 요구한다")


def strict_facility(index: int, rng: random.Random) -> dict[str, Any]:
    first, second = rng.sample(FACILITIES, 2)
    text = f"{first}하고 {josa(second, '이', '가')} {rng.choice(STRICT_MARKERS)}"
    labels = ["strict_and", "specific_facility_required"]
    if first in {"경사로", "엘리베이터", "장애인 주차장", "장애인 화장실"} or second in {"경사로", "엘리베이터", "장애인 주차장", "장애인 화장실"}:
        labels.append("mobility_context")
    if first in {"수유실", "기저귀 교환대"} or second in {"수유실", "기저귀 교환대"}:
        labels.append("family_context")
    return row(index, text, labels, "strict_multiple_facilities", required_terms=[first, second], risk_tags=["strict-and", "facility-evidence"], rationale="복수 시설을 모두 충족해야 하는 필수 조건이다")


def negative_topic(index: int, rng: random.Random) -> dict[str, Any]:
    topic = rng.choice(MEDIA_TOPICS)
    text = f"{topic}을 {rng.choice(['알아보려는', '설명하려는', '비교하려는', '정리하려는'])} 거지 관광지 조건으로 {rng.choice(NEGATIONS)}"
    return row(index, text, [], "negative_topic_near_miss", risk_tags=["near-miss", "topic-vs-condition"], rationale="시설/가족/이동성 단어가 있지만 추천 필터 조건이 아니다")


def add_followup(index: int, rng: random.Random) -> dict[str, Any]:
    prefix = rng.choice(ADD_PREFIXES)
    facility = rng.choice(FACILITIES)
    text = f"{prefix} {facility}도 확인되는 곳만 {rng.choice(TONES)}"
    labels = ["add_condition", "specific_facility_required"]
    if facility in {"수유실", "기저귀 교환대"}:
        labels.append("family_context")
    if facility in {"경사로", "엘리베이터", "장애인 화장실", "장애인 주차장"}:
        labels.append("mobility_context")
    return row(index, text, labels, "add_facility_followup", required_terms=[facility], risk_tags=["followup-add", "facility-required"], rationale="기존 추천을 유지하고 시설 조건을 추가한다")


def exclude_weak_evidence(index: int, rng: random.Random) -> dict[str, Any]:
    facility = rng.choice(FACILITIES)
    text = f"{facility} 단어만 있는 곳은 빼고 실제 이용 가능 정보가 확인되는 곳으로 {rng.choice(TONES)}"
    return row(index, text, ["exclude_condition", "specific_facility_required"], "exclude_weak_facility_evidence", required_terms=[facility], excluded_terms=[f"{facility} 단어만 있는 곳"], risk_tags=["keyword-vs-evidence", "exclude-condition"], rationale="단순 키워드가 아니라 실제 시설 근거를 요구한다")


def family_mobility(index: int, rng: random.Random) -> dict[str, Any]:
    family = rng.choice(FAMILY)
    need = rng.choice(MOBILITY_NEEDS)
    text = f"{family} 가는데 체험시설보다 {need}인 곳이 우선이야"
    return row(index, text, ["family_context", "mobility_context"], "family_mobility_priority", required_terms=[need], optional_terms=[family], risk_tags=["family-mobility", "priority-shift"], rationale="가족 동반 맥락과 이동 편의 우선순위가 함께 있다")


def replace_facility_scope(index: int, rng: random.Random) -> dict[str, Any]:
    facility = rng.choice(["수어 안내", "자막 자료", "점자 안내", "음성안내"])
    old = rng.choice(["공연장", "축제", "행사", "교육 자료"])
    new = rng.choice(["전시 콘텐츠", "관광 안내", "박물관", "문화관"])
    text = f"{facility}가 있는 {old} 말고 {new} 기준으로 바꿔줘"
    return row(index, text, ["replace_condition", "specific_facility_required"], "replace_facility_scope", required_terms=[new, facility], excluded_terms=[old], risk_tags=["facility-scope", "replace-condition"], rationale="시설 조건은 유지하되 적용 대상 범위를 교체한다")


def or_mobility(index: int, rng: random.Random) -> dict[str, Any]:
    first, second = rng.sample(MOBILITY_NEEDS, 2)
    text = f"{first}이거나 {second}이면 괜찮아, 둘 다 꼭 맞출 필요는 없어"
    return row(index, text, ["or_condition", "mobility_context"], "or_mobility_condition", required_terms=[f"{first} 또는 {second}"], risk_tags=["or-vs-strict", "mobility"], rationale="두 이동 편의 조건 중 하나면 충분한 요청이다")


def soft_facility(index: int, rng: random.Random) -> dict[str, Any]:
    facility = rng.choice(FACILITIES)
    place = rng.choice(TARGETS)
    text = f"{place}를 먼저 보고 {facility}는 {rng.choice(SOFT_MARKERS)}"
    labels = ["soft_and", "specific_facility_required"]
    if facility in {"수유실", "기저귀 교환대"}:
        labels.append("family_context")
    if facility in {"경사로", "엘리베이터", "장애인 화장실", "장애인 주차장"}:
        labels.append("mobility_context")
    return row(index, text, labels, "soft_optional_facility", required_terms=[place], optional_terms=[facility], risk_tags=["soft-vs-strict", "facility-optional"], rationale="시설이 언급되지만 필수 조건이 아니라 보조 선호다")


def remove_family(index: int, rng: random.Random) -> dict[str, Any]:
    family = rng.choice(FAMILY)
    target = rng.choice(["조용한 산책", "성인 전시", "혼자 보기 좋은 코스", "부모님 휴식", "역사 해설"])
    text = f"{family} 코스는 이번엔 빼고 {target} 중심으로 다시 잡아줘"
    return row(index, text, ["replace_condition"], "replace_remove_family_context", required_terms=[target], excluded_terms=[family], risk_tags=["negated-family", "replace-condition"], rationale="가족 맥락을 활성 조건으로 쓰지 않고 다른 기준으로 교체한다")


def transit_or_parking(index: int, rng: random.Random) -> dict[str, Any]:
    text = f"가까운 주차가 되거나 대중교통 접근이 편하면 돼, 둘 중 하나 기준으로 {rng.choice(TONES)}"
    return row(index, text, ["or_condition", "mobility_context"], "or_parking_transit", required_terms=["가까운 주차 또는 편한 대중교통"], risk_tags=["or-vs-soft", "mobility"], rationale="이동 접근성 조건 중 하나만 충족하면 된다")


def exact_not_guess(index: int, rng: random.Random) -> dict[str, Any]:
    facility = rng.choice(FACILITIES)
    text = f"{facility} 여부를 추측하지 말고 카드에 확인되는 곳만 {rng.choice(TONES)}"
    return row(index, text, ["specific_facility_required"], "facility_evidence_not_guess", required_terms=[facility], risk_tags=["evidence-required", "not-exclude"], rationale="'말고'가 제외가 아니라 추측 금지 의미이며 시설 근거를 요구한다")


def exclude_long_wait(index: int, rng: random.Random) -> dict[str, Any]:
    need = rng.choice(["줄 서는 시간이 긴 곳", "오래 서 있어야 하는 코스", "오르막이 많은 곳", "계단이 긴 곳", "휴식 공간이 없는 곳"])
    text = f"{need}은 피하고 싶어, 어르신이 무리 없는 곳으로 {rng.choice(TONES)}"
    return row(index, text, ["exclude_condition", "mobility_context"], "exclude_mobility_burden", required_terms=["어르신 무리 없음"], excluded_terms=[need], risk_tags=["exclude-condition", "elderly-mobility"], rationale="이동 부담이 큰 조건을 제외하는 요청이다")


def place_or_place_with_need(index: int, rng: random.Random) -> dict[str, Any]:
    first, second = rng.sample(TARGETS, 2)
    need = rng.choice(MOBILITY_NEEDS)
    text = f"{josa(first, '이나', '나')} {second} 중에서 {need}인 쪽으로 {rng.choice(TONES)}"
    return row(index, text, ["or_condition", "mobility_context"], "or_place_with_mobility_need", required_terms=[f"{first} 또는 {second}", need], risk_tags=["or-place", "mobility"], rationale="장소 유형은 대체 조건이고 이동 편의 요구가 함께 있다")


def strict_same_card(index: int, rng: random.Random) -> dict[str, Any]:
    first, second = rng.sample(FACILITIES, 2)
    text = f"{first} 따로, {second} 따로 말고 같은 카드에서 둘 다 확인되는 곳만 남겨줘"
    return row(index, text, ["strict_and", "specific_facility_required"], "strict_same_card_facility", required_terms=[first, second], risk_tags=["same-card-evidence", "strict-and"], rationale="두 시설이 같은 추천 카드에서 함께 확인되어야 한다")


def no_label_general(index: int, rng: random.Random) -> dict[str, Any]:
    text = f"{rng.choice(['서울', '부산', '제주', '강릉', '전주'])}에서 분위기 좋은 관광지 몇 곳 {rng.choice(TONES)}"
    return row(index, text, [], "negative_general_recommendation", risk_tags=["none-label"], rationale="일반 추천 요청이며 문맥 세부 라벨은 없다")


SCENARIOS: list[Scenario] = [
    soft_mobility,
    replace_exclude_place,
    or_facility,
    strict_facility,
    negative_topic,
    add_followup,
    exclude_weak_evidence,
    family_mobility,
    replace_facility_scope,
    or_mobility,
    soft_facility,
    remove_family,
    transit_or_parking,
    exact_not_guess,
    exclude_long_wait,
    place_or_place_with_need,
    strict_same_card,
    no_label_general,
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate a deterministic human-light Korean context expansion batch.")
    parser.add_argument("--rows", type=int, default=1000)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--seed", type=int, default=20260517)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    rng = random.Random(args.seed)
    rows: list[dict[str, Any]] = []
    seen_texts: set[str] = set()
    attempts = 0
    while len(rows) < args.rows:
        attempts += 1
        if attempts > args.rows * 100:
            raise RuntimeError(f"could not generate {args.rows} unique rows")
        scenario = SCENARIOS[(len(rows) + attempts) % len(SCENARIOS)]
        candidate = maybe_add_user_noise(scenario(len(rows) + 1, rng), rng)
        normalized = normalize_text(str(candidate["text"]))
        if normalized in seen_texts:
            continue
        seen_texts.add(normalized)
        rows.append(candidate)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as file:
        for payload in rows:
            file.write(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n")

    label_counts = {label: 0 for label in CONTEXT_LABELS}
    label_counts["<none>"] = 0
    for payload in rows:
        labels = payload["labels"]
        if not labels:
            label_counts["<none>"] += 1
        for label in labels:
            label_counts[label] += 1
    print(json.dumps({"output": project_relative(args.output), "rows": len(rows), "label_counts": label_counts}, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()

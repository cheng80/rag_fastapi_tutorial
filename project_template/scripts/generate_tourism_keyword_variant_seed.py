from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import random
import re
import sys
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


DEFAULT_OUTPUT = (
    PROJECT_ROOT
    / "data"
    / "generated"
    / "tour_api"
    / "keyword_variant_batches"
    / "keyword_variant_batch_20260518_gpt_style_2400.raw.jsonl"
)
DEFAULT_REPORT = (
    PROJECT_ROOT
    / "data"
    / "generated"
    / "tour_api"
    / "keyword_variant_batches"
    / "keyword_variant_batch_20260518_gpt_style_2400.report.json"
)


TERM_GROUPS = {
    "휠체어": {
        "condition": "휠체어",
        "terms": ["휠체어", "전동휠체어", "이동약자", "무장애", "베리어프리", "바퀴 의자", "휠체어 이동"],
        "typos": ["휄체어", "휠쳐", "휠채어", "휠체여", "휠체어어", "휠 체어", "휠체 어"],
        "paraphrases": ["계단 없이 갈 수 있는", "바퀴 달린 의자로 이동 가능한", "턱이 적은", "걸음이 불편해도 갈 수 있는"],
    },
    "유모차": {
        "condition": "유모차",
        "terms": ["유모차", "유아차", "아이 동반", "영유아", "아기랑", "애기랑", "가족"],
        "typos": ["유모챠", "유모 차", "유아챠", "유아 차", "애기랑", "아가랑"],
        "paraphrases": ["아기 태우고 갈 수 있는", "아이 데리고 이동 편한", "기저귀 갈 곳이 있는", "수유가 가능한"],
    },
    "장애인 화장실": {
        "condition": "화장실",
        "terms": ["장애인 화장실", "다목적 화장실", "화장실", "장애인화장실"],
        "typos": ["장애 인화장실", "장애인화장 실", "화장 실", "화장실되는"],
        "paraphrases": ["휠체어로 들어갈 수 있는 화장실", "넓은 화장실이 확인되는", "접근 가능한 화장실"],
    },
    "장애인 주차": {
        "condition": "주차",
        "terms": ["장애인 주차", "장애인 주차장", "주차", "가까운 주차"],
        "typos": ["장애인주차", "장애 인주차", "주 차", "주차 장"],
        "paraphrases": ["입구 가까이 차를 댈 수 있는", "주차하고 많이 걷지 않는", "주차 편한"],
    },
    "엘리베이터": {
        "condition": "엘리베이터",
        "terms": ["엘리베이터", "승강기", "엘베", "리프트"],
        "typos": ["엘리배이터", "앨리베이터", "엘리 베이터", "승강끼", "승 강기"],
        "paraphrases": ["층 이동이 편한", "계단 말고 올라갈 수 있는", "위아래 이동이 쉬운"],
    },
    "경사로": {
        "condition": "접근로",
        "terms": ["경사로", "접근로", "출입통로", "턱 없음", "무단차", "평탄한 길"],
        "typos": ["경 사로", "접근 로", "출입 통로", "턱없음", "무 단차"],
        "paraphrases": ["입구에 턱이 없는", "길이 평평한", "계단을 피할 수 있는", "유모차 바퀴가 걸리지 않는"],
    },
    "점자": {
        "condition": "시각장애",
        "terms": ["점자", "점자블록", "점자 안내", "촉지도", "음성안내", "오디오가이드"],
        "typos": ["점자 블록", "점자블럭", "점자안내", "촉 지 도", "음성 안내", "오디오 가이드"],
        "paraphrases": ["시각장애인 안내가 있는", "손으로 만져 확인할 안내가 있는", "소리 안내가 있는"],
    },
    "수어": {
        "condition": "청각장애",
        "terms": ["수어", "수화", "자막", "문자안내", "영상안내", "청각장애"],
        "typos": ["수어안내", "수화 안내", "자 막", "문자 안내", "청각 장애"],
        "paraphrases": ["소리 없이도 안내를 볼 수 있는", "영상에 글자 안내가 있는", "청각장애인 안내가 있는"],
    },
    "보조견": {
        "condition": "보조견",
        "terms": ["보조견", "안내견", "장애인 보조견"],
        "typos": ["보조 견", "안내 견", "보조갼"],
        "paraphrases": ["안내견과 같이 들어갈 수 있는", "보조견 동반 가능한"],
    },
    "고령자": {
        "condition": "고령자",
        "terms": ["고령자", "어르신", "노인", "부모님", "무릎 불편"],
        "typos": ["어르 신", "고령 자", "부모 님", "무릅 불편"],
        "paraphrases": ["오래 걷기 힘든 분과 갈 수 있는", "쉬어 갈 곳이 있는", "부모님이 무리 없는"],
    },
}

REGIONS = ["서울", "서울 강남구", "서울 중구", "부산 중구", "성남시", "강릉", "제주시", "서귀포시", "대구", "전주"]
PLACE_WORDS = ["관광지", "박물관", "공원", "실내", "전시관", "산책 코스", "맛집 말고 관광지", "조용한 곳"]
TAILS = ["추천해줘", "찾아줘", "되는 곳", "있는 곳", "갈만한데", "좀", "가능?", "보여줘"]


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        for row in rows:
            file.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def project_relative(path: Path) -> str:
    resolved = path.resolve()
    try:
        return str(resolved.relative_to(PROJECT_ROOT))
    except ValueError:
        return str(path)


def compact(text: str) -> str:
    return re.sub(r"\s+", "", text)


def row(
    index: int,
    canonical: str,
    condition: str,
    variant: str,
    variant_type: str,
    user_query: str,
    expected_conditions: list[str],
    should_promote: bool,
    risk_tags: list[str],
    rationale: str,
) -> dict[str, Any]:
    return {
        "id": f"KWVAR20260518{index:05d}",
        "canonical_term": canonical,
        "condition_label": condition,
        "variant": variant,
        "variant_type": variant_type,
        "user_query": user_query,
        "expected_conditions": expected_conditions,
        "should_promote": should_promote,
        "risk_tags": risk_tags,
        "rationale": rationale,
        "source": "gpt_style_keyword_variant_seed",
    }


def build_query(region: str, variant: str, rng: random.Random, variant_type: str) -> str:
    place = rng.choice(PLACE_WORDS)
    tail = rng.choice(TAILS)
    patterns = [
        f"{region}에서 {variant} {place} {tail}",
        f"{region} {variant} {place} {tail}",
        f"{variant} 기준으로 {region} {place} {tail}",
        f"{region} 근처에서 {variant} 가능한 {place} {tail}",
        f"{region}{variant}{place}{tail}",
    ]
    query = rng.choice(patterns)
    if variant_type == "spacing" or rng.random() < 0.18:
        query = compact(query)
    return query


def generate_positive_rows(target: int, rng: random.Random) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    variant_types = ["typo", "spacing", "abbreviation", "synonym", "paraphrase"]
    while len(rows) < target:
        canonical, payload = rng.choice(list(TERM_GROUPS.items()))
        variant_type = rng.choice(variant_types)
        if variant_type == "typo":
            variant = rng.choice(payload["typos"])
            tags = ["typo"]
        elif variant_type == "spacing":
            variant = compact(rng.choice(payload["terms"]))
            tags = ["spacing"]
        elif variant_type == "abbreviation":
            variant = rng.choice(payload["terms"])
            tags = ["abbreviation", "colloquial"]
        elif variant_type == "synonym":
            variant = rng.choice(payload["terms"])
            tags = ["synonym"]
        else:
            variant = rng.choice(payload["paraphrases"])
            tags = ["paraphrase"]
        query = build_query(rng.choice(REGIONS), variant, rng, variant_type)
        condition = str(payload["condition"])
        rows.append(
            row(
                index=len(rows) + 1,
                canonical=canonical,
                condition=condition,
                variant=variant,
                variant_type=variant_type,
                user_query=query,
                expected_conditions=[condition],
                should_promote=variant_type != "paraphrase" or rng.random() < 0.35,
                risk_tags=[*tags, condition],
                rationale=f"{variant}는 {canonical} 계열의 {variant_type} 표현으로 {condition} 조건 후보다.",
            )
        )
    return rows


def generate_negative_rows(start_index: int, target: int, rng: random.Random) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    negative_patterns = [
        ("점자", "점자블록 디자인 사진 말고 관광지 분위기만 알려줘", ["negative", "topic-vs-condition"]),
        ("수어", "수어 공연 자료를 찾는 게 아니라 일반 관광지 설명이 궁금해", ["negative", "topic-vs-condition"]),
        ("휠체어", "휠체어 대여 가격 비교 말고 관광 정보만 볼래", ["negative", "unsupported-price"]),
        ("장애인 주차", "장애인 주차 정책 뉴스 말고 장소 추천은 아직 아냐", ["negative", "policy-topic"]),
        ("유모차", "유모차 브랜드 말고 아이랑 갈 곳은 나중에 물어볼게", ["negative", "product-topic"]),
        ("엘리베이터", "엘리베이터 사고 뉴스가 궁금한 거지 관광지는 아니야", ["negative", "news-topic"]),
    ]
    ambiguous_patterns = [
        ("휠체어", "휠체어 되는 데", ["ambiguous", "missing-region"]),
        ("화장실", "화장실 되는 곳", ["ambiguous", "missing-region"]),
        ("수어", "수어 자막 둘 중 하나", ["ambiguous", "missing-region"]),
        ("유모차", "애기랑 갈만한 곳", ["ambiguous", "missing-region"]),
        ("점자", "점자 있는 데", ["ambiguous", "missing-region"]),
    ]
    prefixes = ["", "서울에서 ", "성남시에서 ", "부산 중구에서 ", "근처에 ", "이번엔 ", "혹시 "]
    suffixes = ["", " 알려줘", " 추천 말고", " 볼 수 있나", " 가능한가", " 확인해줘", " 좀"]
    while len(rows) < target:
        if rng.random() < 0.55:
            canonical, query, tags = rng.choice(negative_patterns)
            condition = "none"
            expected: list[str] = []
            promote = False
            variant_type = "negative"
            rationale = "핵심어가 나오지만 관광 추천 조건으로 활성화하면 안 되는 반례다."
        else:
            canonical, query, tags = rng.choice(ambiguous_patterns)
            condition = "ambiguous"
            expected = []
            promote = False
            variant_type = "ambiguous"
            rationale = "조건 후보는 보이지만 지역이나 목적이 부족해 추가 질문이 필요하다."
        query = f"{rng.choice(prefixes)}{query}{rng.choice(suffixes)}".strip()
        if rng.random() < 0.18:
            query = compact(query)
        rows.append(
            row(
                index=start_index + len(rows),
                canonical=canonical,
                condition=condition,
                variant=canonical,
                variant_type=variant_type,
                user_query=query,
                expected_conditions=expected,
                should_promote=promote,
                risk_tags=tags,
                rationale=rationale,
            )
        )
    return rows


def dedupe(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result = []
    seen = set()
    for item in rows:
        key = compact(str(item["user_query"])).lower()
        if key in seen:
            continue
        seen.add(key)
        next_item = dict(item)
        next_item["id"] = f"KWVAR20260518{len(result) + 1:05d}"
        result.append(next_item)
    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate GPT-style keyword variant training data for tourism query normalization.")
    parser.add_argument("--rows", type=int, default=2400)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--seed", type=int, default=20260518)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    rng = random.Random(args.seed)
    negative_target = max(int(args.rows * 0.18), 1)
    positive_target = args.rows - negative_target + int(args.rows * 0.2)
    rows = generate_positive_rows(positive_target, rng)
    rows.extend(generate_negative_rows(len(rows) + 1, negative_target, rng))
    rows = dedupe(rows)
    rng.shuffle(rows)
    rows = rows[: args.rows]
    rows = [{**row, "id": f"KWVAR20260518{index:05d}"} for index, row in enumerate(rows, start=1)]
    write_jsonl(args.output, rows)
    report = {
        "output": project_relative(args.output),
        "rows": len(rows),
        "variant_type_counts": dict(Counter(row["variant_type"] for row in rows)),
        "condition_counts": dict(Counter(row["condition_label"] for row in rows)),
        "promote_candidates": sum(1 for row in rows if row["should_promote"]),
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()

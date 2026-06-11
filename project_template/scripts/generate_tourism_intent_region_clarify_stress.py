from __future__ import annotations

from itertools import product
import json
from pathlib import Path
import random
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

DEFAULT_OUTPUT = PROJECT_ROOT / "data" / "eval" / "tourism_intent_region_clarify_stress.jsonl"


def _rows(intent: str, templates: list[str], slots: dict[str, list[str]]) -> list[dict[str, str]]:
    result = []
    for template in templates:
        names = [part.split("}", 1)[0] for part in template.split("{")[1:]]
        values = [slots[name] for name in names]
        for combo in product(*values):
            text = template.format(**dict(zip(names, combo, strict=True)))
            result.append({"text": " ".join(text.split()), "intent": intent})
    return result


def _surface_variants(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    prefixes = ["", "혹시 ", "가능하면 ", "아이랑 가는데 ", "부모님 모시고 ", "이번 여행에서 "]
    suffixes = ["", " 부탁해", " 알려줘", " 가능할까", " 다시 봐줘"]
    result = []
    for row in rows:
        for prefix in prefixes:
            for suffix in suffixes:
                result.append({"text": " ".join(f"{prefix}{row['text']}{suffix}".split()), "intent": row["intent"]})
    return result


def _take(
    rows: list[dict[str, str]],
    *,
    count: int,
    source: str,
    rng: random.Random,
    seen: set[tuple[str, str]],
) -> list[dict[str, str]]:
    rng.shuffle(rows)
    selected = []
    for row in rows:
        key = (row["text"], row["intent"])
        if key in seen:
            continue
        seen.add(key)
        row["source"] = source
        selected.append(row)
        if len(selected) >= count:
            return selected
    raise RuntimeError(f"{source}/{rows[0]['intent'] if rows else 'unknown'} only generated {len(selected)} rows")


def generate_rows(seed: int = 20260516) -> list[dict[str, str]]:
    rng = random.Random(seed)
    seen: set[tuple[str, str]] = set()
    output: list[dict[str, str]] = []

    clarify_templates = [
        "{ambiguous} {need} 관광지",
        "{ambiguous}에서 {need} 갈 곳",
        "{ambiguous} 기준으로 {need} 여행지 추천",
        "{ambiguous} 쪽 {need} 볼거리",
        "{ambiguous} 여행 정보",
        "{ambiguous} 가족 여행지",
        "{ambiguous} 근처 {need} 명소",
        "{ambiguous} {place_type} 찾아줘",
        "{ambiguous} 쪽으로 갈 건데 어디인지 확인 필요해",
        "{ambiguous}만 말하면 어디 지역인지 애매하지 않아",
    ]
    clarify_slots = {
        "ambiguous": ["중구", "동구", "서구", "남구", "북구", "강서구", "고성군"],
        "need": ["휠체어 가능한", "유모차 가능한", "주차 되는", "장애인 화장실 있는", "아이랑 갈 만한", "부모님과 가기 좋은"],
        "place_type": ["관광지", "여행지", "산책 코스", "실내 명소", "시장 말고 볼거리", "박물관"],
    }
    output.extend(
        _take(
            _surface_variants(_rows("clarify_region", clarify_templates, clarify_slots)),
            count=600,
            source="region_clarify_stress",
            rng=rng,
            seen=seen,
        )
    )

    recommend_templates = [
        "{qualified} {need} 관광지",
        "{qualified} 여행 정보",
        "{qualified}에서 {need} 갈 곳",
        "{qualified} {place_type} 추천",
    ]
    recommend_slots = {
        "qualified": ["서울 중구", "부산 중구", "대구 동구", "인천 서구", "광주 남구", "대전 동구", "울산 북구", "경남 고성군", "강원 고성군"],
        "need": ["휠체어 가능한", "유모차 가능한", "아이랑 갈 만한", "장애인 화장실 있는"],
        "place_type": ["관광지", "여행지", "볼거리", "산책 코스"],
    }
    output.extend(
        _take(
            _surface_variants(_rows("recommend_places", recommend_templates, recommend_slots)),
            count=180,
            source="region_clarify_stress",
            rng=rng,
            seen=seen,
        )
    )

    narrow_templates = [
        "{qualified} 쪽으로만 좁혀줘",
        "{qualified} 안에서만 다시 보여줘",
        "아까 지역 중 {qualified} 위주로",
        "범위를 {qualified}까지 줄여줘",
        "{qualified} 카드만 남겨줘",
        "{qualified} 근처 후보로 줄여줘",
    ]
    narrow_slots = {
        "qualified": ["서울 중구", "부산 중구", "대구 동구", "인천 서구", "광주 남구", "대전 동구", "울산 북구", "경남 고성군", "강원 고성군"],
    }
    output.extend(
        _take(
            _surface_variants(_rows("narrow_region", narrow_templates, narrow_slots)),
            count=180,
            source="region_clarify_stress",
            rng=rng,
            seen=seen,
        )
    )

    output.sort(key=lambda row: (row["intent"], row["text"]))
    return output


def main() -> None:
    rows = generate_rows()
    DEFAULT_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with DEFAULT_OUTPUT.open("w", encoding="utf-8") as file:
        for row in rows:
            file.write(json.dumps(row, ensure_ascii=False) + "\n")
    counts: dict[str, int] = {}
    for row in rows:
        counts[row["intent"]] = counts.get(row["intent"], 0) + 1
    print(f"Wrote {len(rows)} rows to {DEFAULT_OUTPUT.relative_to(PROJECT_ROOT)}")
    print(json.dumps(counts, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()

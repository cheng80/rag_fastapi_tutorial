from __future__ import annotations

import argparse
from itertools import product
import json
from pathlib import Path
import random
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


DEFAULT_OUTPUT = PROJECT_ROOT / "data" / "eval" / "tourism_intent_generated_utterances.jsonl"
DEFAULT_ROWS_PER_INTENT = 1200


def _fill_templates(intent: str, templates: list[str], slots: dict[str, list[str]]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for template in templates:
        names = [part.split("}", 1)[0] for part in template.split("{")[1:]]
        values = [slots[name] for name in names]
        for combo in product(*values):
            text = template.format(**dict(zip(names, combo, strict=True)))
            rows.append({"text": " ".join(text.split()), "intent": intent})
    return rows


def _expand_variants(rows: list[dict[str, str]], intent: str) -> list[dict[str, str]]:
    prefixes = ["", "혹시 ", "가능하면 ", "그러면 ", "그럼 ", "이번엔 ", "아까 답변에서 ", "방금 추천 중에서 "]
    suffixes = ["", " 부탁해", " 해줘", " 볼래", " 알려줘", " 확인해줘"]
    polite_endings = ["", "?", "요", "요?", "도 괜찮아", "만 부탁해"]
    expanded: list[dict[str, str]] = []
    for row in rows:
        base = row["text"]
        for prefix in prefixes:
            for suffix in suffixes:
                for ending in polite_endings:
                    text = " ".join(f"{prefix}{base}{suffix}{ending}".split())
                    expanded.append({"text": text, "intent": intent})
    return expanded


def generate_rows(rows_per_intent: int = DEFAULT_ROWS_PER_INTENT, seed: int = 20260516) -> list[dict[str, str]]:
    rng = random.Random(seed)
    specs = {
        "show_more": (
            [
                "{more} {target}",
                "{target} {more}",
                "{amount}까지 {more}",
                "{prefix} {more}",
                "{target}가 더 있으면 {more}",
                "{polite} {target} {more}",
                "{target} {amount} 정도 {more}",
            ],
            {
                "more": ["더 보여줘", "더 보기", "더 알려줘", "이어 보여줘", "계속 보여줘", "더 추천해줘", "목록 더 펼쳐줘", "나머지도 보여줘", "추가로 보여줘", "더 받을래"],
                "target": ["다른 곳", "후보", "추천지", "관광지", "확인된 곳", "갈 만한 곳", "장소", "카드"],
                "amount": ["10곳", "15곳", "20곳", "전부", "전체", "가능한 만큼", "있는 만큼"],
                "prefix": ["아까 것 말고", "지금 목록에서", "카드 더", "추천 더", "나머지", "가능하면", "있다면"],
                "polite": ["혹시", "가능하면", "그러면", "그럼", "이번엔"],
            },
        ),
        "live_topup": (
            [
                "{fresh} {action}",
                "{fresh} 자료로 {action}",
                "{action} {fresh}",
                "후보가 부족하면 {fresh} {action}",
                "더 없으면 {fresh} {action}",
            ],
            {
                "fresh": ["최신", "최근 기준", "현재 기준", "새 자료", "업데이트된 정보", "지금 기준", "공식 자료 기준", "방금 기준", "새로운 자료"],
                "action": ["다시 찾아줘", "더 찾아줘", "확인해줘", "조회해줘", "보강해줘", "새로 검색해줘", "추가로 찾아줘", "다시 봐줘", "더 확인해줘"],
            },
        ),
        "ask_source": (
            [
                "{source} {ask}",
                "{target} {source} {ask}",
                "{ask} {source}",
                "{target}가 어디서 나온 건지 {ask}",
            ],
            {
                "source": ["출처", "근거", "원자료", "자료 이름", "확인 근거", "공식 자료", "카드 근거"],
                "ask": ["알려줘", "보여줘", "같이 보여줘", "정리해줘", "확인해줘", "볼 수 있어?"],
                "target": ["이 추천", "카드", "장소 정보", "접근성 정보", "답변"],
            },
        ),
        "add_condition": (
            [
                "{condition} {suffix}",
                "{condition}도 {suffix}",
                "{condition} 위주로 {suffix}",
                "그중 {condition} {suffix}",
                "{condition} 확인되는 곳만",
            ],
            {
                "condition": ["장애인 주차장", "장애인 화장실", "휠체어 접근", "유모차 가능", "수유실", "엘리베이터", "경사로", "점자블록", "수어 안내", "자막 안내", "보조견 동반", "어르신 걷기 편한 곳", "대중교통 접근"],
                "suffix": ["있는 곳", "가능한 곳", "확인되는 곳", "좋은 곳", "편한 곳", "되는 곳"],
            },
        ),
        "replace_condition": (
            [
                "{old} 말고 {new}",
                "{old} 빼고 {new}",
                "{old} 대신 {new}",
                "{old} 기준 말고 {new} 기준으로",
                "{old}은 제외하고 {new} 확인해줘",
            ],
            {
                "old": ["유모차", "휠체어", "아이", "어르신", "주차", "화장실", "점자", "수어", "실내", "시장", "대중교통"],
                "new": ["휠체어", "유모차", "어르신", "아이", "화장실", "주차", "수어 안내", "점자블록", "산책", "박물관", "경사로"],
            },
        ),
        "exclude_preference": (
            [
                "{place} {exclude}",
                "{place}은 {exclude}",
                "{place} 쪽은 {exclude}",
                "{place} 말고 관광지로",
                "{place} 제외하고 볼거리로",
            ],
            {
                "place": ["시장", "식당", "카페", "숙박", "호텔", "쇼핑몰", "상가", "먹거리 골목", "음식점", "숙소", "상점", "매장", "백화점", "식음료점", "게스트하우스"],
                "exclude": ["빼줘", "제외해줘", "말고", "빼고", "제외하고", "아닌 곳으로", "없는 곳으로"],
            },
        ),
        "change_region": (
            [
                "{old} 말고 {new}",
                "{old} 아니고 {new}",
                "{old} 대신 {new}",
                "{old}에서 {new}로 바꿔줘",
                "{old} 기준 말고 {new} 기준으로",
            ],
            {
                "old": ["서울", "부산", "대구", "인천", "광주", "제주시", "서귀포시", "강릉", "속초", "전주", "경남 고성군", "부산 중구"],
                "new": ["부산", "서울", "대전", "광주광역시", "제주시", "서귀포시", "속초", "강릉", "군산", "강원 고성군", "서울 중구", "부산 해운대구"],
            },
        ),
        "narrow_region": (
            [
                "{district}로 좁혀줘",
                "{district} 쪽만 봐줘",
                "{district} 중심으로 추천해줘",
                "{district}만 보여줘",
                "{district} 기준으로 다시",
                "그중 {district}만",
                "{district} 위주로 다시 보여줘",
                "{district} 근처만 봐줘",
                "{district} 지역만 골라줘",
                "{district} 안에서만 찾아줘",
                "{district}로 범위 줄여줘",
                "아까 지역 중 {district}만 봐줘",
                "{district} 카드만 남겨줘",
                "{district} 쪽으로 좁히자",
                "{district} 기준 카드 보여줘",
            ],
            {
                "district": ["중구", "동구", "서구", "남구", "북구", "강남구", "해운대구", "분당구", "진해구", "마산합포구", "서귀포시", "강서구", "송파구", "수영구", "종로구", "마포구", "수성구", "유성구", "연수구", "일산동구"],
            },
        ),
        "clarify_region": (
            [
                "{ambiguous} {request}",
                "{ambiguous}에서 {request}",
                "{ambiguous} 쪽 {request}",
                "{ambiguous} 기준 {request}",
            ],
            {
                "ambiguous": ["중구", "동구", "서구", "남구", "북구", "강서구", "고성군", "남동구", "영도구", "강동구"],
                "request": ["추천해줘", "관광지 알려줘", "휠체어 가능한 곳", "유모차 가능한 곳", "주차 되는 관광지", "보조견 가능한 곳", "아이랑 갈 곳", "갈 만한 곳", "장애인 화장실 있는 곳", "산책할 곳"],
            },
        ),
        "unsupported_request": (
            [
                "{unsupported} 알려줘",
                "{unsupported} 기준으로 골라줘",
                "{unsupported} 있는 곳만",
                "지금 {unsupported} 확인해줘",
                "{unsupported} 순서로 보여줘",
                "{unsupported} 비교해줘",
                "{unsupported} 제일 좋은 곳",
                "{unsupported} 바로 확인되는 곳",
                "{unsupported} 되는지 알려줘",
                "{unsupported} 확인 가능한 곳",
                "{unsupported} 최신 상태 알려줘",
                "{unsupported} 지금 알 수 있어?",
                "{unsupported} 기준으로 정렬해줘",
                "{unsupported} 가까운 순서",
                "{unsupported} 적은 순서",
                "{unsupported} 많은 순서",
                "{unsupported} 여부 확인해줘",
                "{unsupported} 가능한지 봐줘",
            ],
            {
                "unsupported": ["실시간 혼잡도", "대기시간", "응급실 거리", "약국 가까운 곳", "입장료 제일 싼 곳", "휠체어 대여 재고", "영업 중인 곳", "주차장 빈자리", "택시비 적게 드는 곳", "날씨에 맞는 곳", "사람 적은 곳", "현재 운영 여부", "오늘 휴무 여부", "전동휠체어 충전 가능 여부", "예약 가능한 시간", "실시간 좌석", "현재 주차 가능 여부", "가장 저렴한 코스"],
            },
        ),
        "recommend_places": (
            [
                "{region}에서 {condition} {request}",
                "{region} {condition} {request}",
                "{region}에서 {request}",
                "{region} {preference} {request}",
                "{region}에서 {condition} {preference} {request}",
            ],
            {
                "region": ["서울", "부산", "대구", "인천", "광주광역시", "대전", "제주시", "서귀포시", "강릉", "속초", "전주", "창원시", "성남 분당구", "부산 중구", "서울 강남구"],
                "condition": ["휠체어 가능한", "유모차 가능한", "장애인 주차 가능한", "장애인 화장실 있는", "보조견 동반 가능한", "어르신과 가기 좋은", "아이랑 갈 만한"],
                "preference": ["실내 관광지", "박물관", "산책하기 좋은 곳", "시장", "공원", "볼거리", "가족 여행지"],
                "request": ["추천해줘", "찾아줘", "알려줘", "관광지 추천", "여행지 추천", "갈 곳 추천"],
            },
        ),
    }

    rows = []
    seen: set[tuple[str, str]] = set()
    for intent, (templates, slots) in specs.items():
        candidates = _expand_variants(_fill_templates(intent, templates, slots), intent)
        rng.shuffle(candidates)
        selected = []
        for row in candidates:
            key = (row["text"], row["intent"])
            if key in seen:
                continue
            selected.append(row)
            seen.add(key)
            if len(selected) >= rows_per_intent:
                break
        rows.extend(selected)
    rows.sort(key=lambda row: (row["intent"], row["text"]))
    return rows


def write_jsonl(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        for row in rows:
            file.write(json.dumps(row, ensure_ascii=False) + "\n")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate tourism intent utterances.")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--rows-per-intent", type=int, default=DEFAULT_ROWS_PER_INTENT)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    rows = generate_rows(rows_per_intent=args.rows_per_intent)
    write_jsonl(args.output, rows)
    counts: dict[str, int] = {}
    for row in rows:
        counts[row["intent"]] = counts.get(row["intent"], 0) + 1
    print(f"Wrote {len(rows)} rows to {args.output.relative_to(PROJECT_ROOT)}")
    print(json.dumps(counts, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()

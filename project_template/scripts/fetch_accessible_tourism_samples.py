from __future__ import annotations

import argparse
from pathlib import Path
import json
import sys

import requests

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from app.core.config import get_settings  # noqa: E402
from app.services.tour_api_service import TourAPIError, TourAPIService  # noqa: E402
from app.services.tourism_card_codec import TourismCardMarkdownCodec  # noqa: E402
from app.services.tourism_normalizer import TourismNormalizer  # noqa: E402
from app.services.tourism_query_service import TourismQueryService  # noqa: E402


MVP_TARGET_REGIONS = ["서울", "부산", "강릉"]
FALLBACK_BATCH_REGIONS = {
    "fallback-1": ["서울", "부산", "인천", "대전", "대구", "광주", "울산"],
    "fallback-2": ["경기", "강원", "제주", "경북", "경남"],
    "fallback-3": ["세종", "충북", "충남", "전북", "전남", "강릉"],
}
BROAD_TARGET_REGIONS = [
    "서울",
    "부산",
    "인천",
    "대전",
    "대구",
    "광주",
    "울산",
    "세종",
    "경기",
    "강원",
    "충북",
    "충남",
    "경북",
    "경남",
    "전북",
    "전남",
    "제주",
    "강릉",
]
DEFAULT_ROWS_PER_REGION = 20
DEFAULT_MAX_API_CALLS = 150
IMPORTANT_FIELDS = ["wheelchair", "parking", "restroom", "stroller", "lactationroom", "elevator", "route"]
RAW_OUTPUT_DIR = PROJECT_ROOT / "data" / "generated" / "tour_api"
AREA_CODE_CACHE_PATH = PROJECT_ROOT / "data" / "processed" / "tour_area_codes.json"


def main() -> None:
    args = parse_args()
    target_regions = parse_regions(args.regions) if args.regions else preset_regions(args.preset)
    settings = get_settings()
    output_dir = settings.resolved_tourism_sample_path
    output_dir.mkdir(parents=True, exist_ok=True)
    RAW_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    existing_content_id_paths = collect_existing_content_id_paths(
        [output_dir, settings.resolved_tourism_live_cache_path],
        TourismCardMarkdownCodec(),
    )
    existing_content_ids = set(existing_content_id_paths)
    duplicate_existing_ids = {
        content_id: paths
        for content_id, paths in existing_content_id_paths.items()
        if len(paths) > 1
    }
    if duplicate_existing_ids:
        print(
            "주의: 기존 raw/live Markdown에 같은 콘텐츠ID가 있습니다. "
            f"{len(duplicate_existing_ids)}개 ID는 새 수집에서 재사용하지 않습니다."
        )

    if not settings.tour_api_service_key:
        print("TOUR_API_SERVICE_KEY가 없어 live TourAPI 샘플 수집은 건너뜁니다.")
        print(f"로컬 샘플 디렉터리: {settings.tourism_sample_path}")
        print("판정: 2차 검토 필요 - API 키 설정 후 live 수집을 다시 실행해야 합니다.")
        return

    api = TourAPIService(settings)
    normalizer = TourismNormalizer()
    query_service = TourismQueryService()
    if args.sigungu_fallback:
        summary = collect_sigungu_fallback(
            args=args,
            api=api,
            normalizer=normalizer,
            output_dir=output_dir,
            existing_content_ids=existing_content_ids,
            codec=normalizer.codec,
        )
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        return

    summary: dict[str, dict[str, int]] = {}
    api_calls = 0

    for region in target_regions:
        query = query_service.extract(region)
        area_code = str(query.get("area_code") or "")
        sigungu_code = query.get("sigungu_code")
        region_cards = []
        field_hits = {field: 0 for field in IMPORTANT_FIELDS}
        accessible_errors = 0
        skipped_existing = 0
        skipped_without_accessibility = 0

        try:
            if not area_code:
                raise TourAPIError(f"{region} 지역코드를 찾을 수 없습니다.")
            if api_calls >= args.max_api_calls:
                summary[region] = {"cards": 0, "skipped_by_budget": 1}
                continue
            api_calls += 1
            list_items = api.accessible_area_based_list(
                area_code=area_code,
                sigungu_code=str(sigungu_code) if sigungu_code else None,
                num_of_rows=args.rows,
            )
            raw_path = RAW_OUTPUT_DIR / f"{region}_area_based_raw.json"
            raw_path.write_text(json.dumps(list_items, ensure_ascii=False, indent=2), encoding="utf-8")

            for item in list_items:
                content_id = str(item.get("contentid") or "").strip()
                if not content_id:
                    continue
                if content_id in existing_content_ids:
                    skipped_existing += 1
                    continue
                if api_calls + 2 > args.max_api_calls:
                    skipped_without_accessibility += 1
                    continue
                api_calls += 1
                common = api.detail_common(content_id) or item
                try:
                    api_calls += 1
                    accessible = api.detail_with_tour(content_id)
                except TourAPIError as exc:
                    accessible_errors += 1
                    accessible = {}
                    print(f"{region} {content_id} 무장애 상세 조회 실패: {exc}")
                card = normalizer.normalize_place(common, accessible)
                for field in IMPORTANT_FIELDS:
                    if field in card.raw_fields:
                        field_hits[field] += 1

                if not card.raw_fields:
                    skipped_without_accessibility += 1
                    continue

                region_cards.append(card)
                existing_content_ids.add(card.content_id)

            if region_cards:
                for card in region_cards:
                    markdown_path = output_dir / f"{region}_{card.content_id}.md"
                    if not markdown_path.exists():
                        markdown_path.write_text(normalizer.card_to_markdown(card), encoding="utf-8")

            normalized_path = RAW_OUTPUT_DIR / f"{region}_normalized_cards.json"
            normalized_path.write_text(
                json.dumps([card.model_dump() for card in region_cards], ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            summary[region] = {
                "listed": len(list_items),
                "cards": len(region_cards),
                "accessible_errors": accessible_errors,
                "skipped_existing": skipped_existing,
                "skipped_without_accessibility": skipped_without_accessibility,
                "api_calls_used": api_calls,
                **field_hits,
            }
        except (TourAPIError, requests.RequestException, TimeoutError, ValueError) as exc:
            summary[region] = {"cards": 0, "error": 1}
            print(f"{region} 수집 실패: {exc}")

    print(json.dumps(summary, ensure_ascii=False, indent=2))
    enough_regions = sum(1 for result in summary.values() if result.get("cards", 0) >= 3)
    field_total = sum(result.get(field, 0) for result in summary.values() for field in IMPORTANT_FIELDS)
    if enough_regions >= 3 and field_total > 0:
        print("판정: 1차 진행 가능 - 무장애/가족 친화 필드를 포함한 샘플을 확보했습니다.")
    else:
        print("판정: 2차 검토 필요 - 지역별 3개 이상 카드 또는 핵심 편의정보가 부족합니다.")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="한국관광공사 무장애 여행 정보 샘플 Markdown을 수집합니다.")
    parser.add_argument(
        "--preset",
        choices=["mvp", "fallback-1", "fallback-2", "fallback-3", "broad"],
        default="mvp",
        help="수집 프리셋. mvp는 핵심 3지역, fallback-*은 분할 fallback 수집, broad는 광역권 전체 후보입니다.",
    )
    parser.add_argument(
        "--regions",
        default="",
        help="쉼표로 구분한 수집 지역 목록. 지정하면 --preset보다 우선합니다.",
    )
    parser.add_argument(
        "--rows",
        type=int,
        default=DEFAULT_ROWS_PER_REGION,
        help=f"지역별 areaBasedList2 요청 건수. 기본값은 {DEFAULT_ROWS_PER_REGION}입니다.",
    )
    parser.add_argument(
        "--max-api-calls",
        type=int,
        default=DEFAULT_MAX_API_CALLS,
        help=f"이번 실행에서 허용할 TourAPI 호출 상한. 기본값은 {DEFAULT_MAX_API_CALLS}입니다.",
    )
    parser.add_argument(
        "--sigungu-fallback",
        action="store_true",
        help="전국/선택 광역의 시군구별 부족분만 fallback Markdown으로 수집합니다.",
    )
    parser.add_argument(
        "--cards-per-sigungu",
        type=int,
        default=3,
        help="시군구별 목표 fallback 카드 수입니다.",
    )
    parser.add_argument(
        "--areas",
        default="",
        help="시군구 fallback 수집 대상 광역 목록입니다. 비우면 현재 지역 코드 캐시의 전체 광역을 대상으로 합니다.",
    )
    parser.add_argument(
        "--daily-endpoint-budget",
        type=int,
        default=500,
        help="오늘 수집에서 허용할 엔드포인트별 안전 호출 한도입니다.",
    )
    parser.add_argument("--used-area-based", type=int, default=0, help="오늘 이미 사용한 areaBasedList2 추정 호출 수입니다.")
    parser.add_argument("--used-detail-common", type=int, default=0, help="오늘 이미 사용한 detailCommon2 추정 호출 수입니다.")
    parser.add_argument("--used-detail-with-tour", type=int, default=0, help="오늘 이미 사용한 detailWithTour2 추정 호출 수입니다.")
    return parser.parse_args()


def parse_regions(value: str) -> list[str]:
    return [region.strip() for region in value.split(",") if region.strip()]


def preset_regions(preset: str) -> list[str]:
    if preset in FALLBACK_BATCH_REGIONS:
        return FALLBACK_BATCH_REGIONS[preset]
    if preset == "broad":
        return BROAD_TARGET_REGIONS
    return MVP_TARGET_REGIONS


def collect_existing_content_ids(paths: list[Path], codec: TourismCardMarkdownCodec) -> set[str]:
    return set(collect_existing_content_id_paths(paths, codec))


def collect_existing_content_id_paths(paths: list[Path], codec: TourismCardMarkdownCodec) -> dict[str, list[str]]:
    content_id_paths: dict[str, list[str]] = {}
    for directory in paths:
        if not directory.exists():
            continue
        for path in sorted(directory.glob("*.md")):
            card = codec.from_markdown(path.read_text(encoding="utf-8"))
            if card and card.content_id:
                content_id_paths.setdefault(card.content_id, []).append(path.as_posix())
    return content_id_paths


def collect_sigungu_fallback(
    *,
    args: argparse.Namespace,
    api: TourAPIService,
    normalizer: TourismNormalizer,
    output_dir: Path,
    existing_content_ids: set[str],
    codec: TourismCardMarkdownCodec,
) -> dict[str, object]:
    targets = load_sigungu_targets(parse_regions(args.areas) if args.areas else None)
    coverage = count_sigungu_coverage(output_dir, codec)
    remaining = {
        "area_based": max(args.daily_endpoint_budget - args.used_area_based, 0),
        "detail_common": max(args.daily_endpoint_budget - args.used_detail_common, 0),
        "detail_with_tour": max(args.daily_endpoint_budget - args.used_detail_with_tour, 0),
    }
    calls_used = {"area_based": 0, "detail_common": 0, "detail_with_tour": 0}
    summary: dict[str, dict[str, int]] = {}
    stopped_by_budget = False

    for target in targets:
        key = (target["area_name"], target["sigungu_name"])
        existing_count = coverage.get(key, 0)
        needed = max(args.cards_per_sigungu - existing_count, 0)
        label = f"{target['area_name']} {target['sigungu_name']}"
        if needed <= 0:
            summary[label] = {"existing": existing_count, "cards": 0, "skipped_filled": 1}
            continue
        if remaining["area_based"] <= 0:
            summary[label] = {"existing": existing_count, "cards": 0, "skipped_by_budget": 1}
            stopped_by_budget = True
            break

        remaining["area_based"] -= 1
        calls_used["area_based"] += 1
        try:
            list_items = api.accessible_area_based_list(
                area_code=target["area_code"],
                sigungu_code=target["sigungu_code"],
                num_of_rows=max(args.rows, needed),
            )
        except TourAPIError as exc:
            summary[label] = {"existing": existing_count, "cards": 0, "area_based_error": 1}
            print(f"{label} 후보 목록 조회 실패: {exc}")
            stopped_by_budget = True
            break
        raw_path = RAW_OUTPUT_DIR / f"{target['area_name']}_{target['sigungu_name']}_area_based_raw.json"
        raw_path.write_text(json.dumps(list_items, ensure_ascii=False, indent=2), encoding="utf-8")

        cards = []
        skipped_existing = 0
        skipped_without_accessibility = 0
        accessible_errors = 0
        detail_common_errors = 0
        for item in list_items:
            if len(cards) >= needed:
                break
            content_id = str(item.get("contentid") or "").strip()
            if not content_id:
                continue
            if content_id in existing_content_ids:
                skipped_existing += 1
                continue
            if remaining["detail_common"] <= 0 or remaining["detail_with_tour"] <= 0:
                stopped_by_budget = True
                break
            remaining["detail_common"] -= 1
            calls_used["detail_common"] += 1
            try:
                common = api.detail_common(content_id) or item
            except TourAPIError as exc:
                detail_common_errors += 1
                stopped_by_budget = True
                print(f"{label} {content_id} 공통 상세 조회 실패: {exc}")
                break
            try:
                remaining["detail_with_tour"] -= 1
                calls_used["detail_with_tour"] += 1
                accessible = api.detail_with_tour(content_id)
            except TourAPIError as exc:
                accessible_errors += 1
                accessible = {}
                print(f"{label} {content_id} 무장애 상세 조회 실패: {exc}")
            card = normalizer.normalize_place(common, accessible)
            if not card.raw_fields:
                skipped_without_accessibility += 1
                continue
            cards.append(card)
            existing_content_ids.add(card.content_id)
            coverage[key] = coverage.get(key, 0) + 1

        for card in cards:
            markdown_path = output_dir / f"{target['area_name']}_{target['sigungu_name']}_{card.content_id}.md"
            if not markdown_path.exists():
                markdown_path.write_text(normalizer.card_to_markdown(card), encoding="utf-8")

        normalized_path = RAW_OUTPUT_DIR / f"{target['area_name']}_{target['sigungu_name']}_normalized_cards.json"
        normalized_path.write_text(
            json.dumps([card.model_dump() for card in cards], ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        summary[label] = {
            "existing": existing_count,
            "needed": needed,
            "listed": len(list_items),
            "cards": len(cards),
            "skipped_existing": skipped_existing,
            "skipped_without_accessibility": skipped_without_accessibility,
            "detail_common_errors": detail_common_errors,
            "accessible_errors": accessible_errors,
        }
        if stopped_by_budget:
            break

    return {
        "mode": "sigungu_fallback",
        "cards_per_sigungu": args.cards_per_sigungu,
        "target_count": len(targets),
        "calls_used": calls_used,
        "remaining_budget": remaining,
        "stopped_by_budget": stopped_by_budget,
        "summary": summary,
    }


def load_sigungu_targets(areas: list[str] | None = None) -> list[dict[str, str]]:
    data = json.loads(AREA_CODE_CACHE_PATH.read_text(encoding="utf-8"))
    targets: list[dict[str, str]] = []
    area_filter = set(areas or [])
    for area_name, area_info in data.get("area_codes", {}).items():
        if area_filter and area_name not in area_filter:
            continue
        for sigungu_name, sigungu_code in area_info.get("sigungu", {}).items():
            targets.append(
                {
                    "area_name": area_name,
                    "area_code": str(area_info["area_code"]),
                    "sigungu_name": sigungu_name,
                    "sigungu_code": str(sigungu_code),
                }
            )
    return targets


def count_sigungu_coverage(sample_dir: Path, codec: TourismCardMarkdownCodec) -> dict[tuple[str, str], int]:
    targets = load_sigungu_targets()
    coverage: dict[tuple[str, str], int] = {}
    for path in sorted(sample_dir.glob("*.md")):
        card = codec.from_markdown(path.read_text(encoding="utf-8"))
        if not card:
            continue
        haystack = f"{card.title} {card.address or ''} {path.stem}"
        matched = match_sigungu_target(haystack, targets)
        if matched:
            key = (matched["area_name"], matched["sigungu_name"])
            coverage[key] = coverage.get(key, 0) + 1
    return coverage


def match_sigungu_target(haystack: str, targets: list[dict[str, str]]) -> dict[str, str] | None:
    matches = []
    for target in targets:
        area_aliases = area_name_aliases(target["area_name"])
        if target["sigungu_name"] in haystack and any(alias in haystack for alias in area_aliases):
            matches.append(target)
    if not matches:
        return None
    return sorted(matches, key=lambda item: len(item["sigungu_name"]), reverse=True)[0]


def area_name_aliases(area_name: str) -> set[str]:
    return {
        area_name,
        area_name.replace("특별자치도", ""),
        area_name.replace("특별자치시", ""),
        area_name.replace("광역시", ""),
        area_name.replace("특별시", ""),
        area_name.replace("도", ""),
    }


if __name__ == "__main__":
    main()

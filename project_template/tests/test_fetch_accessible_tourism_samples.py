from app.schemas.tourism import TourismPlaceCard
from app.services.tourism_normalizer import TourismNormalizer
from scripts.fetch_accessible_tourism_samples import (
    area_name_aliases,
    collect_existing_content_id_paths,
    collect_existing_content_ids,
    count_sigungu_coverage,
    match_sigungu_target,
)


def test_collect_existing_content_ids_reads_sample_and_live_cache_dirs(tmp_path):
    sample_dir = tmp_path / "samples"
    live_cache_dir = tmp_path / "live_cache"
    sample_dir.mkdir()
    live_cache_dir.mkdir()
    normalizer = TourismNormalizer()

    sample_card = TourismPlaceCard(
        content_id="sample-1",
        title="샘플 관광지",
        address="서울 중구",
        recommendation_reason="휠체어 접근 정보가 확인되었습니다.",
        accessibility_tags=["휠체어 접근"],
    )
    live_card = TourismPlaceCard(
        content_id="live-1",
        title="라이브 캐시 관광지",
        address="부산 중구",
        recommendation_reason="휠체어 접근 정보가 확인되었습니다.",
        accessibility_tags=["휠체어 접근"],
    )
    (sample_dir / "sample.md").write_text(normalizer.card_to_markdown(sample_card), encoding="utf-8")
    (live_cache_dir / "live.md").write_text(normalizer.card_to_markdown(live_card), encoding="utf-8")

    assert collect_existing_content_ids([sample_dir, live_cache_dir], normalizer.codec) == {"sample-1", "live-1"}


def test_collect_existing_content_id_paths_preserves_duplicate_sources(tmp_path):
    sample_dir = tmp_path / "samples"
    sample_dir.mkdir()
    normalizer = TourismNormalizer()
    card = TourismPlaceCard(
        content_id="same-id",
        title="중복 관광지",
        recommendation_reason="휠체어 접근 정보가 확인되었습니다.",
        accessibility_tags=["휠체어 접근"],
    )
    first = sample_dir / "강원_same.md"
    second = sample_dir / "강릉_same.md"
    first.write_text(normalizer.card_to_markdown(card), encoding="utf-8")
    second.write_text(normalizer.card_to_markdown(card), encoding="utf-8")

    assert collect_existing_content_id_paths([sample_dir], normalizer.codec)["same-id"] == sorted(
        [first.as_posix(), second.as_posix()]
    )


def test_area_name_aliases_accepts_short_region_names():
    assert {"부산광역시", "부산"} <= area_name_aliases("부산광역시")
    assert {"강원특별자치도", "강원"} <= area_name_aliases("강원특별자치도")


def test_match_sigungu_target_requires_area_alias_to_disambiguate():
    targets = [
        {"area_name": "서울특별시", "sigungu_name": "중구"},
        {"area_name": "부산광역시", "sigungu_name": "중구"},
    ]

    assert match_sigungu_target("부산 중구 휠체어 관광지", targets) == targets[1]
    assert match_sigungu_target("중구 휠체어 관광지", targets) is None


def test_count_sigungu_coverage_matches_card_address(monkeypatch, tmp_path):
    sample_dir = tmp_path / "samples"
    sample_dir.mkdir()
    normalizer = TourismNormalizer()
    card = TourismPlaceCard(
        content_id="busan-junggu-1",
        title="부산 중구 관광지",
        address="부산광역시 중구",
        recommendation_reason="휠체어 접근 정보가 확인되었습니다.",
        accessibility_tags=["휠체어 접근"],
    )
    (sample_dir / "부산_중구_1.md").write_text(normalizer.card_to_markdown(card), encoding="utf-8")
    monkeypatch.setattr(
        "scripts.fetch_accessible_tourism_samples.load_sigungu_targets",
        lambda: [{"area_name": "부산광역시", "sigungu_name": "중구"}],
    )

    assert count_sigungu_coverage(sample_dir, normalizer.codec) == {("부산광역시", "중구"): 1}

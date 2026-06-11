from app.services.tourism_card_codec import TourismCardMarkdownCodec
from app.schemas.tourism import TourismPlaceCard
from scripts.audit_tourism_samples import (
    audit_samples,
    choose_canonical_duplicate_path,
    infer_region,
    render_report,
    select_duplicate_paths_to_remove,
)


def test_infer_region_from_filename():
    assert infer_region(type("PathLike", (), {"stem": "서울_123"})()) == "서울"


def test_audit_samples_detects_duplicate_content_id(tmp_path):
    codec = TourismCardMarkdownCodec()
    card = TourismPlaceCard(
        content_id="same-id",
        title="테스트 관광지",
        recommendation_reason="휠체어 접근 정보가 확인되었습니다.",
        accessibility_tags=["휠체어 접근"],
        family_tags=["가족 친화"],
    )
    (tmp_path / "서울_same.md").write_text(codec.to_markdown(card), encoding="utf-8")
    (tmp_path / "부산_same.md").write_text(codec.to_markdown(card), encoding="utf-8")

    result = audit_samples(tmp_path, codec=codec)

    assert result.total_files == 2
    assert result.parsed_cards == 2
    assert result.duplicate_content_ids["same-id"] == [
        str(tmp_path / "부산_same.md"),
        str(tmp_path / "서울_same.md"),
    ]


def test_render_report_includes_korean_sections(tmp_path):
    codec = TourismCardMarkdownCodec()
    card = TourismPlaceCard(
        content_id="content-id",
        title="테스트 관광지",
        recommendation_reason="휠체어 접근 정보가 확인되었습니다.",
        accessibility_tags=["휠체어 접근"],
    )
    (tmp_path / "서울_123.md").write_text(codec.to_markdown(card), encoding="utf-8")

    report = render_report(audit_samples(tmp_path, codec=codec))

    assert "관광 fallback 샘플 감사 결과" in report
    assert "| 서울 | 1 |" in report


def test_duplicate_selection_keeps_gangneung_over_gangwon():
    paths = [
        "data/raw/tourism_accessible/강원_123.md",
        "data/raw/tourism_accessible/강릉_123.md",
    ]

    assert choose_canonical_duplicate_path(paths) == "data/raw/tourism_accessible/강릉_123.md"
    assert select_duplicate_paths_to_remove({"123": paths}) == ["data/raw/tourism_accessible/강원_123.md"]

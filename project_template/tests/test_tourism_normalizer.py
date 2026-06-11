from app.services.tourism_normalizer import TourismNormalizer


def test_tourism_normalizer_builds_accessibility_and_family_card():
    normalizer = TourismNormalizer()

    card = normalizer.normalize_place(
        {
            "contentid": "123",
            "title": "테스트 관광지",
            "addr1": "서울 중구",
            "tel": "02-000-0000",
            "firstimage": "https://example.com/image.jpg",
            "mapx": "126.1",
            "mapy": "37.5",
        },
        {
            "wheelchair": "휠체어 대여 가능",
            "parking": "장애인 주차구역 있음",
            "restroom": "장애인 화장실 있음",
            "stroller": "유모차 대여 가능",
            "lactationroom": "수유실 있음",
        },
    )

    assert card.content_id == "123"
    assert "휠체어 접근" in card.accessibility_tags
    assert "장애인 주차" in card.accessibility_tags
    assert "유모차 대여" in card.family_tags
    assert "수유실" in card.family_tags
    assert card.accessibility.wheelchair == "휠체어 대여 가능"
    assert card.source_url is None


def test_card_markdown_contains_rag_fields():
    normalizer = TourismNormalizer()
    card = normalizer.normalize_place({"contentid": "123", "title": "테스트 관광지"}, {"restroom": "있음"})

    markdown = normalizer.card_to_markdown(card)

    assert "관광지명: 테스트 관광지" in markdown
    assert "출처: 한국관광공사 무장애 여행 정보" in markdown
    assert "편의정보:" in markdown


def test_card_markdown_round_trips_required_fields():
    normalizer = TourismNormalizer()
    card = normalizer.normalize_place(
        {
            "contentid": "123",
            "title": "테스트 관광지",
            "addr1": "서울 중구",
            "tel": "02-000-0000",
            "firstimage": "https://example.com/image.jpg",
            "mapx": "126.1",
            "mapy": "37.5",
        },
        {
            "wheelchair": "휠체어 대여 가능",
            "restroom": "장애인 화장실 있음",
            "lactationroom": "수유실 있음",
        },
    )

    parsed = normalizer.codec.from_markdown(normalizer.card_to_markdown(card))

    assert parsed is not None
    assert parsed.content_id == "123"
    assert parsed.title == "테스트 관광지"
    assert parsed.address == "서울 중구"
    assert parsed.tel == "02-000-0000"
    assert parsed.image_url == "https://example.com/image.jpg"
    assert parsed.map_x == 126.1
    assert parsed.map_y == 37.5
    assert "휠체어 접근" in parsed.accessibility_tags
    assert "수유실" in parsed.family_tags
    assert parsed.accessibility.wheelchair == "휠체어 대여 가능"

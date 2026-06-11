from app.services.korean_query_normalizer import KoreanQueryNormalizer


def test_korean_query_normalizer_restores_typos_spacing_and_rewrite():
    normalizer = KoreanQueryNormalizer()

    query = normalizer.normalize("서울말고부산휠체여가능한곳추천좀", region_names=["서울", "부산"])

    assert query.raw_text == "서울말고부산휠체여가능한곳추천좀"
    assert "서울 말고 부산" in query.normalized_text
    assert "휠체어" in query.normalized_text
    assert "가능한 곳" in query.normalized_text
    assert "휠체여->휠체어" in query.corrections
    assert "no-spacing-input" in query.risk_tags


def test_korean_query_normalizer_restores_wheelchair_vowel_typo():
    normalizer = KoreanQueryNormalizer()

    query = normalizer.normalize("서울 강남구 근처에서 휄체어 관광지 추천해줘", region_names=["서울 강남구"])

    assert query.normalized_text == "서울 강남구 근처에서 휠체어 관광지 추천해줘"
    assert "휄체어->휠체어" in query.corrections


def test_korean_query_normalizer_restores_learned_keyword_variants():
    normalizer = KoreanQueryNormalizer()

    query = normalizer.normalize("서울강남구휠쳐출입 통로앨리베이터자 막보조갼되는곳", region_names=["서울 강남구"])

    assert "서울 강남구" in query.normalized_text
    assert "휠체어" in query.normalized_text
    assert "출입통로" in query.normalized_text
    assert "엘리베이터" in query.normalized_text
    assert "자막" in query.normalized_text
    assert "보조견" in query.normalized_text
    assert "되는 곳" in query.normalized_text


def test_korean_query_normalizer_keeps_original_and_marks_spacing_noise():
    normalizer = KoreanQueryNormalizer()

    query = normalizer.normalize("장애 인화장실 되는곳")

    assert query.raw_text == "장애 인화장실 되는곳"
    assert query.normalized_text == "장애인 화장실 되는 곳"
    assert "spacing-noise-input" in query.risk_tags


def test_korean_query_normalizer_repairs_spaced_legacy_region():
    normalizer = KoreanQueryNormalizer()

    query = normalizer.normalize("남 제주군에서 유모차 관광지 추천해줘")

    assert "남제주군" in query.normalized_text
    assert "남 제주군" not in query.normalized_text


def test_korean_query_normalizer_restores_compact_area_sigungu():
    normalizer = KoreanQueryNormalizer()

    query = normalizer.normalize("부산중구시장빼고휠체어갈수있는곳", region_names=["부산 중구"])

    assert "부산 중구" in query.normalized_text

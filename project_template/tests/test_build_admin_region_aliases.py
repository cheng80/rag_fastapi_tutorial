from scripts.build_admin_region_aliases import build_alias_payload, canonical_sigungu_name, parse_kikmix_line


def test_parse_kikmix_line_reads_current_mapping_row():
    row = parse_kikmix_line("2611057000 부산광역시 중구 광복동 2611013300 광복동1가 19880423")

    assert row == {
        "admin_dong_code": "2611057000",
        "sido_name": "부산광역시",
        "sigungu_name": "중구",
        "admin_dong_name": "광복동",
        "legal_dong_code": "2611013300",
        "legal_dong_name": "광복동1가",
        "created_date": "19880423",
        "deleted_date": "",
    }


def test_canonical_sigungu_name_splits_general_gu_name():
    assert canonical_sigungu_name("창원시마산합포구") == "창원시 마산합포구"
    assert canonical_sigungu_name("제주시") == "제주시"


def test_build_alias_payload_separates_sigungu_and_dong_aliases():
    rows = [
        {
            "admin_dong_code": "2611057000",
            "sido_name": "부산광역시",
            "sigungu_name": "중구",
            "admin_dong_name": "광복동",
            "legal_dong_code": "2611013300",
            "legal_dong_name": "광복동1가",
            "created_date": "19880423",
            "deleted_date": "",
        },
        {
            "admin_dong_code": "2635055100",
            "sido_name": "부산광역시",
            "sigungu_name": "해운대구",
            "admin_dong_name": "좌제1동",
            "legal_dong_code": "2635010700",
            "legal_dong_name": "좌동",
            "created_date": "19880423",
            "deleted_date": "",
        },
    ]
    payload = build_alias_payload(
        rows,
        {
            ("부산", "중구"): {"area_code": "6", "sigungu_code": "15"},
            ("부산", "해운대구"): {"area_code": "6", "sigungu_code": "16"},
        },
    )

    assert payload["aliases"]["부산 중구"][0]["match_level"] == "sigungu"
    assert payload["dong_aliases"]["좌동"][0]["sigungu_name"] == "해운대구"

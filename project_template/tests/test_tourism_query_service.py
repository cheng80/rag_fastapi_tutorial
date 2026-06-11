from pathlib import Path
import json

from app.services.korean_external_corrector import ExternalCorrectionResult
from app.services.tourism_query_service import TourismQueryService


class FakeExternalCorrector:
    def __init__(self, corrected_text: str, accepted: bool = True, damaged_terms: list[str] | None = None):
        self.corrected_text = corrected_text
        self.accepted = accepted
        self.damaged_terms = damaged_terms or []
        self.calls = 0

    def correct(self, text: str, protected_terms):
        self.calls += 1
        return ExternalCorrectionResult(
            raw_text=text,
            corrected_text=self.corrected_text,
            accepted=self.accepted,
            provider="fake",
            model="fake-model",
            reason="accepted" if self.accepted else "protected_term_damaged",
            damaged_terms=self.damaged_terms,
        )


class FakeConditionTransformer:
    def __init__(self, labels: list[str] | None = None):
        self.labels = labels or []
        self.calls = 0

    def predict(self, text: str):
        self.calls += 1
        return {
            "labels": self.labels,
            "confidence_by_label": {label: 0.9 for label in self.labels},
            "reason": "fake",
        }


def test_tourism_query_uses_area_code_cache(tmp_path: Path):
    cache_path = tmp_path / "tour_area_codes.json"
    cache_path.write_text(
        json.dumps(
            {
                "ambiguous_region_aliases": {},
                "region_index": {
                    "강릉": {
                        "area_code": "32",
                        "sigungu_code": "1",
                        "area_name": "강원",
                        "sigungu_name": "강릉시",
                    }
                }
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    service = TourismQueryService(area_code_cache_path=cache_path, admin_region_alias_path=tmp_path / "missing_admin_aliases.json")

    query = service.extract("강릉에서 어르신과 휠체어로 갈만한 관광지")

    assert query["region"] == "강릉"
    assert query["area_code"] == "32"
    assert query["sigungu_code"] == "1"
    assert "고령자" in query["conditions"]
    assert "휠체어" in query["conditions"]


def test_tourism_query_marks_broad_accessibility_phrase_as_ambiguous():
    service = TourismQueryService()

    query = service.extract("강남구에서 접근성 좋은 실내 관광지")

    assert "휠체어" in query["conditions"]
    assert query["ambiguous_conditions"] == ["휠체어", "접근로", "고령자"]


def test_tourism_query_does_not_treat_parent_terms_as_elderly(tmp_path: Path):
    cache_path = tmp_path / "tour_area_codes.json"
    cache_path.write_text(
        json.dumps(
            {
                "ambiguous_region_aliases": {},
                "region_index": {
                    "강릉": {
                        "area_code": "32",
                        "sigungu_code": "1",
                        "area_name": "강원",
                        "sigungu_name": "강릉시",
                    }
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    service = TourismQueryService(area_code_cache_path=cache_path, admin_region_alias_path=tmp_path / "missing_admin_aliases.json")

    query = service.extract("강릉에서 휠체어 타시는 어머니와 갈만한 관광지")

    assert "휠체어" in query["conditions"]
    assert "고령자" not in query["conditions"]


def test_tourism_query_does_not_infer_age_from_parent_relationship(tmp_path: Path):
    cache_path = tmp_path / "tour_area_codes.json"
    cache_path.write_text(
        json.dumps(
            {
                "ambiguous_region_aliases": {},
                "region_index": {
                    "서울": {
                        "area_code": "1",
                        "sigungu_code": None,
                        "area_name": "서울",
                        "sigungu_name": None,
                    }
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    service = TourismQueryService(area_code_cache_path=cache_path, admin_region_alias_path=tmp_path / "missing_admin_aliases.json")

    query = service.extract("서울에서 휠체어 타는 아빠와 갈만한 관광지 추천")

    assert query["conditions"] == ["휠체어"]


def test_tourism_query_extracts_place_feature_keywords(tmp_path: Path):
    cache_path = tmp_path / "tour_area_codes.json"
    cache_path.write_text(
        json.dumps(
            {
                "ambiguous_region_aliases": {},
                "region_index": {
                    "서울 강남구": {
                        "area_code": "1",
                        "sigungu_code": "1",
                        "area_name": "서울",
                        "sigungu_name": "강남구",
                    }
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    service = TourismQueryService(area_code_cache_path=cache_path, admin_region_alias_path=tmp_path / "missing_admin_aliases.json")

    query = service.extract("서울 강남구에 바닷가 휠체어 관광지 추천해줘")

    assert query["region"] == "서울 강남구"
    assert query["features"] == ["바닷가"]


def test_tourism_query_marks_unsupported_price_comparison(tmp_path: Path):
    cache_path = tmp_path / "tour_area_codes.json"
    cache_path.write_text(json.dumps({"ambiguous_region_aliases": {}, "region_index": {}}, ensure_ascii=False), encoding="utf-8")
    service = TourismQueryService(area_code_cache_path=cache_path, admin_region_alias_path=tmp_path / "missing_admin_aliases.json")

    query = service.extract("휠체어 대여 가격이 제일 싼 곳 알려줘")

    assert query["unsupported_intent"] == "wheelchair_rental_price"


def test_tourism_query_distinguishes_lift_facility_from_lift_booking(tmp_path: Path):
    cache_path = tmp_path / "tour_area_codes.json"
    cache_path.write_text(json.dumps({"ambiguous_region_aliases": {}, "region_index": {}}, ensure_ascii=False), encoding="utf-8")
    service = TourismQueryService(area_code_cache_path=cache_path, admin_region_alias_path=tmp_path / "missing_admin_aliases.json")

    facility = service.extract("서울에서 휠체어 리프트 있는 관광지 추천")
    booking = service.extract("서울에서 리프트 차량 예약 가능한 업체 알려줘")

    assert {"휠체어", "엘리베이터"} <= set(facility["conditions"])
    assert facility["unsupported_intent"] is None
    assert booking["unsupported_intent"] == "transport_booking"


def test_tourism_query_marks_mixed_scope_request(tmp_path: Path):
    cache_path = tmp_path / "tour_area_codes.json"
    cache_path.write_text(
        json.dumps(
            {
                "ambiguous_region_aliases": {},
                "region_index": {
                    "서울": {
                        "area_code": "1",
                        "sigungu_code": None,
                        "area_name": "서울",
                        "sigungu_name": None,
                    }
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    service = TourismQueryService(area_code_cache_path=cache_path, admin_region_alias_path=tmp_path / "missing_admin_aliases.json")

    query = service.extract("서울에서 휠체어 관광지 추천하면서 근처 응급실과 약국도 같이 알려줘")

    assert query["region"] == "서울"
    assert "휠체어" in query["conditions"]
    assert query["unsupported_intent"] == "medical_lookup"


def test_tourism_query_normalizes_noisy_region_and_condition(tmp_path: Path):
    cache_path = tmp_path / "tour_area_codes.json"
    cache_path.write_text(
        json.dumps(
            {
                "ambiguous_region_aliases": {},
                "region_index": {
                    "서울": {
                        "area_code": "1",
                        "sigungu_code": None,
                        "area_name": "서울",
                        "sigungu_name": None,
                    },
                    "부산": {
                        "area_code": "6",
                        "sigungu_code": None,
                        "area_name": "부산",
                        "sigungu_name": None,
                    },
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    service = TourismQueryService(area_code_cache_path=cache_path, admin_region_alias_path=tmp_path / "missing_admin_aliases.json")

    query = service.extract("서울말고부산휠체여가능한곳추천좀")

    assert query["region"] == "부산"
    assert query["area_code"] == "6"
    assert "휠체어" in query["conditions"]
    assert "휠체여->휠체어" in query["normalization_corrections"]
    assert "no-spacing-input" in query["normalization_risk_tags"]
    assert "서울 말고 부산" in query["normalized_query"]


def test_tourism_query_ignores_negated_unsupported_keyword(tmp_path: Path):
    cache_path = tmp_path / "tour_area_codes.json"
    cache_path.write_text(
        json.dumps(
            {
                "ambiguous_region_aliases": {},
                "region_index": {
                    "부산 중구": {
                        "area_code": "6",
                        "sigungu_code": "15",
                        "area_name": "부산",
                        "sigungu_name": "중구",
                    }
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    service = TourismQueryService(area_code_cache_path=cache_path, admin_region_alias_path=tmp_path / "missing_admin_aliases.json")

    query = service.extract("부산 중구에서 응급실 말고 휠체어 관광지만 추천해줘")

    assert query["region"] == "부산 중구"
    assert "휠체어" in query["conditions"]
    assert query["unsupported_intent"] is None


def test_tourism_query_maps_legacy_region_name_to_current_sigungu(tmp_path: Path):
    cache_path = tmp_path / "tour_area_codes.json"
    cache_path.write_text(
        json.dumps(
            {
                "ambiguous_region_aliases": {},
                "region_index": {
                    "청원군": {
                        "area_code": "33",
                        "sigungu_code": "9",
                        "area_name": "충북",
                        "sigungu_name": "청원군",
                    },
                    "청주시": {
                        "area_code": "33",
                        "sigungu_code": "10",
                        "area_name": "충북",
                        "sigungu_name": "청주시",
                    },
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    service = TourismQueryService(area_code_cache_path=cache_path, admin_region_alias_path=tmp_path / "missing_admin_aliases.json")

    query = service.extract("청원군에서 휠체어 관광지 추천해줘")

    assert query["region"] == "청주시"
    assert query["area_code"] == "33"
    assert query["sigungu_code"] == "10"
    assert query["sigungu_name"] == "청주시"
    assert query["legacy_region"] == "청원군"
    assert query["legacy_region_replacement"] == "청주시"
    assert query["legacy_region_notice"] == "청원군은 현재 청주시 기준으로 안내드릴게요."


def test_tourism_query_maps_legacy_jeju_county_to_current_city(tmp_path: Path):
    cache_path = tmp_path / "tour_area_codes.json"
    cache_path.write_text(
        json.dumps(
            {
                "ambiguous_region_aliases": {},
                "region_index": {
                    "남제주군": {
                        "area_code": "39",
                        "sigungu_code": "2",
                        "area_name": "제주",
                        "sigungu_name": "남제주군",
                    },
                    "서귀포시": {
                        "area_code": "39",
                        "sigungu_code": "3",
                        "area_name": "제주",
                        "sigungu_name": "서귀포시",
                    },
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    service = TourismQueryService(area_code_cache_path=cache_path, admin_region_alias_path=tmp_path / "missing_admin_aliases.json")

    query = service.extract("제주특별자치도 남제주군에서 유모차 관광지 추천해줘")

    assert query["region"] == "서귀포시"
    assert query["area_code"] == "39"
    assert query["sigungu_code"] == "3"
    assert query["sigungu_name"] == "서귀포시"
    assert query["legacy_region"] == "제주특별자치도 남제주군"
    assert query["legacy_region_notice"] == "남제주군은 현재 서귀포시 기준으로 안내드릴게요."


def test_tourism_query_maps_spaced_legacy_jeju_county_to_current_city(tmp_path: Path):
    cache_path = tmp_path / "area_codes.json"
    cache_path.write_text(
        json.dumps(
            {
                "ambiguous_region_aliases": {},
                "region_index": {
                    "서귀포시": {
                        "area_code": "39",
                        "area_name": "제주",
                        "sigungu_code": "3",
                        "sigungu_name": "서귀포시",
                    },
                    "남제주군": {
                        "area_code": "39",
                        "area_name": "제주",
                        "sigungu_code": "3",
                        "sigungu_name": "남제주군",
                    },
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    service = TourismQueryService(area_code_cache_path=cache_path, admin_region_alias_path=tmp_path / "missing_admin_aliases.json")

    query = service.extract("남 제주군에서 유모차 관광지 추천해줘")

    assert query["area_code"] == "39"
    assert query["sigungu_code"] == "3"
    assert query["region"] == "서귀포시"
    assert query["legacy_region"] == "남제주군"
    assert query["legacy_region_notice"] == "남제주군은 현재 서귀포시 기준으로 안내드릴게요."


def test_tourism_query_detects_compact_multiple_area_conflict(tmp_path: Path):
    cache_path = tmp_path / "area_codes.json"
    cache_path.write_text(json.dumps({"ambiguous_region_aliases": {}, "region_index": {}}, ensure_ascii=False), encoding="utf-8")
    service = TourismQueryService(area_code_cache_path=cache_path, admin_region_alias_path=tmp_path / "missing_admin_aliases.json")

    query = service.extract("서울부산휠체어추천")

    assert query["ambiguous_region"] == "서울/부산"
    assert query["ambiguous_region_candidates"] == [
        {"area_name": "서울", "sigungu_name": "서울", "area_code": "1", "sigungu_code": None},
        {"area_name": "부산", "sigungu_name": "부산", "area_code": "6", "sigungu_code": None},
    ]


def test_tourism_query_falls_back_without_cache(tmp_path: Path):
    service = TourismQueryService(area_code_cache_path=tmp_path / "missing.json", admin_region_alias_path=tmp_path / "missing_admin_aliases.json")

    query = service.extract("부산에서 접근로 좋은 관광지")

    assert query["region"] == "부산"
    assert query["area_code"] == "6"
    assert query["sigungu_code"] is None
    assert "접근로" in query["conditions"]
    assert query["region_cache_status"] == "missing"
    assert "지역 코드 캐시" in query["region_cache_warning"]


def test_tourism_query_reports_invalid_cache(tmp_path: Path):
    cache_path = tmp_path / "tour_area_codes.json"
    cache_path.write_text("{bad json", encoding="utf-8")
    service = TourismQueryService(area_code_cache_path=cache_path, admin_region_alias_path=tmp_path / "missing_admin_aliases.json")

    query = service.extract("부산에서 접근로 좋은 관광지")

    assert query["region"] == "부산"
    assert query["area_code"] == "6"
    assert query["region_cache_status"] == "invalid"
    assert "지역 코드 캐시" in query["region_cache_warning"]


def test_tourism_query_reports_ambiguous_region_alias(tmp_path: Path):
    cache_path = tmp_path / "tour_area_codes.json"
    cache_path.write_text(
        json.dumps(
            {
                "region_index": {
                    "서울": {
                        "area_code": "1",
                        "sigungu_code": None,
                        "area_name": "서울",
                        "sigungu_name": None,
                    },
                    "부산": {
                        "area_code": "6",
                        "sigungu_code": None,
                        "area_name": "부산",
                        "sigungu_name": None,
                    },
                },
                "ambiguous_region_aliases": {
                    "중구": [
                        {
                            "area_code": "1",
                            "sigungu_code": "24",
                            "area_name": "서울",
                            "sigungu_name": "중구",
                        },
                        {
                            "area_code": "6",
                            "sigungu_code": "15",
                            "area_name": "부산",
                            "sigungu_name": "중구",
                        },
                    ]
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    service = TourismQueryService(area_code_cache_path=cache_path, admin_region_alias_path=tmp_path / "missing_admin_aliases.json")

    ambiguous = service.extract("중구에서 휠체어 관광지 추천")
    resolved = service.extract("부산 중구에서 휠체어 관광지 추천")

    assert ambiguous["ambiguous_region"] == "중구"
    assert len(ambiguous["ambiguous_region_candidates"]) == 2
    assert resolved["region"] == "부산 중구"
    assert resolved["area_code"] == "6"
    assert resolved["sigungu_code"] == "15"
    assert resolved["area_name"] == "부산"
    assert resolved["sigungu_name"] == "중구"
    assert resolved["ambiguous_region"] is None


def test_tourism_query_resolves_short_sigungu_with_admin_aliases(tmp_path: Path):
    area_cache_path = tmp_path / "tour_area_codes.json"
    admin_alias_path = tmp_path / "admin_region_aliases.json"
    area_cache_path.write_text(json.dumps({"region_index": {}, "ambiguous_region_aliases": {}}, ensure_ascii=False))
    admin_alias_path.write_text(
        json.dumps(
            {
                "aliases": {
                    "부산 중구": [
                        {
                            "area_name": "부산",
                            "sigungu_name": "중구",
                            "tour_area_code": "6",
                            "tour_sigungu_code": "15",
                        }
                    ]
                },
                "dong_aliases": {},
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    service = TourismQueryService(area_code_cache_path=area_cache_path, admin_region_alias_path=admin_alias_path)

    query = service.extract("부산 중구에서 휠체어 관광지 추천해줘")

    assert query["region"] == "부산 중구"
    assert query["area_code"] == "6"
    assert query["sigungu_code"] == "15"
    assert query["area_name"] == "부산"
    assert query["sigungu_name"] == "중구"


def test_tourism_query_resolves_unique_legal_dong_to_sigungu(tmp_path: Path):
    area_cache_path = tmp_path / "tour_area_codes.json"
    admin_alias_path = tmp_path / "admin_region_aliases.json"
    area_cache_path.write_text(json.dumps({"region_index": {}, "ambiguous_region_aliases": {}}, ensure_ascii=False))
    admin_alias_path.write_text(
        json.dumps(
            {
                "aliases": {},
                "dong_aliases": {
                    "좌동": [
                        {
                            "area_name": "부산",
                            "sigungu_name": "해운대구",
                            "admin_dong_name": "좌제1동",
                            "legal_dong_name": "좌동",
                            "tour_area_code": "6",
                            "tour_sigungu_code": "16",
                        },
                        {
                            "area_name": "부산",
                            "sigungu_name": "해운대구",
                            "admin_dong_name": "좌제2동",
                            "legal_dong_name": "좌동",
                            "tour_area_code": "6",
                            "tour_sigungu_code": "16",
                        },
                    ]
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    service = TourismQueryService(area_code_cache_path=area_cache_path, admin_region_alias_path=admin_alias_path)

    query = service.extract("해운대 좌동에서 유모차로 갈만한 관광지 추천")

    assert query["region"] == "좌동"
    assert query["area_code"] == "6"
    assert query["sigungu_code"] == "16"
    assert query["area_name"] == "부산"
    assert query["sigungu_name"] == "해운대구"
    assert "유모차" in query["conditions"]


def test_tourism_query_keeps_ambiguous_admin_alias_as_clarification(tmp_path: Path):
    area_cache_path = tmp_path / "tour_area_codes.json"
    admin_alias_path = tmp_path / "admin_region_aliases.json"
    area_cache_path.write_text(json.dumps({"region_index": {}, "ambiguous_region_aliases": {}}, ensure_ascii=False))
    admin_alias_path.write_text(
        json.dumps(
            {
                "aliases": {
                    "중구": [
                        {
                            "area_name": "서울",
                            "sigungu_name": "중구",
                            "tour_area_code": "1",
                            "tour_sigungu_code": "24",
                        },
                        {
                            "area_name": "부산",
                            "sigungu_name": "중구",
                            "tour_area_code": "6",
                            "tour_sigungu_code": "15",
                        },
                    ]
                },
                "dong_aliases": {},
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    service = TourismQueryService(area_code_cache_path=area_cache_path, admin_region_alias_path=admin_alias_path)

    query = service.extract("중구에서 휠체어 타시는 아버지와 갈 관광지 추천")

    assert query["region"] is None
    assert query["ambiguous_region"] == "중구"
    assert len(query["ambiguous_region_candidates"]) == 2
    assert "휠체어" in query["conditions"]


def test_tourism_query_keeps_bare_ambiguous_alias_even_if_admin_alias_has_single_default(tmp_path: Path):
    area_cache_path = tmp_path / "tour_area_codes.json"
    admin_alias_path = tmp_path / "admin_region_aliases.json"
    area_cache_path.write_text(
        json.dumps(
            {
                "region_index": {},
                "ambiguous_region_aliases": {
                    "남구": [
                        {
                            "area_code": "6",
                            "sigungu_code": "4",
                            "area_name": "부산",
                            "sigungu_name": "남구",
                        },
                        {
                            "area_code": "7",
                            "sigungu_code": "2",
                            "area_name": "울산",
                            "sigungu_name": "남구",
                        },
                    ]
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    admin_alias_path.write_text(
        json.dumps(
            {
                "aliases": {
                    "남구": [
                        {
                            "area_name": "경북",
                            "sigungu_name": "포항시",
                            "tour_area_code": "35",
                            "tour_sigungu_code": "23",
                        }
                    ]
                },
                "dong_aliases": {},
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    service = TourismQueryService(area_code_cache_path=area_cache_path, admin_region_alias_path=admin_alias_path)

    query = service.extract("남구에서 유모차로 갈 수 있는 곳 추천해줘")

    assert query["region"] == "남구"
    assert query["ambiguous_region"] == "남구"
    assert len(query["ambiguous_region_candidates"]) == 2


def test_tourism_query_does_not_treat_common_word_alias_as_region_when_area_is_known(tmp_path: Path):
    area_cache_path = tmp_path / "tour_area_codes.json"
    admin_alias_path = tmp_path / "admin_region_aliases.json"
    area_cache_path.write_text(
        json.dumps(
            {
                "region_index": {
                    "서울": {
                        "area_code": "1",
                        "sigungu_code": None,
                        "area_name": "서울",
                        "sigungu_name": None,
                    }
                },
                "ambiguous_region_aliases": {},
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    admin_alias_path.write_text(
        json.dumps(
            {
                "aliases": {},
                "dong_aliases": {
                    "이동": [
                        {
                            "area_name": "경기",
                            "sigungu_name": "의왕시",
                            "tour_area_code": "31",
                            "tour_sigungu_code": "24",
                        },
                        {
                            "area_name": "경남",
                            "sigungu_name": "김해시",
                            "tour_area_code": "36",
                            "tour_sigungu_code": "4",
                        },
                    ]
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    service = TourismQueryService(area_code_cache_path=area_cache_path, admin_region_alias_path=admin_alias_path)

    query = service.extract("서울에서 고령자 부모님과 휠체어로 이동하기 좋은 실내 관광지 추천해줘")

    assert query["region"] == "서울"
    assert query["ambiguous_region"] is None
    assert "휠체어" in query["conditions"]
    assert "고령자" in query["conditions"]


def test_tourism_query_maps_general_gu_to_parent_tourapi_sigungu(tmp_path: Path):
    area_cache_path = tmp_path / "tour_area_codes.json"
    admin_alias_path = tmp_path / "admin_region_aliases.json"
    area_cache_path.write_text(json.dumps({"region_index": {}, "ambiguous_region_aliases": {}}, ensure_ascii=False))
    admin_alias_path.write_text(
        json.dumps(
            {
                "aliases": {},
                "dong_aliases": {
                    "마산합포구": [
                        {
                            "area_name": "경남",
                            "sigungu_name": "창원시",
                            "admin_dong_name": "마산합포구",
                            "legal_dong_name": "창원시마산합포구",
                            "tour_area_code": "36",
                            "tour_sigungu_code": "16",
                        }
                    ]
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    service = TourismQueryService(area_code_cache_path=area_cache_path, admin_region_alias_path=admin_alias_path)

    query = service.extract("창원 마산합포구에서 이동약자 관광지 추천")

    assert query["region"] == "마산합포구"
    assert query["area_code"] == "36"
    assert query["sigungu_code"] == "16"
    assert query["area_name"] == "경남"
    assert query["sigungu_name"] == "창원시"
    assert "휠체어" in query["conditions"]


def test_tourism_query_maps_city_general_gu_to_parent_sigungu(tmp_path: Path):
    area_cache_path = tmp_path / "tour_area_codes.json"
    admin_alias_path = tmp_path / "admin_region_aliases.json"
    area_cache_path.write_text(json.dumps({"region_index": {}, "ambiguous_region_aliases": {}}, ensure_ascii=False))
    admin_alias_path.write_text(
        json.dumps(
            {
                "aliases": {
                    "성남 분당구": [
                        {
                            "area_name": "경기",
                            "sigungu_name": "성남시",
                            "tour_area_code": "31",
                            "tour_sigungu_code": "12",
                        }
                    ],
                    "분당구": [
                        {
                            "area_name": "경기",
                            "sigungu_name": "성남시",
                            "tour_area_code": "31",
                            "tour_sigungu_code": "12",
                        }
                    ],
                },
                "dong_aliases": {},
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    service = TourismQueryService(area_code_cache_path=area_cache_path, admin_region_alias_path=admin_alias_path)

    query = service.extract("성남 분당구에서 무장애 관광지 추천")

    assert query["region"] == "성남 분당구"
    assert query["area_code"] == "31"
    assert query["sigungu_code"] == "12"
    assert query["area_name"] == "경기"
    assert query["sigungu_name"] == "성남시"
    assert "휠체어" in query["conditions"]


def test_tourism_query_keeps_bare_general_gu_ambiguous_when_multiple_parents(tmp_path: Path):
    area_cache_path = tmp_path / "tour_area_codes.json"
    admin_alias_path = tmp_path / "admin_region_aliases.json"
    area_cache_path.write_text(json.dumps({"region_index": {}, "ambiguous_region_aliases": {}}, ensure_ascii=False))
    admin_alias_path.write_text(
        json.dumps(
            {
                "aliases": {
                    "분당구": [
                        {
                            "area_name": "경기",
                            "sigungu_name": "성남시",
                            "tour_area_code": "31",
                            "tour_sigungu_code": "12",
                        },
                        {
                            "area_name": "강원",
                            "sigungu_name": "원주시",
                            "tour_area_code": "32",
                            "tour_sigungu_code": "9",
                        },
                    ]
                },
                "dong_aliases": {},
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    service = TourismQueryService(area_code_cache_path=area_cache_path, admin_region_alias_path=admin_alias_path)

    query = service.extract("분당구에서 무장애 관광지 추천")

    assert query["region"] is None
    assert query["ambiguous_region"] == "분당구"
    assert len(query["ambiguous_region_candidates"]) == 2


def test_tourism_query_resolves_general_gu_when_parent_city_is_named(tmp_path: Path):
    area_cache_path = tmp_path / "tour_area_codes.json"
    admin_alias_path = tmp_path / "admin_region_aliases.json"
    area_cache_path.write_text(json.dumps({"region_index": {}, "ambiguous_region_aliases": {}}, ensure_ascii=False))
    admin_alias_path.write_text(
        json.dumps(
            {
                "aliases": {
                    "고양 일산동구": [
                        {
                            "area_name": "경기",
                            "sigungu_name": "고양시",
                            "tour_area_code": "31",
                            "tour_sigungu_code": "2",
                        }
                    ],
                    "일산동구": [
                        {
                            "area_name": "경기",
                            "sigungu_name": "고양시",
                            "tour_area_code": "31",
                            "tour_sigungu_code": "2",
                        },
                        {
                            "area_name": "강원",
                            "sigungu_name": "원주시",
                            "tour_area_code": "32",
                            "tour_sigungu_code": "9",
                        },
                    ],
                },
                "dong_aliases": {},
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    service = TourismQueryService(area_code_cache_path=area_cache_path, admin_region_alias_path=admin_alias_path)

    query = service.extract("고양 일산동구에서 휠체어 관광지 추천")

    assert query["region"] == "고양 일산동구"
    assert query["area_code"] == "31"
    assert query["sigungu_code"] == "2"
    assert query["area_name"] == "경기"
    assert query["sigungu_name"] == "고양시"
    assert query["ambiguous_region"] is None


def test_tourism_query_keeps_bare_legal_dong_ambiguous_when_multiple_sigungu(tmp_path: Path):
    area_cache_path = tmp_path / "tour_area_codes.json"
    admin_alias_path = tmp_path / "admin_region_aliases.json"
    area_cache_path.write_text(json.dumps({"region_index": {}, "ambiguous_region_aliases": {}}, ensure_ascii=False))
    admin_alias_path.write_text(
        json.dumps(
            {
                "aliases": {},
                "dong_aliases": {
                    "상동": [
                        {
                            "area_name": "경기",
                            "sigungu_name": "부천시",
                            "tour_area_code": "31",
                            "tour_sigungu_code": "11",
                        },
                        {
                            "area_name": "전남",
                            "sigungu_name": "목포시",
                            "tour_area_code": "38",
                            "tour_sigungu_code": "8",
                        },
                    ]
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    service = TourismQueryService(area_code_cache_path=area_cache_path, admin_region_alias_path=admin_alias_path)

    query = service.extract("상동에서 유모차로 갈만한 관광지 추천")

    assert query["region"] is None
    assert query["ambiguous_region"] == "상동"
    assert len(query["ambiguous_region_candidates"]) == 2


def test_tourism_query_resolves_legal_dong_when_city_context_is_named(tmp_path: Path):
    area_cache_path = tmp_path / "tour_area_codes.json"
    admin_alias_path = tmp_path / "admin_region_aliases.json"
    area_cache_path.write_text(json.dumps({"region_index": {}, "ambiguous_region_aliases": {}}, ensure_ascii=False))
    admin_alias_path.write_text(
        json.dumps(
            {
                "aliases": {},
                "dong_aliases": {
                    "부천 상동": [
                        {
                            "area_name": "경기",
                            "sigungu_name": "부천시",
                            "tour_area_code": "31",
                            "tour_sigungu_code": "11",
                        }
                    ],
                    "상동": [
                        {
                            "area_name": "경기",
                            "sigungu_name": "부천시",
                            "tour_area_code": "31",
                            "tour_sigungu_code": "11",
                        },
                        {
                            "area_name": "전남",
                            "sigungu_name": "목포시",
                            "tour_area_code": "38",
                            "tour_sigungu_code": "8",
                        },
                    ],
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    service = TourismQueryService(area_code_cache_path=area_cache_path, admin_region_alias_path=admin_alias_path)

    query = service.extract("부천 상동에서 유모차로 갈만한 관광지 추천")

    assert query["region"] == "부천 상동"
    assert query["area_code"] == "31"
    assert query["sigungu_code"] == "11"
    assert query["area_name"] == "경기"
    assert query["sigungu_name"] == "부천시"


def test_tourism_query_uses_region_after_replacement_marker(tmp_path: Path):
    cache_path = tmp_path / "tour_area_codes.json"
    cache_path.write_text(
        json.dumps(
            {
                "ambiguous_region_aliases": {},
                "region_index": {
                    "서귀포": {
                        "area_code": "39",
                        "sigungu_code": "3",
                        "area_name": "제주",
                        "sigungu_name": "서귀포시",
                    },
                    "제주시": {
                        "area_code": "39",
                        "sigungu_code": "4",
                        "area_name": "제주",
                        "sigungu_name": "제주시",
                    },
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    service = TourismQueryService(area_code_cache_path=cache_path, admin_region_alias_path=tmp_path / "missing_admin_aliases.json")

    query = service.extract("서귀포시 말고 제주시")

    assert query["region"] == "제주시"
    assert query["sigungu_code"] == "4"


def test_tourism_query_splits_excluded_and_replacement_preferences(tmp_path: Path):
    cache_path = tmp_path / "tour_area_codes.json"
    cache_path.write_text(json.dumps({"ambiguous_region_aliases": {}, "region_index": {}}, ensure_ascii=False), encoding="utf-8")
    service = TourismQueryService(area_code_cache_path=cache_path, admin_region_alias_path=tmp_path / "missing_admin_aliases.json")

    query = service.extract("시장 말고 실내 박물관 쪽으로 바꿔줘")

    assert query["preferences"] == ["실내", "박물관_전시"]
    assert query["excluded_preferences"] == ["시장_먹거리"]


def test_tourism_query_handles_particle_before_exclusion_marker(tmp_path: Path):
    cache_path = tmp_path / "tour_area_codes.json"
    cache_path.write_text(json.dumps({"ambiguous_region_aliases": {}, "region_index": {}}, ensure_ascii=False), encoding="utf-8")
    service = TourismQueryService(area_code_cache_path=cache_path, admin_region_alias_path=tmp_path / "missing_admin_aliases.json")

    query = service.extract("호텔이나 숙박은 빼고 관광지만 계속")

    assert query["preferences"] == []
    assert query["excluded_preferences"] == ["숙박"]


def test_tourism_query_marks_passed_lodging_as_excluded_preference(tmp_path: Path):
    cache_path = tmp_path / "tour_area_codes.json"
    cache_path.write_text(
        json.dumps(
            {
                "ambiguous_region_aliases": {},
                "region_index": {
                    "제주시": {
                        "area_code": "39",
                        "sigungu_code": "4",
                        "area_name": "제주",
                        "sigungu_name": "제주시",
                    }
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    service = TourismQueryService(area_code_cache_path=cache_path, admin_region_alias_path=tmp_path / "missing_admin_aliases.json")

    query = service.extract("제주시에서 숙박업소처럼 보이는 후보는 패스하고 낮에 볼거리만 추천해줘")

    assert query["region"] == "제주시"
    assert query["unsupported_intent"] is None
    assert query["ml_intent"] == "exclude_preference"
    assert query["excluded_preferences"] == ["숙박"]


def test_tourism_query_removes_negated_conditions(tmp_path: Path):
    cache_path = tmp_path / "tour_area_codes.json"
    cache_path.write_text(json.dumps({"ambiguous_region_aliases": {}, "region_index": {}}, ensure_ascii=False), encoding="utf-8")
    service = TourismQueryService(area_code_cache_path=cache_path, admin_region_alias_path=tmp_path / "missing_admin_aliases.json")

    query = service.extract("유모차 말고 휠체어로 갈 수 있는 곳")

    assert query["conditions"] == ["휠체어"]
    assert query["excluded_conditions"] == ["유모차"]


def test_tourism_query_removes_anaphoric_previous_condition(tmp_path: Path):
    cache_path = tmp_path / "tour_area_codes.json"
    cache_path.write_text(json.dumps({"ambiguous_region_aliases": {}, "region_index": {}}, ensure_ascii=False), encoding="utf-8")
    service = TourismQueryService(area_code_cache_path=cache_path, admin_region_alias_path=tmp_path / "missing_admin_aliases.json")

    query = service.extract("강릉 처음엔 유아차였는데 그건 빼고 차 대는 곳로 다시")

    assert query["conditions"] == ["주차"]
    assert query["excluded_conditions"] == ["유모차"]


def test_tourism_query_removes_negated_parking_condition(tmp_path: Path):
    cache_path = tmp_path / "tour_area_codes.json"
    cache_path.write_text(json.dumps({"ambiguous_region_aliases": {}, "region_index": {}}, ensure_ascii=False), encoding="utf-8")
    service = TourismQueryService(area_code_cache_path=cache_path, admin_region_alias_path=tmp_path / "missing_admin_aliases.json")

    query = service.extract("주차말고 대중교통으로 갈 수 있는 관광지")

    assert query["conditions"] == ["대중교통"]
    assert query["excluded_conditions"] == ["주차"]


def test_tourism_query_normalizes_negated_parking_typo(tmp_path: Path):
    cache_path = tmp_path / "tour_area_codes.json"
    cache_path.write_text(json.dumps({"ambiguous_region_aliases": {}, "region_index": {}}, ensure_ascii=False), encoding="utf-8")
    service = TourismQueryService(area_code_cache_path=cache_path, admin_region_alias_path=tmp_path / "missing_admin_aliases.json")

    query = service.extract("강릉에서 주챠 아니고 대중교통으로 갈 곳")

    assert query["conditions"] == ["대중교통"]
    assert query["excluded_conditions"] == ["주차"]


def test_tourism_query_normalizes_wheelchair_short_typo(tmp_path: Path):
    cache_path = tmp_path / "tour_area_codes.json"
    cache_path.write_text(
        json.dumps(
            {
                "ambiguous_region_aliases": {},
                "region_index": {
                    "서울 강남구": {
                        "area_code": "1",
                        "sigungu_code": "1",
                        "area_name": "서울",
                        "sigungu_name": "강남구",
                    }
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    service = TourismQueryService(
        area_code_cache_path=cache_path,
        admin_region_alias_path=tmp_path / "missing_admin_aliases.json",
        enable_external_correction=False,
        condition_transformer=FakeConditionTransformer([]),
    )

    query = service.extract("서울 강남구 근처 휠챠로 갈만한데")

    assert query["region"] == "서울 강남구"
    assert query["conditions"] == ["휠체어"]


def test_tourism_query_excludes_compact_parking_and_keeps_stroller(tmp_path: Path):
    cache_path = tmp_path / "tour_area_codes.json"
    cache_path.write_text(json.dumps({"ambiguous_region_aliases": {}, "region_index": {}}, ensure_ascii=False), encoding="utf-8")
    service = TourismQueryService(
        area_code_cache_path=cache_path,
        admin_region_alias_path=tmp_path / "missing_admin_aliases.json",
        enable_external_correction=False,
        condition_transformer=FakeConditionTransformer([]),
    )

    query = service.extract("부산중구에서차댈곳아니고아기차기준")

    assert query["conditions"] == ["유모차"]
    assert query["excluded_conditions"] == ["주차"]


def test_tourism_query_replaces_stroller_with_compact_parking(tmp_path: Path):
    cache_path = tmp_path / "tour_area_codes.json"
    cache_path.write_text(json.dumps({"ambiguous_region_aliases": {}, "region_index": {}}, ensure_ascii=False), encoding="utf-8")
    service = TourismQueryService(
        area_code_cache_path=cache_path,
        admin_region_alias_path=tmp_path / "missing_admin_aliases.json",
        enable_external_correction=False,
        condition_transformer=FakeConditionTransformer([]),
    )

    query = service.extract("유아차말고차댈곳기준")

    assert query["conditions"] == ["주차"]
    assert query["excluded_conditions"] == ["유모차"]


def test_tourism_query_excludes_restroom_with_connective_and_keeps_elevator_typo(tmp_path: Path):
    cache_path = tmp_path / "tour_area_codes.json"
    cache_path.write_text(json.dumps({"ambiguous_region_aliases": {}, "region_index": {}}, ensure_ascii=False), encoding="utf-8")
    service = TourismQueryService(
        area_code_cache_path=cache_path,
        admin_region_alias_path=tmp_path / "missing_admin_aliases.json",
        enable_external_correction=False,
        condition_transformer=FakeConditionTransformer([]),
    )

    query = service.extract("강릉에서화장실편한제외하고엘레베터기준")

    assert query["conditions"] == ["엘리베이터"]
    assert query["excluded_conditions"] == ["화장실"]


def test_tourism_query_removes_excluded_condition_from_required_evidence_terms(tmp_path: Path):
    cache_path = tmp_path / "tour_area_codes.json"
    cache_path.write_text(json.dumps({"ambiguous_region_aliases": {}, "region_index": {}}, ensure_ascii=False), encoding="utf-8")
    service = TourismQueryService(
        area_code_cache_path=cache_path,
        admin_region_alias_path=tmp_path / "missing_admin_aliases.json",
        enable_external_correction=False,
        condition_transformer=FakeConditionTransformer([]),
    )

    query = service.extract("부산중구에서승강기말고애기랑기준")

    assert "엘리베이터" not in query["conditions"]
    assert "엘리베이터" in query["excluded_conditions"]
    assert not any("엘리베이터" in group or "승강기" in group for group in query["required_evidence_terms"])
    assert any("유모차" in group for group in query["required_evidence_terms"])


def test_tourism_query_extracts_alternative_evidence_terms_for_or_sensory_request(tmp_path: Path):
    cache_path = tmp_path / "tour_area_codes.json"
    cache_path.write_text(json.dumps({"ambiguous_region_aliases": {}, "region_index": {}}, ensure_ascii=False), encoding="utf-8")
    service = TourismQueryService(
        area_code_cache_path=cache_path,
        admin_region_alias_path=tmp_path / "missing_admin_aliases.json",
        enable_external_correction=False,
        condition_transformer=FakeConditionTransformer([]),
    )

    query = service.extract("점자나 음성안내 둘 중 하나라도 있으면 추천해줘")

    assert query["required_evidence_terms"] == []
    assert ["점자", "점자블록", "음성안내", "음성 안내", "오디오가이드", "점자홍보물"] in query["alternative_evidence_terms"]


def test_tourism_query_does_not_treat_floor_movement_as_ambiguous_region(tmp_path: Path):
    cache_path = tmp_path / "tour_area_codes.json"
    cache_path.write_text(
        json.dumps(
            {
                "ambiguous_region_aliases": {
                    "이동": [
                        {"area_code": "31", "sigungu_code": "10", "area_name": "경기", "sigungu_name": "의왕시"},
                        {"area_code": "36", "sigungu_code": "4", "area_name": "경남", "sigungu_name": "김해시"},
                    ]
                },
                "region_index": {},
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    service = TourismQueryService(area_code_cache_path=cache_path, admin_region_alias_path=tmp_path / "missing_admin_aliases.json")

    query = service.extract("층 이동 쉬운 곳")

    assert query["ambiguous_region"] is None


def test_tourism_query_marks_ambiguous_condition_boundary(tmp_path: Path):
    cache_path = tmp_path / "tour_area_codes.json"
    cache_path.write_text(json.dumps({"ambiguous_region_aliases": {}, "region_index": {}}, ensure_ascii=False), encoding="utf-8")
    service = TourismQueryService(area_code_cache_path=cache_path, admin_region_alias_path=tmp_path / "missing_admin_aliases.json")

    query = service.extract("서울에서 계단 적게 다니는 편한 관광지")

    assert "접근로" in query["conditions"]
    assert query["ambiguous_conditions"] == ["고령자", "접근로"]


def test_tourism_query_does_not_mark_explicit_wheelchair_as_ambiguous(tmp_path: Path):
    cache_path = tmp_path / "tour_area_codes.json"
    cache_path.write_text(json.dumps({"ambiguous_region_aliases": {}, "region_index": {}}, ensure_ascii=False), encoding="utf-8")
    service = TourismQueryService(area_code_cache_path=cache_path, admin_region_alias_path=tmp_path / "missing_admin_aliases.json")

    query = service.extract("서울에서 휠체어로 갈 수 있는 편한 관광지")

    assert "휠체어" in query["conditions"]
    assert query["ambiguous_conditions"] == []


def test_tourism_query_treats_parent_noisy_mobility_as_senior_anchor(tmp_path: Path):
    cache_path = tmp_path / "tour_area_codes.json"
    cache_path.write_text(json.dumps({"ambiguous_region_aliases": {}, "region_index": {}}, ensure_ascii=False), encoding="utf-8")
    service = TourismQueryService(area_code_cache_path=cache_path, admin_region_alias_path=tmp_path / "missing_admin_aliases.json")

    query = service.extract("서울 중구에서 엄마랑 오래안걷는 되는곳좀")

    assert "고령자" in query["conditions"]
    assert query["ambiguous_conditions"] == []


def test_tourism_query_treats_much_less_walking_as_senior_anchor(tmp_path: Path):
    cache_path = tmp_path / "tour_area_codes.json"
    cache_path.write_text(json.dumps({"ambiguous_region_aliases": {}, "region_index": {}}, ensure_ascii=False), encoding="utf-8")
    service = TourismQueryService(area_code_cache_path=cache_path, admin_region_alias_path=tmp_path / "missing_admin_aliases.json")

    query = service.extract("전주에서 주차장서 많이 안 걷는 곳")

    assert "고령자" in query["conditions"]
    assert "주차" in query["conditions"]
    assert query["ambiguous_conditions"] == []


def test_tourism_query_keeps_spaced_metropolitan_city_unambiguous(tmp_path: Path):
    cache_path = tmp_path / "tour_area_codes.json"
    cache_path.write_text(
        json.dumps(
            {
                "ambiguous_region_aliases": {
                    "광주": [
                        {"area_code": "5", "sigungu_code": None, "area_name": "광주", "sigungu_name": None},
                        {"area_code": "31", "sigungu_code": "5", "area_name": "경기도", "sigungu_name": "광주시"},
                    ]
                },
                "region_index": {"광주": {"area_code": "5", "sigungu_code": None, "area_name": "광주", "sigungu_name": None}},
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    service = TourismQueryService(area_code_cache_path=cache_path, admin_region_alias_path=tmp_path / "missing_admin_aliases.json")

    query = service.extract("광주 광역시에서 어르신이랑 조용히 산책하기 좋은 공원 위주로 추천해줘")

    assert query["ambiguous_region"] is None
    assert query["region"] == "광주"


def test_tourism_query_keeps_spaced_food_market_as_preference_not_required_evidence(tmp_path: Path):
    cache_path = tmp_path / "tour_area_codes.json"
    cache_path.write_text(json.dumps({"ambiguous_region_aliases": {}, "region_index": {}}, ensure_ascii=False), encoding="utf-8")
    service = TourismQueryService(area_code_cache_path=cache_path, admin_region_alias_path=tmp_path / "missing_admin_aliases.json")

    query = service.extract("부산 중구에서 먹 거리 나 시장 위주로 유모차 가능한 곳 보여줘")

    assert query["preferences"] == ["시장_먹거리"]
    assert ["시장", "먹자골목", "전통시장"] not in query["required_evidence_terms"]


def test_tourism_query_normalizes_colloquial_restroom_short_form(tmp_path: Path):
    cache_path = tmp_path / "tour_area_codes.json"
    cache_path.write_text(json.dumps({"ambiguous_region_aliases": {}, "region_index": {}}, ensure_ascii=False), encoding="utf-8")
    service = TourismQueryService(area_code_cache_path=cache_path, admin_region_alias_path=tmp_path / "missing_admin_aliases.json")

    query = service.extract("화장실잇는말고휄체어기준")

    assert "화장실" in query["excluded_conditions"]
    assert "휠체어" in query["conditions"]


def test_tourism_query_ignores_negated_legacy_region(tmp_path: Path):
    cache_path = tmp_path / "tour_area_codes.json"
    cache_path.write_text(
        json.dumps(
            {
                "ambiguous_region_aliases": {},
                "region_index": {
                    "제주시": {
                        "area_code": "39",
                        "sigungu_code": "4",
                        "area_name": "제주",
                        "sigungu_name": "제주시",
                    }
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    service = TourismQueryService(area_code_cache_path=cache_path, admin_region_alias_path=tmp_path / "missing_admin_aliases.json")

    query = service.extract("남제주군 말고 제주시로")

    assert query["region"] == "제주시"
    assert query["legacy_region"] is None


def test_tourism_query_extracts_required_evidence_terms_for_explicit_details(tmp_path: Path):
    cache_path = tmp_path / "tour_area_codes.json"
    cache_path.write_text(json.dumps({"ambiguous_region_aliases": {}, "region_index": {}}, ensure_ascii=False), encoding="utf-8")
    service = TourismQueryService(area_code_cache_path=cache_path, admin_region_alias_path=tmp_path / "missing_admin_aliases.json")

    query = service.extract("대구에서 점자블록과 안내견 가능한 곳 추천")

    assert ["점자블록", "점자"] in query["required_evidence_terms"]
    assert ["보조견", "안내견"] in query["required_evidence_terms"]
    assert "specific_facility_required" in query["context_labels"]


def test_tourism_query_extracts_tactile_map_from_compact_phrases(tmp_path: Path):
    cache_path = tmp_path / "tour_area_codes.json"
    cache_path.write_text(json.dumps({"ambiguous_region_aliases": {}, "region_index": {}}, ensure_ascii=False), encoding="utf-8")
    service = TourismQueryService(area_code_cache_path=cache_path, admin_region_alias_path=tmp_path / "missing_admin_aliases.json")

    compact_query = service.extract("제주시쪽손으로만져확인할안내가능한곳")
    spaced_query = service.extract("제주시 근처 촉지 안내도 확인된 실내 관광지")

    assert any("촉지도" in group and "촉지판" in group for group in compact_query["required_evidence_terms"])
    assert any("촉지도" in group and "촉지판" in group for group in spaced_query["required_evidence_terms"])
    assert "시각장애" in compact_query["conditions"]
    assert "시각장애" in spaced_query["conditions"]


def test_tourism_query_requires_all_conditions_only_when_explicit(tmp_path: Path):
    cache_path = tmp_path / "tour_area_codes.json"
    cache_path.write_text(json.dumps({"ambiguous_region_aliases": {}, "region_index": {}}, ensure_ascii=False), encoding="utf-8")
    service = TourismQueryService(area_code_cache_path=cache_path, admin_region_alias_path=tmp_path / "missing_admin_aliases.json")

    loose = service.extract("서울에서 휠체어와 유모차 가능한 관광지 추천")
    strict = service.extract("서울에서 휠체어와 유모차 둘 다 가능한 관광지 추천")

    assert loose["require_all_conditions"] is False
    assert strict["require_all_conditions"] is True
    assert "soft_and" in loose["context_labels"]
    assert "strict_and" in strict["context_labels"]


def test_tourism_query_uses_safe_external_correction_candidate(tmp_path: Path):
    cache_path = tmp_path / "tour_area_codes.json"
    cache_path.write_text(
        json.dumps(
            {
                "ambiguous_region_aliases": {},
                "region_index": {
                    "서울 강남구": {
                        "area_code": "1",
                        "sigungu_code": "1",
                        "area_name": "서울",
                        "sigungu_name": "강남구",
                    }
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    service = TourismQueryService(
        area_code_cache_path=cache_path,
        admin_region_alias_path=tmp_path / "missing_admin_aliases.json",
        external_corrector=FakeExternalCorrector("서울 강남구 근처에서 휠체어 관광지 추천해줘"),
        enable_external_correction=True,
    )

    query = service.extract("서울 강남구 근처에서 휠쳐 관광지 추천해줘")

    assert query["region"] == "서울 강남구"
    assert query["allow_region_expansion"] is False
    assert "휠체어" in query["conditions"]
    assert query["external_correction_accepted"] is True
    assert query["external_correction_query"] == "서울 강남구 근처에서 휠체어 관광지 추천해줘"


def test_tourism_query_rejects_external_correction_when_protected_term_is_damaged(tmp_path: Path):
    cache_path = tmp_path / "tour_area_codes.json"
    cache_path.write_text(
        json.dumps(
            {
                "ambiguous_region_aliases": {},
                "region_index": {
                    "서울 강남구": {
                        "area_code": "1",
                        "sigungu_code": "1",
                        "area_name": "서울",
                        "sigungu_name": "강남구",
                    }
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    service = TourismQueryService(
        area_code_cache_path=cache_path,
        admin_region_alias_path=tmp_path / "missing_admin_aliases.json",
        external_corrector=FakeExternalCorrector("서울 근처에서 휠체어 관광지 추천해줘", accepted=False, damaged_terms=["서울 강남구"]),
        enable_external_correction=True,
    )

    query = service.extract("서울 강남구 근처에서 휠쳐 관광지 추천해줘")

    assert query["region"] == "서울 강남구"
    assert query["conditions"] == ["휠체어"]
    assert query["external_correction_accepted"] is False
    assert query["external_correction_region_damaged"] is True
    assert query["external_correction_query"] == "서울 근처에서 휠체어 관광지 추천해줘"
    assert query["external_correction_damaged_terms"] == ["서울 강남구"]


def test_tourism_query_marks_unconditional_region_expansion():
    service = TourismQueryService()

    query = service.extract("서울 전체로 넓혀서 휠체어 관광지 추천해줘")

    assert query["allow_region_expansion"] is True
    assert query["conditional_region_expansion"] is False


def test_tourism_query_marks_conditional_region_expansion():
    service = TourismQueryService()

    query = service.extract("서울 강남구에서 휠체어 관광지 추천해줘. 부족하면 서울 전체로 넓혀줘")

    assert query["allow_region_expansion"] is True
    assert query["conditional_region_expansion"] is True


def test_tourism_query_default_external_correction_skips_clean_input(tmp_path: Path):
    cache_path = tmp_path / "tour_area_codes.json"
    cache_path.write_text(
        json.dumps(
            {
                "ambiguous_region_aliases": {},
                "region_index": {
                    "서울": {
                        "area_code": "1",
                        "sigungu_code": None,
                        "area_name": "서울",
                        "sigungu_name": None,
                    }
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    fake_corrector = FakeExternalCorrector("서울 휠체어 관광지 추천해줘")
    service = TourismQueryService(
        area_code_cache_path=cache_path,
        admin_region_alias_path=tmp_path / "missing_admin_aliases.json",
        external_corrector=fake_corrector,
    )

    query = service.extract("서울에서 휠체어 관광지 추천해줘")

    assert query["external_correction_enabled"] is True
    assert query["external_correction_accepted"] is False
    assert fake_corrector.calls == 0


def test_tourism_query_default_external_correction_runs_on_noisy_input(tmp_path: Path):
    cache_path = tmp_path / "tour_area_codes.json"
    cache_path.write_text(
        json.dumps(
            {
                "ambiguous_region_aliases": {},
                "region_index": {
                    "서울 강남구": {
                        "area_code": "1",
                        "sigungu_code": "1",
                        "area_name": "서울",
                        "sigungu_name": "강남구",
                    }
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    fake_corrector = FakeExternalCorrector("서울 강남구 근처에서 휠체어 관광지 추천해줘")
    service = TourismQueryService(
        area_code_cache_path=cache_path,
        admin_region_alias_path=tmp_path / "missing_admin_aliases.json",
        external_corrector=fake_corrector,
    )

    query = service.extract("서울강남구근처휄체여관광지추천")

    assert fake_corrector.calls == 1
    assert query["region"] == "서울 강남구"
    assert "휠체어" in query["conditions"]
    assert query["external_correction_accepted"] is True


def test_tourism_query_skips_transformer_for_clean_confident_rule_input(tmp_path: Path):
    cache_path = tmp_path / "tour_area_codes.json"
    cache_path.write_text(json.dumps({"ambiguous_region_aliases": {}, "region_index": {}}, ensure_ascii=False), encoding="utf-8")
    transformer = FakeConditionTransformer(["엘리베이터"])
    service = TourismQueryService(
        area_code_cache_path=cache_path,
        admin_region_alias_path=tmp_path / "missing_admin_aliases.json",
        condition_transformer=transformer,
        enable_external_correction=False,
    )

    query = service.extract("서울에서 휠체어 관광지 추천")

    assert query["conditions"] == ["휠체어"]
    assert query["condition_transformer_invoked"] is False
    assert query["condition_transformer_gate_reason"] == "clean_rule_confident"
    assert transformer.calls == 0


def test_tourism_query_invokes_transformer_when_rule_misses_condition(tmp_path: Path):
    cache_path = tmp_path / "tour_area_codes.json"
    cache_path.write_text(json.dumps({"ambiguous_region_aliases": {}, "region_index": {}}, ensure_ascii=False), encoding="utf-8")
    transformer = FakeConditionTransformer(["수어"])
    service = TourismQueryService(
        area_code_cache_path=cache_path,
        admin_region_alias_path=tmp_path / "missing_admin_aliases.json",
        condition_transformer=transformer,
        enable_external_correction=False,
    )

    query = service.extract("서울에서 소리 없이 안내를 볼 수 있는 곳")

    assert "수어" in query["conditions"]
    assert query["condition_transformer_invoked"] is True
    assert query["condition_transformer_gate_reason"] == "no_rule_condition"
    assert transformer.calls > 0


def test_tourism_query_invokes_transformer_for_noisy_input_even_with_rule_condition(tmp_path: Path):
    cache_path = tmp_path / "tour_area_codes.json"
    cache_path.write_text(json.dumps({"ambiguous_region_aliases": {}, "region_index": {}}, ensure_ascii=False), encoding="utf-8")
    transformer = FakeConditionTransformer(["엘리베이터"])
    service = TourismQueryService(
        area_code_cache_path=cache_path,
        admin_region_alias_path=tmp_path / "missing_admin_aliases.json",
        condition_transformer=transformer,
        enable_external_correction=False,
    )

    query = service.extract("서울휄체어엘베관광지")

    assert "휠체어" in query["conditions"]
    assert "엘리베이터" in query["conditions"]
    assert query["condition_transformer_invoked"] is True
    assert query["condition_transformer_gate_reason"] == "noisy_input"
    assert transformer.calls > 0

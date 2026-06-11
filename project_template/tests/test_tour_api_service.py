import json
import sqlite3

from app.core.config import Settings
from app.services.tour_api_service import TourAPIError, TourAPIService


def test_tour_api_requires_service_key():
    service = TourAPIService(Settings(tour_api_service_key=None))

    try:
        service.area_based_list("1")
    except TourAPIError as exc:
        assert "TOUR_API_SERVICE_KEY" in str(exc)
    else:
        raise AssertionError("TourAPIError was not raised")


def test_tour_api_records_daily_endpoint_usage_before_request(monkeypatch, tmp_path):
    settings = Settings(
        tour_api_service_key="test",
        tour_api_usage_log_path=tmp_path / "usage.json",
        tour_api_response_cache_path=tmp_path / "cache.sqlite3",
    )
    service = TourAPIService(settings)

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {"response": {"header": {"resultCode": "0000"}, "body": {"items": ""}}}

    monkeypatch.setattr("app.services.tour_api_service.requests.get", lambda *args, **kwargs: FakeResponse())

    service.area_based_list("1")

    saved = (tmp_path / "usage.json").read_text(encoding="utf-8")
    assert "areaBasedList2" in saved


def test_tour_api_stops_when_daily_endpoint_limit_is_exhausted(monkeypatch, tmp_path):
    settings = Settings(
        tour_api_service_key="test",
        tour_api_daily_endpoint_limit=1,
        tour_api_usage_log_path=tmp_path / "usage.json",
        tour_api_response_cache_enabled=False,
    )
    service = TourAPIService(settings)
    called = {"count": 0}

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {"response": {"header": {"resultCode": "0000"}, "body": {"items": ""}}}

    def fake_get(*args, **kwargs):
        called["count"] += 1
        return FakeResponse()

    monkeypatch.setattr("app.services.tour_api_service.requests.get", fake_get)

    service.area_based_list("1")
    try:
        service.area_based_list("1")
    except TourAPIError as exc:
        assert "daily quota exceeded" in str(exc)
    else:
        raise AssertionError("TourAPIError was not raised")
    assert called["count"] == 1


def test_tour_api_extracts_single_item_dict():
    service = TourAPIService(Settings(tour_api_service_key="test"))
    payload = {
        "response": {
            "header": {"resultCode": "0000"},
            "body": {"items": {"item": {"contentid": "1", "title": "관광지"}}},
        }
    }

    assert service._extract_items(payload) == [{"contentid": "1", "title": "관광지"}]


def test_tour_api_extracts_empty_string_items_as_empty_list():
    service = TourAPIService(Settings(tour_api_service_key="test"))
    payload = {
        "response": {
            "header": {"resultCode": "0000"},
            "body": {"items": ""},
        }
    }

    assert service._extract_items(payload) == []


def test_tour_api_extracts_top_level_error():
    service = TourAPIService(Settings(tour_api_service_key="test"))

    try:
        service._extract_items({"resultCode": "10", "resultMsg": "INVALID_REQUEST_PARAMETER_ERROR(listYN)"})
    except TourAPIError as exc:
        assert "listYN" in str(exc)
    else:
        raise AssertionError("TourAPIError was not raised")


def test_area_based_list_does_not_send_listyn(monkeypatch):
    service = TourAPIService(Settings(tour_api_service_key="test"))
    captured = {}

    def fake_request_items(operation, params, base_url=None):
        captured["operation"] = operation
        captured["params"] = params
        captured["base_url"] = base_url
        return []

    monkeypatch.setattr(service, "_request_items", fake_request_items)

    assert service.area_based_list("1") == []
    assert captured["operation"] == "areaBasedList2"
    assert "listYN" not in captured["params"]
    assert captured["params"]["areaCode"] == "1"
    assert captured["base_url"] is None

    service.area_based_list("32", sigungu_code="1")
    assert captured["params"]["sigunguCode"] == "1"


def test_accessible_area_based_list_uses_accessible_service(monkeypatch):
    settings = Settings(
        tour_api_service_key="default",
        tour_api_accessible_service_key="accessible",
        tour_api_accessible_base_url="https://example.com/with",
    )
    service = TourAPIService(settings)
    captured = {}

    def fake_request_items(operation, params, base_url=None, service_key=None):
        captured["operation"] = operation
        captured["params"] = params
        captured["base_url"] = base_url
        captured["service_key"] = service_key
        return []

    monkeypatch.setattr(service, "_request_items", fake_request_items)

    assert service.accessible_area_based_list("32", sigungu_code="1") == []
    assert captured["operation"] == "areaBasedList2"
    assert "listYN" not in captured["params"]
    assert captured["params"]["areaCode"] == "32"
    assert captured["params"]["sigunguCode"] == "1"
    assert captured["base_url"] == "https://example.com/with"
    assert captured["service_key"] == "accessible"


def test_detail_common_uses_service2_minimal_parameters(monkeypatch):
    service = TourAPIService(Settings(tour_api_service_key="test"))
    captured = {}

    def fake_request_items(operation, params, base_url=None):
        captured["operation"] = operation
        captured["params"] = params
        captured["base_url"] = base_url
        return [{"contentid": "1"}]

    monkeypatch.setattr(service, "_request_items", fake_request_items)

    assert service.detail_common("1") == {"contentid": "1"}
    assert captured == {
        "operation": "detailCommon2",
        "params": {"contentId": "1"},
        "base_url": None,
    }


def test_detail_with_tour_uses_accessible_base_url(monkeypatch):
    settings = Settings(
        tour_api_service_key="default",
        tour_api_accessible_service_key="accessible",
        tour_api_accessible_base_url="https://example.com/with",
    )
    service = TourAPIService(settings)
    captured = {}

    def fake_request_items(operation, params, base_url=None, service_key=None):
        captured["operation"] = operation
        captured["params"] = params
        captured["base_url"] = base_url
        captured["service_key"] = service_key
        return [{"contentid": "1"}]

    monkeypatch.setattr(service, "_request_items", fake_request_items)

    assert service.detail_with_tour("1") == {"contentid": "1"}
    assert captured == {
        "operation": "detailWithTour2",
        "params": {"contentId": "1"},
        "base_url": "https://example.com/with",
        "service_key": "accessible",
    }


def test_hub_area_based_list_uses_bigdata_region_codes(monkeypatch):
    settings = Settings(tour_api_service_key="test", tour_api_hub_base_url="https://example.com/hub")
    service = TourAPIService(settings)
    captured = {}

    def fake_request_items(operation, params, base_url=None):
        captured["operation"] = operation
        captured["params"] = params
        captured["base_url"] = base_url
        return []

    monkeypatch.setattr(service, "_request_items", fake_request_items)

    assert service.hub_area_based_list("41", signgu_cd="41135", base_ym="202504") == []
    assert captured == {
        "operation": "areaBasedList1",
        "params": {
            "areaCd": "41",
            "signguCd": "41135",
            "baseYm": "202504",
            "numOfRows": 10,
            "pageNo": 1,
        },
        "base_url": "https://example.com/hub",
    }


def test_related_search_keyword_uses_related_service(monkeypatch):
    settings = Settings(tour_api_service_key="test", tour_api_related_base_url="https://example.com/related")
    service = TourAPIService(settings)
    captured = {}

    def fake_request_items(operation, params, base_url=None):
        captured["operation"] = operation
        captured["params"] = params
        captured["base_url"] = base_url
        return []

    monkeypatch.setattr(service, "_request_items", fake_request_items)

    assert service.related_search_keyword("뮤지엄산", area_cd="51", signgu_cd="51130") == []
    assert captured["operation"] == "searchKeyword1"
    assert captured["params"]["keyword"] == "뮤지엄산"
    assert captured["params"]["areaCd"] == "51"
    assert captured["params"]["signguCd"] == "51130"
    assert captured["base_url"] == "https://example.com/related"


def test_wellness_area_based_list_uses_ldong_codes(monkeypatch):
    settings = Settings(tour_api_service_key="test", tour_api_wellness_base_url="https://example.com/wellness")
    service = TourAPIService(settings)
    captured = {}

    def fake_request_items(operation, params, base_url=None):
        captured["operation"] = operation
        captured["params"] = params
        captured["base_url"] = base_url
        return []

    monkeypatch.setattr(service, "_request_items", fake_request_items)

    assert service.wellness_area_based_list("41", "135", content_type_id="39") == []
    assert captured["operation"] == "areaBasedList"
    assert captured["params"]["langDivCd"] == "KOR"
    assert captured["params"]["lDongRegnCd"] == "41"
    assert captured["params"]["lDongSignguCd"] == "135"
    assert captured["params"]["contentTypeId"] == "39"
    assert captured["base_url"] == "https://example.com/wellness"


def test_tour_api_response_cache_hit_skips_network_and_usage(monkeypatch, tmp_path):
    settings = Settings(
        tour_api_service_key="secret-a",
        tour_api_usage_log_path=tmp_path / "usage.json",
        tour_api_response_cache_path=tmp_path / "cache.sqlite3",
    )
    service = TourAPIService(settings)
    called = {"count": 0}

    class FakeResponse:
        status_code = 200

        def raise_for_status(self):
            return None

        def json(self):
            return {
                "response": {
                    "header": {"resultCode": "0000"},
                    "body": {"items": {"item": [{"contentid": "1", "title": "첫 호출"}]}},
                }
            }

    def fake_get(*args, **kwargs):
        called["count"] += 1
        return FakeResponse()

    monkeypatch.setattr("app.services.tour_api_service.requests.get", fake_get)

    assert service.area_based_list("1") == [{"contentid": "1", "title": "첫 호출"}]
    assert service.area_based_list("1") == [{"contentid": "1", "title": "첫 호출"}]
    assert called["count"] == 1

    usage_payload = json.loads((tmp_path / "usage.json").read_text(encoding="utf-8"))
    assert usage_payload["dates"][service.usage_tracker.today()]["endpoints"]["areaBasedList2"] == 1


def test_tour_api_response_cache_does_not_store_service_key(monkeypatch, tmp_path):
    settings = Settings(
        tour_api_service_key="secret-service-key",
        tour_api_usage_log_path=tmp_path / "usage.json",
        tour_api_response_cache_path=tmp_path / "cache.sqlite3",
    )
    service = TourAPIService(settings)

    class FakeResponse:
        status_code = 200

        def raise_for_status(self):
            return None

        def json(self):
            return {"response": {"header": {"resultCode": "0000"}, "body": {"items": ""}}}

    monkeypatch.setattr("app.services.tour_api_service.requests.get", lambda *args, **kwargs: FakeResponse())

    service.area_based_list("1")

    with sqlite3.connect(tmp_path / "cache.sqlite3") as conn:
        params_json = conn.execute("SELECT params_json FROM tour_api_response_cache").fetchone()[0]
    assert "serviceKey" not in params_json
    assert "secret-service-key" not in params_json


def test_tour_api_response_cache_expired_entry_calls_network_again(monkeypatch, tmp_path):
    settings = Settings(
        tour_api_service_key="test",
        tour_api_usage_log_path=tmp_path / "usage.json",
        tour_api_response_cache_path=tmp_path / "cache.sqlite3",
    )
    service = TourAPIService(settings)
    called = {"count": 0}

    class FakeResponse:
        status_code = 200

        def raise_for_status(self):
            return None

        def json(self):
            called["count"] += 1
            return {
                "response": {
                    "header": {"resultCode": "0000"},
                    "body": {"items": {"item": {"contentid": str(called["count"])}}},
                }
            }

    monkeypatch.setattr("app.services.tour_api_service.requests.get", lambda *args, **kwargs: FakeResponse())

    assert service.area_based_list("1") == [{"contentid": "1"}]
    with sqlite3.connect(tmp_path / "cache.sqlite3") as conn:
        conn.execute("UPDATE tour_api_response_cache SET expires_at = '2000-01-01T00:00:00+00:00'")

    assert service.area_based_list("1") == [{"contentid": "2"}]
    assert called["count"] == 2


def test_tour_api_response_cache_replays_cached_error(monkeypatch, tmp_path):
    settings = Settings(
        tour_api_service_key="test",
        tour_api_usage_log_path=tmp_path / "usage.json",
        tour_api_response_cache_path=tmp_path / "cache.sqlite3",
    )
    service = TourAPIService(settings)
    called = {"count": 0}

    class FakeResponse:
        status_code = 200

        def raise_for_status(self):
            return None

        def json(self):
            called["count"] += 1
            return {"response": {"header": {"resultCode": "10", "resultMsg": "INVALID_REQUEST_PARAMETER_ERROR(listYN)"}}}

    monkeypatch.setattr("app.services.tour_api_service.requests.get", lambda *args, **kwargs: FakeResponse())

    for _ in range(2):
        try:
            service.area_based_list("1")
        except TourAPIError as exc:
            assert "listYN" in str(exc)
        else:
            raise AssertionError("TourAPIError was not raised")
    assert called["count"] == 1

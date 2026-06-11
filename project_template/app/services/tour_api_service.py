from __future__ import annotations

from typing import Any

import requests

from app.core.config import Settings
from app.services.tour_api_response_cache import TourAPIResponseCache
from app.services.tour_api_usage import TourAPIQuotaExceeded, TourAPIUsageTracker


class TourAPIError(RuntimeError):
    pass


class TourAPIService:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.base_url = settings.tour_api_base_url.rstrip("/")
        self.accessible_base_url = settings.tour_api_accessible_base_url.rstrip("/")
        self.hub_base_url = settings.tour_api_hub_base_url.rstrip("/")
        self.related_base_url = settings.tour_api_related_base_url.rstrip("/")
        self.wellness_base_url = settings.tour_api_wellness_base_url.rstrip("/")
        self.usage_tracker = TourAPIUsageTracker(
            settings.resolved_tour_api_usage_log_path,
            daily_endpoint_limit=settings.tour_api_daily_endpoint_limit,
        )
        self.response_cache = TourAPIResponseCache(settings.resolved_tour_api_response_cache_path)

    def area_based_list(
        self,
        area_code: str,
        sigungu_code: str | None = None,
        num_of_rows: int = 10,
        page_no: int = 1,
    ) -> list[dict[str, Any]]:
        params: dict[str, Any] = {
            "areaCode": area_code,
            "numOfRows": num_of_rows,
            "pageNo": page_no,
            "arrange": "A",
        }
        if sigungu_code:
            params["sigunguCode"] = sigungu_code
        return self._request_items(
            "areaBasedList2",
            params,
        )

    def accessible_area_based_list(
        self,
        area_code: str,
        sigungu_code: str | None = None,
        num_of_rows: int = 10,
        page_no: int = 1,
    ) -> list[dict[str, Any]]:
        params: dict[str, Any] = {
            "areaCode": area_code,
            "numOfRows": num_of_rows,
            "pageNo": page_no,
            "arrange": "A",
        }
        if sigungu_code:
            params["sigunguCode"] = sigungu_code
        return self._request_items(
            "areaBasedList2",
            params,
            base_url=self.accessible_base_url,
            service_key=self.settings.tour_api_accessible_service_key,
        )

    def detail_common(self, content_id: str) -> dict[str, Any]:
        items = self._request_items(
            "detailCommon2",
            {"contentId": content_id},
        )
        return items[0] if items else {}

    def detail_with_tour(self, content_id: str) -> dict[str, Any]:
        items = self._request_items(
            "detailWithTour2",
            {"contentId": content_id},
            base_url=self.accessible_base_url,
            service_key=self.settings.tour_api_accessible_service_key,
        )
        return items[0] if items else {}

    def area_codes(self, area_code: str | None = None, accessible: bool = True) -> list[dict[str, Any]]:
        params: dict[str, Any] = {"numOfRows": 100, "pageNo": 1}
        if area_code:
            params["areaCode"] = area_code
        return self._request_items(
            "areaCode2",
            params,
            base_url=self.accessible_base_url if accessible else None,
            service_key=self.settings.tour_api_accessible_service_key if accessible else None,
        )

    def hub_area_based_list(
        self,
        area_cd: str,
        signgu_cd: str | None = None,
        base_ym: str | None = None,
        num_of_rows: int = 10,
        page_no: int = 1,
    ) -> list[dict[str, Any]]:
        params = self._bigdata_region_params(area_cd, signgu_cd, base_ym, num_of_rows, page_no)
        return self._request_items("areaBasedList1", params, base_url=self.hub_base_url)

    def related_area_based_list(
        self,
        area_cd: str,
        signgu_cd: str | None = None,
        base_ym: str | None = None,
        num_of_rows: int = 10,
        page_no: int = 1,
    ) -> list[dict[str, Any]]:
        params = self._bigdata_region_params(area_cd, signgu_cd, base_ym, num_of_rows, page_no)
        return self._request_items("areaBasedList1", params, base_url=self.related_base_url)

    def related_search_keyword(
        self,
        keyword: str,
        area_cd: str | None = None,
        signgu_cd: str | None = None,
        base_ym: str | None = None,
        num_of_rows: int = 10,
        page_no: int = 1,
    ) -> list[dict[str, Any]]:
        params: dict[str, Any] = {"keyword": keyword, "numOfRows": num_of_rows, "pageNo": page_no}
        if area_cd:
            params["areaCd"] = area_cd
        if signgu_cd:
            params["signguCd"] = signgu_cd
        if base_ym:
            params["baseYm"] = base_ym
        return self._request_items("searchKeyword1", params, base_url=self.related_base_url)

    def wellness_area_based_list(
        self,
        ldong_regn_cd: str | None = None,
        ldong_signgu_cd: str | None = None,
        content_type_id: str | None = None,
        arrange: str = "C",
        lang_div_cd: str = "KOR",
        num_of_rows: int = 10,
        page_no: int = 1,
    ) -> list[dict[str, Any]]:
        params: dict[str, Any] = {
            "langDivCd": lang_div_cd,
            "arrange": arrange,
            "numOfRows": num_of_rows,
            "pageNo": page_no,
        }
        if content_type_id:
            params["contentTypeId"] = content_type_id
        if ldong_regn_cd:
            params["lDongRegnCd"] = ldong_regn_cd
        if ldong_signgu_cd:
            params["lDongSignguCd"] = ldong_signgu_cd
        return self._request_items("areaBasedList", params, base_url=self.wellness_base_url)

    def wellness_search_keyword(
        self,
        keyword: str,
        ldong_regn_cd: str | None = None,
        ldong_signgu_cd: str | None = None,
        content_type_id: str | None = None,
        arrange: str = "C",
        lang_div_cd: str = "KOR",
        num_of_rows: int = 10,
        page_no: int = 1,
    ) -> list[dict[str, Any]]:
        params: dict[str, Any] = {
            "keyword": keyword,
            "langDivCd": lang_div_cd,
            "arrange": arrange,
            "numOfRows": num_of_rows,
            "pageNo": page_no,
        }
        if content_type_id:
            params["contentTypeId"] = content_type_id
        if ldong_regn_cd:
            params["lDongRegnCd"] = ldong_regn_cd
        if ldong_signgu_cd:
            params["lDongSignguCd"] = ldong_signgu_cd
        return self._request_items("searchKeyword", params, base_url=self.wellness_base_url)

    def wellness_detail_common(self, content_id: str, lang_div_cd: str = "KOR") -> dict[str, Any]:
        items = self._request_items(
            "detailCommon",
            {"contentId": content_id, "langDivCd": lang_div_cd},
            base_url=self.wellness_base_url,
        )
        return items[0] if items else {}

    @staticmethod
    def _bigdata_region_params(
        area_cd: str,
        signgu_cd: str | None,
        base_ym: str | None,
        num_of_rows: int,
        page_no: int,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {"areaCd": area_cd, "numOfRows": num_of_rows, "pageNo": page_no}
        if signgu_cd:
            params["signguCd"] = signgu_cd
        if base_ym:
            params["baseYm"] = base_ym
        return params

    def _request_items(
        self,
        operation: str,
        params: dict[str, Any],
        base_url: str | None = None,
        service_key: str | None = None,
    ) -> list[dict[str, Any]]:
        effective_service_key = service_key or self.settings.tour_api_service_key
        if not effective_service_key:
            raise TourAPIError("TOUR_API_SERVICE_KEY가 설정되어 있지 않습니다.")

        request_params = {
            "serviceKey": effective_service_key,
            "MobileOS": self.settings.tour_api_mobile_os,
            "MobileApp": self.settings.tour_api_mobile_app,
            "_type": "json",
            **params,
        }
        effective_base_url = base_url or self.base_url
        if self._should_use_response_cache(operation):
            cached = self.response_cache.get(operation, effective_base_url, request_params)
            if cached is not None:
                if cached.error_message:
                    raise TourAPIError(cached.error_message)
                if cached.response_json is not None:
                    return self._extract_items(cached.response_json)

        try:
            self.usage_tracker.record(operation)
        except TourAPIQuotaExceeded as exc:
            raise TourAPIError(str(exc)) from exc

        try:
            response = requests.get(
                f"{effective_base_url}/{operation}",
                params=request_params,
                timeout=self.settings.tour_api_timeout,
            )
            response.raise_for_status()
        except requests.HTTPError as exc:
            status_code = exc.response.status_code if exc.response is not None else "unknown"
            message = f"TourAPI HTTP 오류: {status_code}"
            if self._should_use_response_cache(operation):
                self.response_cache.put(operation, effective_base_url, request_params, None, None, message)
            raise TourAPIError(message) from exc
        except requests.RequestException as exc:
            message = f"TourAPI 요청 실패: {exc.__class__.__name__}"
            if self._should_use_response_cache(operation):
                self.response_cache.put(operation, effective_base_url, request_params, None, None, message)
            raise TourAPIError(message) from exc
        payload = response.json()
        status_code = getattr(response, "status_code", None)
        items: list[dict[str, Any]]
        if self._should_use_response_cache(operation):
            try:
                items = self._extract_items(payload)
            except TourAPIError as exc:
                self.response_cache.put(operation, effective_base_url, request_params, payload, status_code, str(exc))
                raise
            self.response_cache.put(operation, effective_base_url, request_params, payload, status_code)
            return items
        return self._extract_items(payload)

    def _should_use_response_cache(self, operation: str) -> bool:
        return self.settings.tour_api_response_cache_enabled and TourAPIResponseCache.is_cacheable(operation)

    def _extract_items(self, payload: dict[str, Any]) -> list[dict[str, Any]]:
        if "resultCode" in payload and str(payload.get("resultCode")) not in {"0000", "0"}:
            message = payload.get("resultMsg") or "TourAPI 응답 오류"
            raise TourAPIError(f"{payload.get('resultCode')}: {message}")

        header = payload.get("response", {}).get("header", {})
        result_code = str(header.get("resultCode", "0000"))
        if result_code not in {"0000", "0"}:
            message = header.get("resultMsg") or "TourAPI 응답 오류"
            raise TourAPIError(f"{result_code}: {message}")

        items = payload.get("response", {}).get("body", {}).get("items", {})
        if not isinstance(items, dict):
            return []
        raw_items = items.get("item", [])
        if isinstance(raw_items, dict):
            return [raw_items]
        if isinstance(raw_items, list):
            return [item for item in raw_items if isinstance(item, dict)]
        return []

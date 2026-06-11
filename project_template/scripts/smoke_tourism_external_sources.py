from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any
from xml.etree import ElementTree

import requests

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from app.core.config import Settings
from app.services.tour_api_service import TourAPIError, TourAPIService

DEFAULT_REGION_CODES = PROJECT_ROOT / "data" / "processed" / "tourapi_bigdata_region_codes.json"
DEFAULT_OUTPUT = PROJECT_ROOT / "data" / "generated" / "tour_api" / "external_source_smoke_latest.json"
DEFAULT_TOURIST_STANDARD = (
    PROJECT_ROOT / "data" / "source" / "public_tourist_standard" / "national_tourist_standard.json"
)


def summarize_items(items: list[dict[str, Any]], fields: list[str]) -> list[dict[str, Any]]:
    return [{field: item.get(field) for field in fields if item.get(field) is not None} for item in items[:3]]


def parse_response(response: requests.Response) -> dict[str, Any]:
    content_type = response.headers.get("content-type", "")
    text = response.text
    if "json" in content_type or text.lstrip().startswith(("{", "[")):
        try:
            payload = response.json()
        except ValueError:
            return {"format": "text", "text_prefix": text[:500]}
        return {"format": "json", "payload": payload}
    try:
        root = ElementTree.fromstring(response.content)
    except ElementTree.ParseError:
        return {"format": "text", "text_prefix": text[:500]}
    return {"format": "xml", "payload": xml_to_dict(root)}


def xml_to_dict(node: ElementTree.Element) -> Any:
    children = list(node)
    if not children:
        return node.text
    result: dict[str, Any] = {}
    for child in children:
        value = xml_to_dict(child)
        if child.tag in result:
            if not isinstance(result[child.tag], list):
                result[child.tag] = [result[child.tag]]
            result[child.tag].append(value)
        else:
            result[child.tag] = value
    return result


def extract_json_items(payload: Any) -> list[dict[str, Any]]:
    if not isinstance(payload, dict):
        return []
    if isinstance(payload.get("servList"), list):
        return [row for row in payload["servList"] if isinstance(row, dict)]
    if isinstance(payload.get("servList"), dict):
        return [payload["servList"]]
    body = payload.get("body") or payload.get("response", {}).get("body") or {}
    items = body.get("items") or payload.get("items") or []
    if isinstance(items, dict):
        item = items.get("item", items)
        if isinstance(item, list):
            return [row for row in item if isinstance(row, dict)]
        if isinstance(item, dict):
            return [item]
    if isinstance(items, list):
        return [row for row in items if isinstance(row, dict)]
    return []


def call_local_tourist_standard(path: Path, region_keyword: str) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return {"name": "local_national_tourist_standard", "ok": False, "error": exc.__class__.__name__}
    records = payload.get("records", [])
    if not isinstance(records, list):
        records = []
    matches = [
        row
        for row in records
        if isinstance(row, dict)
        and (
            region_keyword in str(row.get("소재지도로명주소", ""))
            or region_keyword in str(row.get("소재지지번주소", ""))
            or region_keyword in str(row.get("제공기관명", ""))
        )
    ]
    return {
        "name": "local_national_tourist_standard",
        "ok": True,
        "record_count": len(records),
        "region_match_count": len(matches),
        "sample": summarize_items(
            matches or records,
            ["관광지명", "관광지구분", "소재지도로명주소", "위도", "경도", "관광지소개"],
        ),
    }


def call_raw(name: str, url: str, params: dict[str, Any], timeout: float) -> dict[str, Any]:
    safe_params = {key: ("<set>" if key == "serviceKey" else value) for key, value in params.items()}
    try:
        response = requests.get(url, params=params, timeout=timeout)
        parsed = parse_response(response)
    except requests.RequestException as exc:
        return {"name": name, "ok": False, "error": exc.__class__.__name__, "params": safe_params}
    result: dict[str, Any] = {
        "name": name,
        "ok": response.ok,
        "http_status": response.status_code,
        "url": url,
        "params": safe_params,
        "format": parsed["format"],
    }
    payload = parsed.get("payload")
    if parsed["format"] in {"json", "xml"}:
        items = extract_json_items(payload)
        result["item_count"] = len(items)
        result["sample"] = summarize_items(items, list(items[0].keys())[:8]) if items else []
        result["result_code"] = find_first_key(payload, {"resultCode", "returnReasonCode", "headerCd"})
        result["result_message"] = find_first_key(payload, {"resultMsg", "resultMessage", "returnAuthMsg", "headerMsg"})
    else:
        result["text_prefix"] = parsed.get("text_prefix", "")
    return result


def find_first_key(payload: Any, keys: set[str]) -> Any:
    if isinstance(payload, dict):
        for key, value in payload.items():
            if key in keys:
                return value
            nested = find_first_key(value, keys)
            if nested is not None:
                return nested
    if isinstance(payload, list):
        for item in payload:
            nested = find_first_key(item, keys)
            if nested is not None:
                return nested
    return None


def call_tour_api(name: str, callback) -> dict[str, Any]:
    try:
        items = callback()
    except TourAPIError as exc:
        return {"name": name, "ok": False, "error": str(exc)}
    return {
        "name": name,
        "ok": True,
        "item_count": len(items),
        "sample": summarize_items(items, list(items[0].keys())[:8]) if items else [],
    }


def call_tour_api_by_signgu(
    name: str,
    signgu_codes: list[str],
    callback,
) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    errors: list[dict[str, str]] = []
    for signgu_cd in signgu_codes:
        try:
            items = callback(signgu_cd)
        except TourAPIError as exc:
            errors.append({"signgu_cd": signgu_cd, "error": str(exc)})
            continue
        rows.append(
            {
                "signgu_cd": signgu_cd,
                "item_count": len(items),
                "sample": summarize_items(items, list(items[0].keys())[:8]) if items else [],
            }
        )
    return {
        "name": name,
        "ok": not errors,
        "total_item_count": sum(row["item_count"] for row in rows),
        "by_signgu": rows,
        "errors": errors,
    }


def load_region_probe(path: Path, alias: str) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    single = payload.get("region_index", {}).get(alias)
    group = payload.get("region_group_index", {}).get(alias)
    if single:
        return {"area_cd": single["area_cd"], "signgu_codes": [single["signgu_cd"]], "kind": "single"}
    if group:
        return {"area_cd": group["area_cd"], "signgu_codes": group["signgu_codes"], "kind": "group"}
    raise KeyError(f"region alias not found: {alias}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Smoke test approved tourism-related external APIs with tiny requests.")
    parser.add_argument("--region", default="성남시")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--region-codes", type=Path, default=DEFAULT_REGION_CODES)
    parser.add_argument("--tourist-standard", type=Path, default=DEFAULT_TOURIST_STANDARD)
    parser.add_argument("--rows", type=int, default=3)
    parser.add_argument("--base-ym", default="202504")
    args = parser.parse_args()

    settings = Settings()
    if not settings.tour_api_service_key:
        raise SystemExit("TOUR_API_SERVICE_KEY is required for smoke collection.")

    api = TourAPIService(settings)
    region = load_region_probe(args.region_codes, args.region)
    signgu_cd = region["signgu_codes"][0] if region["signgu_codes"] else None
    wellness_signgu_cd = signgu_cd[-3:] if signgu_cd and len(signgu_cd) >= 3 else None

    results = [
        call_tour_api_by_signgu(
            "hub_area_based_list_by_signgu",
            region["signgu_codes"],
            lambda code: api.hub_area_based_list(
                region["area_cd"],
                signgu_cd=code,
                base_ym=args.base_ym,
                num_of_rows=args.rows,
            ),
        ),
        call_tour_api_by_signgu(
            "related_area_based_list_by_signgu",
            region["signgu_codes"],
            lambda code: api.related_area_based_list(
                region["area_cd"],
                signgu_cd=code,
                base_ym=args.base_ym,
                num_of_rows=args.rows,
            ),
        ),
        call_tour_api(
            "wellness_area_based_list_food",
            lambda: api.wellness_area_based_list(
                region["area_cd"],
                wellness_signgu_cd,
                content_type_id="39",
                num_of_rows=args.rows,
            ),
        ),
        call_raw(
            "demand_area_tar_service",
            "https://apis.data.go.kr/B551011/AreaTarResDemService/areaTarSvcDemList",
            {
                "serviceKey": settings.tour_api_service_key,
                "MobileOS": settings.tour_api_mobile_os,
                "MobileApp": settings.tour_api_mobile_app,
                "pageNo": 1,
                "numOfRows": args.rows,
                "baseYm": "202509",
                "areaCd": region["area_cd"],
                "signguCd": signgu_cd or "",
                "tarSvcDemIxCd": "1112",
                "_type": "json",
            },
            settings.tour_api_timeout,
        ),
        call_raw(
            "sbiz_administrative_dong_codes",
            "https://apis.data.go.kr/B553077/api/open/sdsc2/baroApi",
            {
                "serviceKey": settings.tour_api_service_key,
                "resId": "dong",
                "catId": "admi",
                "signguCd": signgu_cd or "",
                "type": "json",
            },
            settings.tour_api_timeout,
        ),
        call_raw(
            "sbiz_store_list_in_administrative_dong_food",
            "https://apis.data.go.kr/B553077/api/open/sdsc2/storeListInDong",
            {
                "serviceKey": settings.tour_api_service_key,
                "pageNo": 1,
                "numOfRows": args.rows,
                "type": "json",
                "divId": "adongCd",
                "key": "41131510",
                "indsLclsCd": "I2",
            },
            settings.tour_api_timeout,
        ),
        call_raw(
            "disabled_facility_list_seongnam",
            "https://apis.data.go.kr/B554287/DisabledPersonConvenientFacility/getDisConvFaclList",
            {
                "serviceKey": settings.tour_api_service_key,
                "siDoNm": "경기도",
                "cggNm": "성남시",
                "pageNo": 1,
                "numOfRows": args.rows,
            },
            settings.tour_api_timeout,
        ),
        call_raw(
            "disabled_facility_detail_sample",
            "https://apis.data.go.kr/B554287/DisabledPersonConvenientFacility/getFacInfoOpenApiJpEvalInfoList",
            {
                "serviceKey": settings.tour_api_service_key,
                "wfcltId": "4421010800-1-01490001",
            },
            settings.tour_api_timeout,
        ),
        call_local_tourist_standard(args.tourist_standard, args.region),
    ]
    payload = {
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "region": args.region,
        "region_probe": region,
        "base_ym": args.base_ym,
        "results": results,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

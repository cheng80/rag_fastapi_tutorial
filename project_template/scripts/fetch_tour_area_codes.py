from __future__ import annotations

from pathlib import Path
import json
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from app.core.config import get_settings  # noqa: E402
from app.services.tour_api_service import TourAPIService  # noqa: E402


OUTPUT_PATH = PROJECT_ROOT / "data" / "processed" / "tour_area_codes.json"


def _aliases(name: str) -> list[str]:
    aliases = [name]
    if len(name) > 2 and name[-1] in {"시", "군", "구"}:
        aliases.append(name[:-1])
    return aliases


def main() -> None:
    settings = get_settings()
    api = TourAPIService(settings)
    output = {
        "source": "한국관광공사 무장애 여행 정보 OpenAPI areaCode2",
        "area_codes": {},
        "region_index": {},
    }
    alias_candidates: dict[str, list[dict[str, str | None]]] = {}

    for area in api.area_codes(accessible=True):
        area_name = str(area.get("name") or "").strip()
        area_code = str(area.get("code") or "").strip()
        if not area_name or not area_code:
            continue

        sigungu_map = {}
        for sigungu in api.area_codes(area_code=area_code, accessible=True):
            sigungu_name = str(sigungu.get("name") or "").strip()
            sigungu_code = str(sigungu.get("code") or "").strip()
            if not sigungu_name or not sigungu_code:
                continue
            sigungu_map[sigungu_name] = sigungu_code
            for alias in _aliases(sigungu_name):
                alias_candidates.setdefault(alias, []).append(
                    {
                        "area_code": area_code,
                        "sigungu_code": sigungu_code,
                        "area_name": area_name,
                        "sigungu_name": sigungu_name,
                    }
                )

        output["area_codes"][area_name] = {
            "area_code": area_code,
            "sigungu": sigungu_map,
        }
        for alias in _aliases(area_name):
            alias_candidates.setdefault(alias, []).append(
                {
                    "area_code": area_code,
                    "sigungu_code": None,
                    "area_name": area_name,
                    "sigungu_name": None,
                }
            )

    output["ambiguous_region_aliases"] = {
        alias: candidates
        for alias, candidates in alias_candidates.items()
        if len({(candidate["area_code"], candidate["sigungu_code"]) for candidate in candidates}) > 1
    }
    output["region_index"] = {
        alias: candidates[0]
        for alias, candidates in alias_candidates.items()
        if alias not in output["ambiguous_region_aliases"]
    }

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"지역 코드 캐시 생성 완료: {OUTPUT_PATH.relative_to(PROJECT_ROOT)}")
    print(f"광역 {len(output['area_codes'])}개, 검색 별칭 {len(output['region_index'])}개")


if __name__ == "__main__":
    main()

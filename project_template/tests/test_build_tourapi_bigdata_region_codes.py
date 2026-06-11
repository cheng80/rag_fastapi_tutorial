from pathlib import Path

from openpyxl import Workbook

from scripts.build_tourapi_bigdata_region_codes import build_region_codes


def test_build_region_codes_adds_parent_city_group_aliases(tmp_path):
    workbook = Workbook()
    sheet = workbook.active
    sheet.append(["areaCd", "areaNm", "sigunguCd", "sigunguNm"])
    sheet.append([41, "경기도", 41131, "성남시 수정구"])
    sheet.append([41, "경기도", 41133, "성남시 중원구"])
    sheet.append([41, "경기도", 41135, "성남시 분당구"])
    path = tmp_path / "codes.xlsx"
    workbook.save(path)

    payload = build_region_codes(Path(path))

    assert payload["region_index"]["성남시 분당구"]["signgu_cd"] == "41135"
    assert payload["region_group_index"]["성남시"]["signgu_codes"] == ["41131", "41133", "41135"]
    assert payload["region_group_index"]["경기 성남시"]["area_cd"] == "41"

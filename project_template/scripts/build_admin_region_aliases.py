from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys
from urllib.request import urlretrieve
from zipfile import ZipFile

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))


DEFAULT_SOURCE_ZIP = PROJECT_ROOT / "data" / "source" / "admin_regions" / "jscode20260325.zip"
DEFAULT_OUTPUT_PATH = PROJECT_ROOT / "data" / "processed" / "admin_region_aliases.json"
TOUR_AREA_CODES_PATH = PROJECT_ROOT / "data" / "processed" / "tour_area_codes.json"
MOIS_SOURCE_URL = "https://www.mois.go.kr/cmm/fms/FileDown.do?atchFileId=FILE_00143539RhJP6z3&fileSn=1"

AREA_ALIASES = {
    "서울특별시": "서울",
    "부산광역시": "부산",
    "대구광역시": "대구",
    "인천광역시": "인천",
    "광주광역시": "광주",
    "대전광역시": "대전",
    "울산광역시": "울산",
    "세종특별자치시": "세종",
    "경기도": "경기",
    "강원도": "강원",
    "강원특별자치도": "강원",
    "충청북도": "충북",
    "충청남도": "충남",
    "전라북도": "전북",
    "전북특별자치도": "전북",
    "전라남도": "전남",
    "경상북도": "경북",
    "경상남도": "경남",
    "제주특별자치도": "제주",
}


def main() -> None:
    args = parse_args()
    source_zip = Path(args.source_zip)
    if args.download and not source_zip.exists():
        source_zip.parent.mkdir(parents=True, exist_ok=True)
        urlretrieve(args.source_url, source_zip)

    rows = read_kikmix(source_zip)
    payload = build_alias_payload(rows, load_tour_lookup(Path(args.tour_area_codes)))
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"행정동/법정동 매칭 데이터 생성 완료: {output_path.relative_to(PROJECT_ROOT)}")
    print(
        "rows={rows} sigungu_targets={targets} aliases={aliases}".format(
            rows=payload["summary"]["source_rows"],
            targets=payload["summary"]["sigungu_target_count"],
            aliases=payload["summary"]["alias_count"],
        )
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="행안부 주민등록주소코드로 지역명 매칭 데이터를 생성합니다.")
    parser.add_argument("--source-zip", default=str(DEFAULT_SOURCE_ZIP), help="행안부 jscode zip 경로입니다.")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT_PATH), help="생성할 JSON 경로입니다.")
    parser.add_argument("--tour-area-codes", default=str(TOUR_AREA_CODES_PATH), help="TourAPI 지역 코드 캐시 경로입니다.")
    parser.add_argument("--download", action="store_true", help="source zip이 없으면 행안부 게시판 첨부파일을 다운로드합니다.")
    parser.add_argument("--source-url", default=MOIS_SOURCE_URL, help="행안부 jscode zip 다운로드 URL입니다.")
    return parser.parse_args()


def read_kikmix(source_zip: Path) -> list[dict[str, str]]:
    if not source_zip.exists():
        raise FileNotFoundError(f"source zip을 찾을 수 없습니다: {source_zip}")
    with ZipFile(source_zip) as archive:
        kikmix_name = next(name for name in archive.namelist() if "/KIKmix." in name)
        with archive.open(kikmix_name) as file_obj:
            lines = file_obj.read().decode("cp949").splitlines()

    rows = []
    for line in lines[1:]:
        row = parse_kikmix_line(line)
        if not row:
            continue
        if row["deleted_date"]:
            continue
        if not row["sido_name"] or not row["sigungu_name"]:
            continue
        rows.append(row)
    return rows


def parse_kikmix_line(line: str) -> dict[str, str] | None:
    parts = line.split()
    if len(parts) < 7:
        return None
    deleted_date = parts[7] if len(parts) >= 8 else ""
    return {
        "admin_dong_code": parts[0],
        "sido_name": parts[1],
        "sigungu_name": canonical_sigungu_name(parts[2]),
        "admin_dong_name": parts[3],
        "legal_dong_code": parts[4],
        "legal_dong_name": parts[5],
        "created_date": parts[6],
        "deleted_date": deleted_date,
    }


def build_alias_payload(rows: list[dict[str, str]], tour_lookup: dict[tuple[str, str], dict[str, str]]) -> dict:
    candidate_by_key: dict[tuple[str, str, str, str, str], dict] = {}
    alias_map: dict[str, set[tuple[str, str, str, str, str]]] = {}
    dong_alias_candidates: dict[str, set[tuple[str, str, str, str, str]]] = {}
    sigungu_targets: dict[tuple[str, str], dict] = {}

    for row in rows:
        area_name = short_area_name(row["sido_name"])
        sigungu_name = canonical_sigungu_name(row["sigungu_name"])
        tour_codes = tour_lookup.get((area_name, sigungu_name), {})
        sigungu_key = (
            area_name,
            sigungu_name,
            "",
            "",
            "",
        )
        key = (
            area_name,
            sigungu_name,
            row["admin_dong_name"],
            row["legal_dong_name"],
            row["legal_dong_code"],
        )
        candidate_by_key.setdefault(
            sigungu_key,
            {
                "area_name": area_name,
                "sido_name": row["sido_name"],
                "sigungu_name": sigungu_name,
                "admin_dong_name": None,
                "legal_dong_name": None,
                "admin_dong_code": None,
                "legal_dong_code": None,
                "tour_area_code": tour_codes.get("area_code"),
                "tour_sigungu_code": tour_codes.get("sigungu_code"),
                "match_level": "sigungu",
            },
        )
        candidate_by_key.setdefault(
            key,
            {
                "area_name": area_name,
                "sido_name": row["sido_name"],
                "sigungu_name": sigungu_name,
                "admin_dong_name": row["admin_dong_name"] or None,
                "legal_dong_name": row["legal_dong_name"] or None,
                "admin_dong_code": row["admin_dong_code"],
                "legal_dong_code": row["legal_dong_code"],
                "tour_area_code": tour_codes.get("area_code"),
                "tour_sigungu_code": tour_codes.get("sigungu_code"),
                "match_level": "dong",
            },
        )
        sigungu_targets.setdefault(
            (area_name, sigungu_name),
            {
                "area_name": area_name,
                "sido_name": row["sido_name"],
                "sigungu_name": sigungu_name,
                "tour_area_code": tour_codes.get("area_code"),
                "tour_sigungu_code": tour_codes.get("sigungu_code"),
            },
        )

        for alias in sigungu_aliases(row["sido_name"], area_name, sigungu_name):
            add_alias(alias_map, alias, sigungu_key)

        for dong_name in {row["admin_dong_name"], row["legal_dong_name"]} - {""}:
            add_alias(dong_alias_candidates, dong_name, key)

    aliases = {
        alias: [candidate_by_key[key] for key in sorted(keys)]
        for alias, keys in sorted(alias_map.items())
        if alias and len(alias) >= 2
    }
    dong_aliases = {
        alias: [candidate_by_key[key] for key in sorted(keys)]
        for alias, keys in sorted(dong_alias_candidates.items())
        if alias and len(alias) >= 2
    }
    return {
        "source": "행정안전부 주민등록주소코드 jscode20260325.zip / KIKmix.20260325",
        "source_url": MOIS_SOURCE_URL,
        "generated_from": "data/source/admin_regions/jscode20260325.zip",
        "summary": {
            "source_rows": len(rows),
            "sigungu_target_count": len(sigungu_targets),
            "alias_count": len(aliases),
            "dong_alias_count": len(dong_aliases),
            "tourapi_matched_sigungu_count": sum(
                1 for target in sigungu_targets.values() if target.get("tour_sigungu_code")
            ),
        },
        "sigungu_targets": list(sigungu_targets.values()),
        "aliases": aliases,
        "dong_aliases": dong_aliases,
    }


def load_tour_lookup(path: Path) -> dict[tuple[str, str], dict[str, str]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    lookup = {}
    for area_name, area_info in payload.get("area_codes", {}).items():
        for sigungu_name, sigungu_code in area_info.get("sigungu", {}).items():
            lookup[(short_area_name(area_name), canonical_sigungu_name(sigungu_name))] = {
                "area_code": str(area_info["area_code"]),
                "sigungu_code": str(sigungu_code),
            }
    return lookup


def add_alias(target: dict[str, set[tuple[str, str, str, str, str]]], alias: str, key: tuple[str, str, str, str, str]) -> None:
    alias = normalize_alias(alias)
    if len(alias) < 2:
        return
    target.setdefault(alias, set()).add(key)


def sigungu_aliases(sido_name: str, area_name: str, sigungu_name: str) -> set[str]:
    return {
        sigungu_name,
        compact_name(sigungu_name),
        f"{area_name} {sigungu_name}",
        f"{area_name} {compact_name(sigungu_name)}",
        f"{sido_name} {sigungu_name}",
        f"{sido_name} {compact_name(sigungu_name)}",
    }


def short_area_name(name: str) -> str:
    return AREA_ALIASES.get(name, name)


def canonical_sigungu_name(name: str) -> str:
    name = normalize_alias(name)
    return re.sub(r"^(.+시)(.+구)$", r"\1 \2", name)


def compact_name(name: str) -> str:
    return normalize_alias(name).replace(" ", "")


def normalize_alias(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip())


if __name__ == "__main__":
    main()

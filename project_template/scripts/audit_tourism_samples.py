from __future__ import annotations

import argparse
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from app.services.tourism_card_codec import TourismCardMarkdownCodec
from app.schemas.tourism import TourismPlaceCard


DEFAULT_SAMPLE_DIR = PROJECT_ROOT / "data" / "raw" / "tourism_accessible"
DEFAULT_OUTPUT = PROJECT_ROOT / "data" / "generated" / "tour_api" / "tourism_sample_audit.md"
REQUIRED_CARD_FIELDS = ("content_id", "title", "recommendation_reason", "source_name")
SPECIFIC_REGION_PRIORITY = ["강릉", "서울", "부산"]


@dataclass(frozen=True)
class SampleAuditResult:
    total_files: int
    parsed_cards: int
    parse_failures: list[str]
    duplicate_content_ids: dict[str, list[str]]
    missing_required_fields: dict[str, list[str]]
    missing_address_files: list[str]
    missing_source_url_files: list[str]
    region_counts: Counter[str]
    accessibility_tag_counts: Counter[str]
    family_tag_counts: Counter[str]
    raw_field_counts: Counter[str]


def infer_region(path: Path) -> str:
    stem = path.stem
    if "_" not in stem:
        return "unknown"
    return stem.split("_", 1)[0]


def missing_required_fields(card: TourismPlaceCard) -> list[str]:
    missing: list[str] = []
    for field_name in REQUIRED_CARD_FIELDS:
        value = getattr(card, field_name)
        if not value:
            missing.append(field_name)
    return missing


def audit_samples(sample_dir: Path, codec: TourismCardMarkdownCodec | None = None) -> SampleAuditResult:
    codec = codec or TourismCardMarkdownCodec()
    markdown_files = sorted(sample_dir.glob("*.md"))
    parse_failures: list[str] = []
    missing_fields: dict[str, list[str]] = {}
    missing_address_files: list[str] = []
    missing_source_url_files: list[str] = []
    by_content_id: dict[str, list[str]] = defaultdict(list)
    region_counts: Counter[str] = Counter()
    accessibility_tag_counts: Counter[str] = Counter()
    family_tag_counts: Counter[str] = Counter()
    raw_field_counts: Counter[str] = Counter()

    for path in markdown_files:
        relative_path = path.relative_to(PROJECT_ROOT).as_posix() if path.is_relative_to(PROJECT_ROOT) else path.as_posix()
        card = codec.from_markdown(path.read_text(encoding="utf-8"))
        if card is None:
            parse_failures.append(relative_path)
            continue

        region_counts[infer_region(path)] += 1
        by_content_id[card.content_id].append(relative_path)
        if fields := missing_required_fields(card):
            missing_fields[relative_path] = fields
        if card.address is None:
            missing_address_files.append(relative_path)
        if card.source_url is None:
            missing_source_url_files.append(relative_path)
        accessibility_tag_counts.update(card.accessibility_tags)
        family_tag_counts.update(card.family_tags)
        raw_field_counts.update(card.raw_fields.keys())

    duplicates = {content_id: paths for content_id, paths in by_content_id.items() if len(paths) > 1}
    return SampleAuditResult(
        total_files=len(markdown_files),
        parsed_cards=len(markdown_files) - len(parse_failures),
        parse_failures=parse_failures,
        duplicate_content_ids=duplicates,
        missing_required_fields=missing_fields,
        missing_address_files=missing_address_files,
        missing_source_url_files=missing_source_url_files,
        region_counts=region_counts,
        accessibility_tag_counts=accessibility_tag_counts,
        family_tag_counts=family_tag_counts,
        raw_field_counts=raw_field_counts,
    )


def top_rows(counter: Counter[str], limit: int = 20) -> str:
    if not counter:
        return "- 없음\n"
    return "\n".join(f"| {name} | {count} |" for name, count in counter.most_common(limit)) + "\n"


def list_rows(items: list[str], limit: int = 30) -> str:
    if not items:
        return "- 없음\n"
    rows = [f"- `{item}`" for item in items[:limit]]
    if len(items) > limit:
        rows.append(f"- ... {len(items) - limit}개 더 있음")
    return "\n".join(rows) + "\n"


def render_report(result: SampleAuditResult) -> str:
    duplicate_files = sum(len(paths) for paths in result.duplicate_content_ids.values())
    return "\n".join(
        [
            "# 관광 fallback 샘플 감사 결과",
            "",
            "이 파일은 `scripts/audit_tourism_samples.py`로 생성하는 로컬 QA 산출물이다.",
            "",
            "## 요약",
            "",
            f"- Markdown 파일: {result.total_files}",
            f"- 파싱 성공 카드: {result.parsed_cards}",
            f"- 파싱 실패: {len(result.parse_failures)}",
            f"- 중복 콘텐츠ID: {len(result.duplicate_content_ids)}개 ID / {duplicate_files}개 파일",
            f"- 필수 필드 누락 파일: {len(result.missing_required_fields)}",
            f"- 주소 확인 필요 파일: {len(result.missing_address_files)}",
            f"- 출처 URL 확인 필요 파일: {len(result.missing_source_url_files)}",
            "",
            "## 지역별 파일 수",
            "",
            "| 지역 | 파일 수 |",
            "|---|---:|",
            top_rows(result.region_counts, limit=40).rstrip(),
            "",
            "## 접근성 태그 Top 20",
            "",
            "| 태그 | 카드 수 |",
            "|---|---:|",
            top_rows(result.accessibility_tag_counts, limit=20).rstrip(),
            "",
            "## 가족 태그 Top 20",
            "",
            "| 태그 | 카드 수 |",
            "|---|---:|",
            top_rows(result.family_tag_counts, limit=20).rstrip(),
            "",
            "## 편의정보 필드 Top 30",
            "",
            "| 필드 | 카드 수 |",
            "|---|---:|",
            top_rows(result.raw_field_counts, limit=30).rstrip(),
            "",
            "## 파싱 실패",
            "",
            list_rows(result.parse_failures).rstrip(),
            "",
            "## 중복 콘텐츠ID",
            "",
            render_duplicates(result.duplicate_content_ids).rstrip(),
            "",
            "## 필수 필드 누락",
            "",
            render_missing_fields(result.missing_required_fields).rstrip(),
            "",
        ]
    ) + "\n"


def render_duplicates(duplicates: dict[str, list[str]], limit: int = 30) -> str:
    if not duplicates:
        return "- 없음\n"
    rows: list[str] = []
    for index, (content_id, paths) in enumerate(sorted(duplicates.items()), start=1):
        if index > limit:
            rows.append(f"- ... {len(duplicates) - limit}개 ID 더 있음")
            break
        rows.append(f"- `{content_id}`: {', '.join(f'`{path}`' for path in paths)}")
    return "\n".join(rows) + "\n"


def render_missing_fields(missing_fields: dict[str, list[str]], limit: int = 30) -> str:
    if not missing_fields:
        return "- 없음\n"
    rows: list[str] = []
    for index, (path, fields) in enumerate(sorted(missing_fields.items()), start=1):
        if index > limit:
            rows.append(f"- ... {len(missing_fields) - limit}개 파일 더 있음")
            break
        rows.append(f"- `{path}`: {', '.join(fields)}")
    return "\n".join(rows) + "\n"


def select_duplicate_paths_to_remove(duplicate_content_ids: dict[str, list[str]]) -> list[str]:
    paths_to_remove: list[str] = []
    for paths in duplicate_content_ids.values():
        if len(paths) < 2:
            continue
        keep_path = choose_canonical_duplicate_path(paths)
        paths_to_remove.extend(path for path in paths if path != keep_path)
    return sorted(paths_to_remove)


def choose_canonical_duplicate_path(paths: list[str]) -> str:
    def score(path: str) -> tuple[int, int, str]:
        name = Path(path).name
        region = name.split("_", 1)[0] if "_" in name else ""
        priority = SPECIFIC_REGION_PRIORITY.index(region) if region in SPECIFIC_REGION_PRIORITY else len(SPECIFIC_REGION_PRIORITY)
        return (priority, len(region), path)

    return sorted(paths, key=score)[0]


def remove_duplicate_files(paths: list[str]) -> None:
    for path_text in paths:
        path = Path(path_text)
        if not path.is_absolute():
            path = PROJECT_ROOT / path
        path.unlink()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Audit local tourism fallback Markdown samples.")
    parser.add_argument("--sample-dir", type=Path, default=DEFAULT_SAMPLE_DIR)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--dedupe",
        action="store_true",
        help="Remove duplicate Markdown files after keeping the canonical file for each content ID.",
    )
    parser.add_argument(
        "--fail-on-duplicates",
        action="store_true",
        help="Exit with status 1 when duplicate content IDs are present.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    result = audit_samples(args.sample_dir)
    report = render_report(result)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(report, encoding="utf-8")
    print(f"files={result.total_files} parsed={result.parsed_cards} parse_failures={len(result.parse_failures)}")
    print(f"duplicates={len(result.duplicate_content_ids)} missing_required={len(result.missing_required_fields)}")
    print(f"wrote {args.output}")
    if args.dedupe and result.duplicate_content_ids:
        paths_to_remove = select_duplicate_paths_to_remove(result.duplicate_content_ids)
        remove_duplicate_files(paths_to_remove)
        print(f"removed_duplicate_files={len(paths_to_remove)}")
    if args.fail_on_duplicates and result.duplicate_content_ids:
        raise SystemExit(1)


if __name__ == "__main__":
    main()

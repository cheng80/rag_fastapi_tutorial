from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.core.config import Settings  # noqa: E402
from app.services.tour_api_usage import TourAPIUsageTracker  # noqa: E402


RAW_SAMPLE_DIR = PROJECT_ROOT / "data" / "raw" / "tourism_accessible"
GENERATED_TOUR_API_DIR = PROJECT_ROOT / "data" / "generated" / "tour_api"
LIVE_MARKDOWN_DIR = GENERATED_TOUR_API_DIR / "live_markdown"


def infer_counts_from_artifacts(date: str) -> dict[str, int]:
    start = datetime.strptime(date, "%Y-%m-%d")
    area_based_count = _count_files_modified_since(GENERATED_TOUR_API_DIR, "*_area_based_raw.json", start)
    raw_card_count = _count_files_modified_since(RAW_SAMPLE_DIR, "*.md", start)
    live_card_count = _count_files_modified_since(LIVE_MARKDOWN_DIR, "*.md", start)
    detail_count = raw_card_count + live_card_count
    return {
        "areaBasedList2": area_based_count,
        "detailCommon2": detail_count,
        "detailWithTour2": detail_count,
    }


def _count_files_modified_since(directory: Path, pattern: str, start: datetime) -> int:
    if not directory.exists():
        return 0
    start_ts = start.timestamp()
    return sum(1 for path in directory.glob(pattern) if path.is_file() and path.stat().st_mtime >= start_ts)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Bootstrap today's TourAPI usage log from generated artifacts.")
    parser.add_argument("--date", default=datetime.now().strftime("%Y-%m-%d"), help="Usage date in YYYY-MM-DD format.")
    parser.add_argument("--dry-run", action="store_true", help="Print inferred counts without writing the usage log.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    settings = Settings()
    tracker = TourAPIUsageTracker(
        settings.resolved_tour_api_usage_log_path,
        daily_endpoint_limit=settings.tour_api_daily_endpoint_limit,
    )
    inferred = infer_counts_from_artifacts(args.date)
    if args.dry_run:
        print({"date": args.date, "inferred_counts": inferred, "current_counts": tracker.snapshot(args.date).counts})
        return
    snapshot = tracker.set_minimum_counts(inferred, date=args.date)
    print({"date": snapshot.date, "limit": snapshot.limit, "counts": snapshot.counts})


if __name__ == "__main__":
    main()

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path
import sqlite3
import sys
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.core.config import Settings  # noqa: E402


TABLE_NAME = "tour_api_response_cache"


def summarize_cache(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"path": str(path), "exists": False, "total_rows": 0, "operations": {}}
    with sqlite3.connect(path) as conn:
        if not _table_exists(conn):
            return {"path": str(path), "exists": True, "total_rows": 0, "operations": {}}
        rows = conn.execute(
            f"""
            SELECT operation, COUNT(*), MIN(fetched_at), MAX(fetched_at), MIN(expires_at), MAX(expires_at)
            FROM {TABLE_NAME}
            GROUP BY operation
            ORDER BY operation
            """
        ).fetchall()
        total_rows = conn.execute(f"SELECT COUNT(*) FROM {TABLE_NAME}").fetchone()[0]
    return {
        "path": str(path),
        "exists": True,
        "total_rows": int(total_rows),
        "operations": {
            operation: {
                "rows": int(count),
                "first_fetched_at": first_fetched_at,
                "last_fetched_at": last_fetched_at,
                "first_expires_at": first_expires_at,
                "last_expires_at": last_expires_at,
            }
            for operation, count, first_fetched_at, last_fetched_at, first_expires_at, last_expires_at in rows
        },
    }


def clear_cache(path: Path, operation: str | None = None, expired_only: bool = False, now: datetime | None = None) -> int:
    if not path.exists():
        return 0
    with sqlite3.connect(path) as conn:
        if not _table_exists(conn):
            return 0
        where_parts: list[str] = []
        params: list[Any] = []
        if operation:
            where_parts.append("operation = ?")
            params.append(operation)
        if expired_only:
            where_parts.append("expires_at <= ?")
            params.append((now or datetime.now(timezone.utc)).isoformat())
        where_clause = f" WHERE {' AND '.join(where_parts)}" if where_parts else ""
        before = conn.execute(f"SELECT COUNT(*) FROM {TABLE_NAME}{where_clause}", params).fetchone()[0]
        conn.execute(f"DELETE FROM {TABLE_NAME}{where_clause}", params)
    return int(before)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Inspect or clear the local TourAPI raw response cache.")
    parser.add_argument("--path", type=Path, default=None, help="Override cache path. Defaults to Settings.")
    parser.add_argument("--clear", action="store_true", help="Delete matching cache rows instead of only summarizing.")
    parser.add_argument("--operation", default=None, help="Limit summary/delete to one TourAPI operation.")
    parser.add_argument("--expired-only", action="store_true", help="Delete only expired rows. Requires --clear.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    settings = Settings()
    path = args.path or settings.resolved_tour_api_response_cache_path
    if args.expired_only and not args.clear:
        raise SystemExit("--expired-only requires --clear")
    if args.clear:
        deleted = clear_cache(path, operation=args.operation, expired_only=args.expired_only)
        print({"path": str(path), "deleted_rows": deleted, "operation": args.operation, "expired_only": args.expired_only})
        return
    summary = summarize_cache(path)
    if args.operation and summary["operations"]:
        summary["operations"] = {
            operation: detail for operation, detail in summary["operations"].items() if operation == args.operation
        }
        summary["total_rows"] = sum(detail["rows"] for detail in summary["operations"].values())
    print(summary)


def _table_exists(conn: sqlite3.Connection) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
        (TABLE_NAME,),
    ).fetchone()
    return row is not None


if __name__ == "__main__":
    main()

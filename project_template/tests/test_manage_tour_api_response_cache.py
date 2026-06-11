from datetime import datetime, timezone
import sqlite3

from scripts.manage_tour_api_response_cache import clear_cache, summarize_cache


def test_summarize_cache_reports_rows_by_operation(tmp_path):
    cache_path = tmp_path / "cache.sqlite3"
    _create_cache(cache_path)
    _insert_row(cache_path, operation="areaBasedList2", cache_key="a")
    _insert_row(cache_path, operation="detailCommon2", cache_key="b")
    _insert_row(cache_path, operation="detailCommon2", cache_key="c")

    summary = summarize_cache(cache_path)

    assert summary["exists"] is True
    assert summary["total_rows"] == 3
    assert summary["operations"]["areaBasedList2"]["rows"] == 1
    assert summary["operations"]["detailCommon2"]["rows"] == 2


def test_clear_cache_can_delete_expired_rows_only(tmp_path):
    cache_path = tmp_path / "cache.sqlite3"
    _create_cache(cache_path)
    _insert_row(cache_path, operation="areaBasedList2", cache_key="expired", expires_at="2026-05-01T00:00:00+00:00")
    _insert_row(cache_path, operation="areaBasedList2", cache_key="fresh", expires_at="2026-06-01T00:00:00+00:00")

    deleted = clear_cache(
        cache_path,
        expired_only=True,
        now=datetime(2026, 5, 26, tzinfo=timezone.utc),
    )

    assert deleted == 1
    summary = summarize_cache(cache_path)
    assert summary["total_rows"] == 1


def test_clear_cache_can_limit_to_operation(tmp_path):
    cache_path = tmp_path / "cache.sqlite3"
    _create_cache(cache_path)
    _insert_row(cache_path, operation="areaBasedList2", cache_key="a")
    _insert_row(cache_path, operation="detailCommon2", cache_key="b")

    deleted = clear_cache(cache_path, operation="detailCommon2")

    assert deleted == 1
    summary = summarize_cache(cache_path)
    assert summary["total_rows"] == 1
    assert "areaBasedList2" in summary["operations"]


def _create_cache(path):
    with sqlite3.connect(path) as conn:
        conn.execute(
            """
            CREATE TABLE tour_api_response_cache (
                cache_key TEXT PRIMARY KEY,
                operation TEXT NOT NULL,
                params_json TEXT NOT NULL,
                response_json TEXT,
                status_code INTEGER,
                error_message TEXT,
                fetched_at TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                source_version TEXT NOT NULL
            )
            """
        )


def _insert_row(path, operation, cache_key, expires_at="2026-06-01T00:00:00+00:00"):
    with sqlite3.connect(path) as conn:
        conn.execute(
            """
            INSERT INTO tour_api_response_cache (
                cache_key,
                operation,
                params_json,
                response_json,
                status_code,
                error_message,
                fetched_at,
                expires_at,
                source_version
            )
            VALUES (?, ?, '{}', '{}', 200, NULL, '2026-05-01T00:00:00+00:00', ?, 'test')
            """,
            (cache_key, operation, expires_at),
        )

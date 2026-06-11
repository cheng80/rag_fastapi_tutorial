from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import sqlite3
from typing import Any


SOURCE_VERSION = "tour_api_response_cache_v1"


@dataclass(frozen=True)
class TourAPIResponseCacheEntry:
    response_json: dict[str, Any] | None
    status_code: int | None
    error_message: str | None


class TourAPIResponseCache:
    def __init__(self, path: Path):
        self.path = path

    def get(self, operation: str, base_url: str, params: dict[str, Any]) -> TourAPIResponseCacheEntry | None:
        self._ensure_schema()
        cache_key = self.cache_key(operation, base_url, params)
        now = self._now().isoformat()
        with sqlite3.connect(self.path) as conn:
            row = conn.execute(
                """
                SELECT response_json, status_code, error_message
                FROM tour_api_response_cache
                WHERE cache_key = ? AND expires_at > ?
                """,
                (cache_key, now),
            ).fetchone()
        if row is None:
            return None
        response_json, status_code, error_message = row
        return TourAPIResponseCacheEntry(
            response_json=json.loads(response_json) if response_json else None,
            status_code=int(status_code) if status_code is not None else None,
            error_message=str(error_message) if error_message else None,
        )

    def put(
        self,
        operation: str,
        base_url: str,
        params: dict[str, Any],
        response_json: dict[str, Any] | None,
        status_code: int | None,
        error_message: str | None = None,
    ) -> None:
        self._ensure_schema()
        now = self._now()
        expires_at = now + self.ttl_for(operation, is_error=bool(error_message))
        params_json = self._params_json(params)
        with sqlite3.connect(self.path) as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO tour_api_response_cache (
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
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    self.cache_key(operation, base_url, params),
                    operation,
                    params_json,
                    json.dumps(response_json, ensure_ascii=False, sort_keys=True) if response_json is not None else None,
                    status_code,
                    error_message,
                    now.isoformat(),
                    expires_at.isoformat(),
                    SOURCE_VERSION,
                ),
            )

    @staticmethod
    def cache_key(operation: str, base_url: str, params: dict[str, Any]) -> str:
        payload = {
            "operation": operation,
            "base_url": base_url.rstrip("/"),
            "params": TourAPIResponseCache._sanitized_params(params),
            "source_version": SOURCE_VERSION,
        }
        raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    @staticmethod
    def ttl_for(operation: str, is_error: bool = False) -> timedelta:
        if is_error:
            return timedelta(days=1)
        ttl_days = {
            "areaCode2": 30,
            "areaBasedList2": 7,
            "searchKeyword2": 7,
            "detailCommon2": 30,
            "detailWithTour2": 30,
        }.get(operation, 0)
        return timedelta(days=ttl_days)

    @classmethod
    def is_cacheable(cls, operation: str) -> bool:
        return cls.ttl_for(operation) > timedelta(0)

    def _ensure_schema(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS tour_api_response_cache (
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
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_tour_api_response_cache_operation_expires
                ON tour_api_response_cache(operation, expires_at)
                """
            )

    @staticmethod
    def _now() -> datetime:
        return datetime.now(timezone.utc)

    @staticmethod
    def _params_json(params: dict[str, Any]) -> str:
        return json.dumps(TourAPIResponseCache._sanitized_params(params), ensure_ascii=False, sort_keys=True)

    @staticmethod
    def _sanitized_params(params: dict[str, Any]) -> dict[str, Any]:
        return {str(key): value for key, value in params.items() if str(key) != "serviceKey"}

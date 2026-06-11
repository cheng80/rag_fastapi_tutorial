from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import json
from pathlib import Path
from typing import Any


class TourAPIQuotaExceeded(RuntimeError):
    pass


@dataclass(frozen=True)
class TourAPIUsageSnapshot:
    date: str
    limit: int
    counts: dict[str, int]

    def remaining(self, operation: str) -> int:
        return max(self.limit - self.counts.get(operation, 0), 0)


class TourAPIUsageTracker:
    def __init__(self, path: Path, daily_endpoint_limit: int = 1000):
        self.path = path
        self.daily_endpoint_limit = daily_endpoint_limit

    def today(self) -> str:
        return datetime.now().strftime("%Y-%m-%d")

    def snapshot(self, date: str | None = None) -> TourAPIUsageSnapshot:
        target_date = date or self.today()
        return TourAPIUsageSnapshot(
            date=target_date,
            limit=self.daily_endpoint_limit,
            counts=self._read_counts(target_date),
        )

    def assert_available(self, operation: str, amount: int = 1, date: str | None = None) -> None:
        snapshot = self.snapshot(date)
        used = snapshot.counts.get(operation, 0)
        if used + amount > self.daily_endpoint_limit:
            raise TourAPIQuotaExceeded(
                f"{operation} daily quota exceeded: used={used}, requested={amount}, limit={self.daily_endpoint_limit}, date={snapshot.date}"
            )

    def record(self, operation: str, amount: int = 1, date: str | None = None) -> TourAPIUsageSnapshot:
        target_date = date or self.today()
        self.assert_available(operation, amount=amount, date=target_date)
        payload = self._read_payload()
        dates = payload.setdefault("dates", {})
        day = dates.setdefault(target_date, {})
        endpoints = day.setdefault("endpoints", {})
        endpoints[operation] = int(endpoints.get(operation, 0)) + amount
        self._write_payload(payload)
        return self.snapshot(target_date)

    def assert_estimated_available(self, estimated_counts: dict[str, int], date: str | None = None) -> None:
        for operation, amount in estimated_counts.items():
            self.assert_available(operation, amount=amount, date=date)

    def set_minimum_counts(self, minimum_counts: dict[str, int], date: str | None = None) -> TourAPIUsageSnapshot:
        target_date = date or self.today()
        payload = self._read_payload()
        dates = payload.setdefault("dates", {})
        day = dates.setdefault(target_date, {})
        endpoints = day.setdefault("endpoints", {})
        for operation, count in minimum_counts.items():
            endpoints[operation] = max(int(endpoints.get(operation, 0)), int(count))
        self._write_payload(payload)
        return self.snapshot(target_date)

    def _read_counts(self, date: str) -> dict[str, int]:
        payload = self._read_payload()
        endpoints = payload.get("dates", {}).get(date, {}).get("endpoints", {})
        if not isinstance(endpoints, dict):
            return {}
        return {str(operation): int(count) for operation, count in endpoints.items()}

    def _read_payload(self) -> dict[str, Any]:
        if not self.path.exists():
            return {"dates": {}}
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {"dates": {}}
        if not isinstance(payload, dict):
            return {"dates": {}}
        if not isinstance(payload.get("dates"), dict):
            payload["dates"] = {}
        return payload

    def _write_payload(self, payload: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

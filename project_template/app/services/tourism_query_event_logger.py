from __future__ import annotations

from datetime import datetime
import hashlib
import json
import logging

from app.core.config import Settings
from app.schemas.tourism import TourismChatResponse

logger = logging.getLogger(__name__)


class TourismQueryEventLogger:
    def __init__(self, settings: Settings):
        self.settings = settings

    def log(
        self,
        *,
        message: str,
        session_id: str | None,
        query: dict,
        response: TourismChatResponse,
        live_api_called: bool,
    ) -> None:
        if not self.settings.tourism_query_event_log_enabled:
            return

        event = {
            "timestamp": datetime.now().astimezone().isoformat(),
            "session_id": session_id,
            "message": message if self.settings.tourism_query_event_log_include_message else None,
            "message_hash": hashlib.sha256(message.encode("utf-8")).hexdigest(),
            "region": query.get("region"),
            "area_name": query.get("area_name"),
            "sigungu_name": query.get("sigungu_name"),
            "legacy_region": query.get("legacy_region"),
            "legacy_region_replacement": query.get("legacy_region_replacement"),
            "conditions": query.get("conditions") or [],
            "preferences": query.get("preferences") or [],
            "excluded_preferences": query.get("excluded_preferences") or [],
            "ml_intent": query.get("ml_intent"),
            "ml_intent_confidence": query.get("ml_intent_confidence"),
            "allow_region_expansion": bool(query.get("allow_region_expansion")),
            "lookup_mode": response.lookup_mode,
            "degraded": response.degraded,
            "live_api_called": live_api_called,
            "reasoning_assist_used": response.reasoning_assist_used,
            "reasoning_assist_notes": response.reasoning_assist_notes,
            "card_count": len(response.cards),
            "cards": [
                {
                    "rank": index,
                    "content_id": card.content_id,
                    "title": card.title,
                    "source_name": card.source_name,
                }
                for index, card in enumerate(response.cards, start=1)
            ],
            "warnings": response.warnings,
        }

        try:
            path = self.settings.resolved_tourism_query_event_log_path
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("a", encoding="utf-8") as file:
                file.write(json.dumps(event, ensure_ascii=False, separators=(",", ":")) + "\n")
        except OSError as exc:
            logger.warning("관광 질문 이벤트 로그 저장 실패: %s", exc.__class__.__name__)

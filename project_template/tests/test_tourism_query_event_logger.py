import json

from app.core.config import Settings
from app.schemas.tourism import TourismChatResponse, TourismPlaceCard
from app.services.tourism_query_event_logger import TourismQueryEventLogger


def test_tourism_query_event_logger_writes_jsonl_without_raw_message(tmp_path):
    log_path = tmp_path / "events.jsonl"
    logger = TourismQueryEventLogger(
        Settings(
            tourism_query_event_log_path=log_path,
            tourism_query_event_log_enabled=True,
            tourism_query_event_log_include_message=False,
        )
    )
    response = TourismChatResponse(
        answer="서울 기준으로 1곳을 추천합니다.",
        lookup_mode="indexed",
        cards=[
            TourismPlaceCard(
                content_id="2456536",
                title="강남 마이스 관광특구",
                recommendation_reason="휠체어 접근 정보가 확인되었습니다.",
                accessibility_tags=["휠체어 접근"],
            )
        ],
        warnings=[],
    )

    logger.log(
        message="서울 강남구에서 휠체어 관광지 추천해줘",
        session_id="session-1",
        query={
            "region": "강남구",
            "area_name": "서울",
            "sigungu_name": "강남구",
            "conditions": ["휠체어"],
            "allow_region_expansion": False,
        },
        response=response,
        live_api_called=False,
    )

    payload = json.loads(log_path.read_text(encoding="utf-8"))
    assert payload["message"] is None
    assert payload["message_hash"]
    assert payload["region"] == "강남구"
    assert payload["lookup_mode"] == "indexed"
    assert payload["live_api_called"] is False
    assert payload["cards"] == [
        {
            "rank": 1,
            "content_id": "2456536",
            "title": "강남 마이스 관광특구",
            "source_name": "한국관광공사 무장애 여행 정보",
        }
    ]


def test_tourism_query_event_logger_can_include_raw_message(tmp_path):
    log_path = tmp_path / "events.jsonl"
    logger = TourismQueryEventLogger(
        Settings(
            tourism_query_event_log_path=log_path,
            tourism_query_event_log_enabled=True,
            tourism_query_event_log_include_message=True,
        )
    )

    logger.log(
        message="부산 중구 휠체어 관광지",
        session_id=None,
        query={"region": "부산 중구"},
        response=TourismChatResponse(answer="없음", lookup_mode="unknown"),
        live_api_called=True,
    )

    payload = json.loads(log_path.read_text(encoding="utf-8"))
    assert payload["message"] == "부산 중구 휠체어 관광지"
    assert payload["live_api_called"] is True

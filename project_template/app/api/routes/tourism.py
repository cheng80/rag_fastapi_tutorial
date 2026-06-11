import json
import logging
from typing import Any

from fastapi import APIRouter, HTTPException, Request

from ...core.config import PROJECT_ROOT
from ...schemas.tourism import TourismChatRequest, TourismChatResponse
from ..deps import get_tourism_chat_service

router = APIRouter()
logger = logging.getLogger(__name__)


AREA_NAME_ALIASES = {
    "서울특별시": "서울",
    "부산광역시": "부산",
    "대구광역시": "대구",
    "인천광역시": "인천",
    "광주광역시": "광주",
    "대전광역시": "대전",
    "울산광역시": "울산",
    "세종특별자치시": "세종",
    "경기도": "경기",
    "강원특별자치도": "강원",
    "충청북도": "충북",
    "충청남도": "충남",
    "전북특별자치도": "전북",
    "전라남도": "전남",
    "경상북도": "경북",
    "경상남도": "경남",
    "제주특별자치도": "제주",
}


@router.post("/chat", response_model=TourismChatResponse)
def tourism_chat(chat_request: TourismChatRequest, request: Request) -> TourismChatResponse:
    if not chat_request.message.strip():
        raise HTTPException(status_code=400, detail="message는 비어 있을 수 없습니다.")

    try:
        service_provider = request.app.dependency_overrides.get(
            get_tourism_chat_service,
            get_tourism_chat_service,
        )
        tourism_chat_service = service_provider()
        return tourism_chat_service.answer(
            message=chat_request.message,
            session_id=chat_request.session_id,
        )
    except Exception as exc:
        logger.exception("관광 챗봇 응답 생성 실패")
        raise HTTPException(
            status_code=500,
            detail={
                "code": "TOURISM_CHAT_FAILED",
                "message": "관광 상담 응답을 만드는 중 문제가 발생했습니다. 잠시 후 다시 시도해 주세요.",
            },
        ) from exc


@router.get("/regions")
def tourism_regions() -> dict[str, Any]:
    path = PROJECT_ROOT / "data" / "processed" / "tour_area_codes.json"
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="지역 코드 캐시를 찾을 수 없습니다.") from exc
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=500, detail="지역 코드 캐시를 읽을 수 없습니다.") from exc

    areas = []
    for area_name, meta in payload.get("area_codes", {}).items():
        sigungu = list((meta.get("sigungu") or {}).keys())
        areas.append(
            {
                "name": AREA_NAME_ALIASES.get(area_name, area_name),
                "source_name": area_name,
                "sigungu": sigungu,
            }
        )
    return {"areas": areas}

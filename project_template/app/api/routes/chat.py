from fastapi import APIRouter, HTTPException, Request

from ...schemas.chat import ChatRequest, ChatResponse
from ..deps import get_rag_service

router = APIRouter()


@router.post("", response_model=ChatResponse)
def chat(chat_request: ChatRequest, request: Request) -> ChatResponse:
    if not chat_request.message.strip():
        raise HTTPException(status_code=400, detail="message는 비어 있을 수 없습니다.")

    try:
        service_provider = request.app.dependency_overrides.get(get_rag_service, get_rag_service)
        rag_service = service_provider()
        return rag_service.answer(
            question=chat_request.message,
            session_id=chat_request.session_id,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, description="사용자 질문")
    session_id: str | None = Field(default=None, description="선택 대화 세션 ID")


class Source(BaseModel):
    source: str
    page: int | None = None
    chunk_id: str
    chunk_index: int | None = None
    distance: float | None = None


class ChatResponse(BaseModel):
    answer: str
    sources: list[Source] = Field(default_factory=list)

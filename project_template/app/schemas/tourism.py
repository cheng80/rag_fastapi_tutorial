from pydantic import BaseModel, Field

from app.schemas.chat import Source


class AccessibilityInfo(BaseModel):
    wheelchair: str | None = Field(default=None, description="휠체어 접근/대여/동선 정보")
    parking: str | None = Field(default=None, description="장애인 주차 또는 일반 주차 정보")
    restroom: str | None = Field(default=None, description="장애인 화장실 또는 화장실 정보")
    stroller: str | None = Field(default=None, description="유모차 대여/이동 정보")
    nursing_room: str | None = Field(default=None, description="수유실 정보")
    elevator: str | None = Field(default=None, description="엘리베이터 또는 승강 설비 정보")
    route: str | None = Field(default=None, description="접근로/관람 동선 정보")


class TourismPlaceCard(BaseModel):
    content_id: str
    title: str
    address: str | None = None
    image_url: str | None = None
    tel: str | None = None
    map_x: float | None = None
    map_y: float | None = None
    recommendation_reason: str
    accessibility: AccessibilityInfo = Field(default_factory=AccessibilityInfo)
    family_tags: list[str] = Field(default_factory=list)
    accessibility_tags: list[str] = Field(default_factory=list)
    source_name: str = "한국관광공사 무장애 여행 정보"
    source_url: str | None = None
    raw_fields: dict[str, str] = Field(default_factory=dict)


class TourismChatRequest(BaseModel):
    message: str = Field(..., min_length=1, description="사용자 관광 상담 질문")
    session_id: str | None = Field(default=None, description="선택 대화 세션 ID")


class TourismChatResponse(BaseModel):
    answer: str
    cards: list[TourismPlaceCard] = Field(default_factory=list)
    sources: list[Source] = Field(default_factory=list)
    lookup_mode: str = Field(default="unknown", description="응답 상태 식별자")
    degraded: bool = Field(default=False, description="일부 자료 확인 실패로 먼저 확인된 자료를 사용했는지 여부")
    warnings: list[str] = Field(default_factory=list, description="응답 품질이나 설정 상태에 대한 진단 메시지")
    suggested_messages: list[str] = Field(default_factory=list, description="지역 선택 등 후속 질문 후보")
    live_update_pending: bool = Field(default=False, description="늦게 도착할 최신 추천 결과가 있는지 여부")
    live_update_id: str | None = Field(default=None, description="세션별 최신 추천 결과 식별자")
    reasoning_assist_used: bool = Field(default=False, description="복합 조건 확인을 사용했는지 여부")
    reasoning_assist_notes: list[str] = Field(default_factory=list, description="복합 조건 확인에서 남긴 부족/확인 필요 메모")

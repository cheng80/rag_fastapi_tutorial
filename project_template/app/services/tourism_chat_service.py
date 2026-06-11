from __future__ import annotations

from concurrent.futures import Future, ThreadPoolExecutor, TimeoutError as FutureTimeoutError
from dataclasses import dataclass, field
import json
import logging
import re
import threading
import time
from typing import Any

from app.core.config import Settings
from app.schemas.chat import Source
from app.schemas.tourism import TourismChatResponse, TourismPlaceCard
from app.services.llm_service import LLMService
from app.services.retriever import Retriever
from app.services.tour_api_service import TourAPIError, TourAPIService
from app.services.tourism_card_codec import TourismCardMarkdownCodec
from app.services.tourism_normalizer import TourismNormalizer
from app.services.tourism_query_event_logger import TourismQueryEventLogger
from app.services.tourism_query_service import FEATURE_KEYWORDS, PREFERENCE_KEYWORDS, TourismQueryService

logger = logging.getLogger(__name__)

REASONING_ASSIST_KEYWORDS = [
    "오래 걷",
    "걷기 힘",
    "비 오",
    "비가",
    "붐비지",
    "조용",
    "실내",
    "쉬기 좋은",
    "아이랑",
    "아이와",
    "가족이 같이",
    "멀지 않은",
    "가까운",
    "동선",
]
DEFAULT_CARD_LIMIT = 5
MORE_CARD_KEYWORDS = ["더 보기", "더보기", "더 많이", "더 보여", "전체", "전부", "20곳", "20개"]
LIVE_TOP_UP_KEYWORDS = ["최신 추천 더 확인하기", "최신 정보 더 찾기", "최신 정보", "live 확인", "라이브 확인", "TourAPI 확인"]
LIVE_UPDATE_ACCEPT_KEYWORDS = [
    "업데이트 보기",
    "업데이트 반영",
    "최신 결과 보기",
    "최신 결과 보여",
    "최신 정보 보기",
    "최신 정보 반영",
    "반영해",
]
STROLLER_MOBILITY_EVIDENCE = [
    "휠체어",
    "무장애",
    "장애인",
    "턱이 없어",
    "경사로",
    "출입통로",
    "접근로",
    "엘리베이터",
    "승강기",
    "무단차",
    "평탄",
]
STROLLER_FAMILY_EVIDENCE = [
    "유모차",
    "유아차",
    "수유실",
    "영유아",
    "기저귀",
    "어린이",
    "아이",
    "유아",
    "가족",
    "유아용 의자",
]
CONDITION_EVIDENCE_KEYWORDS = {
    "휠체어": ["휠체어", "무장애", "장애인", "턱이 없어", "경사로", "출입통로"],
    "유모차": [*STROLLER_FAMILY_EVIDENCE, *STROLLER_MOBILITY_EVIDENCE],
    "고령자": [
        "고령자",
        "어르신",
        "노인",
        "노약자",
        "쉬움",
        "의자",
        "휴식",
        "휠체어",
        "장애인",
        "무단차",
        "경사로",
        "평탄",
        "출입통로",
        "접근로",
        "대중교통",
        "화장실",
        "엘리베이터",
        "승강기",
    ],
    "주차": ["주차", "주차장"],
    "화장실": ["화장실", "기저귀", "보호의자"],
    "접근로": ["접근로", "동선", "경사로", "턱이 없어", "출입통로"],
    "대중교통": ["대중교통", "버스", "지하철"],
    "엘리베이터": ["엘리베이터", "승강기"],
    "보조견": ["보조견", "안내견"],
    "시각장애": [
        "점자",
        "점자블록",
        "촉지도",
        "촉지 안내도",
        "촉지안내도",
        "촉지 안내판",
        "촉지안내판",
        "촉지판",
        "촉지",
        "음성안내",
        "오디오가이드",
        "점자홍보물",
    ],
    "청각장애": ["청각장애", "수어", "수화", "자막", "문자안내"],
}


@dataclass
class LiveUpdateJob:
    update_id: str
    session_id: str
    message: str
    query: dict[str, Any]
    future: Future
    started_at: float
    background_timeout_seconds: float
    generation: int
    status: str = "running"
    cards: list[TourismPlaceCard] = field(default_factory=list)
    degraded: bool = False
    api_called: bool = False


@dataclass
class LiveUpdateConsumeResult:
    status: str
    job: LiveUpdateJob
CONDITION_RAW_FIELD_KEYS = {
    "휠체어": ["휠체어"],
    "유모차": ["유모차", "수유실", "영유아 가족 편의", "유아용 의자", "휠체어", "출입통로", "접근로", "엘리베이터", "대중교통"],
    "고령자": ["기타 장애인 편의", "영유아 가족 편의"],
    "주차": ["주차"],
    "화장실": ["화장실"],
    "접근로": ["접근로", "출입통로", "대중교통"],
    "대중교통": ["대중교통"],
    "엘리베이터": ["엘리베이터"],
    "보조견": ["보조견"],
    "시각장애": ["점자블록", "오디오가이드", "촉지도", "촉지 안내도", "촉지 안내판", "촉지판", "음성안내", "점자홍보물", "안내시스템"],
    "청각장애": ["청각장애", "자막", "수어", "안내시설"],
}
PREFERENCE_EVIDENCE_KEYWORDS = {
    "실내": ["실내", "박물관", "전시관", "미술관", "체험관", "기념관", "문화관"],
    "박물관_전시": ["박물관", "전시관", "전시", "미술관", "체험관", "기념관", "문화관"],
    "시장_먹거리": [
        "시장",
        "먹거리",
        "맛집",
        "음식",
        "식당",
        "먹자골목",
        "음식점",
        "게장",
        "돈가스",
        "국시",
        "국수",
        "백숙",
        "막국수",
        "오리",
        "칼국수",
        "해장",
        "구이",
        "분식",
        "한식",
        "중식",
        "양식",
        "갈비",
        "고기",
    ],
    "공원_산책": ["공원", "산책", "산책로", "숲길", "정원", "둘레길", "생태"],
    "숙박": ["호텔", "숙박", "리조트", "펜션", "캠핑장", "야영장"],
    "카페_음식점": [
        "카페",
        "커피",
        "식당",
        "음식점",
        "맛집",
        "레스토랑",
        "음식",
        "한식",
        "중식",
        "양식",
        "분식",
        "의자식 테이블",
        "국수",
        "칼국수",
        "해장",
        "구이",
        "흑돼지",
        "에스프레소",
        "베이커리",
        "돈가스",
        "막국수",
        "백숙",
        "게장",
    ],
    "조용한": ["조용", "한적", "숲", "정원", "산책", "생태"],
}
SOFT_PLACE_PREFERENCES = {"실내", "조용한"}
PLACE_TYPE_PREFERENCES = {"박물관_전시", "시장_먹거리", "공원_산책", "숙박", "카페_음식점"}
PREFERENCE_DISPLAY_LABELS = {
    "실내": "실내",
    "박물관_전시": "박물관/전시",
    "시장_먹거리": "먹거리/식당",
    "공원_산책": "공원/산책",
    "숙박": "숙박",
    "카페_음식점": "카페/음식점",
    "조용한": "조용한 곳",
}
STRICT_CONDITION_EVIDENCE = {"유모차", "보조견", "시각장애", "청각장애"}
CONTEXTUAL_ML_INTENTS = {
    "show_more",
    "live_topup",
    "ask_source",
    "add_condition",
    "replace_condition",
    "exclude_preference",
    "narrow_region",
    "change_region",
    "unsupported_request",
}
CONTEXTUAL_ML_CONFIDENCE = 0.58
CONTEXTUAL_FOLLOWUP_KEYWORDS = [
    "더 보기",
    "더보기",
    "더 많이",
    "더 보여",
    "전체",
    "전부",
    "그중",
    "그 중",
    "그럼",
    "아니",
    "말고",
    "빼고",
    "제외",
    "최신 정보",
    "위주",
    "비 오는",
    "비오는",
    "실내",
    "박물관",
    "전시관",
    "좁혀",
    "넓혀",
    "넓혀서",
    "전체로",
    "범위",
    "있는 곳",
    "있는 곳만",
    "주차",
    "주차장",
    "장애인 주차",
    "점자",
    "점자블록",
    "수어",
    "수화",
    "자막",
    "출처",
    "경사로",
    "동선",
    "지하철역",
    "바로 연결",
    "휠체어",
    "유모차",
    "유아차",
    "어르신",
    "고령자",
    "할머니",
    "할아버지",
    "계단",
    "걷기",
    "시각장애",
    "청각장애",
    "보조견",
    "안내견",
]


class TourismChatService:
    def __init__(
        self,
        settings: Settings,
        retriever: Retriever,
        query_service: TourismQueryService,
        tour_api_service: TourAPIService | None = None,
        normalizer: TourismNormalizer | None = None,
        card_codec: TourismCardMarkdownCodec | None = None,
        event_logger: TourismQueryEventLogger | None = None,
        llm_service: LLMService | None = None,
    ):
        self.settings = settings
        self.retriever = retriever
        self.query_service = query_service
        self.tour_api_service = tour_api_service
        self.normalizer = normalizer or TourismNormalizer()
        self.card_codec = card_codec or TourismCardMarkdownCodec()
        self.event_logger = event_logger
        self.llm_service = llm_service
        self._sample_cards_cache: list[TourismPlaceCard] | None = None
        self._live_cards_cache: dict[str, list[TourismPlaceCard]] = {}
        self._live_markdown_cards_cache: list[TourismPlaceCard] | None = None
        self._session_queries: dict[str, dict[str, Any]] = {}
        self._live_update_executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="tourism-live-update")
        self._live_update_lock = threading.Lock()
        self._live_update_jobs: dict[str, LiveUpdateJob] = {}
        self._live_update_generations: dict[str, int] = {}

    def answer(self, message: str, session_id: str | None = None) -> TourismChatResponse:
        query = self._resolve_conversation_query(message, session_id)
        effective_message = self._build_effective_message(message, query)
        if self._is_live_update_strategy() and session_id and self._requests_live_update_accept(message):
            pending_response = self._consume_live_update_response(session_id, message)
            if pending_response is not None:
                self._log_event(message, session_id, pending_response[0], pending_response[1], live_api_called=False)
                self._remember_session_query(session_id, pending_response[0], pending_response[1])
                return pending_response[1]
            empty_update_response = TourismChatResponse(
                answer="반영할 새 추천 결과가 없습니다. 새 지역과 조건을 입력하면 다시 확인하겠습니다.",
                cards=[],
                sources=[],
                lookup_mode="live_update_empty",
                degraded=False,
                warnings=[],
            )
            self._log_event(message, session_id, query, empty_update_response, live_api_called=False)
            self._remember_session_query(session_id, query, empty_update_response)
            return empty_update_response
        if self._is_live_update_strategy() and session_id:
            self._cancel_session_live_update(session_id)
        if self._should_clarify_unsupported_core(query):
            response = TourismChatResponse(
                answer=self._build_unsupported_core_clarification_answer(query),
                cards=[],
                sources=[],
                lookup_mode="clarification",
                degraded=False,
                warnings=self._build_warnings(query, degraded=False),
                suggested_messages=self._build_unsupported_core_suggestions(query),
            )
            self._log_event(message, session_id, query, response, live_api_called=False)
            self._remember_session_query(session_id, query, response)
            return response
        if query.get("unsupported_intent") and not self._has_supported_tourism_part(query):
            response = TourismChatResponse(
                answer=(
                    "현재 서비스 범위는 무장애 관광지의 접근성, 가족 편의, 위치 기반 추천을 우선 지원합니다. "
                    "가격 비교, 실시간 혼잡도, 의료기관, 예약, 이동시간 계산은 확인된 데이터가 없어 추천하지 않겠습니다. "
                    "대신 방문하려는 지역과 접근성 조건을 알려주면 갈 수 있는 관광지를 찾아드릴 수 있습니다."
                ),
                cards=[],
                sources=[],
                lookup_mode="unsupported",
                degraded=False,
                warnings=self._build_warnings(query, degraded=False),
            )
            self._log_event(message, session_id, query, response, live_api_called=False)
            self._remember_session_query(session_id, query, response)
            return response
        if query.get("ambiguous_region"):
            response = TourismChatResponse(
                answer=self._build_region_clarification_answer(query),
                cards=[],
                sources=[],
                lookup_mode="clarification",
                degraded=False,
                warnings=self._build_warnings(query, degraded=False),
                suggested_messages=self._build_region_clarification_suggestions(query, message),
            )
            self._log_event(message, session_id, query, response, live_api_called=False)
            self._remember_session_query(session_id, query, response)
            return response
        if query.get("ambiguous_conditions"):
            response = TourismChatResponse(
                answer=self._build_condition_clarification_answer(query),
                cards=[],
                sources=[],
                lookup_mode="clarification",
                degraded=False,
                warnings=self._build_warnings(query, degraded=False),
                suggested_messages=self._build_condition_clarification_suggestions(query),
            )
            self._log_event(message, session_id, query, response, live_api_called=False)
            self._remember_session_query(session_id, query, response)
            return response
        if not query.get("region"):
            response = TourismChatResponse(
                answer=(
                    "추천할 지역을 먼저 알려 주세요. 예: '서울에서 휠체어 관광지 추천해줘', "
                    "'부산에서 유모차로 갈 만한 곳 알려줘'처럼 지역과 조건을 함께 말하면 근거가 있는 카드만 찾겠습니다."
                ),
                cards=[],
                sources=[],
                lookup_mode="clarification",
                degraded=False,
                warnings=self._build_warnings(query, degraded=False),
                suggested_messages=self._build_missing_region_suggestions(query),
            )
            self._log_event(message, session_id, query, response, live_api_called=False)
            self._remember_session_query(session_id, query, response)
            return response
        if self._is_general_tourism_only_query(query):
            response = TourismChatResponse(
                answer=self._build_general_tourism_scope_answer(query),
                cards=[],
                sources=[],
                lookup_mode="unsupported",
                degraded=False,
                warnings=self._build_warnings(query, degraded=False),
                suggested_messages=self._build_general_tourism_scope_suggestions(query),
            )
            self._log_event(message, session_id, query, response, live_api_called=False)
            self._remember_session_query(session_id, query, response)
            return response

        degraded = False
        lookup_mode = "unknown"
        contexts: list[dict] = []
        source_contexts: list[dict] = []
        cards: list[TourismPlaceCard] = []
        expanded = False
        has_more_cards = False
        live_api_called = False
        live_top_up_requested = self._requests_live_top_up(message)
        diagnostic_candidates: list[TourismPlaceCard] = []
        live_update_pending = False
        live_update_id: str | None = None

        if self._is_live_update_strategy() and self._can_use_live_tour_api(query):
            live_job = self._start_live_update_job(message, query, session_id)
            if live_job is not None:
                live_update_id = live_job.update_id
                live_candidates, live_degraded, api_called, live_timed_out = self._wait_for_live_update_job(live_job)
                live_api_called = live_api_called or api_called
                degraded = degraded or live_degraded
                diagnostic_candidates.extend(live_candidates)
                if live_candidates:
                    cards, expanded, has_more_cards = self._select_stage_cards(live_candidates, effective_message, query)
                    if cards and self._cards_cover_requested_conditions(cards, query):
                        candidates = live_candidates
                        lookup_mode = "live"
                    else:
                        cards = []
                        lookup_mode = "unknown"
                if live_timed_out:
                    live_update_pending = bool(session_id)

        if not cards:
            candidates = self._cards_from_live_markdown_cache(query)
            diagnostic_candidates.extend(candidates)
            cards, expanded, has_more_cards = self._select_stage_cards(candidates, effective_message, query)
            if cards:
                lookup_mode = "cache"
                if not self._cards_cover_requested_conditions(cards, query):
                    cards = []
                    lookup_mode = "unknown"

        if not cards:
            contexts, retrieve_degraded = self._retrieve(effective_message)
            degraded = degraded or retrieve_degraded
            candidates = self._cards_from_contexts(contexts)
            diagnostic_candidates.extend(candidates)
            cards, expanded, has_more_cards = self._select_stage_cards(candidates, effective_message, query)
            if cards:
                lookup_mode = "indexed"
                source_contexts = contexts
                if not self._cards_cover_requested_conditions(cards, query):
                    cards = []
                    lookup_mode = "unknown"
                    source_contexts = []

        if not cards:
            candidates = self._cards_from_markdown_samples()
            diagnostic_candidates.extend(candidates)
            cards, expanded, has_more_cards = self._select_stage_cards(candidates, effective_message, query)
            if cards:
                lookup_mode = "sample"
                if not self._cards_cover_requested_conditions(cards, query):
                    cards = []
                    lookup_mode = "unknown"

        if (
            cards
            and lookup_mode != "sample"
            and len(cards) < DEFAULT_CARD_LIMIT
            and query.get("area_name")
            and query.get("sigungu_name")
            and self._message_mentions_area(message, str(query.get("area_name")))
        ):
            supplemental_candidates = self._deduplicate([*candidates, *self._cards_from_markdown_samples()])
            supplemental_cards, supplemental_expanded, supplemental_has_more_cards = self._select_stage_cards(
                supplemental_candidates,
                effective_message,
                query,
            )
            if len(supplemental_cards) > len(cards):
                cards = supplemental_cards
                expanded = expanded or supplemental_expanded
                has_more_cards = supplemental_has_more_cards

        if not cards and not (self._is_live_update_strategy() and live_update_pending):
            candidates, live_degraded, api_called = self._cards_from_live_tour_api(query)
            live_api_called = live_api_called or api_called
            degraded = degraded or live_degraded
            diagnostic_candidates.extend(candidates)
            cards, expanded, has_more_cards = self._select_stage_cards(candidates, effective_message, query)
            if cards:
                lookup_mode = "live"

        if cards and live_top_up_requested and lookup_mode != "live":
            live_candidates, live_degraded, api_called = self._cards_from_live_tour_api(query)
            live_api_called = live_api_called or api_called
            degraded = degraded or live_degraded
            if live_candidates:
                candidates = self._deduplicate([*cards, *live_candidates])
                cards, expanded, has_more_cards = self._select_stage_cards(candidates, effective_message, query)
                lookup_mode = "live_top_up"

        if cards and len(cards) >= DEFAULT_CARD_LIMIT:
            more_candidates = self._deduplicate([*candidates, *self._cards_from_markdown_samples()])
            more_probe_message = effective_message if self._requests_more_cards(message) else f"{effective_message} 더 보기"
            more_cards, more_expanded, more_has_more_cards = self._select_stage_cards(more_candidates, more_probe_message, query)
            if self._requests_more_cards(message) and len(more_cards) > len(cards):
                cards = more_cards
                expanded = expanded or more_expanded
                has_more_cards = more_has_more_cards
            elif not self._requests_more_cards(message) and len(more_cards) > len(cards):
                has_more_cards = True

        sources = self._build_sources(source_contexts, cards)
        warnings = self._build_warnings(query, degraded)

        if not cards:
            region_text = self._display_region(query)
            answer = self._build_no_card_answer(query, region_text, diagnostic_candidates)
            if query.get("legacy_region_notice"):
                answer = f"{query['legacy_region_notice']}\n{answer}"
            response = TourismChatResponse(
                answer=answer,
                cards=[],
                sources=sources,
                lookup_mode=lookup_mode,
                degraded=degraded,
                warnings=warnings,
                suggested_messages=self._build_no_card_suggestions(query),
                live_update_pending=live_update_pending,
                live_update_id=live_update_id if live_update_pending else None,
            )
            self._log_event(message, session_id, query, response, live_api_called)
            self._remember_session_query(session_id, query, response)
            return response

        cards = self._annotate_cards_for_query_evidence(cards, query)
        cards, reasoning_used, reasoning_notes = self._apply_reasoning_assist(cards, effective_message, query)
        answer = self._build_answer(
            cards,
            query,
            expanded=expanded,
            reasoning_notes=reasoning_notes,
            live_top_up_available=self._should_suggest_live_top_up(message, cards, query, lookup_mode),
        )
        response = TourismChatResponse(
            answer=answer,
            cards=cards,
            sources=sources,
            lookup_mode=lookup_mode,
            degraded=degraded,
            warnings=warnings,
            suggested_messages=self._build_suggestions(
                effective_message,
                has_more_cards,
                cards,
                query,
                lookup_mode,
                live_update_pending=live_update_pending,
            ),
            live_update_pending=live_update_pending,
            live_update_id=live_update_id if live_update_pending else None,
            reasoning_assist_used=reasoning_used,
            reasoning_assist_notes=reasoning_notes,
        )
        self._log_event(message, session_id, query, response, live_api_called)
        self._remember_session_query(session_id, query, response)
        return response

    def _resolve_conversation_query(self, message: str, session_id: str | None) -> dict[str, Any]:
        query = self.query_service.extract(message)
        query["conversation_context_used"] = False
        if not session_id:
            return self._remove_negated_conditions(query, message)
        previous = self._session_queries.get(session_id)
        if previous and query.get("ambiguous_region"):
            scoped_query = self._resolve_ambiguous_region_from_context(query, previous)
            if scoped_query:
                query = scoped_query
        if not previous or not self._should_use_conversation_context(message, query):
            return self._remove_negated_conditions(query, message)

        merged = dict(query)
        region_identity_keys = [
            "region",
            "area_code",
            "sigungu_code",
            "area_name",
            "sigungu_name",
            "is_sigungu",
            "legacy_region",
            "legacy_region_replacement",
            "legacy_region_notice",
        ]
        if not query.get("region"):
            for key in region_identity_keys:
                if not merged.get(key) and previous.get(key):
                    merged[key] = previous[key]
        replacing_context = query.get("ml_intent") == "replace_condition" or self._looks_like_condition_reset_followup(message, query)
        for key in ["conditions", "features", "preferences", "excluded_preferences", "excluded_conditions"]:
            current = list(merged.get(key) or [])
            previous_values = list(previous.get(key) or [])
            if replacing_context and key in {"conditions", "features", "preferences"}:
                merged[key] = list(dict.fromkeys(current))
            elif current:
                merged[key] = list(dict.fromkeys([*previous_values, *current]))
            else:
                merged[key] = previous_values
        if merged.get("excluded_conditions"):
            excluded_conditions = set(merged.get("excluded_conditions") or [])
            merged["conditions"] = [condition for condition in merged.get("conditions") or [] if condition not in excluded_conditions]
        if merged.get("excluded_preferences"):
            excluded = set(merged.get("excluded_preferences") or [])
            merged["preferences"] = [preference for preference in merged.get("preferences") or [] if preference not in excluded]
        current_required = [tuple(group) for group in merged.get("required_evidence_terms") or []]
        previous_required = [tuple(group) for group in previous.get("required_evidence_terms") or []]
        required_groups = current_required if replacing_context else [*previous_required, *current_required]
        current_alternative = [tuple(group) for group in merged.get("alternative_evidence_terms") or []]
        previous_alternative = [tuple(group) for group in previous.get("alternative_evidence_terms") or []]
        alternative_groups = current_alternative if replacing_context else [*previous_alternative, *current_alternative]
        excluded_preferences = set(merged.get("excluded_preferences") or [])
        merged["required_evidence_terms"] = [
            list(group)
            for group in dict.fromkeys(required_groups)
            if not self._required_group_matches_excluded_preference(group, excluded_preferences)
        ]
        merged["alternative_evidence_terms"] = [
            list(group)
            for group in dict.fromkeys(alternative_groups)
            if not self._required_group_matches_excluded_preference(group, excluded_preferences)
        ]
        current_allows_expansion = bool(merged.get("allow_region_expansion"))
        previous_allows_unconditional_expansion = bool(previous.get("allow_region_expansion")) and not bool(
            previous.get("conditional_region_expansion")
        )
        merged["allow_region_expansion"] = current_allows_expansion or previous_allows_unconditional_expansion
        merged["conditional_region_expansion"] = bool(
            merged.get("conditional_region_expansion") and current_allows_expansion
        )
        merged["conversation_context_used"] = True
        return self._remove_negated_conditions(merged, message)

    @staticmethod
    def _resolve_ambiguous_region_from_context(query: dict, previous: dict) -> dict[str, Any] | None:
        previous_area = previous.get("area_name") or previous.get("region")
        if not previous_area:
            return None
        for candidate in query.get("ambiguous_region_candidates") or []:
            if not TourismChatService._same_area_context(str(previous_area), str(candidate.get("area_name") or "")):
                continue
            scoped = dict(query)
            sigungu_name = candidate.get("sigungu_name") or query.get("ambiguous_region")
            scoped.update(
                {
                    "region": f"{candidate.get('area_name')} {sigungu_name}",
                    "area_code": candidate.get("area_code"),
                    "sigungu_code": candidate.get("sigungu_code"),
                    "area_name": candidate.get("area_name"),
                    "sigungu_name": sigungu_name,
                    "is_sigungu": bool(candidate.get("sigungu_code")),
                    "ambiguous_region": None,
                    "ambiguous_region_candidates": [],
                    "conversation_context_used": True,
                }
            )
            return scoped
        return None

    @staticmethod
    def _same_area_context(previous_area: str, candidate_area: str) -> bool:
        aliases = {
            "강원": "강원",
            "강원특별자치도": "강원",
            "경남": "경남",
            "경상남도": "경남",
            "경북": "경북",
            "경상북도": "경북",
            "전남": "전남",
            "전라남도": "전남",
            "전북": "전북",
            "전라북도": "전북",
            "충남": "충남",
            "충청남도": "충남",
            "충북": "충북",
            "충청북도": "충북",
            "경기": "경기",
            "경기도": "경기",
            "서울": "서울",
            "서울특별시": "서울",
            "부산": "부산",
            "부산광역시": "부산",
            "대구": "대구",
            "대구광역시": "대구",
            "인천": "인천",
            "인천광역시": "인천",
            "대전": "대전",
            "대전광역시": "대전",
            "광주": "광주",
            "광주광역시": "광주",
            "울산": "울산",
            "울산광역시": "울산",
            "세종": "세종",
            "세종특별자치시": "세종",
            "제주": "제주",
            "제주특별자치도": "제주",
        }
        return aliases.get(previous_area, previous_area) == aliases.get(candidate_area, candidate_area)

    @staticmethod
    def _looks_like_condition_reset_followup(message: str, query: dict) -> bool:
        if not query.get("conditions") and not query.get("required_evidence_terms"):
            return False
        if query.get("region"):
            return False
        if any(marker in message for marker in ["까지", "도 같이", "도 봐", "추가", "함께", "유지"]):
            return False
        return bool(re.search(r"(다시|새로).{0,10}(찾아|보여|추천|알려)", message))

    @staticmethod
    def _required_group_matches_excluded_preference(group: tuple[str, ...], excluded_preferences: set[str]) -> bool:
        group_terms = set(group)
        preference_terms = {
            "시장_먹거리": {"시장", "먹자골목", "전통시장", "먹거리", "음식", "식당", "맛집"},
            "카페_음식점": {"카페", "커피", "식당", "음식점", "맛집", "레스토랑"},
            "숙박": {"호텔", "숙박", "리조트", "펜션", "캠핑장", "야영장"},
        }
        return any(group_terms & preference_terms.get(preference, set()) for preference in excluded_preferences)

    @staticmethod
    def _should_use_conversation_context(message: str, query: dict) -> bool:
        if (
            query.get("unsupported_intent")
            and not query.get("region")
            and not [condition for condition in query.get("conditions") or [] if condition != "대중교통"]
            and not query.get("preferences")
            and not query.get("excluded_preferences")
        ):
            return False
        ml_contextual = (
            query.get("ml_intent") in CONTEXTUAL_ML_INTENTS
            and float(query.get("ml_intent_confidence") or 0.0) >= CONTEXTUAL_ML_CONFIDENCE
        )
        if not any(keyword in message for keyword in CONTEXTUAL_FOLLOWUP_KEYWORDS) and not ml_contextual:
            return False
        if query.get("ambiguous_region"):
            return False
        if query.get("region") and query.get("ml_intent") == "change_region":
            return True
        return not query.get("region") or bool(
            query.get("conditions")
            or query.get("preferences")
            or query.get("excluded_preferences")
            or query.get("features")
            or query.get("allow_region_expansion")
        )

    @staticmethod
    def _remove_negated_conditions(query: dict, message: str) -> dict[str, Any]:
        conditions = list(query.get("conditions") or [])
        negated = {
            condition
            for condition, keywords in {
                "휠체어": ["휠체어", "무장애", "장애인"],
                "유모차": ["유모차", "유아차", "아이", "어린이"],
                "고령자": ["고령자", "어르신", "노인"],
                "보조견": ["보조견", "안내견"],
                "시각장애": ["점자", "점자블록", "오디오가이드", "시각장애"],
                "청각장애": ["수어", "수화", "자막", "청각장애"],
            }.items()
            if any(TourismChatService._term_is_negated(message, keyword) for keyword in keywords)
        }
        if negated:
            query = dict(query)
            query["conditions"] = [condition for condition in conditions if condition not in negated]
        return query

    @staticmethod
    def _term_is_negated(message: str, keyword: str) -> bool:
        start = message.find(keyword)
        if start == -1:
            return False
        end = start + len(keyword)
        window = message[end : min(len(message), end + 8)]
        return any(negation in window for negation in ["말고", "빼고", "제외", "아닌"])

    @staticmethod
    def _build_effective_message(message: str, query: dict) -> str:
        if not query.get("conversation_context_used"):
            return message
        parts = []
        display_region = TourismChatService._display_region(query)
        if display_region != "요청 지역":
            parts.append(display_region)
        parts.extend(str(value) for value in query.get("conditions") or [])
        parts.extend(str(value) for value in query.get("preferences") or [])
        if query.get("ml_intent") not in {"replace_condition", "exclude_preference"}:
            parts.append(message)
        return " ".join(part for part in parts if part).strip()

    def _remember_session_query(self, session_id: str | None, query: dict, response: TourismChatResponse) -> None:
        if not session_id:
            return
        if response.lookup_mode == "clarification" and not response.cards:
            if not query.get("region"):
                return
        if not query.get("region"):
            return
        self._session_queries[session_id] = {
            key: query.get(key)
            for key in [
                "region",
                "area_code",
                "sigungu_code",
                "area_name",
                "sigungu_name",
                "is_sigungu",
                "allow_region_expansion",
                "conditional_region_expansion",
                "require_all_conditions",
                "conditions",
                "excluded_conditions",
                "ambiguous_conditions",
                "required_evidence_terms",
                "alternative_evidence_terms",
                "features",
                "preferences",
                "excluded_preferences",
                "legacy_region",
                "legacy_region_replacement",
                "legacy_region_notice",
            ]
        }

    def _select_stage_cards(
        self,
        candidates: list[TourismPlaceCard],
        message: str,
        query: dict,
    ) -> tuple[list[TourismPlaceCard], bool, bool]:
        if not candidates:
            return [], False, False
        if query.get("allow_region_expansion"):
            candidates = self._deduplicate([*candidates, *self._cards_from_markdown_samples()])
        return self._select_cards(candidates, message, query)

    def _retrieve(self, message: str) -> tuple[list[dict], bool]:
        try:
            return self.retriever.retrieve(message), False
        except Exception as exc:
            logger.warning("관광 RAG 검색 실패, 로컬 샘플 fallback 사용: %s", exc.__class__.__name__)
            return [], True

    def _is_live_update_strategy(self) -> bool:
        return str(self.settings.tourism_lookup_strategy).strip().lower() == "live_update"

    def _next_live_update_generation(self, session_id: str) -> int:
        with self._live_update_lock:
            generation = self._live_update_generations.get(session_id, 0) + 1
            self._live_update_generations[session_id] = generation
            return generation

    def _cancel_session_live_update(self, session_id: str) -> None:
        with self._live_update_lock:
            job = self._live_update_jobs.pop(session_id, None)
            self._live_update_generations[session_id] = self._live_update_generations.get(session_id, 0) + 1
        if job is not None:
            job.status = "cancelled"
            job.future.cancel()

    def _start_live_update_job(
        self,
        message: str,
        query: dict[str, Any],
        session_id: str | None,
    ) -> LiveUpdateJob | None:
        if session_id is None:
            future = self._live_update_executor.submit(
                self._cards_from_live_tour_api,
                dict(query),
                False,
                False,
            )
            return LiveUpdateJob(
                update_id="request",
                session_id="",
                message=message,
                query=dict(query),
                future=future,
                started_at=time.monotonic(),
                background_timeout_seconds=max(float(self.settings.tourism_live_first_wait_seconds), 0.0),
                generation=0,
            )

        generation = self._next_live_update_generation(session_id)
        update_id = f"{session_id}:{generation}"
        job = LiveUpdateJob(
            update_id=update_id,
            session_id=session_id,
            message=message,
            query=dict(query),
            future=self._live_update_executor.submit(
                self._cards_from_live_tour_api,
                dict(query),
                False,
                False,
            ),
            started_at=time.monotonic(),
            background_timeout_seconds=max(float(self.settings.tourism_live_background_timeout_seconds), 0.0),
            generation=generation,
        )
        with self._live_update_lock:
            self._live_update_jobs[session_id] = job
        job.future.add_done_callback(lambda future: self._store_live_update_result(session_id, generation, future))
        return job

    def _wait_for_live_update_job(
        self,
        job: LiveUpdateJob,
    ) -> tuple[list[TourismPlaceCard], bool, bool, bool]:
        wait_seconds = max(float(self.settings.tourism_live_first_wait_seconds), 0.0)
        try:
            cards, degraded, api_called = job.future.result(timeout=wait_seconds)
        except FutureTimeoutError:
            if not job.session_id:
                job.status = "timeout"
                job.future.cancel()
            return [], False, True, True
        except Exception as exc:  # noqa: BLE001 - live update must degrade to fallback.
            logger.warning("관광 live update 작업 실패, fallback 응답 사용: %s", exc.__class__.__name__)
            job.status = "failed"
            return [], True, True, False

        job.cards = list(cards)
        job.degraded = degraded
        job.api_called = api_called
        job.status = "ready" if cards else "failed"
        if job.session_id:
            with self._live_update_lock:
                current = self._live_update_jobs.get(job.session_id)
                if current is job:
                    self._live_update_jobs.pop(job.session_id, None)
        if cards and not degraded:
            self._live_cards_cache[self._live_cache_key(job.query)] = self._deduplicate(cards)
            self._persist_live_cards(job.query, self._live_cards_cache[self._live_cache_key(job.query)])
        return list(cards), degraded, api_called, False

    def _store_live_update_result(self, session_id: str, generation: int, future: Future) -> None:
        if not session_id:
            return
        with self._live_update_lock:
            job = self._live_update_jobs.get(session_id)
            current_generation = self._live_update_generations.get(session_id)
        if job is None or job.generation != generation or current_generation != generation:
            return
        elapsed = time.monotonic() - job.started_at
        if elapsed > job.background_timeout_seconds:
            job.status = "timeout"
            with self._live_update_lock:
                if self._live_update_jobs.get(session_id) is job:
                    self._live_update_jobs.pop(session_id, None)
            return
        try:
            cards, degraded, api_called = future.result()
        except Exception as exc:  # noqa: BLE001 - background failure should not break chat.
            logger.warning("관광 live update background 작업 실패: %s", exc.__class__.__name__)
            job.status = "failed"
            with self._live_update_lock:
                if self._live_update_jobs.get(session_id) is job:
                    self._live_update_jobs.pop(session_id, None)
            return
        selected_cards, _, _ = self._select_stage_cards(list(cards), job.message, job.query)
        if not selected_cards or not self._cards_cover_requested_conditions(selected_cards, job.query):
            job.status = "failed"
            with self._live_update_lock:
                if self._live_update_jobs.get(session_id) is job:
                    self._live_update_jobs.pop(session_id, None)
            return
        job.cards = list(selected_cards)
        job.degraded = degraded
        job.api_called = api_called
        job.status = "ready"

    @staticmethod
    def _requests_live_update_accept(message: str) -> bool:
        return any(keyword in message for keyword in LIVE_UPDATE_ACCEPT_KEYWORDS)

    def _consume_live_update_response(
        self,
        session_id: str,
        message: str,
    ) -> tuple[dict[str, Any], TourismChatResponse] | None:
        consume_result = self._wait_for_live_update_acceptance(session_id)
        if consume_result is None:
            return None
        job = consume_result.job
        if consume_result.status == "timeout":
            query = dict(job.query)
            response = TourismChatResponse(
                answer="최신 추천 결과 확인 시간이 초과되어 먼저 안내한 결과를 유지합니다.",
                cards=[],
                sources=[],
                lookup_mode="live_update_timeout",
                degraded=True,
                warnings=self._build_warnings(query, degraded=True),
            )
            return query, response
        if consume_result.status == "pending":
            query = dict(job.query)
            response = TourismChatResponse(
                answer="최신 추천 결과를 아직 확인 중입니다. 준비되면 다시 알려드릴게요.",
                cards=[],
                sources=[],
                lookup_mode="live_update_pending",
                degraded=False,
                warnings=self._build_warnings(query, degraded=False),
                live_update_pending=True,
                live_update_id=job.update_id,
            )
            return query, response

        query = dict(job.query)
        cards = self._annotate_cards_for_query_evidence(list(job.cards), query)
        cards, reasoning_used, reasoning_notes = self._apply_reasoning_assist(cards, job.message, query)
        if cards and not job.degraded:
            self._live_cards_cache[self._live_cache_key(query)] = self._deduplicate(cards)
            self._persist_live_cards(query, self._live_cards_cache[self._live_cache_key(query)])
        sources = self._build_sources([], cards)
        answer = self._build_answer(cards, query, expanded=False, reasoning_notes=reasoning_notes)
        response = TourismChatResponse(
            answer=f"새로운 최신 추천 결과가 준비되어 반영했습니다.\n{answer}",
            cards=cards,
            sources=sources,
            lookup_mode="live_update",
            degraded=job.degraded,
            warnings=self._build_warnings(query, job.degraded),
            suggested_messages=self._build_suggestions(message, False, cards, query, "live_update"),
            reasoning_assist_used=reasoning_used,
            reasoning_assist_notes=reasoning_notes,
        )
        return query, response

    def _wait_for_live_update_acceptance(self, session_id: str) -> LiveUpdateConsumeResult | None:
        with self._live_update_lock:
            job = self._live_update_jobs.get(session_id)
            if job is None:
                return None
            elapsed = time.monotonic() - job.started_at
            if elapsed > job.background_timeout_seconds:
                self._live_update_jobs.pop(session_id, None)
                self._live_update_generations[session_id] = self._live_update_generations.get(session_id, 0) + 1
                job.status = "timeout"
                job.future.cancel()
                return LiveUpdateConsumeResult(status="timeout", job=job)
            if job.status != "ready":
                remaining_seconds = max(job.background_timeout_seconds - elapsed, 0.0)
            else:
                remaining_seconds = 0.0

        if job.status != "ready" and remaining_seconds > 0:
            try:
                job.future.result(timeout=remaining_seconds)
                self._store_live_update_result(session_id, job.generation, job.future)
            except FutureTimeoutError:
                with self._live_update_lock:
                    if self._live_update_jobs.get(session_id) is job:
                        self._live_update_jobs.pop(session_id, None)
                        self._live_update_generations[session_id] = self._live_update_generations.get(session_id, 0) + 1
                job.status = "timeout"
                job.future.cancel()
                return LiveUpdateConsumeResult(status="timeout", job=job)
            except Exception as exc:  # noqa: BLE001 - late update should degrade quietly.
                logger.warning("관광 live update 승인 대기 실패: %s", exc.__class__.__name__)
                with self._live_update_lock:
                    if self._live_update_jobs.get(session_id) is job:
                        self._live_update_jobs.pop(session_id, None)
                        self._live_update_generations[session_id] = self._live_update_generations.get(session_id, 0) + 1
                job.status = "failed"
                return LiveUpdateConsumeResult(status="timeout", job=job)

        with self._live_update_lock:
            current = self._live_update_jobs.get(session_id)
            if current is not job:
                return None
            if job.status != "ready":
                return LiveUpdateConsumeResult(status="pending", job=job)
            self._live_update_jobs.pop(session_id, None)
            self._live_update_generations[session_id] = self._live_update_generations.get(session_id, 0) + 1
        return LiveUpdateConsumeResult(status="ready", job=job)

    def _cards_from_live_tour_api(
        self,
        query: dict,
        use_cache: bool = True,
        persist: bool = True,
    ) -> tuple[list[TourismPlaceCard], bool, bool]:
        if not self._can_use_live_tour_api(query):
            return [], False, False

        cache_key = self._live_cache_key(query)
        if use_cache and cache_key in self._live_cards_cache:
            return list(self._live_cards_cache[cache_key]), False, False

        api = self.tour_api_service
        assert api is not None
        try:
            list_items = api.accessible_area_based_list(
                area_code=str(query.get("area_code") or ""),
                sigungu_code=str(query.get("sigungu_code")) if query.get("sigungu_code") else None,
                num_of_rows=self.settings.tourism_live_rows,
            )
            cards = self._normalize_live_items(list_items)
        except (TourAPIError, TimeoutError, ValueError) as exc:
            logger.warning("관광 live TourAPI 조회 실패, RAG fallback 사용: %s", exc.__class__.__name__)
            return [], True, True

        cards = self._deduplicate(cards)
        if persist:
            self._live_cards_cache[cache_key] = cards
            self._persist_live_cards(query, self._live_cards_cache[cache_key])
        return list(cards), False, True

    def _log_event(
        self,
        message: str,
        session_id: str | None,
        query: dict,
        response: TourismChatResponse,
        live_api_called: bool,
    ) -> None:
        if self.event_logger:
            self.event_logger.log(
                message=message,
                session_id=session_id,
                query=query,
                response=response,
                live_api_called=live_api_called,
            )

    def _can_use_live_tour_api(self, query: dict) -> bool:
        if not self.settings.tourism_live_lookup_enabled:
            return False
        if not self.tour_api_service:
            return False
        if not query.get("area_code"):
            return False
        return bool(self.settings.tour_api_service_key)

    def _normalize_live_items(self, list_items: list[dict]) -> list[TourismPlaceCard]:
        cards = []
        detail_calls = 0
        max_detail_calls = max(self.settings.tourism_live_max_detail_calls, 0)
        api = self.tour_api_service
        assert api is not None

        for item in list_items:
            content_id = str(item.get("contentid") or "").strip()
            if not content_id or detail_calls + 2 > max_detail_calls:
                continue
            try:
                detail_calls += 1
                common = api.detail_common(content_id) or item
                detail_calls += 1
                accessible = api.detail_with_tour(content_id)
            except TourAPIError as exc:
                logger.info("관광 live 상세 조회 일부 실패: %s (%s)", content_id, exc.__class__.__name__)
                continue
            card = self.normalizer.normalize_place(common, accessible)
            if card.raw_fields:
                cards.append(card)
        return cards

    def _apply_reasoning_assist(
        self,
        cards: list[TourismPlaceCard],
        message: str,
        query: dict,
    ) -> tuple[list[TourismPlaceCard], bool, list[str]]:
        if not self._should_use_reasoning_assist(cards, message, query):
            return cards, False, []
        assert self.llm_service is not None
        try:
            payload = self._call_reasoning_assist(cards, message, query)
        except Exception as exc:  # noqa: BLE001 - reasoning assist must never break the main answer.
            logger.warning("관광 추론 보조 실패, 기존 카드 순서 유지: %s", exc.__class__.__name__)
            return cards, False, []

        ranked_cards = self._reorder_cards_by_reasoning(cards, payload.get("ranked_ids"))
        notes = self._normalize_reasoning_notes(payload)
        return ranked_cards, True, notes

    def _should_use_reasoning_assist(self, cards: list[TourismPlaceCard], message: str, query: dict) -> bool:
        if not self.settings.tourism_reasoning_assist_enabled:
            return False
        if not self.llm_service:
            return False
        if not cards:
            return False
        if query.get("ambiguous_region") or query.get("unsupported_intent"):
            return False
        conditions = query.get("conditions") or []
        if len(conditions) >= 3:
            return True
        return any(keyword in message for keyword in REASONING_ASSIST_KEYWORDS)

    def _call_reasoning_assist(
        self,
        cards: list[TourismPlaceCard],
        message: str,
        query: dict,
    ) -> dict[str, Any]:
        prompt = self._build_reasoning_assist_prompt(cards, message, query)
        raw = self.llm_service.generate(prompt)
        return self._parse_reasoning_assist_json(raw)

    def _build_reasoning_assist_prompt(
        self,
        cards: list[TourismPlaceCard],
        message: str,
        query: dict,
    ) -> str:
        max_cards = max(self.settings.tourism_reasoning_assist_max_cards, 1)
        card_payload = []
        for index, card in enumerate(cards[:max_cards], start=1):
            card_payload.append(
                {
                    "id": card.content_id,
                    "rank": index,
                    "title": card.title,
                    "address": card.address,
                    "accessibility_tags": card.accessibility_tags,
                    "family_tags": card.family_tags,
                    "recommendation_reason": card.recommendation_reason,
                    "known_fields": card.raw_fields,
                }
            )
        payload = {
            "message": message,
            "region": query.get("region"),
            "conditions": query.get("conditions") or [],
            "features": query.get("features") or [],
            "preferences": query.get("preferences") or [],
            "excluded_preferences": query.get("excluded_preferences") or [],
            "cards": card_payload,
        }
        return (
            "너는 무장애 관광 챗봇의 후보 재랭킹 보조 계층이다.\n"
            "규칙:\n"
            "- 후보 카드에 없는 장소나 접근성 정보를 만들지 않는다.\n"
            "- 후보 카드 id만 ranked_ids에 넣는다.\n"
            "- 사용자의 복합 상황을 해석해 후보 순서와 확인 필요 메모만 정리한다.\n"
            "- 출력은 JSON 객체만 한다. Markdown 코드블록을 쓰지 않는다.\n\n"
            "입력 JSON:\n"
            f"{json.dumps(payload, ensure_ascii=False)}\n\n"
            "출력 JSON 형식:\n"
            "{\"ranked_ids\":[\"card-id\"],\"missing_or_uncertain\":[\"확인 필요 메모\"]}"
        )

    @staticmethod
    def _parse_reasoning_assist_json(raw: str) -> dict[str, Any]:
        text = raw.strip()
        if text.startswith("```"):
            text = re.sub(r"^```(?:json)?", "", text, flags=re.IGNORECASE).strip()
            text = re.sub(r"```$", "", text).strip()
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise ValueError("추론 보조 JSON 객체를 찾지 못했습니다.")
        parsed = json.loads(text[start : end + 1])
        if not isinstance(parsed, dict):
            raise ValueError("추론 보조 응답이 JSON 객체가 아닙니다.")
        return parsed

    @staticmethod
    def _reorder_cards_by_reasoning(cards: list[TourismPlaceCard], ranked_ids: Any) -> list[TourismPlaceCard]:
        if not isinstance(ranked_ids, list):
            return cards
        by_id = {card.content_id: card for card in cards}
        ordered = []
        seen = set()
        for raw_id in ranked_ids:
            content_id = str(raw_id)
            if content_id in by_id and content_id not in seen:
                ordered.append(by_id[content_id])
                seen.add(content_id)
        return [*ordered, *[card for card in cards if card.content_id not in seen]]

    @staticmethod
    def _normalize_reasoning_notes(payload: dict[str, Any]) -> list[str]:
        notes = payload.get("missing_or_uncertain") or payload.get("notes") or []
        if isinstance(notes, str):
            notes = [notes]
        if not isinstance(notes, list):
            return []
        result = []
        for note in notes:
            text = str(note).strip()
            if text:
                result.append(text)
        return result[:3]

    @staticmethod
    def _live_cache_key(query: dict) -> str:
        return ":".join([str(query.get("area_code") or ""), str(query.get("sigungu_code") or "")])

    def _cards_from_contexts(self, contexts: list[dict]) -> list[TourismPlaceCard]:
        cards = []
        for context in contexts:
            card = self.card_codec.from_markdown(context.get("text") or "")
            if card:
                cards.append(card)
        return self._deduplicate(cards)

    def _cards_from_markdown_samples(self) -> list[TourismPlaceCard]:
        if self._sample_cards_cache is not None:
            return list(self._sample_cards_cache)

        sample_path = self.settings.resolved_tourism_sample_path
        cards = []
        for path in sorted(sample_path.glob("*.md")):
            card = self.card_codec.from_markdown(path.read_text(encoding="utf-8"))
            if card:
                cards.append(card)
        self._sample_cards_cache = self._deduplicate(cards)
        return list(self._sample_cards_cache)

    def _cards_from_live_markdown_cache(self, query: dict) -> list[TourismPlaceCard]:
        if not query.get("area_code"):
            return []
        cards = self._filter_cards_by_query_region(self._load_live_markdown_cards(), query)
        return self._deduplicate(cards)

    def _load_live_markdown_cards(self) -> list[TourismPlaceCard]:
        if self._live_markdown_cards_cache is not None:
            return list(self._live_markdown_cards_cache)

        cache_path = self.settings.resolved_tourism_live_cache_path
        cards = []
        if cache_path.exists():
            for path in sorted(cache_path.glob("*.md")):
                card = self.card_codec.from_markdown(path.read_text(encoding="utf-8"))
                if card:
                    cards.append(card)
        self._live_markdown_cards_cache = self._deduplicate(cards)
        return list(self._live_markdown_cards_cache)

    def _persist_live_cards(self, query: dict, cards: list[TourismPlaceCard]) -> None:
        if not cards:
            return
        cache_path = self.settings.resolved_tourism_live_cache_path
        try:
            cache_path.mkdir(parents=True, exist_ok=True)
            for card in cards:
                path = cache_path / self._live_card_cache_filename(query, card)
                if not path.exists():
                    path.write_text(self.card_codec.to_markdown(card), encoding="utf-8")
            self._live_markdown_cards_cache = None
        except OSError as exc:
            logger.warning("관광 live Markdown 캐시 저장 실패: %s", exc.__class__.__name__)

    @staticmethod
    def _live_card_cache_filename(query: dict, card: TourismPlaceCard) -> str:
        area_name = str(query.get("area_name") or query.get("area_code") or "area")
        sigungu_name = str(query.get("sigungu_name") or query.get("sigungu_code") or "")
        region = "_".join(part for part in [area_name, sigungu_name] if part)
        safe_region = re.sub(r"[^0-9A-Za-z가-힣_-]+", "_", region).strip("_") or "area"
        safe_content_id = re.sub(r"[^0-9A-Za-z_-]+", "_", card.content_id).strip("_") or "unknown"
        return f"{safe_region}_{safe_content_id}.md"

    def _select_cards(
        self,
        cards: list[TourismPlaceCard],
        message: str,
        query: dict,
    ) -> tuple[list[TourismPlaceCard], bool, bool]:
        more_requested = self._requests_more_cards(message)
        region = query.get("region")
        if region and query.get("is_sigungu"):
            query_region_cards = self._filter_cards_by_query_region(cards, query)
            query_region_cards = self._filter_cards_by_conditions(query_region_cards, query)
            query_region_cards = self._filter_cards_by_required_evidence_terms(query_region_cards, query)
            if not query_region_cards:
                expanded_cards = self._select_place_type_area_expansion(cards, message, query, more_requested)
                if expanded_cards:
                    return expanded_cards
                return [], False, False
            if query.get("features"):
                query_region_cards = self._filter_cards_by_features(query_region_cards, query)
                if not query_region_cards and not query.get("allow_region_expansion"):
                    return [], False, False
            query_region_cards = self._filter_cards_by_preferences(query_region_cards, query)
            if not query_region_cards:
                expanded_cards = self._select_place_type_area_expansion(cards, message, query, more_requested)
                if expanded_cards:
                    return expanded_cards
                return [], False, False
            region_cards = self._rank_cards(
                query_region_cards,
                message,
                query,
                filter_region=False,
            )
            if query.get("conditional_region_expansion") and len(region_cards) >= DEFAULT_CARD_LIMIT:
                return self._limit_cards(region_cards, more_requested), False, self._has_more_cards(region_cards, more_requested)
            if not query.get("allow_region_expansion"):
                return self._limit_cards(region_cards, more_requested), False, self._has_more_cards(region_cards, more_requested)

            area_name = query.get("area_name")
            expanded_candidates = self._filter_cards_by_conditions(self._filter_cards_by_region(cards, area_name), query)
            expanded_candidates = self._filter_cards_by_required_evidence_terms(expanded_candidates, query)
            expanded_candidates = self._filter_cards_by_preferences(expanded_candidates, query)
            expanded_cards = self._rank_cards(
                expanded_candidates,
                message,
                query,
                filter_region=False,
            )
            ranked_cards = self._deduplicate([*region_cards, *expanded_cards])
            limited_cards = self._limit_cards(ranked_cards, more_requested)
            actual_expanded = self._cards_include_outside_query_region(limited_cards, query)
            return limited_cards, actual_expanded, self._has_more_cards(ranked_cards, more_requested)

        if region:
            cards = self._filter_cards_by_query_region(cards, query)
            if not cards:
                return [], False, False
        cards = self._filter_cards_by_conditions(cards, query)
        cards = self._filter_cards_by_required_evidence_terms(cards, query)
        if not cards:
            return [], False, False
        cards = self._filter_cards_by_preferences(cards, query)
        if not cards:
            return [], False, False
        ranked_cards = self._rank_cards(cards, message, query, filter_region=False)
        return self._limit_cards(ranked_cards, more_requested), False, self._has_more_cards(ranked_cards, more_requested)

    def _select_place_type_area_expansion(
        self,
        cards: list[TourismPlaceCard],
        message: str,
        query: dict,
        more_requested: bool,
    ) -> tuple[list[TourismPlaceCard], bool, bool] | None:
        if not self._should_expand_place_type_only_query(query):
            return None
        area_name = query.get("area_name")
        expanded_candidates = self._filter_cards_by_region(cards, area_name)
        expanded_candidates = self._filter_cards_by_preferences(expanded_candidates, query)
        if not expanded_candidates:
            return None
        ranked_cards = self._rank_cards(
            expanded_candidates,
            message,
            query,
            filter_region=False,
        )
        limited_cards = self._limit_cards(ranked_cards, more_requested)
        actual_expanded = self._cards_include_outside_query_region(limited_cards, query)
        return limited_cards, actual_expanded, self._has_more_cards(ranked_cards, more_requested)

    def _rank_cards(
        self,
        cards: list[TourismPlaceCard],
        message: str,
        query: dict,
        filter_region: bool = True,
    ) -> list[TourismPlaceCard]:
        conditions = query.get("conditions") or []
        region = query.get("region")
        if filter_region and region:
            cards = self._filter_cards_by_query_region(cards, query)
            if not cards:
                return []
        feature_cards = self._filter_cards_by_features(cards, query)
        if feature_cards:
            cards = feature_cards
        elif query.get("features"):
            return []
        cards = self._filter_cards_by_excluded_preferences(cards, query)

        def score(card: TourismPlaceCard) -> int:
            haystack = self._card_haystack(card)
            value = 0
            if region and region in haystack:
                value += 4
            for condition in conditions:
                value += self._condition_evidence_score(card, condition)
            for feature in query.get("features") or []:
                if feature in haystack:
                    value += 3
            for preference in query.get("preferences") or []:
                value += self._preference_evidence_score(card, preference)
            for excluded_preference in query.get("excluded_preferences") or []:
                if self._preference_matches(card, excluded_preference):
                    value -= 12
            for token in message.split():
                if len(token) >= 2 and token in haystack:
                    value += 1
            return value

        return sorted(cards, key=score, reverse=True)

    @classmethod
    def _cards_cover_requested_conditions(cls, cards: list[TourismPlaceCard], query: dict) -> bool:
        conditions = [
            condition
            for condition in query.get("conditions") or []
            if condition in STRICT_CONDITION_EVIDENCE
        ]
        condition_covered = all(any(cls._card_satisfies_condition(card, condition, query) for card in cards) for condition in conditions)
        if not condition_covered and (query.get("require_all_conditions") or len(query.get("conditions") or []) <= 1):
            return False
        required_groups = query.get("required_evidence_terms") or []
        required_covered = all(
            any(any(term in cls._card_haystack(card) for term in group) for card in cards)
            for group in required_groups
        )
        if not required_covered:
            return False
        alternative_groups = query.get("alternative_evidence_terms") or []
        alternative_covered = not alternative_groups or any(
            any(any(term in cls._card_haystack(card) for term in group) for card in cards)
            for group in alternative_groups
        )
        if not alternative_covered:
            return False
        # Preferences are ranking signals. They should not invalidate otherwise
        # relevant cards when the local data has no explicit preference evidence.
        return True

    @classmethod
    def _filter_cards_by_conditions(cls, cards: list[TourismPlaceCard], query: dict) -> list[TourismPlaceCard]:
        conditions = query.get("conditions") or []
        if not conditions:
            return cards
        if conditions == ["유모차"] and not cls._place_type_preferences(query):
            direct_stroller_matches = [card for card in cards if cls._stroller_family_evidence_score(card) > 0]
            if direct_stroller_matches:
                return direct_stroller_matches
        all_condition_matches = [
            card
            for card in cards
            if all(cls._card_satisfies_condition(card, condition, query) for condition in conditions)
        ]
        if all_condition_matches:
            return all_condition_matches
        if len(conditions) == 1:
            return []
        if query.get("require_all_conditions"):
            return []
        return [
            card
            for card in cards
            if any(cls._condition_evidence_score(card, condition) > 0 for condition in conditions)
        ]

    @classmethod
    def _filter_cards_by_required_evidence_terms(cls, cards: list[TourismPlaceCard], query: dict) -> list[TourismPlaceCard]:
        required_groups = query.get("required_evidence_terms") or []
        alternative_groups = query.get("alternative_evidence_terms") or []
        if not required_groups and not alternative_groups:
            return cards
        return [
            card
            for card in cards
            if all(any(term in cls._card_haystack(card) for term in group) for group in required_groups)
            and (
                not alternative_groups
                or any(any(term in cls._card_haystack(card) for term in group) for group in alternative_groups)
            )
        ]

    @classmethod
    def _annotate_cards_for_query_evidence(cls, cards: list[TourismPlaceCard], query: dict) -> list[TourismPlaceCard]:
        conditions = query.get("conditions") or []
        if not conditions:
            return cards
        annotated: list[TourismPlaceCard] = []
        for card in cards:
            reason = card.recommendation_reason
            if "고령자" in conditions and cls._condition_evidence_score(card, "고령자") > 0 and "고령자 요청" not in reason:
                reason = f"{reason} 고령자 요청은 휠체어 접근, 경사로, 화장실, 대중교통 같은 이동 편의 근거를 함께 확인합니다."
            focused_reason = cls._build_focused_card_reason(card, query)
            if focused_reason:
                reason = focused_reason
            update = {"recommendation_reason": reason}
            focused_tags = cls._select_condition_tags([*card.accessibility_tags, *card.family_tags], query)
            if focused_tags and cls._should_show_only_focused_tags(query):
                update["accessibility_tags"] = [tag for tag in focused_tags if tag in card.accessibility_tags]
                update["family_tags"] = [tag for tag in focused_tags if tag in card.family_tags]
            elif focused_tags:
                update["accessibility_tags"] = cls._prioritize_tags(card.accessibility_tags, focused_tags)
                update["family_tags"] = cls._prioritize_tags(card.family_tags, focused_tags)
            annotated.append(card.model_copy(update=update))
        return annotated

    @staticmethod
    def _should_show_only_focused_tags(query: dict) -> bool:
        focused_conditions = {"시각장애", "청각장애", "보조견"}
        return any(condition in focused_conditions for condition in query.get("conditions") or [])

    @staticmethod
    def _prioritize_tags(tags: list[str], focused_tags: list[str]) -> list[str]:
        focused_set = set(focused_tags)
        return [*dict.fromkeys([tag for tag in tags if tag in focused_set]), *[tag for tag in tags if tag not in focused_set]]

    @classmethod
    def _build_focused_card_reason(cls, card: TourismPlaceCard, query: dict) -> str | None:
        conditions = query.get("conditions") or []
        if not conditions:
            return None
        focused_conditions = [
            condition
            for condition in conditions
            if condition in {"시각장애", "청각장애", "보조견", "주차", "화장실", "엘리베이터", "접근로", "유모차"}
        ]
        if not focused_conditions:
            return None
        tags = cls._select_condition_tags([*card.accessibility_tags, *card.family_tags], query)
        evidence = cls._select_raw_evidence(card, query)
        if not tags and not evidence:
            return None
        parts = []
        if tags:
            parts.append(", ".join(tags[:2]))
        parts.extend(evidence[:1])
        return f"{card.title}은(는) {' / '.join(parts[:2])} 정보가 확인되어 요청 조건에 맞는 후보입니다."

    @classmethod
    def _filter_cards_by_preferences(cls, cards: list[TourismPlaceCard], query: dict) -> list[TourismPlaceCard]:
        preferences = query.get("preferences") or []
        if not preferences:
            return cards
        strong_preferences = [preference for preference in preferences if preference not in SOFT_PLACE_PREFERENCES]
        soft_requested = [preference for preference in preferences if preference in SOFT_PLACE_PREFERENCES]

        if strong_preferences:
            strong_matches = [
                card
                for card in cards
                if any(cls._preference_evidence_score(card, preference) > 0 for preference in strong_preferences)
            ]
            if not strong_matches:
                return []
            soft_matches = [
                card
                for card in strong_matches
                if any(cls._preference_evidence_score(card, preference) > 0 for preference in soft_requested)
            ]
            return soft_matches or strong_matches

        matched_cards = [
            card
            for card in cards
            if any(cls._preference_evidence_score(card, preference) > 0 for preference in soft_requested)
        ]
        return matched_cards or cards

    @staticmethod
    def _place_type_preferences(query: dict) -> list[str]:
        return [preference for preference in query.get("preferences") or [] if preference in PLACE_TYPE_PREFERENCES]

    @classmethod
    def _should_expand_place_type_only_query(cls, query: dict) -> bool:
        if not query.get("is_sigungu") or not query.get("area_name"):
            return False
        if query.get("allow_region_expansion"):
            return False
        if query.get("conditions") or query.get("features") or query.get("required_evidence_terms"):
            return False
        return bool(cls._place_type_preferences(query))

    @staticmethod
    def _card_haystack(card: TourismPlaceCard) -> str:
        return " ".join(
            [
                card.title,
                card.address or "",
                card.recommendation_reason,
                " ".join(card.accessibility_tags),
                " ".join(card.family_tags),
                " ".join(f"{key} {value}" for key, value in card.raw_fields.items()),
            ]
        )

    @classmethod
    def _condition_evidence_score(cls, card: TourismPlaceCard, condition: str) -> int:
        haystack = cls._card_haystack(card)
        keywords = CONDITION_EVIDENCE_KEYWORDS.get(condition, [condition])
        matched = sum(1 for keyword in keywords if keyword in haystack)
        if not matched:
            return 0
        weight = 5 if condition == "유모차" else 4
        raw_key_bonus = 0
        raw_field_keys = CONDITION_RAW_FIELD_KEYS.get(condition, [condition])
        if any(keyword in key for key in card.raw_fields for keyword in raw_field_keys):
            raw_key_bonus = 4
        return weight + matched + raw_key_bonus

    @classmethod
    def _card_satisfies_condition(cls, card: TourismPlaceCard, condition: str, query: dict) -> bool:
        if cls._condition_evidence_score(card, condition) <= 0:
            return False
        conditions = set(query.get("conditions") or [])
        if query.get("require_all_conditions") and condition == "유모차" and "휠체어" in conditions:
            return cls._stroller_family_evidence_score(card) > 0
        return True

    @classmethod
    def _stroller_family_evidence_score(cls, card: TourismPlaceCard) -> int:
        haystack = cls._card_haystack(card)
        matched = sum(1 for keyword in STROLLER_FAMILY_EVIDENCE if keyword in haystack)
        raw_field_keys = ["유모차", "수유실", "영유아 가족 편의", "유아용 의자"]
        raw_key_bonus = 2 if any(keyword in key for key in card.raw_fields for keyword in raw_field_keys) else 0
        return matched + raw_key_bonus

    @classmethod
    def _preference_evidence_score(cls, card: TourismPlaceCard, preference: str) -> int:
        keywords = PREFERENCE_EVIDENCE_KEYWORDS.get(preference, PREFERENCE_KEYWORDS.get(preference, [preference]))
        matched = sum(1 for keyword in keywords if keyword in cls._card_haystack(card))
        return 0 if not matched else 3 + matched

    @classmethod
    def _preference_matches(cls, card: TourismPlaceCard, preference: str) -> bool:
        keywords = PREFERENCE_EVIDENCE_KEYWORDS.get(preference, PREFERENCE_KEYWORDS.get(preference, [preference]))
        haystack = cls._card_haystack(card)
        return any(keyword in haystack for keyword in keywords)

    @classmethod
    def _filter_cards_by_excluded_preferences(cls, cards: list[TourismPlaceCard], query: dict) -> list[TourismPlaceCard]:
        excluded_preferences = query.get("excluded_preferences") or []
        if not excluded_preferences:
            return cards
        filtered = [
            card
            for card in cards
            if not any(cls._preference_matches(card, preference) for preference in excluded_preferences)
        ]
        return filtered

    @staticmethod
    def _filter_cards_by_features(cards: list[TourismPlaceCard], query: dict) -> list[TourismPlaceCard]:
        features = query.get("features") or []
        if not features:
            return cards
        filtered = []
        for card in cards:
            haystack = " ".join(
                [
                    card.title,
                    card.address or "",
                    card.recommendation_reason,
                    " ".join(card.accessibility_tags),
                    " ".join(card.family_tags),
                    " ".join(card.raw_fields.values()),
                ]
            )
            if all(any(term in haystack for term in FEATURE_KEYWORDS.get(feature, [feature])) for feature in features):
                filtered.append(card)
        return filtered

    @staticmethod
    def _filter_cards_by_region(cards: list[TourismPlaceCard], region: str | None) -> list[TourismPlaceCard]:
        if not region:
            return cards
        variants = TourismChatService._area_name_variants(str(region))
        return [card for card in cards if TourismChatService._address_matches_area(card, variants)]

    @staticmethod
    def _filter_cards_by_query_region(cards: list[TourismPlaceCard], query: dict) -> list[TourismPlaceCard]:
        region = query.get("region")
        sigungu_name = query.get("sigungu_name")
        if not region:
            return cards
        area_name = query.get("area_name")
        terms = []
        if area_name:
            terms.append(("area", TourismChatService._area_name_variants(str(area_name))))
        if sigungu_name:
            terms.append(("sigungu", [str(sigungu_name)]))
        if not terms:
            terms.append(("area", TourismChatService._area_name_variants(str(region))))
        filtered = []
        for card in cards:
            if all(TourismChatService._address_matches_region_group(card, group_type, term_group) for group_type, term_group in terms):
                filtered.append(card)
        return filtered

    @staticmethod
    def _cards_include_outside_query_region(cards: list[TourismPlaceCard], query: dict) -> bool:
        if not cards or not query.get("is_sigungu") or not query.get("sigungu_name"):
            return False
        return len(TourismChatService._filter_cards_by_query_region(cards, query)) < len(cards)

    @staticmethod
    def _card_region_text(card: TourismPlaceCard) -> str:
        return card.address or ""

    @staticmethod
    def _address_matches_region_group(card: TourismPlaceCard, group_type: str, terms: list[str]) -> bool:
        if group_type == "area":
            return TourismChatService._address_matches_area(card, terms)
        address = TourismChatService._card_region_text(card)
        return any(term in address for term in terms)

    @staticmethod
    def _address_matches_area(card: TourismPlaceCard, terms: list[str]) -> bool:
        address = TourismChatService._card_region_text(card).lstrip()
        return any(address.startswith(term) for term in terms)

    @staticmethod
    def _area_name_variants(area_name: str) -> list[str]:
        variants = {
            "서울": ["서울", "서울특별시"],
            "서울특별시": ["서울", "서울특별시"],
            "부산": ["부산", "부산광역시"],
            "부산광역시": ["부산", "부산광역시"],
            "대구": ["대구", "대구광역시"],
            "대구광역시": ["대구", "대구광역시"],
            "인천": ["인천", "인천광역시"],
            "인천광역시": ["인천", "인천광역시"],
            "광주": ["광주", "광주광역시"],
            "광주광역시": ["광주", "광주광역시"],
            "대전": ["대전", "대전광역시"],
            "대전광역시": ["대전", "대전광역시"],
            "울산": ["울산", "울산광역시"],
            "울산광역시": ["울산", "울산광역시"],
            "세종": ["세종", "세종특별자치시"],
            "세종특별자치시": ["세종", "세종특별자치시"],
            "경기": ["경기", "경기도"],
            "경기도": ["경기", "경기도"],
            "강원": ["강원", "강원도", "강원특별자치도"],
            "강원도": ["강원", "강원도", "강원특별자치도"],
            "강원특별자치도": ["강원", "강원도", "강원특별자치도"],
            "충북": ["충북", "충청북도"],
            "충청북도": ["충북", "충청북도"],
            "충남": ["충남", "충청남도"],
            "충청남도": ["충남", "충청남도"],
            "전북": ["전북", "전라북도", "전북특별자치도"],
            "전라북도": ["전북", "전라북도", "전북특별자치도"],
            "전북특별자치도": ["전북", "전라북도", "전북특별자치도"],
            "전남": ["전남", "전라남도"],
            "전라남도": ["전남", "전라남도"],
            "경북": ["경북", "경상북도"],
            "경상북도": ["경북", "경상북도"],
            "경남": ["경남", "경상남도"],
            "경상남도": ["경남", "경상남도"],
            "제주": ["제주", "제주도", "제주특별자치도"],
            "제주도": ["제주", "제주도", "제주특별자치도"],
            "제주특별자치도": ["제주", "제주도", "제주특별자치도"],
        }
        return variants.get(area_name, [area_name])

    def _build_answer(
        self,
        cards: list[TourismPlaceCard],
        query: dict,
        expanded: bool = False,
        reasoning_notes: list[str] | None = None,
        live_top_up_available: bool = False,
    ) -> str:
        region = self._display_region(query)
        focus_label = self._query_focus_label(query)
        area_name = query.get("area_name") or "상위 지역"
        if expanded:
            if query.get("conditional_region_expansion"):
                expansion_reason = f"{region} 안의 후보가 부족해"
            else:
                expansion_reason = "요청대로"
            lines = [
                f"{expansion_reason} {area_name} 범위까지 넓혀 {focus_label}에 맞는 후보 {len(cards)}곳을 추천합니다."
            ]
        else:
            lines = [f"{region} 기준으로 {focus_label}에 맞는 후보 {len(cards)}곳을 추천합니다."]
        if query.get("legacy_region_notice"):
            lines.append(str(query["legacy_region_notice"]))
        if query.get("is_sigungu") and len(cards) < DEFAULT_CARD_LIMIT and not expanded:
            lines.append(
                f"{region} 안에서 확인된 후보가 {len(cards)}곳이라 요청 지역 안의 결과만 먼저 제공합니다. "
                "더 많은 후보가 필요하면 '서울 전체로 넓혀줘'처럼 상위 지역 확장을 명확히 말해 주세요."
            )
        scope_note = self._build_scope_note(query)
        if scope_note:
            lines.append(scope_note)
        if reasoning_notes:
            lines.append(f"복합 조건을 반영해 후보 순서를 조정했습니다. 확인 필요: {', '.join(reasoning_notes)}")
        for index, card in enumerate(cards, start=1):
            basis = self._build_card_basis(card, query)
            lines.append(f"{index}. {card.title}: {basis}. 출처는 {self._public_source_name(card.source_name)}입니다.")
        if live_top_up_available:
            lines.append("지금 확인된 후보를 먼저 보여드렸습니다. 더 찾아보려면 '최신 추천 더 확인하기'를 눌러 주세요.")
        lines.append("방문 전 운영시간과 편의시설 위치는 현장 상황에 따라 달라질 수 있어 공식 안내나 전화로 한 번 더 확인해 주세요.")
        return "\n".join(lines)

    @staticmethod
    def _query_focus_label(query: dict) -> str:
        conditions = query.get("conditions") or []
        if conditions:
            return f"{', '.join(conditions)} 조건"
        preferences = [
            PREFERENCE_DISPLAY_LABELS.get(preference, str(preference))
            for preference in query.get("preferences") or []
        ]
        if preferences:
            return f"{', '.join(dict.fromkeys(preferences))} 요청"
        return "확인 가능한 무장애/가족 친화 정보"

    @staticmethod
    def _display_region(query: dict) -> str:
        region = str(query.get("region") or "")
        area_name = str(query.get("area_name") or "")
        sigungu_name = str(query.get("sigungu_name") or "")
        if query.get("is_sigungu") and area_name and sigungu_name and sigungu_name not in region:
            return f"{area_name} {sigungu_name}"
        return region or "요청 지역"

    @staticmethod
    def _build_card_basis(card: TourismPlaceCard, query: dict) -> str:
        tags = [*card.accessibility_tags, *card.family_tags]
        evidence = TourismChatService._select_raw_evidence(card, query)
        basis_parts = []
        matching_tags = TourismChatService._select_condition_tags(tags, query)
        if matching_tags:
            basis_parts.append(", ".join(matching_tags[:3]))
        elif not evidence and tags:
            basis_parts.append(", ".join(tags[:3]))
        basis_parts.extend(evidence)
        if not basis_parts:
            return "세부 편의정보 확인 필요"
        return " / ".join(basis_parts[:3])

    @staticmethod
    def _select_condition_tags(tags: list[str], query: dict) -> list[str]:
        conditions = query.get("conditions") or []
        if not conditions:
            return []
        preferred_keywords: list[str] = []
        for condition in conditions:
            preferred_keywords.extend(CONDITION_EVIDENCE_KEYWORDS.get(condition, [condition]))
        if not preferred_keywords:
            return []
        return [tag for tag in tags if any(keyword in tag for keyword in preferred_keywords)]

    @staticmethod
    def _select_raw_evidence(card: TourismPlaceCard, query: dict) -> list[str]:
        conditions = query.get("conditions") or []
        preferred_keywords = []
        for condition in conditions:
            preferred_keywords.extend(CONDITION_EVIDENCE_KEYWORDS.get(condition, [condition]))
        evidence = []
        for key, value in card.raw_fields.items():
            text = f"{key}: {value}".strip()
            if not text:
                continue
            if preferred_keywords and not any(keyword in text for keyword in preferred_keywords):
                continue
            evidence.append(TourismChatService._shorten_evidence(text))
            if len(evidence) >= 2:
                break
        if evidence:
            return evidence
        for key, value in card.raw_fields.items():
            text = f"{key}: {value}".strip()
            if text:
                evidence.append(TourismChatService._shorten_evidence(text))
            if len(evidence) >= 1:
                break
        return evidence

    @staticmethod
    def _shorten_evidence(text: str, limit: int = 54) -> str:
        normalized = re.sub(r"\s+", " ", text.replace("<br/>", " ")).strip()
        if len(normalized) <= limit:
            return normalized
        return f"{normalized[:limit].rstrip()}..."

    @staticmethod
    def _build_region_clarification_answer(query: dict) -> str:
        alias = query.get("ambiguous_region") or "해당 지역"
        candidates = query.get("ambiguous_region_candidates") or []
        options = []
        for candidate in candidates:
            area_name = candidate.get("area_name")
            sigungu_name = candidate.get("sigungu_name") or alias
            if area_name and sigungu_name:
                options.append(str(area_name) if area_name == sigungu_name else f"{area_name} {sigungu_name}")
        option_text = ", ".join(dict.fromkeys(options))
        if not option_text:
            return f"'{alias}' 지역이 여러 곳에 있어 어느 지역인지 먼저 알려 주세요."
        return (
            f"'{alias}'는 여러 시도에 있는 지명이라 바로 추천하기 어렵습니다. "
            f"어느 지역인지 함께 적어 주세요. 예: {option_text}"
        )

    @staticmethod
    def _build_region_clarification_suggestions(query: dict, message: str) -> list[str]:
        alias = query.get("ambiguous_region") or ""
        candidates = query.get("ambiguous_region_candidates") or []
        conditions = query.get("conditions") or ["무장애"]
        condition_text = " ".join(str(condition) for condition in conditions[:2])
        suggestions = []
        for candidate in candidates:
            area_name = candidate.get("area_name")
            sigungu_name = candidate.get("sigungu_name") or alias
            if area_name and sigungu_name:
                region_text = str(area_name) if area_name == sigungu_name else f"{area_name} {sigungu_name}"
                if alias and alias in message:
                    suggestions.append(message.replace(alias, region_text, 1))
                else:
                    suggestions.append(f"{region_text}에서 {condition_text} 관광지 추천해줘")
        return list(dict.fromkeys(suggestions))

    @staticmethod
    def _build_condition_clarification_answer(query: dict) -> str:
        region = query.get("region") or "해당 지역"
        options = TourismChatService._condition_clarification_options(query)
        option_text = ", ".join(options)
        return (
            f"{region} 요청의 접근성 의미가 조금 애매합니다. "
            f"{option_text} 중 어떤 기준을 우선할지 알려 주세요."
        )

    @staticmethod
    def _build_condition_clarification_suggestions(query: dict) -> list[str]:
        region = query.get("region") or "서울"
        suggestions = []
        for condition in TourismChatService._condition_clarification_options(query):
            suggestions.append(f"{region}에서 {condition} 관광지 추천해줘")
        return suggestions

    @classmethod
    def _build_no_card_answer(cls, query: dict, region_text: str, candidates: list[TourismPlaceCard]) -> str:
        alternative_note = cls._build_alternative_evidence_note(query, candidates)
        if alternative_note:
            return (
                f"{region_text} 기준으로 정확히 요청한 접근성 근거가 확인된 카드는 찾지 못했습니다. "
                f"{alternative_note} 지역이나 접근성 조건을 조금 넓혀 다시 질문해 주세요."
            )
        return f"{region_text} 기준으로 조건에 맞는 관광지를 확인하지 못했습니다. 지역이나 접근성 조건을 조금 넓혀 다시 질문해 주세요."

    @classmethod
    def _build_alternative_evidence_note(cls, query: dict, candidates: list[TourismPlaceCard]) -> str | None:
        if not candidates:
            return None
        required_groups = query.get("required_evidence_terms") or []
        alternative_groups = query.get("alternative_evidence_terms") or []
        if not required_groups and not alternative_groups:
            return None

        scoped = cls._filter_cards_by_query_region(cls._deduplicate(candidates), query) if query.get("region") else cls._deduplicate(candidates)
        if not scoped:
            return None
        condition_candidates = cls._filter_cards_by_conditions(scoped, query)
        if not condition_candidates:
            return None
        exact_candidates = cls._filter_cards_by_required_evidence_terms(condition_candidates, query)
        if exact_candidates:
            return None

        requested = cls._display_required_evidence_groups([*required_groups, *alternative_groups])
        alternatives = cls._summarize_alternative_evidence(condition_candidates)
        if alternatives:
            return f"다만 같은 범주의 대체 근거({alternatives})가 있는 후보는 확인됩니다. 요청하신 기준은 {requested}로 더 엄격하게 보았습니다."
        return f"다만 관련 접근성 후보는 있으나 요청하신 기준({requested})과 직접 일치하는 근거는 부족합니다."

    @staticmethod
    def _display_required_evidence_groups(required_groups: list[list[str]]) -> str:
        displays = []
        for group in required_groups:
            if any(term in group for term in ["수어", "수화"]):
                displays.append("수어/수화")
            elif any(term in group for term in ["자막", "문자안내", "영상안내"]):
                displays.append("자막/문자안내")
            elif any(term in group for term in ["점자", "점자블록"]):
                displays.append("점자/점자블록")
            elif any("촉지" in term for term in group):
                displays.append("촉지도")
            elif any(term in group for term in ["보조견", "안내견"]):
                displays.append("보조견/안내견")
            else:
                displays.append("/".join(str(term) for term in group[:3]))
        return ", ".join(dict.fromkeys(displays))

    @classmethod
    def _summarize_alternative_evidence(cls, cards: list[TourismPlaceCard]) -> str:
        labels = []
        haystack = " ".join(cls._card_haystack(card) for card in cards)
        for label, terms in [
            ("자막/영상안내", ["자막", "문자안내", "영상안내"]),
            ("오디오가이드/음성안내", ["오디오가이드", "음성안내", "음성 안내"]),
            ("점자블록", ["점자블록"]),
            ("촉지도", ["촉지도", "촉지 안내도", "촉지안내도", "촉지 안내판", "촉지안내판", "촉지판", "촉지"]),
            ("보조견", ["보조견", "안내견"]),
        ]:
            if any(term in haystack for term in terms):
                labels.append(label)
        return ", ".join(list(dict.fromkeys(labels))[:3])

    @staticmethod
    def _condition_clarification_options(query: dict) -> list[str]:
        ambiguous = list(query.get("ambiguous_conditions") or [])
        label_map = {
            "휠체어": "휠체어 접근",
            "접근로": "입구/동선 접근로",
            "고령자": "어르신 이동 부담 적은 곳",
        }
        options = [label_map.get(condition, str(condition)) for condition in ambiguous]
        return list(dict.fromkeys(options)) or ["휠체어 접근", "입구/동선 접근로", "어르신 이동 부담 적은 곳"]

    @staticmethod
    def _build_missing_region_suggestions(query: dict) -> list[str]:
        conditions = query.get("conditions") or ["무장애"]
        condition_text = " ".join(str(condition) for condition in conditions[:2])
        return [
            f"서울에서 {condition_text} 관광지 추천해줘",
            f"부산에서 {condition_text} 관광지 추천해줘",
            f"제주에서 {condition_text} 관광지 추천해줘",
        ]

    @staticmethod
    def _build_unsupported_core_clarification_answer(query: dict) -> str:
        region = query.get("region") or "해당 지역"
        return (
            f"{region} 질문에 포함된 핵심 조건은 현재 관광지 접근성 카드로 확인하기 어렵습니다. "
            "그 조건을 빼고 무장애/가족 편의 관광지 기준으로 추천할지 먼저 확인해 주세요."
        )

    @staticmethod
    def _build_unsupported_core_suggestions(query: dict) -> list[str]:
        region = query.get("region") or "서울"
        conditions = [condition for condition in (query.get("conditions") or []) if condition not in {"대중교통"}]
        condition_text = " ".join(str(condition) for condition in conditions[:2]) or "무장애"
        return [f"{region}에서 {condition_text} 관광지 추천해줘"]

    @staticmethod
    def _build_general_tourism_scope_answer(query: dict) -> str:
        region = query.get("region") or "해당 지역"
        return (
            f"죄송합니다. 현재 챗봇은 {region}의 일반 관광지, 식당, 카페 전체 목록이 아니라 "
            "무장애 관광 연관 장소만 제공하고 있습니다. "
            "휠체어, 유모차, 장애인 화장실, 점자, 수어/자막처럼 확인할 접근성 조건을 함께 알려주시면 "
            "보유한 무장애 관광 카드 기준으로 추천하겠습니다."
        )

    @staticmethod
    def _build_general_tourism_scope_suggestions(query: dict) -> list[str]:
        region = query.get("region") or "서울"
        return [
            f"{region}에서 휠체어 접근 가능한 관광지 추천해줘",
            f"{region}에서 장애인 화장실 있는 관광지 추천해줘",
            f"{region}에서 유모차로 갈 만한 관광지 추천해줘",
        ]

    @staticmethod
    def _build_no_card_suggestions(query: dict) -> list[str]:
        conditions = [str(condition) for condition in query.get("conditions") or []]
        condition_text = " ".join(conditions[:2]) or "무장애"
        region = query.get("region") or "서울"
        suggestions = []
        if query.get("is_sigungu") and query.get("area_name"):
            suggestions.append(f"{region}에서 {condition_text} 관광지 추천해줘")
            suggestions.append(f"{query['area_name']} 전체로 넓혀서 {condition_text} 관광지 추천해줘")
        elif region:
            suggestions.append(f"{region}에서 무장애 관광지 추천해줘")
        if conditions:
            suggestions.append(f"{region}에서 무장애 관광지 추천해줘")
        return list(dict.fromkeys(suggestions))[:3]

    @staticmethod
    def _build_more_card_suggestions(message: str, has_more_cards: bool) -> list[str]:
        if not has_more_cards or TourismChatService._requests_more_cards(message):
            return []
        return [f"{TourismChatService._strip_followup_intent(message)} 더 보기"]

    def _build_suggestions(
        self,
        message: str,
        has_more_cards: bool,
        cards: list[TourismPlaceCard],
        query: dict,
        lookup_mode: str,
        live_update_pending: bool = False,
    ) -> list[str]:
        suggestions = self._build_more_card_suggestions(message, has_more_cards)
        live_top_up_suggested = self._should_suggest_live_top_up(message, cards, query, lookup_mode)
        if live_top_up_suggested:
            suggestions.append(f"{self._strip_followup_intent(message)} 최신 추천 더 확인하기")
        if (
            not live_top_up_suggested
            and cards
            and len(cards) < DEFAULT_CARD_LIMIT
            and query.get("is_sigungu")
            and query.get("area_name")
            and (not query.get("allow_region_expansion") or query.get("conditional_region_expansion"))
        ):
            condition_text = " ".join(str(condition) for condition in (query.get("conditions") or [])[:2]) or "무장애"
            suggestions.append(f"{query['area_name']} 전체로 넓혀서 {condition_text} 관광지 추천해줘")
        return list(dict.fromkeys(suggestions))

    @staticmethod
    def _limit_cards(cards: list[TourismPlaceCard], more_requested: bool) -> list[TourismPlaceCard]:
        if more_requested:
            return cards
        return cards[:DEFAULT_CARD_LIMIT]

    @staticmethod
    def _has_more_cards(cards: list[TourismPlaceCard], more_requested: bool) -> bool:
        return not more_requested and len(cards) > DEFAULT_CARD_LIMIT

    @staticmethod
    def _requests_more_cards(message: str) -> bool:
        return any(keyword in message for keyword in MORE_CARD_KEYWORDS)

    @staticmethod
    def _requests_live_top_up(message: str) -> bool:
        return any(keyword in message for keyword in LIVE_TOP_UP_KEYWORDS)

    @staticmethod
    def _message_mentions_area(message: str, area_name: str) -> bool:
        return any(area in message for area in TourismChatService._area_name_variants(area_name))

    @staticmethod
    def _public_source_name(source_name: str | None) -> str:
        if not source_name:
            return "한국관광공사 무장애 여행 정보"
        return source_name.replace(" OpenAPI", "")

    def _should_suggest_live_top_up(
        self,
        message: str,
        cards: list[TourismPlaceCard],
        query: dict,
        lookup_mode: str,
    ) -> bool:
        if self._requests_live_top_up(message):
            return False
        if lookup_mode in {"live", "live_top_up"}:
            return False
        if len(cards) >= DEFAULT_CARD_LIMIT:
            return False
        return self._can_use_live_tour_api(query)

    @staticmethod
    def _strip_followup_intent(message: str) -> str:
        text = message.strip()
        for keyword in [*MORE_CARD_KEYWORDS, *LIVE_TOP_UP_KEYWORDS]:
            text = text.replace(keyword, "")
        return " ".join(text.split())

    def _build_sources(self, contexts: list[dict], cards: list[TourismPlaceCard]) -> list[Source]:
        sources = []
        card_ids = {card.content_id for card in cards}
        sourced_card_ids = set()
        for context in contexts:
            context_card = self.card_codec.from_markdown(context.get("text") or "")
            if card_ids and (not context_card or context_card.content_id not in card_ids):
                continue
            metadata = context.get("metadata") or {}
            source = metadata.get("source") or metadata.get("file_path")
            if source:
                sources.append(
                    Source(
                        source=source,
                        page=metadata.get("page"),
                        chunk_id=context.get("id") or "",
                        chunk_index=metadata.get("chunk_index"),
                        distance=context.get("distance"),
                    )
                )
                if context_card:
                    sourced_card_ids.add(context_card.content_id)

        for card in cards:
            if card.content_id not in sourced_card_ids:
                sources.append(
                    Source(source=card.source_name, page=None, chunk_id=card.content_id, chunk_index=None, distance=None)
                )
        return sources

    @staticmethod
    def _build_warnings(query: dict, degraded: bool) -> list[str]:
        warnings = []
        if degraded:
            warnings.append("일부 자료 확인이 원활하지 않아 먼저 확인된 자료로 안내했습니다.")
        cache_warning = query.get("region_cache_warning")
        if cache_warning:
            warnings.append(str(cache_warning))
        if query.get("unsupported_intent"):
            warnings.append("현재 서비스에서 바로 확인하기 어려운 요청은 제외하고, 관광지 접근성 카드 근거 안에서만 답변했습니다.")
        return warnings

    @staticmethod
    def _has_supported_tourism_part(query: dict) -> bool:
        supported_conditions = [condition for condition in query.get("conditions") or [] if condition != "대중교통"]
        if supported_conditions:
            return bool(query.get("region"))
        return bool(query.get("region") and "대중교통" in (query.get("conditions") or []) and query.get("excluded_conditions"))

    @staticmethod
    def _is_general_tourism_only_query(query: dict) -> bool:
        if query.get("unsupported_intent"):
            return False
        supported_conditions = [condition for condition in query.get("conditions") or [] if condition != "대중교통"]
        if supported_conditions:
            return False
        if "대중교통" in (query.get("conditions") or []) and query.get("excluded_conditions"):
            return False
        if query.get("required_evidence_terms"):
            return True
        if query.get("alternative_evidence_terms"):
            return True
        return bool(query.get("preferences") or query.get("features") or query.get("region"))

    @staticmethod
    def _should_clarify_unsupported_core(query: dict) -> bool:
        return query.get("unsupported_intent") == "subway_direct"

    @staticmethod
    def _build_scope_note(query: dict) -> str | None:
        intent = query.get("unsupported_intent")
        if not intent:
            return None
        return (
            "다만 질문에 포함된 가격 비교, 실시간 혼잡도, 의료기관, 예약, 이동시간 계산 같은 요청은 "
            "현재 서비스에서 확인할 수 있는 데이터 범위 밖이라 단정하지 않습니다. 아래 추천은 관광지 접근성 카드 근거에 한정합니다."
        )

    @staticmethod
    def _deduplicate(cards: list[TourismPlaceCard]) -> list[TourismPlaceCard]:
        result = []
        seen = set()
        for card in cards:
            if card.content_id in seen:
                continue
            seen.add(card.content_id)
            result.append(card)
        return result

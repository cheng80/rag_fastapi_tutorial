from pathlib import Path
import json
import threading
import time

from app.core.config import Settings
from app.schemas.tourism import AccessibilityInfo, TourismPlaceCard
from app.services.tour_api_service import TourAPIError
from app.services.tourism_chat_service import TourismChatService
from app.services.tourism_normalizer import TourismNormalizer
from app.services.tourism_query_event_logger import TourismQueryEventLogger
from app.services.tourism_query_service import TourismQueryService


class FakeRetriever:
    def retrieve(self, message: str):
        return [
            {
                "id": "chunk-1",
                "text": Path("data/raw/tourism_accessible/seoul_sample_001.md").read_text(encoding="utf-8"),
                "metadata": {"source": "data/raw/tourism_accessible/seoul_sample_001.md", "chunk_index": 0},
                "distance": 0.1,
            },
            {
                "id": "chunk-2",
                "text": Path("data/raw/tourism_accessible/seoul_sample_002.md").read_text(encoding="utf-8"),
                "metadata": {"source": "data/raw/tourism_accessible/seoul_sample_002.md", "chunk_index": 0},
                "distance": 0.2,
            },
            {
                "id": "chunk-3",
                "text": Path("data/raw/tourism_accessible/busan_sample_001.md").read_text(encoding="utf-8"),
                "metadata": {"source": "data/raw/tourism_accessible/busan_sample_001.md", "chunk_index": 0},
                "distance": 0.3,
            },
        ]


class EmptyRetriever:
    def retrieve(self, message: str):
        return []


class FakeLLMService:
    def __init__(self, response: str):
        self.response = response
        self.prompts = []

    def generate(self, prompt: str) -> str:
        self.prompts.append(prompt)
        return self.response


def tourism_settings(**overrides):
    defaults = {
        "tourism_lookup_strategy": "cache_first",
        "tourism_reasoning_assist_enabled": False,
        "tourism_condition_transformer_enabled": False,
    }
    defaults.update(overrides)
    return Settings(**defaults)


def test_tourism_chat_returns_cards_and_sources(tmp_path):
    service = TourismChatService(tourism_settings(tourism_live_cache_path=tmp_path / "live_cache"), FakeRetriever(), TourismQueryService())

    response = service.answer("서울에서 휠체어와 유모차로 가기 좋은 곳 추천해줘")

    assert len(response.cards) == 2
    assert response.cards[0].title == "서울어린이대공원"
    assert response.lookup_mode == "indexed"
    assert response.sources[0].source == "data/raw/tourism_accessible/seoul_sample_001.md"
    assert all("seoul" in source.source for source in response.sources)
    assert "출처" in response.answer


def test_tourism_chat_uses_reasoning_assist_for_complex_question(tmp_path):
    llm = FakeLLMService(
        '{"ranked_ids":["sample-seoul-002","sample-seoul-001"],'
        '"missing_or_uncertain":["혼잡도는 확인 필요"]}'
    )
    service = TourismChatService(
        tourism_settings(tourism_reasoning_assist_enabled=True, tourism_live_cache_path=tmp_path / "live_cache"),
        FakeRetriever(),
        TourismQueryService(),
        llm_service=llm,
    )

    response = service.answer("서울에서 휠체어 타는 아버지와 아이가 비 오면 이동하기 편한 실내 관광지 추천")

    assert response.reasoning_assist_used is True
    assert response.reasoning_assist_notes == ["혼잡도는 확인 필요"]
    assert response.cards[0].title == "국립중앙박물관"
    assert "복합 조건을 반영해 후보 순서를 조정했습니다" in response.answer
    assert "후보 카드에 없는 장소나 접근성 정보를 만들지 않는다" in llm.prompts[0]


def test_tourism_chat_disables_reasoning_assist_by_default(tmp_path):
    llm = FakeLLMService(
        '{"ranked_ids":["sample-seoul-002","sample-seoul-001"],'
        '"missing_or_uncertain":["혼잡도는 확인 필요"]}'
    )
    service = TourismChatService(
        tourism_settings(tourism_live_cache_path=tmp_path / "live_cache"),
        FakeRetriever(),
        TourismQueryService(),
        llm_service=llm,
    )

    response = service.answer("서울에서 휠체어 타는 아버지와 아이가 비 오면 이동하기 편한 실내 관광지 추천")

    assert response.reasoning_assist_used is False
    assert response.reasoning_assist_notes == []
    assert response.cards[0].title == "국립중앙박물관"
    assert llm.prompts == []


def test_tourism_chat_skips_reasoning_assist_for_simple_question(tmp_path):
    llm = FakeLLMService('{"ranked_ids":["sample-seoul-002"]}')
    service = TourismChatService(
        tourism_settings(tourism_reasoning_assist_enabled=True, tourism_live_cache_path=tmp_path / "live_cache"),
        FakeRetriever(),
        TourismQueryService(),
        llm_service=llm,
    )

    response = service.answer("서울에서 휠체어 관광지 추천")

    assert response.reasoning_assist_used is False
    assert response.cards[0].title == "서울어린이대공원"
    assert llm.prompts == []


def test_tourism_chat_keeps_existing_order_when_reasoning_assist_fails(tmp_path):
    llm = FakeLLMService("not-json")
    service = TourismChatService(
        tourism_settings(tourism_reasoning_assist_enabled=True, tourism_live_cache_path=tmp_path / "live_cache"),
        FakeRetriever(),
        TourismQueryService(),
        llm_service=llm,
    )

    response = service.answer("서울에서 휠체어 타는 아버지와 아이가 비 오면 이동하기 편한 실내 관광지 추천")

    assert response.reasoning_assist_used is False
    assert response.cards[0].title == "국립중앙박물관"


def test_tourism_chat_prefers_live_tour_api_when_available(tmp_path):
    class FakeTourAPI:
        def __init__(self):
            self.list_calls = 0
            self.detail_common_calls = 0
            self.detail_with_tour_calls = 0

        def accessible_area_based_list(self, area_code: str, sigungu_code=None, num_of_rows=10):
            self.list_calls += 1
            return [{"contentid": "live-1"}, {"contentid": "live-2"}]

        def detail_common(self, content_id: str):
            self.detail_common_calls += 1
            return {
                "contentid": content_id,
                "title": f"Live 관광지 {content_id}",
                "addr1": "서울 중구",
            }

        def detail_with_tour(self, content_id: str):
            self.detail_with_tour_calls += 1
            return {"contentid": content_id, "wheelchair": "주 출입구 휠체어 접근 가능"}

    tour_api = FakeTourAPI()
    service = TourismChatService(
        tourism_settings(
            tour_api_service_key="test",
            tour_api_accessible_service_key="test",
            tourism_live_rows=2,
            tourism_live_max_detail_calls=4,
            tourism_live_cache_path=tmp_path / "live_cache",
            tourism_sample_path=tmp_path / "samples",
        ),
        EmptyRetriever(),
        TourismQueryService(),
        tour_api_service=tour_api,
    )

    response = service.answer("서울에서 휠체어 관광지 추천")

    assert [card.content_id for card in response.cards] == ["live-1", "live-2"]
    assert response.lookup_mode == "live"
    assert response.degraded is False
    assert response.sources[0].source == "한국관광공사 무장애 여행 정보"
    assert tour_api.list_calls == 1
    assert tour_api.detail_common_calls == 2
    assert tour_api.detail_with_tour_calls == 2


def test_tourism_chat_uses_indexed_cards_before_live_tour_api(tmp_path):
    class CountingTourAPI:
        def __init__(self):
            self.list_calls = 0

        def accessible_area_based_list(self, area_code: str, sigungu_code=None, num_of_rows=10):
            self.list_calls += 1
            return [{"contentid": "should-not-call"}]

    tour_api = CountingTourAPI()
    service = TourismChatService(
        tourism_settings(
            tour_api_service_key="test",
            tour_api_accessible_service_key="test",
            tourism_live_cache_path=tmp_path / "live_cache",
            tourism_sample_path=tmp_path / "samples",
        ),
        FakeRetriever(),
        TourismQueryService(),
        tour_api_service=tour_api,
    )

    response = service.answer("서울에서 휠체어 관광지 추천")

    assert response.lookup_mode == "indexed"
    assert response.cards[0].title == "서울어린이대공원"
    assert tour_api.list_calls == 0


def test_tourism_chat_caches_live_tour_api_region_results(tmp_path):
    class FakeTourAPI:
        def __init__(self):
            self.list_calls = 0

        def accessible_area_based_list(self, area_code: str, sigungu_code=None, num_of_rows=10):
            self.list_calls += 1
            return [{"contentid": "live-cache"}]

        def detail_common(self, content_id: str):
            return {"contentid": content_id, "title": "Live 캐시 관광지", "addr1": "서울 중구"}

        def detail_with_tour(self, content_id: str):
            return {"contentid": content_id, "wheelchair": "휠체어 접근 가능", "stroller": "유모차 대여 가능"}

    tour_api = FakeTourAPI()
    service = TourismChatService(
        tourism_settings(
            tour_api_service_key="test",
            tour_api_accessible_service_key="test",
            tourism_live_cache_path=tmp_path / "live_cache",
            tourism_sample_path=tmp_path / "samples",
        ),
        EmptyRetriever(),
        TourismQueryService(),
        tour_api_service=tour_api,
    )

    assert service.answer("서울 휠체어 관광지").cards[0].title == "Live 캐시 관광지"
    assert service.answer("서울 유모차 관광지").cards[0].title == "Live 캐시 관광지"
    assert tour_api.list_calls == 1


def test_tourism_chat_reads_persisted_live_markdown_before_api_call(tmp_path):
    live_cache_dir = tmp_path / "live_cache"
    live_cache_dir.mkdir()
    card = TourismPlaceCard(
        content_id="persisted-live",
        title="저장된 라이브 관광지",
        address="서울 중구",
        recommendation_reason="휠체어 접근 정보가 확인되었습니다.",
        accessibility_tags=["휠체어 접근"],
    )
    (live_cache_dir / "서울_persisted-live.md").write_text(TourismNormalizer().card_to_markdown(card), encoding="utf-8")

    class CountingTourAPI:
        def __init__(self):
            self.list_calls = 0

        def accessible_area_based_list(self, area_code: str, sigungu_code=None, num_of_rows=10):
            self.list_calls += 1
            return [{"contentid": "should-not-call"}]

    tour_api = CountingTourAPI()
    service = TourismChatService(
        tourism_settings(
            tour_api_service_key="test",
            tour_api_accessible_service_key="test",
            tourism_live_cache_path=live_cache_dir,
            tourism_sample_path=tmp_path / "samples",
        ),
        EmptyRetriever(),
        TourismQueryService(),
        tour_api_service=tour_api,
    )

    response = service.answer("서울에서 휠체어 관광지 추천")

    assert response.cards[0].title == "저장된 라이브 관광지"
    assert response.lookup_mode == "cache"
    assert tour_api.list_calls == 0


def test_tourism_chat_persists_live_tour_api_cards_to_markdown(tmp_path):
    live_cache_dir = tmp_path / "live_cache"

    class FakeTourAPI:
        def accessible_area_based_list(self, area_code: str, sigungu_code=None, num_of_rows=10):
            return [{"contentid": "live-persist"}]

        def detail_common(self, content_id: str):
            return {"contentid": content_id, "title": "저장 대상 관광지", "addr1": "서울 중구"}

        def detail_with_tour(self, content_id: str):
            return {"contentid": content_id, "wheelchair": "휠체어 접근 가능"}

    service = TourismChatService(
        tourism_settings(
            tour_api_service_key="test",
            tour_api_accessible_service_key="test",
            tourism_live_cache_path=live_cache_dir,
            tourism_sample_path=tmp_path / "samples",
        ),
        EmptyRetriever(),
        TourismQueryService(),
        tour_api_service=FakeTourAPI(),
    )

    response = service.answer("서울에서 휠체어 관광지 추천")

    assert response.lookup_mode == "live"
    cached_files = list(live_cache_dir.glob("*.md"))
    assert len(cached_files) == 1
    assert "저장 대상 관광지" in cached_files[0].read_text(encoding="utf-8")


def test_tourism_chat_live_update_returns_live_when_ready_before_grace(tmp_path):
    class FastTourAPI:
        def accessible_area_based_list(self, area_code: str, sigungu_code=None, num_of_rows=10):
            time.sleep(0.01)
            return [{"contentid": "live-fast"}]

        def detail_common(self, content_id: str):
            return {"contentid": content_id, "title": "빠른 최신 관광지", "addr1": "서울 중구"}

        def detail_with_tour(self, content_id: str):
            return {"contentid": content_id, "wheelchair": "휠체어 접근 가능"}

    service = TourismChatService(
        tourism_settings(
            tourism_lookup_strategy="live_update",
            tourism_live_first_wait_seconds=0.05,
            tourism_live_background_timeout_seconds=0.2,
            tour_api_service_key="test",
            tour_api_accessible_service_key="test",
            tourism_live_cache_path=tmp_path / "live_cache",
            tourism_sample_path=tmp_path / "samples",
        ),
        FakeRetriever(),
        TourismQueryService(),
        tour_api_service=FastTourAPI(),
    )

    response = service.answer("서울에서 휠체어 관광지 추천", session_id="s-fast")

    assert response.lookup_mode == "live"
    assert response.live_update_pending is False
    assert response.cards[0].title == "빠른 최신 관광지"


def test_tourism_chat_live_update_fallback_then_pending_update(tmp_path):
    class SlowTourAPI:
        def accessible_area_based_list(self, area_code: str, sigungu_code=None, num_of_rows=10):
            time.sleep(0.08)
            return [{"contentid": "live-slow"}]

        def detail_common(self, content_id: str):
            return {"contentid": content_id, "title": "늦게 온 최신 관광지", "addr1": "서울 중구"}

        def detail_with_tour(self, content_id: str):
            return {"contentid": content_id, "wheelchair": "휠체어 접근 가능"}

    service = TourismChatService(
        tourism_settings(
            tourism_lookup_strategy="live_update",
            tourism_live_first_wait_seconds=0.02,
            tourism_live_background_timeout_seconds=30.0,
            tour_api_service_key="test",
            tour_api_accessible_service_key="test",
            tourism_live_cache_path=tmp_path / "live_cache",
            tourism_sample_path=tmp_path / "samples",
        ),
        FakeRetriever(),
        TourismQueryService(),
        tour_api_service=SlowTourAPI(),
    )

    first = service.answer("서울에서 휠체어 관광지 추천", session_id="s-slow")

    assert first.lookup_mode == "indexed"
    assert first.live_update_pending is True
    assert "최신 결과 업데이트 보기" not in first.suggested_messages

    update = service.answer("최신 결과 업데이트 보기", session_id="s-slow")
    for _ in range(50):
        if update.lookup_mode == "live_update":
            break
        time.sleep(0.1)
        update = service.answer("최신 결과 업데이트 보기", session_id="s-slow")

    assert update.lookup_mode == "live_update"
    assert update.live_update_pending is False
    assert update.cards[0].title == "늦게 온 최신 관광지"
    assert "새로운 최신 추천 결과" in update.answer


def test_tourism_chat_live_update_does_not_start_second_sync_live_call_after_grace(tmp_path):
    calls = 0
    lock = threading.Lock()

    class SlowTourAPI:
        def accessible_area_based_list(self, area_code: str, sigungu_code=None, num_of_rows=10):
            nonlocal calls
            with lock:
                calls += 1
            time.sleep(0.2)
            return [{"contentid": "live-slow-no-sync"}]

        def detail_common(self, content_id: str):
            return {"contentid": content_id, "title": "동기 재호출 방지 관광지", "addr1": "서울 중구"}

        def detail_with_tour(self, content_id: str):
            return {"contentid": content_id, "wheelchair": "휠체어 접근 가능"}

    service = TourismChatService(
        tourism_settings(
            tourism_lookup_strategy="live_update",
            tourism_live_first_wait_seconds=0.02,
            tourism_live_background_timeout_seconds=1.0,
            tour_api_service_key="test",
            tour_api_accessible_service_key="test",
            tourism_live_cache_path=tmp_path / "live_cache",
            tourism_sample_path=tmp_path / "samples",
        ),
        EmptyRetriever(),
        TourismQueryService(),
        tour_api_service=SlowTourAPI(),
    )

    started_at = time.perf_counter()
    first = service.answer("서울에서 휠체어 관광지 추천", session_id="s-no-sync")
    elapsed = time.perf_counter() - started_at

    assert first.lookup_mode == "unknown"
    assert first.live_update_pending is True
    assert elapsed < 0.3
    with lock:
        assert calls == 1


def test_tourism_chat_live_update_times_out_after_background_limit(tmp_path):
    release = threading.Event()

    class TooSlowTourAPI:
        def accessible_area_based_list(self, area_code: str, sigungu_code=None, num_of_rows=10):
            release.wait(30)
            return [{"contentid": "live-too-slow"}]

        def detail_common(self, content_id: str):
            return {"contentid": content_id, "title": "너무 늦은 최신 관광지", "addr1": "서울 중구"}

        def detail_with_tour(self, content_id: str):
            return {"contentid": content_id, "wheelchair": "휠체어 접근 가능"}

    service = TourismChatService(
        tourism_settings(
            tourism_lookup_strategy="live_update",
            tourism_live_first_wait_seconds=0.02,
            tourism_live_background_timeout_seconds=0.08,
            tour_api_service_key="test",
            tour_api_accessible_service_key="test",
            tourism_live_cache_path=tmp_path / "live_cache",
            tourism_sample_path=tmp_path / "samples",
        ),
        FakeRetriever(),
        TourismQueryService(),
        tour_api_service=TooSlowTourAPI(),
    )

    first = service.answer("서울에서 휠체어 관광지 추천", session_id="s-timeout")
    assert first.lookup_mode == "indexed"
    assert first.live_update_pending is True

    time.sleep(0.12)
    timeout = service.answer("최신 결과 업데이트 보기", session_id="s-timeout")
    release.set()

    assert timeout.lookup_mode == "live_update_timeout"
    assert timeout.cards == []
    assert timeout.degraded is True


def test_tourism_chat_live_update_cancels_previous_on_new_request(tmp_path):
    release = threading.Event()

    class BlockingTourAPI:
        def accessible_area_based_list(self, area_code: str, sigungu_code=None, num_of_rows=10):
            release.wait(0.3)
            return [{"contentid": "cancelled-live"}]

        def detail_common(self, content_id: str):
            return {"contentid": content_id, "title": "취소된 최신 관광지", "addr1": "서울 중구"}

        def detail_with_tour(self, content_id: str):
            return {"contentid": content_id, "wheelchair": "휠체어 접근 가능"}

    service = TourismChatService(
        tourism_settings(
            tourism_lookup_strategy="live_update",
            tourism_live_first_wait_seconds=0.02,
            tourism_live_background_timeout_seconds=0.2,
            tour_api_service_key="test",
            tour_api_accessible_service_key="test",
            tourism_live_cache_path=tmp_path / "live_cache",
            tourism_sample_path=tmp_path / "samples",
        ),
        FakeRetriever(),
        TourismQueryService(),
        tour_api_service=BlockingTourAPI(),
    )

    first = service.answer("서울에서 휠체어 관광지 추천", session_id="s-cancel")
    assert first.live_update_pending is True

    second = service.answer("부산에서 휠체어 관광지 추천", session_id="s-cancel")
    assert second.lookup_mode in {"indexed", "sample"}
    release.set()
    time.sleep(0.05)

    update = service.answer("최신 결과 업데이트 보기", session_id="s-cancel")

    assert update.lookup_mode != "live_update"
    assert all(card.title != "취소된 최신 관광지" for card in update.cards)
    cached_text = "\n".join(path.read_text(encoding="utf-8") for path in (tmp_path / "live_cache").glob("*.md"))
    assert "취소된 최신 관광지" not in cached_text


def test_tourism_chat_logs_query_card_event(tmp_path):
    log_path = tmp_path / "events.jsonl"
    service = TourismChatService(
        tourism_settings(
            tourism_query_event_log_path=log_path,
            tourism_query_event_log_enabled=True,
            tourism_query_event_log_include_message=False,
            tourism_live_cache_path=tmp_path / "live_cache",
            tour_api_service_key=None,
        ),
        FakeRetriever(),
        TourismQueryService(),
        event_logger=TourismQueryEventLogger(
            tourism_settings(
                tourism_query_event_log_path=log_path,
                tourism_query_event_log_enabled=True,
                tourism_query_event_log_include_message=False,
            )
        ),
    )

    response = service.answer("서울에서 휠체어 관광지 추천", session_id="test-session")

    payload = json.loads(log_path.read_text(encoding="utf-8"))
    assert response.lookup_mode == "indexed"
    assert payload["session_id"] == "test-session"
    assert payload["message"] is None
    assert payload["lookup_mode"] == "indexed"
    assert payload["live_api_called"] is False
    assert payload["reasoning_assist_used"] is False
    assert payload["reasoning_assist_notes"] == []
    assert payload["cards"][0]["title"] == "서울어린이대공원"


def test_tourism_chat_uses_local_samples_before_live_tour_api(tmp_path):
    sample_dir = tmp_path / "tourism"
    sample_dir.mkdir()
    sample = Path("data/raw/tourism_accessible/gangneung_sample_001.md").read_text(encoding="utf-8")
    (sample_dir / "gangneung.md").write_text(sample, encoding="utf-8")

    class BrokenTourAPI:
        def __init__(self):
            self.list_calls = 0

        def accessible_area_based_list(self, area_code: str, sigungu_code=None, num_of_rows=10):
            self.list_calls += 1
            raise TourAPIError("quota exhausted")

    tour_api = BrokenTourAPI()
    service = TourismChatService(
        tourism_settings(
            tourism_sample_path=sample_dir,
            tourism_live_cache_path=tmp_path / "live_cache",
            tour_api_service_key="test",
            tour_api_accessible_service_key="test",
        ),
        EmptyRetriever(),
        TourismQueryService(),
        tour_api_service=tour_api,
    )

    response = service.answer("강릉 휠체어 관광지")

    assert len(response.cards) == 1
    assert response.cards[0].title == "오죽헌"
    assert response.lookup_mode == "sample"
    assert response.degraded is False
    assert response.warnings == []
    assert tour_api.list_calls == 0


def test_tourism_chat_suggests_live_top_up_when_fallback_has_less_than_five_cards(tmp_path):
    sample_dir = tmp_path / "tourism"
    sample_dir.mkdir()
    for index in range(3):
        card = TourismPlaceCard(
            content_id=f"jeju-fallback-{index}",
            title=f"제주 폴백 관광지 {index}",
            address="제주특별자치도 제주시",
            recommendation_reason="휠체어 접근 정보가 확인되었습니다.",
            accessibility_tags=["휠체어 접근"],
        )
        (sample_dir / f"jeju_{index}.md").write_text(TourismNormalizer().card_to_markdown(card), encoding="utf-8")

    class CountingTourAPI:
        def __init__(self):
            self.list_calls = 0

        def accessible_area_based_list(self, area_code: str, sigungu_code=None, num_of_rows=10):
            self.list_calls += 1
            return [{"contentid": "live-extra"}]

    tour_api = CountingTourAPI()
    service = TourismChatService(
        tourism_settings(
            tourism_sample_path=sample_dir,
            tourism_live_cache_path=tmp_path / "live_cache",
            tour_api_service_key="test",
            tour_api_accessible_service_key="test",
        ),
        EmptyRetriever(),
        TourismQueryService(),
        tour_api_service=tour_api,
    )

    response = service.answer("제주시에서 휠체어 관광지 추천해줘")

    assert len(response.cards) == 3
    assert tour_api.list_calls == 0
    assert response.suggested_messages == ["제주시에서 휠체어 관광지 추천해줘 최신 추천 더 확인하기"]


def test_tourism_chat_live_top_up_runs_only_when_user_requests_it(tmp_path):
    sample_dir = tmp_path / "tourism"
    sample_dir.mkdir()
    for index in range(3):
        card = TourismPlaceCard(
            content_id=f"jeju-fallback-topup-{index}",
            title=f"제주 폴백 보강 관광지 {index}",
            address="제주특별자치도 제주시",
            recommendation_reason="휠체어 접근 정보가 확인되었습니다.",
            accessibility_tags=["휠체어 접근"],
        )
        (sample_dir / f"jeju_{index}.md").write_text(TourismNormalizer().card_to_markdown(card), encoding="utf-8")

    class FakeTourAPI:
        def __init__(self):
            self.list_calls = 0

        def accessible_area_based_list(self, area_code: str, sigungu_code=None, num_of_rows=10):
            self.list_calls += 1
            return [{"contentid": f"jeju-live-{index}"} for index in range(5)]

        def detail_common(self, content_id: str):
            return {
                "contentid": content_id,
                "title": f"제주 라이브 관광지 {content_id}",
                "addr1": "제주특별자치도 제주시",
            }

        def detail_with_tour(self, content_id: str):
            return {"contentid": content_id, "wheelchair": "휠체어 접근 가능"}

    tour_api = FakeTourAPI()
    service = TourismChatService(
        tourism_settings(
            tourism_sample_path=sample_dir,
            tourism_live_cache_path=tmp_path / "live_cache",
            tour_api_service_key="test",
            tour_api_accessible_service_key="test",
            tourism_live_rows=5,
            tourism_live_max_detail_calls=10,
        ),
        EmptyRetriever(),
        TourismQueryService(),
        tour_api_service=tour_api,
    )

    response = service.answer("제주시에서 휠체어 관광지 추천해줘 최신 정보 더 찾기")

    assert response.lookup_mode == "live_top_up"
    assert len(response.cards) == 5
    assert any(card.content_id.startswith("jeju-live-") for card in response.cards)
    assert response.suggested_messages == ["제주시에서 휠체어 관광지 추천해줘 더 보기"]
    assert tour_api.list_calls == 1


def test_tourism_chat_falls_back_to_local_samples(tmp_path):
    sample_dir = tmp_path / "tourism"
    sample_dir.mkdir()
    sample = Path("data/raw/tourism_accessible/gangneung_sample_001.md").read_text(encoding="utf-8")
    (sample_dir / "gangneung.md").write_text(sample, encoding="utf-8")

    class BrokenRetriever:
        def retrieve(self, message: str):
            raise RuntimeError("Ollama unavailable")

    service = TourismChatService(
        tourism_settings(
            tourism_sample_path=sample_dir,
            tourism_live_cache_path=tmp_path / "live_cache",
            tour_api_service_key=None,
        ),
        BrokenRetriever(),
        TourismQueryService(),
    )

    response = service.answer("강릉 부모님과 갈만한 무장애 관광지")

    assert len(response.cards) == 1
    assert response.cards[0].title == "오죽헌"
    assert response.sources[0].chunk_id == "sample-gangneung-001"
    assert response.degraded is True
    assert "먼저 확인된 자료" in response.warnings[0]


def test_tourism_chat_does_not_expand_sigungu_without_intent():
    service = TourismChatService(tourism_settings(), FakeRetriever(), TourismQueryService())

    response = service.answer("광진구에서 휠체어로 갈만한 곳 추천")

    assert len(response.cards) == 1
    assert response.cards[0].title == "서울어린이대공원"
    assert "요청 지역 안의 결과만 먼저 제공합니다" in response.answer


def test_tourism_chat_keeps_nearby_sigungu_inside_requested_region(tmp_path):
    service = TourismChatService(
        tourism_settings(tourism_live_cache_path=tmp_path / "live_cache"),
        FakeRetriever(),
        TourismQueryService(),
    )

    response = service.answer("광진구 근처에서 휠체어로 갈만한 곳 추천")

    assert len(response.cards) == 1
    assert response.cards[0].title == "서울어린이대공원"
    assert all("광진구" in (card.address or "") for card in response.cards)
    assert "요청 지역 안의 결과만 먼저 제공합니다" in response.answer
    assert "서울 전체로 넓혀줘" in response.answer
    assert response.suggested_messages == ["서울 전체로 넓혀서 휠체어 관광지 추천해줘"]


def test_tourism_chat_explicit_expand_followup_keeps_previous_condition(tmp_path):
    service = TourismChatService(
        tourism_settings(tourism_live_cache_path=tmp_path / "live_cache"),
        FakeRetriever(),
        TourismQueryService(),
    )

    first = service.answer("광진구에서 휠체어 관광지 추천해줘", session_id="expand-session")
    second = service.answer("서울 전체로 넓혀서 더 찾아줘", session_id="expand-session")

    assert first.cards
    assert second.lookup_mode != "unsupported"
    assert second.cards
    assert "휠체어" in second.answer


def test_tourism_chat_expansion_copy_requires_actual_outside_sigungu_cards():
    query = {"is_sigungu": True, "area_name": "서울", "sigungu_name": "강남구", "region": "강남구"}
    gangnam_cards = [
        TourismPlaceCard(content_id="g1", title="강남 1", address="서울특별시 강남구 테헤란로", recommendation_reason="test"),
        TourismPlaceCard(content_id="g2", title="강남 2", address="서울 강남구 삼성동", recommendation_reason="test"),
    ]
    mixed_cards = [
        *gangnam_cards,
        TourismPlaceCard(content_id="o1", title="광진", address="서울특별시 광진구 능동", recommendation_reason="test"),
    ]

    assert TourismChatService._cards_include_outside_query_region(gangnam_cards, query) is False
    assert TourismChatService._cards_include_outside_query_region(mixed_cards, query) is True


def test_tourism_chat_conditional_expansion_keeps_local_cards_first():
    service = TourismChatService(tourism_settings(), EmptyRetriever(), TourismQueryService())
    query = {
        "is_sigungu": True,
        "area_name": "서울",
        "sigungu_name": "강남구",
        "region": "서울 강남구",
        "conditions": ["휠체어"],
        "allow_region_expansion": True,
        "conditional_region_expansion": True,
    }
    cards = [
        _wheelchair_card(f"g{i}", f"강남 {i}", "서울특별시 강남구 테헤란로")
        for i in range(1, 6)
    ] + [
        _wheelchair_card("o1", "서울 다른 구", "서울특별시 광진구 능동")
    ]

    selected, expanded, has_more = service._select_cards(
        cards,
        "서울 강남구에서 휠체어 관광지 추천해줘. 부족하면 서울 전체로 넓혀줘",
        query,
    )

    assert len(selected) == 5
    assert all("강남구" in (card.address or "") for card in selected)
    assert expanded is False
    assert has_more is False


def test_tourism_chat_conditional_expansion_expands_only_when_local_cards_are_few():
    service = TourismChatService(tourism_settings(), EmptyRetriever(), TourismQueryService())
    query = {
        "is_sigungu": True,
        "area_name": "서울",
        "sigungu_name": "강남구",
        "region": "서울 강남구",
        "conditions": ["휠체어"],
        "allow_region_expansion": True,
        "conditional_region_expansion": True,
    }
    cards = [
        _wheelchair_card("g1", "강남 1", "서울특별시 강남구 테헤란로"),
        _wheelchair_card("g2", "강남 2", "서울특별시 강남구 삼성동"),
        _wheelchair_card("o1", "서울 다른 구", "서울특별시 광진구 능동"),
    ]

    selected, expanded, _ = service._select_cards(
        cards,
        "서울 강남구에서 휠체어 관광지 추천해줘. 부족하면 서울 전체로 넓혀줘",
        query,
    )

    assert [card.title for card in selected] == ["강남 1", "강남 2", "서울 다른 구"]
    assert expanded is True


def test_tourism_chat_no_card_suggestions_include_distinct_recovery_actions():
    query = {
        "is_sigungu": True,
        "area_name": "제주",
        "sigungu_name": "제주시",
        "region": "제주시",
        "conditions": ["청각장애", "시각장애"],
    }

    suggestions = TourismChatService._build_no_card_suggestions(query)

    assert suggestions == [
        "제주시에서 청각장애 시각장애 관광지 추천해줘",
        "제주 전체로 넓혀서 청각장애 시각장애 관광지 추천해줘",
        "제주시에서 무장애 관광지 추천해줘",
    ]


def _wheelchair_card(content_id: str, title: str, address: str) -> TourismPlaceCard:
    return TourismPlaceCard(
        content_id=content_id,
        title=title,
        address=address,
        recommendation_reason="휠체어 접근 정보가 확인되어 조건에 맞는 후보입니다.",
        accessibility=AccessibilityInfo(wheelchair="주출입구는 턱이 없어 휠체어 접근 가능함"),
        accessibility_tags=["휠체어 접근"],
    )


def test_tourism_chat_rejects_general_place_type_only_query(tmp_path):
    sample_dir = tmp_path / "samples"
    sample_dir.mkdir()
    normalizer = TourismNormalizer()
    gallery = TourismPlaceCard(
        content_id="seongnam-gallery",
        title="나폴레옹갤러리",
        address="경기도 성남시",
        recommendation_reason="실내 미술 갤러리입니다.",
        raw_fields={"안내": "실내 전시 관람 가능"},
    )
    restaurant = TourismPlaceCard(
        content_id="gyeonggi-restaurant",
        title="군포식당",
        address="경기도 군포시",
        recommendation_reason="음식점으로 확인된 실내 식당입니다.",
        raw_fields={"음식점": "의자식 테이블 있음"},
    )
    (sample_dir / "gallery.md").write_text(normalizer.card_to_markdown(gallery), encoding="utf-8")
    (sample_dir / "restaurant.md").write_text(normalizer.card_to_markdown(restaurant), encoding="utf-8")
    service = TourismChatService(
        tourism_settings(
            tourism_sample_path=sample_dir,
            tourism_live_cache_path=tmp_path / "live_cache",
            tour_api_service_key=None,
        ),
        EmptyRetriever(),
        TourismQueryService(),
    )

    response = service.answer("성남시 실내식당")

    assert response.cards == []
    assert response.lookup_mode == "unsupported"
    assert "무장애 관광 연관 장소만 제공" in response.answer
    assert "휠체어" in response.suggested_messages[0]


def test_tourism_chat_rejects_general_tourism_query_without_accessibility_condition(tmp_path):
    service = TourismChatService(
        tourism_settings(tourism_live_cache_path=tmp_path / "live_cache"),
        FakeRetriever(),
        TourismQueryService(),
    )

    response = service.answer("서울 관광지 추천")

    assert response.cards == []
    assert response.lookup_mode == "unsupported"
    assert "일반 관광지" in response.answer
    assert "장애인 화장실" in response.suggested_messages[1]


def test_tourism_chat_does_not_expand_place_type_when_accessibility_condition_is_unsatisfied(tmp_path):
    sample_dir = tmp_path / "samples"
    sample_dir.mkdir()
    normalizer = TourismNormalizer()
    gallery = TourismPlaceCard(
        content_id="seongnam-gallery",
        title="나폴레옹갤러리",
        address="경기도 성남시",
        recommendation_reason="실내 미술 갤러리입니다.",
        accessibility_tags=["청각장애"],
        raw_fields={"청각장애 편의": "수어 안내 있음", "안내": "실내 전시 관람 가능"},
    )
    restaurant = TourismPlaceCard(
        content_id="gyeonggi-restaurant",
        title="군포식당",
        address="경기도 군포시",
        recommendation_reason="음식점으로 확인된 실내 식당입니다.",
        raw_fields={"음식점": "의자식 테이블 있음"},
    )
    (sample_dir / "gallery.md").write_text(normalizer.card_to_markdown(gallery), encoding="utf-8")
    (sample_dir / "restaurant.md").write_text(normalizer.card_to_markdown(restaurant), encoding="utf-8")
    service = TourismChatService(
        tourism_settings(
            tourism_sample_path=sample_dir,
            tourism_live_cache_path=tmp_path / "live_cache",
            tour_api_service_key=None,
        ),
        EmptyRetriever(),
        TourismQueryService(),
    )

    response = service.answer("성남시 수어 자막 있는 실내식당")

    assert response.cards == []
    assert "정확히 요청한 접근성 근거" in response.answer


def test_tourism_chat_distinguishes_exact_evidence_missing_from_no_card_output(tmp_path):
    sample_dir = tmp_path / "samples"
    sample_dir.mkdir()
    normalizer = TourismNormalizer()
    gallery = TourismPlaceCard(
        content_id="seongnam-gallery",
        title="나폴레옹갤러리",
        address="경기도 성남시",
        recommendation_reason="자막 안내가 있는 실내 전시관입니다.",
        accessibility_tags=["청각장애", "자막/영상안내"],
        raw_fields={"자막/영상안내": "음성안내기 자막 제공"},
    )
    (sample_dir / "gallery.md").write_text(normalizer.card_to_markdown(gallery), encoding="utf-8")
    service = TourismChatService(
        tourism_settings(
            tourism_sample_path=sample_dir,
            tourism_live_cache_path=tmp_path / "live_cache",
            tour_api_service_key=None,
        ),
        EmptyRetriever(),
        TourismQueryService(),
    )

    response = service.answer("성남시 수어 안내 관광지 추천")

    assert response.cards == []
    assert "정확히 요청한 접근성 근거" in response.answer
    assert "대체 근거" in response.answer
    assert "자막/영상안내" in response.answer
    assert "수어/수화" in response.answer


def test_tourism_chat_accepts_one_alternative_evidence_group(tmp_path):
    sample_dir = tmp_path / "samples"
    sample_dir.mkdir()
    normalizer = TourismNormalizer()
    library = TourismPlaceCard(
        content_id="seongnam-library",
        title="성남도서관",
        address="경기도 성남시",
        recommendation_reason="점자블록이 확인된 도서관입니다.",
        accessibility_tags=["점자블록"],
        raw_fields={"점자블록": "점자블록 있음(계단 앞)"},
    )
    (sample_dir / "library.md").write_text(normalizer.card_to_markdown(library), encoding="utf-8")
    service = TourismChatService(
        tourism_settings(
            tourism_sample_path=sample_dir,
            tourism_live_cache_path=tmp_path / "live_cache",
            tour_api_service_key=None,
        ),
        EmptyRetriever(),
        TourismQueryService(),
    )

    response = service.answer("성남시 점자나 음성안내 둘 중 하나라도 있으면 추천해줘")

    assert response.cards
    assert response.cards[0].title == "성남도서관"


def test_tourism_chat_keeps_tactile_map_strict_from_braille_block(tmp_path):
    sample_dir = tmp_path / "samples"
    sample_dir.mkdir()
    normalizer = TourismNormalizer()
    braille_only = TourismPlaceCard(
        content_id="seongnam-braille-only",
        title="성남 점자블록 전시관",
        address="경기도 성남시",
        recommendation_reason="점자블록이 확인된 전시관입니다.",
        accessibility_tags=["점자블록"],
        raw_fields={"점자블록": "점자블록 있음"},
    )
    tactile = TourismPlaceCard(
        content_id="seongnam-tactile",
        title="성남 촉지 안내관",
        address="경기도 성남시",
        recommendation_reason="촉지 안내판이 확인된 전시관입니다.",
        accessibility_tags=["시각장애"],
        raw_fields={"안내시스템": "촉지 안내판 있음"},
    )
    (sample_dir / "braille.md").write_text(normalizer.card_to_markdown(braille_only), encoding="utf-8")
    (sample_dir / "tactile.md").write_text(normalizer.card_to_markdown(tactile), encoding="utf-8")
    service = TourismChatService(
        tourism_settings(
            tourism_sample_path=sample_dir,
            tourism_live_cache_path=tmp_path / "live_cache",
            tour_api_service_key=None,
        ),
        EmptyRetriever(),
        TourismQueryService(),
    )

    response = service.answer("성남시손으로만져확인할안내되는곳만보여줘.비슷한접근성말고")

    assert [card.title for card in response.cards] == ["성남 촉지 안내관"]


def test_tourism_chat_remembers_region_after_condition_clarification(tmp_path):
    service = TourismChatService(
        tourism_settings(tourism_live_cache_path=tmp_path / "live_cache"),
        FakeRetriever(),
        TourismQueryService(),
    )

    first = service.answer("대전 계단 적은 관광지 추천", session_id="clarify-region-memory")
    second = service.answer("그중 엘레베터 되는 곳만", session_id="clarify-region-memory")

    assert first.lookup_mode == "clarification"
    assert "대전" in second.answer
    assert "추천할 지역을 먼저" not in second.answer


def test_tourism_chat_asks_to_clarify_ambiguous_region(tmp_path):
    cache_path = tmp_path / "tour_area_codes.json"
    cache_path.write_text(
        json.dumps(
            {
                "region_index": {
                    "서울": {
                        "area_code": "1",
                        "sigungu_code": None,
                        "area_name": "서울",
                        "sigungu_name": None,
                    },
                    "부산": {
                        "area_code": "6",
                        "sigungu_code": None,
                        "area_name": "부산",
                        "sigungu_name": None,
                    },
                },
                "ambiguous_region_aliases": {
                    "중구": [
                        {
                            "area_code": "1",
                            "sigungu_code": "24",
                            "area_name": "서울",
                            "sigungu_name": "중구",
                        },
                        {
                            "area_code": "6",
                            "sigungu_code": "15",
                            "area_name": "부산",
                            "sigungu_name": "중구",
                        },
                    ]
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    service = TourismChatService(tourism_settings(), FakeRetriever(), TourismQueryService(area_code_cache_path=cache_path))

    response = service.answer("중구에서 휠체어 타시는 아버지와 갈 관광지 추천")

    assert response.cards == []
    assert response.lookup_mode == "clarification"
    assert "'중구'는 여러 시도에 있는 지명" in response.answer
    assert "어느 지역인지" in response.answer
    assert "서울 중구" in response.answer
    assert "부산 중구" in response.answer
    assert response.suggested_messages == [
        "서울 중구에서 휠체어 타시는 아버지와 갈 관광지 추천",
        "부산 중구에서 휠체어 타시는 아버지와 갈 관광지 추천",
    ]


def test_tourism_chat_asks_to_clarify_ambiguous_condition_boundary(tmp_path):
    service = TourismChatService(
        tourism_settings(tourism_live_cache_path=tmp_path / "live_cache"),
        FakeRetriever(),
        TourismQueryService(),
    )

    response = service.answer("서울에서 계단 적게 다니는 편한 관광지")

    assert response.cards == []
    assert response.lookup_mode == "clarification"
    assert "접근성 의미가 조금 애매합니다" in response.answer
    assert "어르신 이동 부담 적은 곳" in response.answer
    assert "입구/동선 접근로" in response.answer
    assert response.suggested_messages == [
        "서울에서 어르신 이동 부담 적은 곳 관광지 추천해줘",
        "서울에서 입구/동선 접근로 관광지 추천해줘",
    ]


def test_tourism_chat_clarifies_broad_accessibility_good_phrase(tmp_path):
    service = TourismChatService(
        tourism_settings(tourism_live_cache_path=tmp_path / "live_cache"),
        FakeRetriever(),
        TourismQueryService(),
    )

    response = service.answer("강남구에서 접근성 좋은 실내 관광지")

    assert response.cards == []
    assert response.lookup_mode == "clarification"
    assert "접근성 의미가 조금 애매합니다" in response.answer
    assert "휠체어 접근" in response.answer
    assert "입구/동선 접근로" in response.answer
    assert "어르신 이동 부담 적은 곳" in response.answer
    assert response.suggested_messages == [
        "강남구에서 휠체어 접근 관광지 추천해줘",
        "강남구에서 입구/동선 접근로 관광지 추천해줘",
        "강남구에서 어르신 이동 부담 적은 곳 관광지 추천해줘",
    ]


def test_tourism_chat_resolves_area_qualified_ambiguous_region(tmp_path):
    sample_dir = tmp_path / "tourism"
    sample_dir.mkdir()
    sample = Path("data/raw/tourism_accessible/부산_2609623.md").read_text(encoding="utf-8")
    (sample_dir / "busan_junggu.md").write_text(sample, encoding="utf-8")
    cache_path = tmp_path / "tour_area_codes.json"
    cache_path.write_text(
        json.dumps(
            {
                "region_index": {
                    "부산": {
                        "area_code": "6",
                        "sigungu_code": None,
                        "area_name": "부산",
                        "sigungu_name": None,
                    },
                },
                "ambiguous_region_aliases": {
                    "중구": [
                        {
                            "area_code": "1",
                            "sigungu_code": "24",
                            "area_name": "서울",
                            "sigungu_name": "중구",
                        },
                        {
                            "area_code": "6",
                            "sigungu_code": "15",
                            "area_name": "부산",
                            "sigungu_name": "중구",
                        },
                    ]
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    class EmptyRetriever:
        def retrieve(self, message: str):
            return []

    service = TourismChatService(
        tourism_settings(
            tourism_sample_path=sample_dir,
            tourism_live_cache_path=tmp_path / "live_cache",
            tour_api_service_key=None,
        ),
        EmptyRetriever(),
        TourismQueryService(area_code_cache_path=cache_path),
    )

    response = service.answer("부산 중구에서 휠체어 타시는 어머니를 모시고 다닐수 있는 관광지를 추천해줘")

    assert len(response.cards) == 1
    assert response.cards[0].title == "개미집 본점"
    assert "부산 중구 기준" in response.answer


def test_tourism_chat_filters_same_sigungu_name_by_area(tmp_path):
    sample_dir = tmp_path / "tourism"
    sample_dir.mkdir()
    busan_card = TourismPlaceCard(
        content_id="busan-junggu",
        title="부산 중구 관광지",
        address="부산광역시 중구",
        recommendation_reason="휠체어 접근 정보가 확인되었습니다.",
        accessibility_tags=["휠체어 접근"],
    )
    ulsan_card = TourismPlaceCard(
        content_id="ulsan-junggu",
        title="울산중구어린이역사과학체험관",
        address="울산광역시 중구",
        recommendation_reason="휠체어 접근 정보가 확인되었습니다.",
        accessibility_tags=["휠체어 접근"],
    )
    (sample_dir / "busan.md").write_text(TourismNormalizer().card_to_markdown(busan_card), encoding="utf-8")
    (sample_dir / "ulsan.md").write_text(TourismNormalizer().card_to_markdown(ulsan_card), encoding="utf-8")

    service = TourismChatService(
        tourism_settings(
            tourism_sample_path=sample_dir,
            tourism_live_cache_path=tmp_path / "live_cache",
            tour_api_service_key=None,
        ),
        EmptyRetriever(),
        TourismQueryService(),
    )

    response = service.answer("부산 중구에서 휠체어 관광지 추천해줘")

    assert [card.title for card in response.cards] == ["부산 중구 관광지"]


def test_tourism_chat_explains_legacy_region_name_replacement(tmp_path):
    sample_dir = tmp_path / "tourism"
    sample_dir.mkdir()
    card = TourismPlaceCard(
        content_id="legacy-cheongju",
        title="청주 무장애 관광지",
        address="충청북도 청주시 청원구",
        recommendation_reason="휠체어 접근 정보가 확인되었습니다.",
        accessibility_tags=["휠체어 접근"],
    )
    (sample_dir / "cheongju.md").write_text(TourismNormalizer().card_to_markdown(card), encoding="utf-8")
    cache_path = tmp_path / "tour_area_codes.json"
    cache_path.write_text(
        json.dumps(
            {
                "ambiguous_region_aliases": {},
                "region_index": {
                    "청원군": {
                        "area_code": "33",
                        "sigungu_code": "9",
                        "area_name": "충북",
                        "sigungu_name": "청원군",
                    },
                    "청주시": {
                        "area_code": "33",
                        "sigungu_code": "10",
                        "area_name": "충북",
                        "sigungu_name": "청주시",
                    },
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    service = TourismChatService(
        tourism_settings(tourism_sample_path=sample_dir, tourism_live_cache_path=tmp_path / "live_cache", tour_api_service_key=None),
        EmptyRetriever(),
        TourismQueryService(area_code_cache_path=cache_path),
    )

    response = service.answer("청원군에서 휠체어 관광지 추천해줘")

    assert len(response.cards) == 1
    assert response.cards[0].title == "청주 무장애 관광지"
    assert "청주시 기준" in response.answer
    assert "청원군은 현재 청주시 기준으로 안내드릴게요" in response.answer


def test_tourism_chat_suggests_more_when_more_than_five_cards_exist(tmp_path):
    sample_dir = tmp_path / "tourism"
    sample_dir.mkdir()
    for index in range(6):
        card = TourismPlaceCard(
            content_id=f"jeju-more-{index}",
            title=f"제주 더보기 관광지 {index}",
            address="제주특별자치도 제주시",
            recommendation_reason="휠체어 접근 정보가 확인되었습니다.",
            accessibility_tags=["휠체어 접근"],
        )
        (sample_dir / f"jeju_{index}.md").write_text(TourismNormalizer().card_to_markdown(card), encoding="utf-8")
    service = TourismChatService(
        tourism_settings(tourism_sample_path=sample_dir, tourism_live_cache_path=tmp_path / "live_cache", tour_api_service_key=None),
        EmptyRetriever(),
        TourismQueryService(),
    )

    response = service.answer("제주시에서 휠체어 관광지 추천해줘")

    assert len(response.cards) == 5
    assert response.suggested_messages == ["제주시에서 휠체어 관광지 추천해줘 더 보기"]


def test_tourism_chat_returns_more_cards_when_more_is_requested(tmp_path):
    sample_dir = tmp_path / "tourism"
    sample_dir.mkdir()
    for index in range(25):
        card = TourismPlaceCard(
            content_id=f"jeju-more-requested-{index}",
            title=f"제주 전체 관광지 {index}",
            address="제주특별자치도 제주시",
            recommendation_reason="휠체어 접근 정보가 확인되었습니다.",
            accessibility_tags=["휠체어 접근"],
        )
        (sample_dir / f"jeju_{index}.md").write_text(TourismNormalizer().card_to_markdown(card), encoding="utf-8")
    service = TourismChatService(
        tourism_settings(tourism_sample_path=sample_dir, tourism_live_cache_path=tmp_path / "live_cache", tour_api_service_key=None),
        EmptyRetriever(),
        TourismQueryService(),
    )

    response = service.answer("제주시에서 휠체어 관광지 추천해줘 더 보기")

    assert len(response.cards) == 25
    assert response.suggested_messages == []


def test_tourism_chat_more_keeps_area_region_scope(tmp_path):
    sample_dir = tmp_path / "tourism"
    sample_dir.mkdir()
    normalizer = TourismNormalizer()
    for index in range(6):
        card = TourismPlaceCard(
            content_id=f"jeonnam-more-{index}",
            title=f"전남 휠체어 관광지 {index}",
            address="전라남도 여수시",
            recommendation_reason="휠체어 접근 정보가 확인되었습니다.",
            accessibility_tags=["휠체어 접근"],
        )
        (sample_dir / f"jeonnam_{index}.md").write_text(normalizer.card_to_markdown(card), encoding="utf-8")
    for index in range(30):
        card = TourismPlaceCard(
            content_id=f"seoul-noise-{index}",
            title=f"서울 휠체어 관광지 {index}",
            address="서울특별시 중구",
            recommendation_reason="휠체어 접근 정보가 확인되었습니다.",
            accessibility_tags=["휠체어 접근"],
        )
        (sample_dir / f"seoul_{index}.md").write_text(normalizer.card_to_markdown(card), encoding="utf-8")
    service = TourismChatService(
        tourism_settings(tourism_sample_path=sample_dir, tourism_live_cache_path=tmp_path / "live_cache", tour_api_service_key=None),
        EmptyRetriever(),
        TourismQueryService(),
    )

    response = service.answer("전남에서 휠체어 관광지 추천해줘 더 보기")

    assert len(response.cards) == 6
    assert all("전라남도" in (card.address or "") for card in response.cards)
    assert all("서울" not in (card.address or "") for card in response.cards)


def test_tourism_chat_area_filter_uses_address_not_title(tmp_path):
    sample_dir = tmp_path / "tourism"
    sample_dir.mkdir()
    normalizer = TourismNormalizer()
    valid_card = TourismPlaceCard(
        content_id="gyeonggi-valid",
        title="수원 무장애 관광지",
        address="경기도 수원시",
        recommendation_reason="휠체어 접근 정보가 확인되었습니다.",
        accessibility_tags=["휠체어 접근"],
    )
    title_noise = TourismPlaceCard(
        content_id="gyeonggi-title-noise",
        title="경기여고 근처 산책길",
        address="서울특별시 강남구",
        recommendation_reason="휠체어 접근 정보가 확인되었습니다.",
        accessibility_tags=["휠체어 접근"],
    )
    (sample_dir / "gyeonggi_valid.md").write_text(normalizer.card_to_markdown(valid_card), encoding="utf-8")
    (sample_dir / "gyeonggi_noise.md").write_text(normalizer.card_to_markdown(title_noise), encoding="utf-8")
    service = TourismChatService(
        tourism_settings(tourism_sample_path=sample_dir, tourism_live_cache_path=tmp_path / "live_cache", tour_api_service_key=None),
        EmptyRetriever(),
        TourismQueryService(),
    )

    response = service.answer("경기에서 휠체어 관광지 추천해줘 더 보기")

    assert [card.title for card in response.cards] == ["수원 무장애 관광지"]


def test_tourism_chat_area_filter_does_not_match_address_suffix_alias(tmp_path):
    sample_dir = tmp_path / "tourism"
    sample_dir.mkdir()
    normalizer = TourismNormalizer()
    valid_card = TourismPlaceCard(
        content_id="sejong-valid",
        title="세종 무장애 관광지",
        address="세종특별자치시 다솜로 216",
        recommendation_reason="장애인 주차 정보가 확인되었습니다.",
        accessibility_tags=["장애인 주차"],
        raw_fields={"주차": "장애인 전용 주차구역 있음"},
    )
    suffix_noise = TourismPlaceCard(
        content_id="sejong-suffix-noise",
        title="경복궁",
        address="서울특별시 종로구 사직로 161 (세종로)",
        recommendation_reason="장애인 주차 정보가 확인되었습니다.",
        accessibility_tags=["장애인 주차"],
        raw_fields={"주차": "장애인 전용 주차구역 있음"},
    )
    (sample_dir / "sejong_valid.md").write_text(normalizer.card_to_markdown(valid_card), encoding="utf-8")
    (sample_dir / "sejong_noise.md").write_text(normalizer.card_to_markdown(suffix_noise), encoding="utf-8")
    service = TourismChatService(
        tourism_settings(tourism_sample_path=sample_dir, tourism_live_cache_path=tmp_path / "live_cache", tour_api_service_key=None),
        EmptyRetriever(),
        TourismQueryService(),
    )

    response = service.answer("세종에서 장애인 주차장 관광지 추천해줘 더 보기")

    assert [card.title for card in response.cards] == ["세종 무장애 관광지"]


def test_tourism_chat_more_filters_every_card_by_requested_condition(tmp_path):
    sample_dir = tmp_path / "tourism"
    sample_dir.mkdir()
    normalizer = TourismNormalizer()
    for index in range(7):
        card = TourismPlaceCard(
            content_id=f"busan-stroller-{index}",
            title=f"부산 유모차 관광지 {index}",
            address="부산광역시 해운대구",
            recommendation_reason="유모차 편의 정보가 확인되었습니다.",
            family_tags=["유모차 대여"],
            raw_fields={"유모차": "유모차 대여 가능함"},
        )
        (sample_dir / f"busan_stroller_{index}.md").write_text(normalizer.card_to_markdown(card), encoding="utf-8")
    for index in range(10):
        card = TourismPlaceCard(
            content_id=f"busan-wheelchair-noise-{index}",
            title=f"부산 휠체어 관광지 {index}",
            address="부산광역시 중구",
            recommendation_reason="휠체어 접근 정보가 확인되었습니다.",
            accessibility_tags=["휠체어 접근"],
            raw_fields={"출입통로": "주출입구는 턱이 없어 휠체어 접근 가능함"},
        )
        (sample_dir / f"busan_noise_{index}.md").write_text(normalizer.card_to_markdown(card), encoding="utf-8")
    service = TourismChatService(
        tourism_settings(tourism_sample_path=sample_dir, tourism_live_cache_path=tmp_path / "live_cache", tour_api_service_key=None),
        EmptyRetriever(),
        TourismQueryService(),
    )

    response = service.answer("부산에서 유모차 관광지 추천해줘 더 보기")

    assert len(response.cards) == 7
    assert all("유모차" in card.recommendation_reason or "유모차" in " ".join(card.family_tags) for card in response.cards)


def test_tourism_chat_handles_empty_retrieval_and_empty_samples(tmp_path):
    sample_dir = tmp_path / "empty"
    sample_dir.mkdir()

    class EmptyRetriever:
        def retrieve(self, message: str):
            return []

    service = TourismChatService(
        tourism_settings(
            tourism_sample_path=sample_dir,
            tourism_live_cache_path=tmp_path / "live_cache",
            tour_api_service_key=None,
        ),
        EmptyRetriever(),
        TourismQueryService(),
    )

    response = service.answer("서울 휠체어 관광지 추천")

    assert response.cards == []
    assert "조건에 맞는 관광지를 확인하지 못했습니다" in response.answer
    assert response.suggested_messages


def test_tourism_chat_no_card_suggestions_include_region_expansion_and_relaxation(tmp_path):
    service = TourismChatService(
        tourism_settings(tourism_live_cache_path=tmp_path / "live_cache"),
        EmptyRetriever(),
        TourismQueryService(),
    )

    response = service.answer("서울 강남구에서 수어 자막 관광지 추천")

    assert response.cards == []
    assert any("서울" in suggestion and "전체로 넓혀" in suggestion for suggestion in response.suggested_messages)
    assert any("청각장애" in suggestion for suggestion in response.suggested_messages)


def test_tourism_chat_does_not_return_region_cards_for_unmatched_place_feature():
    service = TourismChatService(tourism_settings(), FakeRetriever(), TourismQueryService())

    response = service.answer("서울 강남구에 바닷가 휠체어 관광지 추천해줘")

    assert response.cards == []
    assert "조건에 맞는 관광지를 확인하지 못했습니다" in response.answer


def test_tourism_chat_does_not_return_broad_region_cards_for_unmatched_place_feature():
    service = TourismChatService(tourism_settings(), FakeRetriever(), TourismQueryService())

    response = service.answer("대전에서 바닷가 휠체어 관광지 추천해줘")

    assert response.cards == []
    assert "조건에 맞는 관광지를 확인하지 못했습니다" in response.answer


def test_tourism_chat_asks_for_region_before_searching():
    service = TourismChatService(tourism_settings(), FakeRetriever(), TourismQueryService())

    response = service.answer("휠체어 타는 가족이랑 갈 만한 관광지 추천해줘")

    assert response.cards == []
    assert response.lookup_mode == "clarification"
    assert "추천할 지역을 먼저 알려 주세요" in response.answer
    assert response.suggested_messages


def test_tourism_chat_rejects_unsupported_price_comparison():
    service = TourismChatService(tourism_settings(), FakeRetriever(), TourismQueryService())

    response = service.answer("휠체어 대여 가격이 제일 싼 곳 알려줘")

    assert response.cards == []
    assert response.lookup_mode == "unsupported"
    assert "가격 비교" in response.answer


def test_tourism_chat_answers_supported_part_when_scope_request_is_mixed(tmp_path):
    service = TourismChatService(tourism_settings(tourism_live_cache_path=tmp_path / "live_cache"), FakeRetriever(), TourismQueryService())

    response = service.answer("서울에서 휠체어 관광지 추천하면서 근처 응급실과 약국도 같이 알려줘")

    assert response.cards
    assert response.lookup_mode == "indexed"
    assert "현재 서비스에서 확인할 수 있는 데이터 범위 밖" in response.answer
    assert response.warnings


def test_tourism_chat_clarifies_when_unsupported_condition_is_core():
    service = TourismChatService(tourism_settings(), FakeRetriever(), TourismQueryService())

    response = service.answer("제주에서 지하철역 바로 연결된 무장애 관광지 추천해줘")

    assert response.cards == []
    assert response.lookup_mode == "clarification"
    assert "핵심 조건" in response.answer
    assert response.suggested_messages == ["제주에서 휠체어 관광지 추천해줘"]


def test_tourism_chat_sample_cards_are_cached(tmp_path):
    sample_dir = tmp_path / "tourism"
    sample_dir.mkdir()
    card = TourismPlaceCard(
        content_id="cache-sample",
        title="캐시 테스트 관광지",
        address="서울 중구",
        recommendation_reason="휠체어 접근 정보가 확인되었습니다.",
        accessibility_tags=["휠체어 접근"],
    )
    (sample_dir / "sample.md").write_text(TourismNormalizer().card_to_markdown(card), encoding="utf-8")

    class CountingCodec:
        def __init__(self):
            self.calls = 0

        def from_markdown(self, text: str):
            self.calls += 1
            return TourismNormalizer().codec.from_markdown(text)

    class EmptyRetriever:
        def retrieve(self, message: str):
            return []

    codec = CountingCodec()
    service = TourismChatService(
        tourism_settings(
            tourism_sample_path=sample_dir,
            tourism_live_cache_path=tmp_path / "live_cache",
            tour_api_service_key=None,
        ),
        EmptyRetriever(),
        TourismQueryService(),
        card_codec=codec,
    )

    assert service.answer("서울 휠체어 관광지").cards[0].title == "캐시 테스트 관광지"
    assert service.answer("서울 휠체어 관광지").cards[0].title == "캐시 테스트 관광지"
    assert codec.calls == 1


def test_tourism_chat_uses_session_region_for_more_followup(tmp_path):
    service = TourismChatService(tourism_settings(tourism_live_cache_path=tmp_path / "live_cache"), FakeRetriever(), TourismQueryService())

    first = service.answer("서울에서 휠체어 관광지 추천해줘", session_id="conv-more")
    followup = service.answer("더 보기", session_id="conv-more")

    assert first.cards
    assert followup.cards
    assert "서울" in followup.answer
    assert followup.lookup_mode in {"indexed", "sample", "cache"}


def test_tourism_chat_replaces_negated_condition_in_followup(tmp_path):
    service = TourismChatService(tourism_settings(tourism_live_cache_path=tmp_path / "live_cache"), FakeRetriever(), TourismQueryService())

    service.answer("서울에서 유모차 관광지 추천해줘", session_id="conv-condition")
    followup = service.answer("아니, 유모차 말고 휠체어로 갈 수 있는 곳", session_id="conv-condition")

    assert followup.cards
    assert "서울" in followup.answer
    assert "휠체어 조건" in followup.answer
    assert "유모차, 휠체어 조건" not in followup.answer


def test_tourism_chat_does_not_reuse_context_for_pure_unsupported_followup(tmp_path):
    service = TourismChatService(tourism_settings(tourism_live_cache_path=tmp_path / "live_cache"), FakeRetriever(), TourismQueryService())

    first = service.answer("서울에서 휠체어 관광지 추천해줘", session_id="conv-unsupported")
    followup = service.answer("입장료도 알려줘", session_id="conv-unsupported")

    assert first.cards
    assert followup.cards == []
    assert followup.lookup_mode == "unsupported"

    second = service.answer("버스 번호와 소요시간도 알려줘", session_id="conv-unsupported")
    assert second.cards == []
    assert second.lookup_mode == "unsupported"

    third = service.answer("오늘 환율 알려줘", session_id="conv-unsupported")
    assert third.cards == []
    assert third.lookup_mode == "unsupported"


def test_tourism_chat_resets_conditions_for_find_again_followup(tmp_path):
    sample_dir = tmp_path / "samples"
    sample_dir.mkdir()
    hearing_card = TourismPlaceCard(
        content_id="gangneung-hearing",
        title="강릉 자막 전시관",
        address="강원특별자치도 강릉시",
        recommendation_reason="자막/영상안내 정보가 확인되었습니다.",
        accessibility_tags=["자막/영상안내"],
        raw_fields={"자막/영상안내": "자막비디오가이드 있음"},
    )
    (sample_dir / "gangneung_hearing.md").write_text(TourismNormalizer().card_to_markdown(hearing_card), encoding="utf-8")
    service = TourismChatService(
        tourism_settings(tourism_sample_path=sample_dir, tourism_live_cache_path=tmp_path / "live_cache", tour_api_service_key=None),
        EmptyRetriever(),
        TourismQueryService(),
    )

    service.answer("강릉에서 보조견 동반 가능한 관광지 추천해줘", session_id="conv-hearing-reset")
    followup = service.answer("수어 안내나 자막 안내 있는 곳으로 다시 찾아줘", session_id="conv-hearing-reset")

    assert followup.cards
    assert followup.lookup_mode == "sample"
    assert followup.cards[0].title == "강릉 자막 전시관"
    assert "보조견" not in followup.answer


def test_tourism_chat_continues_when_unsupported_topic_is_negated(tmp_path):
    service = TourismChatService(tourism_settings(tourism_live_cache_path=tmp_path / "live_cache"), FakeRetriever(), TourismQueryService())

    service.answer("부산 중구에서 휠체어 관광지 추천해줘", session_id="conv-negated-unsupported")
    followup = service.answer("응급실은 말고 관광지만 계속", session_id="conv-negated-unsupported")

    assert followup.cards
    assert followup.lookup_mode in {"indexed", "sample", "cache"}
    assert "부산 중구" in followup.answer


def test_tourism_chat_clarifies_core_unsupported_followup(tmp_path):
    service = TourismChatService(tourism_settings(tourism_live_cache_path=tmp_path / "live_cache"), FakeRetriever(), TourismQueryService())

    service.answer("제주에서 휠체어 관광지 추천해줘", session_id="conv-subway-core")
    followup = service.answer("지하철역 바로 연결된 곳만", session_id="conv-subway-core")

    assert followup.cards == []
    assert followup.lookup_mode == "clarification"
    assert "확인하기 어렵습니다" in followup.answer


def test_tourism_chat_applies_negative_preference_in_followup(tmp_path):
    service = TourismChatService(tourism_settings(tourism_live_cache_path=tmp_path / "live_cache"), FakeRetriever(), TourismQueryService())

    service.answer("부산 중구에서 휠체어 관광지 추천해줘", session_id="conv-negative")
    followup = service.answer("그중 시장 말고", session_id="conv-negative")

    assert "부산 중구" in followup.answer
    assert all("시장" not in card.title for card in followup.cards)


def test_tourism_chat_does_not_inherit_sigungu_when_switching_to_area(tmp_path):
    service = TourismChatService(tourism_settings(tourism_live_cache_path=tmp_path / "live_cache"), FakeRetriever(), TourismQueryService())

    service.answer("강릉에서 휠체어 관광지 추천해줘", session_id="conv-area-switch")
    followup = service.answer("강릉 말고 서울로", session_id="conv-area-switch")

    assert followup.cards
    assert "서울" in followup.answer
    assert all("강릉" not in (card.address or "") for card in followup.cards)


def test_tourism_chat_removes_excluded_previous_preference(tmp_path):
    service = TourismChatService(tourism_settings(tourism_live_cache_path=tmp_path / "live_cache"), FakeRetriever(), TourismQueryService())

    service.answer("서울에서 시장 관광지 추천해줘", session_id="conv-preference-remove")
    followup = service.answer("시장 말고 휠체어 기준", session_id="conv-preference-remove")

    assert followup.cards
    assert "서울" in followup.answer
    assert all("시장" not in card.title for card in followup.cards)


def test_tourism_chat_uses_stroller_mobility_evidence_when_no_dedicated_stroller_field(tmp_path):
    sample_dir = tmp_path / "samples"
    sample_dir.mkdir()
    card = TourismPlaceCard(
        content_id="stroller-mobility",
        title="평탄한 산책 공원",
        address="서울 중구",
        recommendation_reason="주 출입통로에 턱이 없어 이동이 편합니다.",
        accessibility_tags=["휠체어 접근", "경사로"],
        raw_fields={"출입통로": "주 출입구는 턱이 없어 이동 가능합니다."},
    )
    (sample_dir / "stroller_mobility.md").write_text(TourismNormalizer().card_to_markdown(card), encoding="utf-8")
    service = TourismChatService(
        tourism_settings(tourism_sample_path=sample_dir, tourism_live_cache_path=tmp_path / "live_cache", tour_api_service_key=None),
        EmptyRetriever(),
        TourismQueryService(),
    )

    response = service.answer("서울에서 유모차로 이동하기 좋은 관광지 추천")

    assert [card.title for card in response.cards] == ["평탄한 산책 공원"]


def test_tourism_chat_requires_explicit_detail_terms_on_same_card(tmp_path):
    sample_dir = tmp_path / "samples"
    sample_dir.mkdir()
    cards = [
        TourismPlaceCard(
            content_id="guide-dog-only",
            title="보조견만 가능한 곳",
            address="대구 중구",
            recommendation_reason="보조견 동반 가능합니다.",
            accessibility_tags=["보조견"],
            raw_fields={"보조견": "보조견 동반 가능"},
        ),
        TourismPlaceCard(
            content_id="braille-guide-dog",
            title="점자 안내 박물관",
            address="대구 중구",
            recommendation_reason="점자블록과 보조견 동반 정보가 확인됩니다.",
            accessibility_tags=["점자블록", "보조견"],
            raw_fields={"점자블록": "점자블록 있음", "보조견": "보조견 동반 가능"},
        ),
    ]
    for card in cards:
        (sample_dir / f"{card.content_id}.md").write_text(TourismNormalizer().card_to_markdown(card), encoding="utf-8")
    service = TourismChatService(
        tourism_settings(tourism_sample_path=sample_dir, tourism_live_cache_path=tmp_path / "live_cache", tour_api_service_key=None),
        EmptyRetriever(),
        TourismQueryService(),
    )

    response = service.answer("대구에서 점자블록과 안내견 가능한 관광지 추천")

    assert [card.title for card in response.cards] == ["점자 안내 박물관"]


def test_tourism_chat_contextualizes_visual_accessibility_card_reason(tmp_path):
    sample_dir = tmp_path / "samples"
    sample_dir.mkdir()
    card = TourismPlaceCard(
        content_id="jeju-braille",
        title="제주 점자 안내관",
        address="제주특별자치도 제주시",
        recommendation_reason="제주 점자 안내관은(는) 휠체어 접근, 장애인 주차, 장애인 화장실 정보가 확인되어 조건에 맞는 후보입니다.",
        accessibility_tags=["휠체어 접근", "장애인 주차", "장애인 화장실", "점자블록"],
        raw_fields={
            "휠체어": "대여 가능",
            "주차": "장애인 주차장 있음",
            "점자블록": "점자블록 있음(출입구 앞)",
        },
    )
    (sample_dir / "jeju_braille.md").write_text(TourismNormalizer().card_to_markdown(card), encoding="utf-8")
    service = TourismChatService(
        tourism_settings(tourism_sample_path=sample_dir, tourism_live_cache_path=tmp_path / "live_cache", tour_api_service_key=None),
        EmptyRetriever(),
        TourismQueryService(),
    )

    response = service.answer("제주에서 점자 안내 있는 곳 찾아줘")

    assert response.cards
    assert response.cards[0].recommendation_reason.startswith("제주 점자 안내관은(는) 점자블록")
    assert response.cards[0].accessibility_tags == ["점자블록"]
    assert "1. 제주 점자 안내관: 점자블록 / 점자블록: 점자블록 있음" in response.answer
    assert "1. 제주 점자 안내관: 휠체어 접근" not in response.answer


def test_tourism_chat_relaxes_multi_condition_unless_all_conditions_are_explicit(tmp_path):
    sample_dir = tmp_path / "samples"
    sample_dir.mkdir()
    wheelchair_only = TourismPlaceCard(
        content_id="wheelchair-only",
        title="휠체어 접근 공원",
        address="서울 중구",
        recommendation_reason="휠체어 접근 가능한 출입통로가 있습니다.",
        accessibility_tags=["휠체어 접근"],
        raw_fields={"휠체어": "휠체어 접근 가능", "출입통로": "턱 없음"},
    )
    stroller_only = TourismPlaceCard(
        content_id="stroller-only",
        title="영유아 편의관",
        address="서울 중구",
        recommendation_reason="수유실과 유아용 의자가 있습니다.",
        family_tags=["수유실", "유아용 의자"],
        raw_fields={"수유실": "수유실 있음", "유아용 의자": "유아용 의자 있음"},
    )
    for card in [wheelchair_only, stroller_only]:
        (sample_dir / f"{card.content_id}.md").write_text(TourismNormalizer().card_to_markdown(card), encoding="utf-8")
    service = TourismChatService(
        tourism_settings(tourism_sample_path=sample_dir, tourism_live_cache_path=tmp_path / "live_cache", tour_api_service_key=None),
        EmptyRetriever(),
        TourismQueryService(),
    )

    loose = service.answer("서울에서 휠체어와 유모차 가능한 관광지 추천")
    strict = service.answer("서울에서 휠체어와 유모차 둘 다 가능한 관광지 추천")

    assert loose.cards
    assert strict.cards == []


def test_tourism_chat_excludes_food_cards_with_table_evidence(tmp_path):
    sample_dir = tmp_path / "samples"
    sample_dir.mkdir()
    museum = TourismPlaceCard(
        content_id="museum",
        title="서울 전시관",
        address="서울특별시 중구",
        recommendation_reason="휠체어 접근 가능한 전시관입니다.",
        accessibility_tags=["휠체어 접근"],
        raw_fields={"휠체어": "휠체어 접근 가능"},
    )
    restaurant = TourismPlaceCard(
        content_id="restaurant",
        title="서울 맛집",
        address="서울특별시 중구",
        recommendation_reason="휠체어 접근 가능한 음식점입니다.",
        accessibility_tags=["휠체어 접근"],
        raw_fields={"유아용 의자": "의자식 테이블 있음"},
    )
    for card in [museum, restaurant]:
        (sample_dir / f"{card.content_id}.md").write_text(TourismNormalizer().card_to_markdown(card), encoding="utf-8")
    service = TourismChatService(
        tourism_settings(tourism_sample_path=sample_dir, tourism_live_cache_path=tmp_path / "live_cache", tour_api_service_key=None),
        EmptyRetriever(),
        TourismQueryService(),
    )

    response = service.answer("서울에서 휠체어 관광지 추천해줘. 식당이나 카페 말고 관광지 위주로")

    assert [card.title for card in response.cards] == ["서울 전시관"]


def test_tourism_chat_uses_mobility_evidence_for_stroller_place_type_preference(tmp_path):
    sample_dir = tmp_path / "samples"
    sample_dir.mkdir()
    family_museum = TourismPlaceCard(
        content_id="family-museum",
        title="부산 어린이 전시관",
        address="부산광역시 중구",
        recommendation_reason="유모차 대여가 가능한 전시관입니다.",
        family_tags=["유모차 대여"],
        raw_fields={"유모차": "유모차 대여 가능"},
    )
    accessible_market = TourismPlaceCard(
        content_id="accessible-market",
        title="부산 먹거리 시장",
        address="부산광역시 중구",
        recommendation_reason="시장 안 출입구까지 턱이 없어 휠체어 접근이 가능합니다.",
        accessibility_tags=["휠체어 접근"],
        raw_fields={"출입통로": "출입구까지 턱이 없어 휠체어 접근 가능"},
    )
    for card in [family_museum, accessible_market]:
        (sample_dir / f"{card.content_id}.md").write_text(TourismNormalizer().card_to_markdown(card), encoding="utf-8")
    service = TourismChatService(
        tourism_settings(tourism_sample_path=sample_dir, tourism_live_cache_path=tmp_path / "live_cache", tour_api_service_key=None),
        EmptyRetriever(),
        TourismQueryService(),
    )

    response = service.answer("부산 중구에서 먹거리나 시장 위주로 유모차 가능한 곳 보여줘")

    assert response.cards
    assert response.cards[0].title == "부산 먹거리 시장"

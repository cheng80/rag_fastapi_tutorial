import json
from pathlib import Path

import pytest

from app.core.config import Settings
from app.schemas.tourism import TourismPlaceCard
from app.services.tourism_chat_service import TourismChatService
from app.services.tourism_query_service import TourismQueryService


class EmptyRetriever:
    def retrieve(self, message: str):
        return []


def _region_quality_cases(limit: int = 110) -> list[tuple[str, str, str, str]]:
    payload = json.loads(Path("data/processed/tour_area_codes.json").read_text(encoding="utf-8"))
    legacy_region_names = {"청원군", "마산시", "진해시", "남제주군", "북제주군"}
    cases = []
    seen = set()
    for region, meta in payload["region_index"].items():
        area_name = meta.get("area_name")
        sigungu_name = meta.get("sigungu_name")
        sigungu_code = meta.get("sigungu_code")
        if not area_name or not sigungu_name or not sigungu_code:
            continue
        if region in legacy_region_names or sigungu_name in legacy_region_names:
            continue
        key = (area_name, sigungu_name)
        if key in seen:
            continue
        seen.add(key)
        cases.append((f"{region}에서 휠체어 관광지 추천해줘", region, area_name, sigungu_name))
        if len(cases) >= limit:
            break
    assert len(cases) >= limit
    return cases


@pytest.mark.parametrize(
    ("message", "expected_region", "expected_area", "expected_sigungu"),
    _region_quality_cases(),
)
def test_quality_region_extraction_matrix(message, expected_region, expected_area, expected_sigungu):
    query = TourismQueryService().extract(message)

    assert query["region"] == expected_region
    assert query["area_name"] == expected_area
    assert query["sigungu_name"] == expected_sigungu
    assert query["is_sigungu"] is True
    assert "휠체어" in query["conditions"]


@pytest.mark.parametrize(
    ("message", "expected_conditions"),
    [
        ("서울에서 휠체어 관광지 추천", {"휠체어"}),
        ("서울에서 무장애 관광지 추천", {"휠체어"}),
        ("서울에서 이동약자와 갈만한 곳", {"휠체어"}),
        ("서울에서 베리어프리 관광지 추천", {"휠체어"}),
        ("서울에서 장애인 화장실 있는 곳", {"화장실"}),
        ("서울에서 유모차 끌고 갈 곳", {"유모차"}),
        ("서울에서 유아차 끌고 갈 곳", {"유모차"}),
        ("서울에서 아이랑 수유실 있는 곳", {"유모차"}),
        ("서울에서 기저귀 교환대 있는 곳", {"유모차"}),
        ("서울에서 어린이와 갈만한 곳", {"유모차"}),
        ("서울에서 영유아 동반 관광지", {"유모차"}),
        ("서울에서 어르신과 갈만한 곳", {"고령자"}),
        ("서울에서 노인 동반 관광지", {"고령자"}),
        ("서울에서 장애인 주차 가능한 곳", {"주차"}),
        ("서울에서 주차 편한 무장애 관광지", {"휠체어", "주차"}),
        ("서울에서 화장실 확인되는 곳", {"화장실"}),
        ("서울에서 경사로 있는 곳", {"접근로"}),
        ("서울에서 턱이 없어 이동하기 좋은 곳", {"접근로"}),
        ("서울에서 동선 단순한 관광지", {"접근로"}),
        ("서울에서 버스로 갈만한 곳", {"대중교통"}),
        ("서울에서 지하철로 갈만한 곳", {"대중교통"}),
        ("서울에서 엘리베이터 있는 곳", {"엘리베이터"}),
        ("서울에서 휠체어 리프트 있는 곳", {"휠체어", "엘리베이터"}),
        ("서울에서 지하철 리프트나 승강기 있는 곳", {"대중교통", "엘리베이터"}),
        ("서울에서 공공기관 리프트 접근 가능한 관광지", {"엘리베이터"}),
        ("서울에서 관광시설 리프트 있는 전시관", {"엘리베이터"}),
        ("서울에서 건물 리프트나 계단 리프트 있는 곳", {"엘리베이터"}),
        ("서울에서 승강기 있는 무장애 관광지", {"휠체어", "엘리베이터"}),
        ("서울에서 휠체어와 유모차 모두 편한 곳", {"휠체어", "유모차"}),
        ("서울에서 아이랑 화장실 확인되는 곳", {"유모차", "화장실"}),
        ("서울에서 어르신 모시고 주차 가능한 곳", {"고령자", "주차"}),
        ("서울에서 접근로와 장애인 화장실 확인되는 곳", {"접근로", "화장실"}),
        ("서울에서 휠체어 타는 아빠와 갈만한 곳", {"휠체어"}),
        ("서울에서 휠체어 타시는 어머니와 갈만한 곳", {"휠체어"}),
        ("서울에서 바퀴 의자 이동 가능한 곳", {"휠체어"}),
        ("서울에서 휠쳐 관광지 추천", {"휠체어"}),
        ("서울에서 안내견 동반 가능한 곳", {"보조견"}),
        ("서울에서 보조갼 동반 가능한 곳", {"보조견"}),
        ("서울에서 점자블록이나 오디오가이드 있는 곳", {"시각장애"}),
        ("서울에서 음성 안내나 촉 지 도 있는 곳", {"시각장애"}),
        ("서울에서 수어 안내나 자막 있는 곳", {"청각장애"}),
        ("서울에서 영상안내나 자 막 있는 곳", {"청각장애"}),
        ("서울에서 무단차 출입통로 있는 곳", {"접근로"}),
        ("서울에서 부모님이 무리 없는 곳", {"고령자"}),
    ],
)
def test_quality_condition_extraction_matrix(message, expected_conditions):
    query = TourismQueryService().extract(message)

    assert expected_conditions <= set(query["conditions"])


def test_quality_query_handles_nearby_sigungu_with_wheelchair_typo():
    query = TourismQueryService().extract("서울 강남구 근처에서 휄체어 관광지 추천해줘")

    assert query["region"] == "서울 강남구"
    assert query["area_name"] == "서울"
    assert query["sigungu_name"] == "강남구"
    assert query["is_sigungu"] is True
    assert query["allow_region_expansion"] is False
    assert "휠체어" in query["conditions"]
    assert query["normalized_query"] == "서울 강남구 근처에서 휠체어 관광지 추천해줘"
    assert "휄체어->휠체어" in query["normalization_corrections"]


def test_quality_query_extracts_preferences_and_negative_preferences():
    query = TourismQueryService().extract("서울에서 비 오는 날 실내 박물관 추천해줘. 호텔은 빼고")

    assert {"실내", "박물관_전시"} <= set(query["preferences"])
    assert "숙박" in query["excluded_preferences"]


def test_quality_ranking_prefers_requested_accessibility_evidence(tmp_path):
    service = TourismChatService(
        Settings(tourism_sample_path=tmp_path / "samples", tourism_live_cache_path=tmp_path / "live", tour_api_service_key=None),
        EmptyRetriever(),
        TourismQueryService(),
    )
    query = {
        "region": "서울",
        "conditions": ["휠체어", "화장실", "엘리베이터"],
        "features": [],
    }
    weak = TourismPlaceCard(
        content_id="weak",
        title="서울 산책길",
        address="서울",
        recommendation_reason="서울에 있어 후보입니다.",
        accessibility_tags=["휠체어 접근"],
        raw_fields={"출입통로": "휠체어 접근 가능"},
    )
    strong = TourismPlaceCard(
        content_id="strong",
        title="서울 실내박물관",
        address="서울",
        recommendation_reason="휠체어 접근, 장애인 화장실, 엘리베이터 정보가 확인되었습니다.",
        accessibility_tags=["휠체어 접근", "장애인 화장실", "엘리베이터"],
        raw_fields={
            "출입통로": "주출입구는 턱이 없어 휠체어 접근 가능함",
            "화장실": "장애인 화장실 있음",
            "엘리베이터": "엘리베이터 있음",
        },
    )

    ranked = service._rank_cards([weak, strong], "서울에서 휠체어 화장실 엘리베이터 있는 곳", query)

    assert [card.content_id for card in ranked] == ["strong", "weak"]


def test_quality_ranking_prefers_family_evidence_for_child_query(tmp_path):
    service = TourismChatService(
        Settings(tourism_sample_path=tmp_path / "samples", tourism_live_cache_path=tmp_path / "live", tour_api_service_key=None),
        EmptyRetriever(),
        TourismQueryService(),
    )
    query = {
        "region": "서울",
        "conditions": ["유모차", "화장실"],
        "features": [],
    }
    adult_only = TourismPlaceCard(
        content_id="adult",
        title="서울 전시관",
        address="서울",
        recommendation_reason="화장실 정보가 확인되었습니다.",
        accessibility_tags=["장애인 화장실"],
        raw_fields={"화장실": "장애인 화장실 있음"},
    )
    family = TourismPlaceCard(
        content_id="family",
        title="서울 가족박물관",
        address="서울",
        recommendation_reason="유모차 대여, 수유실, 기저귀 교환대 정보가 확인되었습니다.",
        family_tags=["유모차 대여", "수유실", "영유아 동반"],
        raw_fields={"유모차": "대여가능", "수유실": "수유실 있음", "영유아 가족 편의": "기저귀 교환대 있음"},
    )

    ranked = service._rank_cards([adult_only, family], "서울에서 아이랑 유모차 화장실 확인되는 곳", query)

    assert [card.content_id for card in ranked] == ["family", "adult"]


def test_quality_ranking_prefers_soft_preferences_and_excludes_negative_preferences(tmp_path):
    service = TourismChatService(
        Settings(tourism_sample_path=tmp_path / "samples", tourism_live_cache_path=tmp_path / "live", tour_api_service_key=None),
        EmptyRetriever(),
        TourismQueryService(),
    )
    query = {
        "region": "서울",
        "conditions": [],
        "features": [],
        "preferences": ["실내", "박물관_전시"],
        "excluded_preferences": ["숙박"],
    }
    hotel = TourismPlaceCard(
        content_id="hotel",
        title="서울 관광호텔",
        address="서울",
        recommendation_reason="숙박 가능한 호텔입니다.",
        raw_fields={"숙박": "객실 있음"},
    )
    museum = TourismPlaceCard(
        content_id="museum",
        title="서울 역사박물관",
        address="서울",
        recommendation_reason="비 오는 날에도 관람하기 좋은 실내 전시관입니다.",
        raw_fields={"안내시설": "전시관 내부 관람 가능"},
    )

    ranked = service._rank_cards([hotel, museum], "서울에서 비 오는 날 실내 박물관 추천. 호텔은 빼고", query)

    assert [card.content_id for card in ranked] == ["museum"]


def test_quality_strong_food_preference_excludes_indoor_gallery(tmp_path):
    service = TourismChatService(
        Settings(tourism_sample_path=tmp_path / "samples", tourism_live_cache_path=tmp_path / "live", tour_api_service_key=None),
        EmptyRetriever(),
        TourismQueryService(),
    )
    query = {
        "preferences": ["실내", "시장_먹거리", "카페_음식점"],
    }
    gallery = TourismPlaceCard(
        content_id="gallery",
        title="나폴레옹갤러리",
        address="경기도 성남시",
        recommendation_reason="실내 미술 갤러리입니다.",
        raw_fields={"안내": "실내 전시 관람 가능"},
    )
    restaurant = TourismPlaceCard(
        content_id="restaurant",
        title="성남 실내식당",
        address="경기도 성남시",
        recommendation_reason="실내 음식점입니다.",
        raw_fields={"음식점": "의자식 테이블 있음"},
    )

    filtered = service._filter_cards_by_preferences([gallery, restaurant], query)

    assert [card.content_id for card in filtered] == ["restaurant"]


def test_quality_ranking_scores_sensory_accessibility_evidence(tmp_path):
    service = TourismChatService(
        Settings(tourism_sample_path=tmp_path / "samples", tourism_live_cache_path=tmp_path / "live", tour_api_service_key=None),
        EmptyRetriever(),
        TourismQueryService(),
    )
    query = {
        "region": "서울",
        "conditions": ["시각장애"],
        "features": [],
        "preferences": [],
        "excluded_preferences": [],
    }
    generic = TourismPlaceCard(
        content_id="generic",
        title="서울 문화관",
        address="서울",
        recommendation_reason="서울에 있어 후보입니다.",
    )
    sensory = TourismPlaceCard(
        content_id="sensory",
        title="서울 접근성 전시관",
        address="서울",
        recommendation_reason="점자블록과 오디오가이드 정보가 확인되었습니다.",
        accessibility_tags=["점자블록", "오디오가이드"],
        raw_fields={"시각장애 편의": "점자블록 있음, 오디오가이드 있음"},
    )

    ranked = service._rank_cards([generic, sensory], "서울에서 점자블록 오디오가이드 있는 곳", query)

    assert [card.content_id for card in ranked] == ["sensory", "generic"]


def test_quality_answer_includes_specific_card_evidence(tmp_path):
    service = TourismChatService(
        Settings(tourism_sample_path=tmp_path / "samples", tourism_live_cache_path=tmp_path / "live", tour_api_service_key=None),
        EmptyRetriever(),
        TourismQueryService(),
    )
    card = TourismPlaceCard(
        content_id="evidence",
        title="서울 접근성 박물관",
        address="서울",
        recommendation_reason="휠체어 접근, 장애인 화장실 정보가 확인되었습니다.",
        accessibility_tags=["휠체어 접근", "장애인 화장실"],
        raw_fields={
            "출입통로": "주출입구는 턱이 없어 휠체어 접근 가능함",
            "화장실": "장애인 화장실 있음(1층)",
        },
    )

    answer = service._build_answer([card], {"region": "서울", "conditions": ["휠체어", "화장실"]})

    assert "서울 접근성 박물관" in answer
    assert "주출입구" in answer
    assert "장애인 화장실" in answer

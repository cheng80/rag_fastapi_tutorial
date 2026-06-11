from fastapi.testclient import TestClient

from app.api.deps import get_tourism_chat_service
from app.main import app
from app.schemas.tourism import TourismChatResponse, TourismPlaceCard


class FakeTourismChatService:
    def answer(self, message: str, session_id: str | None = None):
        return TourismChatResponse(
            answer="서울 기준으로 1곳을 추천합니다.",
            cards=[
                TourismPlaceCard(
                    content_id="sample",
                    title="테스트 관광지",
                    recommendation_reason="휠체어 접근 정보가 확인되었습니다.",
                    accessibility_tags=["휠체어 접근"],
                    family_tags=["가족 친화"],
                )
            ],
            sources=[],
        )


class FailingTourismChatService:
    def answer(self, message: str, session_id: str | None = None):
        raise RuntimeError("secret internal path private-dir")


def test_tourism_chat_api_smoke():
    app.dependency_overrides[get_tourism_chat_service] = lambda: FakeTourismChatService()
    client = TestClient(app)

    response = client.post("/tourism/chat", json={"message": "서울 휠체어 관광지 추천"})

    app.dependency_overrides.clear()
    assert response.status_code == 200
    data = response.json()
    assert data["cards"][0]["title"] == "테스트 관광지"
    assert data["cards"][0]["accessibility_tags"] == ["휠체어 접근"]


def test_tourism_chat_rejects_blank_message():
    app.dependency_overrides[get_tourism_chat_service] = lambda: FakeTourismChatService()
    client = TestClient(app)

    response = client.post("/tourism/chat", json={"message": "   "})

    app.dependency_overrides.clear()
    assert response.status_code == 400
    assert response.json()["detail"] == "message는 비어 있을 수 없습니다."


def test_tourism_chat_hides_internal_exception_details():
    app.dependency_overrides[get_tourism_chat_service] = lambda: FailingTourismChatService()
    client = TestClient(app)

    response = client.post("/tourism/chat", json={"message": "서울 휠체어 관광지 추천"})

    app.dependency_overrides.clear()
    assert response.status_code == 500
    assert response.json()["detail"] == {
        "code": "TOURISM_CHAT_FAILED",
        "message": "관광 상담 응답을 만드는 중 문제가 발생했습니다. 잠시 후 다시 시도해 주세요.",
    }
    assert "secret internal path" not in response.text


def test_tourism_regions_lists_area_then_sigungu_options():
    client = TestClient(app)

    response = client.get("/tourism/regions")

    assert response.status_code == 200
    areas = response.json()["areas"]
    seoul = next(area for area in areas if area["name"] == "서울")
    busan = next(area for area in areas if area["name"] == "부산")
    assert "강남구" in seoul["sigungu"]
    assert "중구" in busan["sigungu"]

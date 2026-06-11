import json
import subprocess
from pathlib import Path

from app.services.tourism_query_service import TourismQueryService


PROJECT_ROOT = Path(__file__).resolve().parents[1]
WEB_ROOT = PROJECT_ROOT / "frontend" / "web"


def build_option_message(state: dict) -> str:
    script = """
const builder = require('./frontend/web/option_flow_builder.js');
const state = JSON.parse(process.argv[1]);
process.stdout.write(builder.buildOptionFlowMessage(state));
"""
    result = subprocess.run(
        ["node", "-e", script, json.dumps(state, ensure_ascii=False)],
        cwd=PROJECT_ROOT,
        check=True,
        text=True,
        capture_output=True,
    )
    return result.stdout


def test_option_flow_builds_conditional_expansion_query():
    message = build_option_message(
        {
            "area": "서울",
            "sigungu": "강남구",
            "conditions": ["wheelchair", "restroom"],
            "preferences": [],
            "exclusions": [],
            "intensity": "required",
            "expansion": "conditional",
        }
    )

    assert message == "서울 강남구에서 휠체어 접근과 장애인 화장실 모두 있는 관광지 추천해줘. 부족하면 서울 전체로 넓혀줘"

    query = TourismQueryService().extract(message)
    assert {"휠체어", "화장실"} <= set(query["conditions"])
    assert query["require_all_conditions"] is True
    assert query["allow_region_expansion"] is True
    assert query["conditional_region_expansion"] is True


def test_option_flow_builds_preference_and_exclusion_query():
    message = build_option_message(
        {
            "area": "부산",
            "conditions": ["stroller"],
            "preferences": ["indoor"],
            "exclusions": ["market"],
            "intensity": "optional",
            "expansion": "local_only",
        }
    )

    assert message == "부산에서 실내 유모차 있으면 좋은 관광지 추천해줘. 시장은 제외해줘"


def test_option_flow_uses_natural_korean_and_particle():
    message = build_option_message(
        {
            "area": "울산",
            "sigungu": "남구",
            "conditions": ["stroller", "nursing"],
            "preferences": ["park"],
            "intensity": "required",
            "expansion": "local_only",
        }
    )

    assert message == "울산 남구 안에서 공원이나 산책하기 좋은 유모차와 수유실 모두 있는 관광지 추천해줘"


def test_option_flow_ui_keeps_existing_chat_contract():
    html = (WEB_ROOT / "index.html").read_text(encoding="utf-8")
    app_js = (WEB_ROOT / "app.js").read_text(encoding="utf-8")

    assert 'id="chatModeButton"' in html
    assert 'id="optionModeButton"' in html
    assert 'id="promptDrawer" class="prompt-drawer chat-only-drawer"' in html
    assert 'id="optionDrawer"' in html
    assert 'id="optionBuilder"' in html
    assert 'id="optionSummary" class="option-summary" hidden' in html
    assert '<select id="optionSigungu" disabled>' in html
    assert 'fetch(`${normalizedApiBase()}/tourism/regions`)' in app_js
    assert "populateSigunguOptions(optionArea.value)" in app_js
    assert "collapseComposerAfterSubmit()" in app_js
    assert "optionDrawer.open = false" in app_js
    assert '<script src="./option_flow_builder.js" defer></script>' in html
    assert html.index("option_flow_builder.js") < html.index("app.js")
    assert 'fetch(`${normalizedApiBase()}/tourism/chat`' in app_js
    assert "JSON.stringify({ message, session_id: sessionId })" in app_js

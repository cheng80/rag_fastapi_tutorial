import importlib
import json
import re
import shutil
import sys
from html.parser import HTMLParser
from pathlib import Path

from fastapi.testclient import TestClient


PROJECT_ROOT = Path(__file__).resolve().parents[1]
TEMPLATE_ROOT = PROJECT_ROOT / "project_template"
INTERNAL_TERMS = (
    "Chroma",
    "top_k",
    "lookup_mode",
    "fallback",
    "debug",
    "pipeline",
    "parity",
)


class VisibleTextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        stripped = data.strip()
        if stripped:
            self.parts.append(stripped)

    def text(self) -> str:
        return " ".join(self.parts)


def load_template_app():
    assert (TEMPLATE_ROOT / "app" / "main.py").exists(), "project_template app entrypoint missing"
    sys.path.insert(0, str(TEMPLATE_ROOT))
    for module_name in list(sys.modules):
        if module_name == "app" or module_name.startswith("app."):
            del sys.modules[module_name]
    return importlib.import_module("app.main").app


def remove_template_runtime_artifacts() -> None:
    for path in [
        TEMPLATE_ROOT / "data" / "vector_store" / "chroma",
        TEMPLATE_ROOT / ".pytest_cache",
    ]:
        if path.exists():
            shutil.rmtree(path)
    for path in TEMPLATE_ROOT.rglob("__pycache__"):
        shutil.rmtree(path)
    for path in TEMPLATE_ROOT.rglob("*.pyc"):
        path.unlink()


def test_project_template_health_and_regions_surface():
    # Given: a project_template FastAPI app with original-style tourism data.
    app = load_template_app()
    client = TestClient(app)

    # When: health and region endpoints are called through the HTTP app surface.
    health_response = client.get("/health")
    regions_response = client.get("/tourism/regions")

    # Then: the app exposes the original health contract and nationwide regions.
    assert health_response.status_code == 200
    assert health_response.json() == {"status": "ok"}
    assert regions_response.status_code == 200
    areas = regions_response.json()["areas"]
    assert len(areas) == 17

    by_name = {area["name"]: area for area in areas}
    assert {"서울", "부산", "인천"} <= set(by_name)
    assert "중구" in by_name["서울"]["sigungu"]
    assert "중구" in by_name["부산"]["sigungu"]
    assert "중구" in by_name["인천"]["sigungu"]
    assert "강남구" in by_name["서울"]["sigungu"]
    assert "해운대구" in by_name["부산"]["sigungu"]

    area_codes = json.loads(
        (TEMPLATE_ROOT / "data" / "processed" / "tour_area_codes.json").read_text(encoding="utf-8")
    )
    region_index = area_codes["region_index"]
    assert region_index["강남구"]["area_name"] == "서울"
    assert region_index["해운대구"]["area_name"] == "부산"
    assert region_index["제주시"]["area_name"] == "제주특별자치도"
    assert "중구" in area_codes["ambiguous_region_aliases"]
    remove_template_runtime_artifacts()


def test_project_template_tourism_chat_rejects_blank_without_internal_terms():
    # Given: a project_template FastAPI app.
    app = load_template_app()
    client = TestClient(app)

    # When: malformed blank input reaches the tourism chat endpoint.
    response = client.post("/tourism/chat", json={"message": "   "})

    # Then: the user-facing error is clean and contains no implementation terms.
    assert response.status_code == 400
    assert response.json()["detail"] == "message는 비어 있을 수 없습니다."
    for term in INTERNAL_TERMS:
        assert term not in response.text
    remove_template_runtime_artifacts()


def test_project_template_tourism_chat_uses_original_seed_cards_without_live_api(monkeypatch):
    # Given: the project_template app runs without a TourAPI key or live network lookup.
    monkeypatch.setenv("TOUR_API_SERVICE_KEY", "")
    monkeypatch.setenv("TOUR_API_ACCESSIBLE_SERVICE_KEY", "")
    monkeypatch.setenv("TOURISM_LIVE_LOOKUP_ENABLED", "false")
    monkeypatch.setenv("TOURISM_QUERY_EVENT_LOG_ENABLED", "false")
    app = load_template_app()
    client = TestClient(app)

    # When: a specific original-app tourism query reaches the real API route.
    response = client.post("/tourism/chat", json={"message": "서울 강남구 휠체어 관광지 추천"})

    # Then: the template still returns original-style evidence-backed recommendation cards.
    assert response.status_code == 200
    data = response.json()
    assert data["lookup_mode"] in {"cache", "indexed", "sample", "live_top_up"}
    assert len(data["cards"]) >= 1
    assert any("강남구" in (card.get("address") or "") for card in data["cards"])
    assert any(
        "휠체어" in " ".join(
            [
                card.get("recommendation_reason") or "",
                " ".join(card.get("accessibility_tags") or []),
            ]
        )
        for card in data["cards"]
    )
    remove_template_runtime_artifacts()


def test_project_template_web_ui_contract_and_no_user_internal_terms():
    # Given: original-style static tourism UI files in project_template.
    web_root = TEMPLATE_ROOT / "frontend" / "web"
    html_path = web_root / "index.html"
    app_js_path = web_root / "app.js"
    option_builder_path = web_root / "option_flow_builder.js"
    styles_path = web_root / "styles.css"
    assert html_path.exists(), "project_template tourism UI index missing"

    # When: the UI files are inspected as the browser-facing contract.
    html = html_path.read_text(encoding="utf-8")
    app_js = app_js_path.read_text(encoding="utf-8")
    option_builder = option_builder_path.read_text(encoding="utf-8")
    styles = styles_path.read_text(encoding="utf-8")

    # Then: option-flow controls and endpoint wiring match the original surface.
    assert 'id="chatModeButton"' in html
    assert 'id="optionModeButton"' in html
    assert 'id="optionDrawer"' in html
    assert 'id="optionBuilder"' in html
    assert '<select id="optionSigungu" disabled>' in html
    assert '<script src="./option_flow_builder.js" defer></script>' in html
    assert html.index("option_flow_builder.js") < html.index("app.js")
    assert 'fetch(`${normalizedApiBase()}/tourism/regions`)' in app_js
    assert 'fetch(`${normalizedApiBase()}/tourism/chat`' in app_js
    assert "populateSigunguOptions(optionArea.value)" in app_js
    assert "collapseComposerAfterSubmit()" in app_js
    assert "optionDrawer.open = false" in app_js
    assert "buildOptionFlowMessage" in option_builder
    assert ".option-drawer" in styles

    parser = VisibleTextParser()
    parser.feed(html)
    visible_text = parser.text()
    forbidden_visible_text = (
        "RAG 질문",
        "FastAPI tutorial result",
        "Chroma 관광 근거 검색",
        "top_k",
        "lookup_mode",
        "fallback",
        "pipeline",
        "parity",
    )
    for term in forbidden_visible_text:
        assert term not in visible_text


def test_project_template_excludes_runtime_artifacts_and_resolves_readme_links():
    # Given: project_template is the deliverable copied from the original app.
    remove_template_runtime_artifacts()
    forbidden_paths = [
        TEMPLATE_ROOT / ".pytest_cache",
        TEMPLATE_ROOT / "data" / "vector_store" / "chroma",
    ]
    local_venv_path = TEMPLATE_ROOT / ".venv"
    if local_venv_path.exists() and not local_venv_path.is_symlink():
        forbidden_paths.append(local_venv_path)
    forbidden_files = list(TEMPLATE_ROOT.rglob("*.pyc"))
    forbidden_files.extend(TEMPLATE_ROOT.rglob("*.sqlite3"))
    forbidden_files.extend(TEMPLATE_ROOT.rglob("*.db"))

    # When: runtime artifacts and README links are inspected.
    existing_forbidden_paths = [path for path in forbidden_paths if path.exists()]
    existing_forbidden_files = [path for path in forbidden_files if path.exists()]
    readme = (TEMPLATE_ROOT / "README.md").read_text(encoding="utf-8")
    linked_paths = [
        TEMPLATE_ROOT / match.group(1)
        for match in re.finditer(r"\]\((?!https?://)([^)#]+)", readme)
        if not match.group(1).startswith("#")
    ]
    missing_links = [path for path in linked_paths if not path.exists()]

    # Then: the template contains no runtime cache files and no broken local README links.
    assert existing_forbidden_paths == []
    assert existing_forbidden_files == []
    assert missing_links == []

from argparse import ArgumentParser
from html.parser import HTMLParser
from pathlib import Path
from typing import Final, Literal, assert_never


PROJECT_ROOT: Final = Path(__file__).resolve().parents[1]
REFERENCE_DOC: Final = PROJECT_ROOT / "docs" / "original_app_reference.md"
TUTORIAL_DOC: Final = PROJECT_ROOT / "docs" / "tutorial_build_original_app.md"
TEMPLATE_ROOT: Final = PROJECT_ROOT / "project_template"
CHAPTERS_ROOT: Final = PROJECT_ROOT / "docs" / "chapters"
REFERENCES_ROOT: Final = PROJECT_ROOT / "docs" / "references"
NOTEBOOK_TEMPLATES_ROOT: Final = PROJECT_ROOT / "notebooks" / "templates"
NOTEBOOK_EXECUTED_ROOT: Final = PROJECT_ROOT / "notebooks" / "executed"

CheckName = Literal[
    "original-map",
    "tutorial-chapters",
    "tutorial-book-structure",
    "no-ui-tutorial-leak",
    "all",
]

EXPECTED_CHAPTERS: Final = [
    "00_roadmap.md",
    "01_environment.md",
    "02_fastapi.md",
    "03_document_loading.md",
    "04_chunk_embedding.md",
    "05_chroma_retrieval.md",
    "06_rag_answer.md",
    "07_chat_api.md",
    "08_tourapi.md",
    "09_cache_fallback.md",
    "10_region_parsing.md",
    "11_intent_context.md",
    "12_card_evidence.md",
    "13_eval_event.md",
    "14_web_ui.md",
    "15_operations.md",
    "16_notion.md",
]
REQUIRED_CHAPTER_SECTIONS: Final = [
    "이번 장에서 만들 것",
    "왜 필요한가",
    "최종 폴더 상태",
    "새로 만들 파일",
    "코드 전체",
    "코드 흐름 설명",
    "실행 명령",
    "성공 기준",
    "검증 노트북",
    "자주 나는 오류와 해결",
    "다음 장으로 넘어가기 전 체크리스트",
]
EXPECTED_REFERENCES: Final = [
    "terms.md",
    "commands.md",
    "troubleshooting.md",
    "production_mapping.md",
]
EXPECTED_NOTEBOOKS: Final = [
    "01_environment_check.ipynb",
    "02_fastapi_health_check.ipynb",
    "03_document_loading_check.ipynb",
    "04_embedding_retrieval_check.ipynb",
    "05_chat_api_check.ipynb",
    "06_tourapi_cache_fallback_check.ipynb",
    "07_eval_report_check.ipynb",
    "08_web_ui_smoke_check.ipynb",
]


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


def read_required(path: Path) -> str:
    if not path.exists():
        raise FileNotFoundError(f"{path.relative_to(PROJECT_ROOT)} missing")
    return path.read_text(encoding="utf-8")


def assert_contains(text: str, fragments: list[str]) -> None:
    missing = [fragment for fragment in fragments if fragment not in text]
    if missing:
        raise AssertionError("missing fragments: " + ", ".join(missing))


def validate_original_map() -> str:
    text = read_required(REFERENCE_DOC)
    assert_contains(
        text,
        [
            "원본 앱 파일 맵",
            "app/main.py",
            "app/api/routes/tourism.py",
            "frontend/web/index.html",
            "data/processed/tour_area_codes.json",
            "data/processed/tourapi_bigdata_region_codes.json",
            "복사 금지 대상",
            ".env",
            "로컬 SQLite 데이터베이스",
            "Chroma 런타임 저장소",
            "목표 구조 비교",
            "project_template/app/main.py",
            "project_template/frontend/web/index.html",
        ],
    )
    return "original-map: ok"


def validate_tutorial_chapters() -> str:
    text = read_required(TUTORIAL_DOC)
    chapter_titles = [
        "1장. 원본 기준 고정",
        "2장. 원본 구조 이식",
        "3장. 핵심 기능 재현",
        "4장. 검증 체계 작성",
        "5장. 튜토리얼 문서 운영",
    ]
    section_titles = [
        "왜 필요한가",
        "만들 파일",
        "코드 흐름",
        "실행 명령",
        "확인 기준",
        "자주 나는 오류",
    ]
    for chapter in chapter_titles:
        if chapter not in text:
            raise AssertionError(f"missing chapter: {chapter}")
        chapter_body = text.split(chapter, 1)[1].split("\n## ", 1)[0]
        for section in section_titles:
            if f"### {section}" not in chapter_body:
                raise AssertionError(f"{chapter} missing section: {section}")
    return "tutorial-chapters: ok"


def visible_html_text(path: Path) -> str:
    parser = VisibleTextParser()
    parser.feed(read_required(path))
    return parser.text()


def validate_no_ui_tutorial_leak() -> str:
    visible_text = visible_html_text(TEMPLATE_ROOT / "frontend" / "web" / "index.html")
    forbidden = [
        "FastAPI tutorial result",
        "튜토리얼 결과",
        "튜토리얼 샘플",
        "RAG 질문",
        "Chroma 관광 근거 검색",
        "top_k",
        "lookup_mode",
        "fallback",
        "pipeline",
        "parity",
    ]
    assert_contains_without_match(visible_text, forbidden)
    route_text = read_required(TEMPLATE_ROOT / "app" / "api" / "routes" / "tourism.py")
    assert_contains_without_match(route_text, ["FastAPI tutorial result", "튜토리얼 결과", "튜토리얼 샘플"])
    return "no-ui-tutorial-leak: ok"


def validate_tutorial_book_structure() -> str:
    for chapter_name in EXPECTED_CHAPTERS:
        chapter_text = read_required(CHAPTERS_ROOT / chapter_name)
        for section in REQUIRED_CHAPTER_SECTIONS:
            if f"## {section}" not in chapter_text:
                raise AssertionError(f"{chapter_name} missing section: {section}")
    for reference_name in EXPECTED_REFERENCES:
        read_required(REFERENCES_ROOT / reference_name)
    for notebook_name in EXPECTED_NOTEBOOKS:
        template_text = read_required(NOTEBOOK_TEMPLATES_ROOT / notebook_name)
        executed_text = read_required(NOTEBOOK_EXECUTED_ROOT / notebook_name)
        assert_contains(template_text, ['"cells"', "검증 목적"])
        assert_contains(executed_text, ['"cells"', "검증 완료"])
        assert_notebook_is_lesson(template_text, notebook_name)
        assert_notebook_is_lesson(executed_text, notebook_name)
    return "tutorial-book-structure: ok"


def assert_notebook_is_lesson(text: str, notebook_name: str) -> None:
    assert_contains(text, ["학습 흐름", "실행 전 준비", "튜토리얼 앱 연결", "정리"])
    cell_count = text.count('"cell_type"')
    markdown_count = text.count('"cell_type": "markdown"')
    code_count = text.count('"cell_type": "code"')
    if cell_count < 11:
        raise AssertionError(f"{notebook_name} has too few cells: {cell_count}")
    if markdown_count < 5:
        raise AssertionError(f"{notebook_name} has too few markdown cells: {markdown_count}")
    if code_count < 6:
        raise AssertionError(f"{notebook_name} has too few code cells: {code_count}")
    if len(text) < 3000:
        raise AssertionError(f"{notebook_name} is too thin: {len(text)} chars")


def assert_contains_without_match(text: str, fragments: list[str]) -> None:
    found = [fragment for fragment in fragments if fragment in text]
    if found:
        raise AssertionError("forbidden fragments: " + ", ".join(found))


def parse_check(raw: str) -> CheckName:
    match raw:
        case (
            "original-map"
            | "tutorial-chapters"
            | "tutorial-book-structure"
            | "no-ui-tutorial-leak"
            | "all"
        ):
            return raw
        case _:
            raise ValueError(f"unknown check: {raw}")


def run_check(check: CheckName) -> list[str]:
    match check:
        case "original-map":
            return [validate_original_map()]
        case "tutorial-chapters":
            return [validate_tutorial_chapters()]
        case "tutorial-book-structure":
            return [validate_tutorial_book_structure()]
        case "no-ui-tutorial-leak":
            return [validate_no_ui_tutorial_leak()]
        case "all":
            return [
                validate_original_map(),
                validate_tutorial_chapters(),
                validate_tutorial_book_structure(),
                validate_no_ui_tutorial_leak(),
            ]
        case unreachable:
            assert_never(unreachable)


def main() -> int:
    parser = ArgumentParser()
    parser.add_argument("--check", default="all")
    args = parser.parse_args()
    check = parse_check(args.check)
    for line in run_check(check):
        print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

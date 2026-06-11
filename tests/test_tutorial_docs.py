import subprocess
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REFERENCE_DOC = PROJECT_ROOT / "docs" / "original_app_reference.md"
TUTORIAL_DOC = PROJECT_ROOT / "docs" / "tutorial_build_original_app.md"
VALIDATOR = PROJECT_ROOT / "scripts" / "validate_tutorial_docs.py"
CHAPTERS_ROOT = PROJECT_ROOT / "docs" / "chapters"
REFERENCES_ROOT = PROJECT_ROOT / "docs" / "references"
NOTEBOOK_TEMPLATES_ROOT = PROJECT_ROOT / "notebooks" / "templates"
NOTEBOOK_EXECUTED_ROOT = PROJECT_ROOT / "notebooks" / "executed"
NOTION_DRAFT = PROJECT_ROOT / "notion" / "rag_fastapi_tutorial_notion_draft.md"


def read_text(path: Path) -> str:
    assert path.exists(), f"{path.relative_to(PROJECT_ROOT)} missing"
    return path.read_text(encoding="utf-8")


def test_original_file_map_and_copy_policy_documented():
    # Given: the original-first plan requires a fixed original baseline.
    text = read_text(REFERENCE_DOC)

    # When: the reference document is inspected.
    required_fragments = [
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
    ]

    # Then: the document pins source, exclusions, and comparable target structure.
    for fragment in required_fragments:
        assert fragment in text


def test_tutorial_chapters_have_required_beginner_sections():
    # Given: the plan requires beginner-facing tutorial chapters.
    text = read_text(TUTORIAL_DOC)

    # When: each planned chapter is inspected.
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

    # Then: every chapter includes every required teaching section.
    for chapter in chapter_titles:
        assert chapter in text
        chapter_body = text.split(chapter, 1)[1].split("\n## ", 1)[0]
        for section in section_titles:
            assert f"### {section}" in chapter_body


def test_chapter_files_use_original_first_beginner_book_format():
    # Given: the first git commit required docs/chapters as the tutorial book body.
    expected_chapters = [
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
    required_sections = [
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

    # When: every chapter file is inspected.
    missing_chapters = [name for name in expected_chapters if not (CHAPTERS_ROOT / name).exists()]

    # Then: the chapter set exists and each chapter follows the original beginner-book format.
    assert missing_chapters == []
    for chapter_name in expected_chapters:
        text = read_text(CHAPTERS_ROOT / chapter_name)
        for section in required_sections:
            assert f"## {section}" in text


def test_references_and_notebook_verification_structure_exist():
    # Given: the first git commit required references and verification notebooks.
    reference_files = [
        REFERENCES_ROOT / "terms.md",
        REFERENCES_ROOT / "commands.md",
        REFERENCES_ROOT / "troubleshooting.md",
        REFERENCES_ROOT / "production_mapping.md",
    ]
    notebook_pairs = [
        (
            NOTEBOOK_TEMPLATES_ROOT / "01_environment_check.ipynb",
            NOTEBOOK_EXECUTED_ROOT / "01_environment_check.ipynb",
        ),
        (
            NOTEBOOK_TEMPLATES_ROOT / "02_fastapi_health_check.ipynb",
            NOTEBOOK_EXECUTED_ROOT / "02_fastapi_health_check.ipynb",
        ),
        (
            NOTEBOOK_TEMPLATES_ROOT / "03_document_loading_check.ipynb",
            NOTEBOOK_EXECUTED_ROOT / "03_document_loading_check.ipynb",
        ),
        (
            NOTEBOOK_TEMPLATES_ROOT / "04_embedding_retrieval_check.ipynb",
            NOTEBOOK_EXECUTED_ROOT / "04_embedding_retrieval_check.ipynb",
        ),
        (
            NOTEBOOK_TEMPLATES_ROOT / "05_chat_api_check.ipynb",
            NOTEBOOK_EXECUTED_ROOT / "05_chat_api_check.ipynb",
        ),
        (
            NOTEBOOK_TEMPLATES_ROOT / "06_tourapi_cache_fallback_check.ipynb",
            NOTEBOOK_EXECUTED_ROOT / "06_tourapi_cache_fallback_check.ipynb",
        ),
        (
            NOTEBOOK_TEMPLATES_ROOT / "07_eval_report_check.ipynb",
            NOTEBOOK_EXECUTED_ROOT / "07_eval_report_check.ipynb",
        ),
        (
            NOTEBOOK_TEMPLATES_ROOT / "08_web_ui_smoke_check.ipynb",
            NOTEBOOK_EXECUTED_ROOT / "08_web_ui_smoke_check.ipynb",
        ),
    ]

    # When: the support files are inspected.
    missing_references = [path for path in reference_files if not path.exists()]
    missing_notebooks = [path for pair in notebook_pairs for path in pair if not path.exists()]

    # Then: references and template/executed notebook evidence exist.
    assert missing_references == []
    assert missing_notebooks == []
    for template_path, executed_path in notebook_pairs:
        template = read_text(template_path)
        executed = read_text(executed_path)
        template_cell_count = template.count('"cell_type"')
        template_markdown_count = template.count('"cell_type": "markdown"')
        template_code_count = template.count('"cell_type": "code"')
        executed_cell_count = executed.count('"cell_type"')
        executed_markdown_count = executed.count('"cell_type": "markdown"')
        executed_code_count = executed.count('"cell_type": "code"')
        assert '"cells"' in template
        assert '"cells"' in executed
        assert "검증 목적" in template
        assert "검증 완료" in executed
        assert "학습 흐름" in template
        assert "실행 전 준비" in template
        assert "원본형 앱 연결" in template
        assert "정리" in template
        assert template_cell_count >= 11
        assert template_markdown_count >= 5
        assert template_code_count >= 6
        assert len(template) >= 3000
        assert executed_cell_count >= 11
        assert executed_markdown_count >= 5
        assert executed_code_count >= 6
        assert len(executed) >= 3000


def test_project_template_keeps_tutorial_language_out_of_user_surface():
    # Given: a validator script protects docs/output separation.
    assert VALIDATOR.exists(), "tutorial docs validator missing"

    # When: the no-leak check runs through the CLI surface.
    result = subprocess.run(
        ["python3", str(VALIDATOR), "--check", "no-ui-tutorial-leak"],
        cwd=PROJECT_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    # Then: the validator confirms UI/API user surface has no tutorial wording leaks.
    assert "no-ui-tutorial-leak: ok" in result.stdout


def test_validator_checks_full_tutorial_book_structure():
    # Given: the validator is the CLI guard for tutorial completeness.
    assert VALIDATOR.exists(), "tutorial docs validator missing"

    # When: the full tutorial-structure check runs.
    result = subprocess.run(
        ["python3", str(VALIDATOR), "--check", "tutorial-book-structure"],
        cwd=PROJECT_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    # Then: the validator confirms chapter/reference/notebook structure.
    assert "tutorial-book-structure: ok" in result.stdout


def test_notion_final_tutorial_draft_exists_and_is_validated():
    # Given: the last tutorial artifact is the Notion-ready final book.
    assert NOTION_DRAFT.exists(), "Notion final tutorial draft missing"

    # When: the Notion draft validator runs.
    result = subprocess.run(
        ["python3", "scripts/validate_notion_tutorial_book.py"],
        cwd=PROJECT_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    # Then: the draft contains the expected final Notion tutorial structure.
    assert "notion-tutorial-book: ok" in result.stdout

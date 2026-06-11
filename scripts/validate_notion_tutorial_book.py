from pathlib import Path
from typing import Final


PROJECT_ROOT: Final = Path(__file__).resolve().parents[1]
DRAFT_PATH: Final = PROJECT_ROOT / "notion" / "rag_fastapi_tutorial_notion_draft.md"

REQUIRED_FRAGMENTS: Final = [
    "# RAG FastAPI 관광 챗봇 튜토리얼북",
    "시작하기 전에",
    "전체 흐름",
    "1장. 환경 준비",
    "2장. FastAPI 앱 만들기",
    "8장. TourAPI 서비스 붙이기",
    "9장. Cache/Fallback 안전망 만들기",
    "14장. Web UI 확인",
    "16장. Notion 최종본 만들기",
    "변경 내역을 위에 쌓지 않는다",
    "cache/fallback 데이터가 9장 학습 재료라는 설명",
    "01_environment_check.ipynb",
    "02_fastapi_health_check.ipynb",
    "03_document_loading_check.ipynb",
    "04_embedding_retrieval_check.ipynb",
    "05_chat_api_check.ipynb",
    "06_tourapi_cache_fallback_check.ipynb",
    "07_eval_report_check.ipynb",
    "08_web_ui_smoke_check.ipynb",
    "설명 셀과 코드 셀을 번갈아 두는 강의형 자료",
    "18-20셀",
    "막힐 때 보는 오류표",
    "관광 카드가 0개다",
    "/tourism/chat",
    "tutorial-book-structure: ok",
    "notion-tutorial-book: ok",
]
FORBIDDEN_INTRO_FRAGMENTS: Final = [
    "최종 판정",
    "업데이트 내역",
    "이번에 추가한 데이터",
    "Parity 현황",
    "실제 표면 QA 증거",
]
FORBIDDEN_FRAGMENTS: Final = [
    "/" + "Users/",
    "~/" + "Desktop",
    "/" + "home/",
    "/" + "tmp/",
]


def read_draft() -> str:
    if not DRAFT_PATH.exists():
        raise FileNotFoundError(f"{DRAFT_PATH.relative_to(PROJECT_ROOT)} missing")
    return DRAFT_PATH.read_text(encoding="utf-8")


def assert_contains_all(text: str, fragments: list[str]) -> None:
    missing = [fragment for fragment in fragments if fragment not in text]
    if missing:
        raise AssertionError("missing fragments: " + ", ".join(missing))


def assert_contains_none(text: str, fragments: list[str]) -> None:
    found = [fragment for fragment in fragments if fragment in text]
    if found:
        raise AssertionError("forbidden fragments: " + ", ".join(found))


def assert_intro_is_tutorial(text: str) -> None:
    intro = text[:1200]
    assert_contains_none(intro, FORBIDDEN_INTRO_FRAGMENTS)


def main() -> int:
    text = read_draft()
    assert_contains_all(text, REQUIRED_FRAGMENTS)
    assert_contains_none(text, FORBIDDEN_FRAGMENTS)
    assert_intro_is_tutorial(text)
    print("notion-tutorial-book: ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

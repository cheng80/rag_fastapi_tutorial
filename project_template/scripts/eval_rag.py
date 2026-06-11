from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from app.api.deps import get_rag_service  # noqa: E402


QUESTIONS = [
    "환불은 언제까지 가능한가요?",
    "설치 방법을 알려줘.",
]


def main() -> None:
    rag_service = get_rag_service()
    for question in QUESTIONS:
        print("=" * 80)
        print(f"Q. {question}")
        response = rag_service.answer(question)
        print(f"A. {response.answer}")
        print("sources:", [source.model_dump() for source in response.sources])


if __name__ == "__main__":
    main()

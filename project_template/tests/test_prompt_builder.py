from app.core.config import get_settings
from app.services.prompt_builder import PromptBuilder


def test_prompt_builder_contains_question():
    builder = PromptBuilder(get_settings())
    prompt = builder.build(
        question="환불은 언제까지 가능한가요?",
        contexts=[
            {
                "id": "chunk-1",
                "text": "환불은 구매일로부터 7일 이내에 가능합니다.",
                "metadata": {"source": "faq.md", "page": -1, "chunk_index": 0},
                "distance": 0.1,
            }
        ],
    )

    assert "환불은 언제까지 가능한가요?" in prompt
    assert "환불은 구매일로부터 7일" in prompt

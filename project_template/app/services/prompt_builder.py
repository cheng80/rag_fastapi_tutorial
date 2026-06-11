from app.core.config import Settings


class PromptBuilder:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.template = settings.prompt_path.read_text(encoding="utf-8")
        self.no_context_template = settings.no_context_prompt_path.read_text(encoding="utf-8")

    def build(self, question: str, contexts: list[dict]) -> str:
        context_text = self._format_contexts(contexts)
        return self.template.format(context=context_text, question=question)

    def build_no_context_answer(self) -> str:
        return self.no_context_template.strip()

    @staticmethod
    def _format_contexts(contexts: list[dict]) -> str:
        blocks: list[str] = []
        for index, item in enumerate(contexts, start=1):
            metadata = item.get("metadata", {}) or {}
            page = metadata.get("page")
            page_text = "없음" if page in (None, -1) else str(page)
            block = (
                f"[문서 {index}] source: {metadata.get('source', '')}, page: {page_text}\n"
                f"{item.get('text', '')}"
            )
            blocks.append(block)

        return "\n\n".join(blocks)

from app.schemas.chat import ChatResponse
from app.services.citation_service import CitationService
from app.services.llm_service import LLMService
from app.services.prompt_builder import PromptBuilder
from app.services.retriever import Retriever


class RAGService:
    def __init__(
        self,
        retriever: Retriever,
        prompt_builder: PromptBuilder,
        llm_service: LLMService,
        citation_service: CitationService,
    ):
        self.retriever = retriever
        self.prompt_builder = prompt_builder
        self.llm_service = llm_service
        self.citation_service = citation_service

    def answer(self, question: str, session_id: str | None = None) -> ChatResponse:
        contexts = self.retriever.retrieve(question)

        if not contexts:
            return ChatResponse(
                answer=self.prompt_builder.build_no_context_answer(),
                sources=[],
            )

        prompt = self.prompt_builder.build(question=question, contexts=contexts)
        answer = self.llm_service.generate(prompt)
        sources = self.citation_service.build_sources(contexts)

        return ChatResponse(answer=answer, sources=sources)

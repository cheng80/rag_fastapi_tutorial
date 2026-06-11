from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.core.config import Settings
    from app.services.embedding_service import EmbeddingService
    from app.services.vector_store import VectorStore


class Retriever:
    def __init__(
        self,
        settings: Settings,
        embedding_service: EmbeddingService,
        vector_store: VectorStore,
    ):
        self.settings = settings
        self.embedding_service = embedding_service
        self.vector_store = vector_store

    def retrieve(self, question: str) -> list[dict]:
        query_embedding = self.embedding_service.embed_query(question)
        return self.vector_store.search(query_embedding=query_embedding, top_k=self.settings.top_k)

from functools import lru_cache
from threading import Lock

from app.core.config import Settings, get_settings
from app.services.citation_service import CitationService
from app.services.document_loader import DocumentLoader
from app.services.embedding_service import EmbeddingService
from app.services.ingestion_service import IngestionService
from app.services.llm_service import LLMService
from app.services.prompt_builder import PromptBuilder
from app.services.rag_service import RAGService
from app.services.retriever import Retriever
from app.services.text_splitter import TextSplitter
from app.services.tour_api_service import TourAPIService
from app.services.tourism_chat_service import TourismChatService
from app.services.tourism_query_event_logger import TourismQueryEventLogger
from app.services.tourism_query_service import TourismQueryService
from app.services.vector_store import VectorStore


_vector_store_lock = Lock()
_vector_store: VectorStore | None = None


@lru_cache(maxsize=1)
def get_embedding_service() -> EmbeddingService:
    return EmbeddingService(get_settings())


def get_vector_store() -> VectorStore:
    global _vector_store
    with _vector_store_lock:
        if _vector_store is None:
            _vector_store = VectorStore(get_settings())
        return _vector_store


@lru_cache(maxsize=1)
def get_retriever() -> Retriever:
    return Retriever(
        settings=get_settings(),
        embedding_service=get_embedding_service(),
        vector_store=get_vector_store(),
    )


@lru_cache(maxsize=1)
def get_prompt_builder() -> PromptBuilder:
    return PromptBuilder(get_settings())


@lru_cache(maxsize=1)
def get_llm_service() -> LLMService:
    return LLMService(get_settings())


@lru_cache(maxsize=1)
def get_citation_service() -> CitationService:
    return CitationService()


@lru_cache(maxsize=1)
def get_rag_service() -> RAGService:
    return RAGService(
        retriever=get_retriever(),
        prompt_builder=get_prompt_builder(),
        llm_service=get_llm_service(),
        citation_service=get_citation_service(),
    )


@lru_cache(maxsize=1)
def get_ingestion_service() -> IngestionService:
    settings: Settings = get_settings()
    return IngestionService(
        settings=settings,
        document_loader=DocumentLoader(),
        text_splitter=TextSplitter(
            chunk_size=settings.chunk_size,
            chunk_overlap=settings.chunk_overlap,
        ),
        embedding_service=get_embedding_service(),
        vector_store=get_vector_store(),
    )


@lru_cache(maxsize=1)
def get_tourism_query_service() -> TourismQueryService:
    return TourismQueryService()


@lru_cache(maxsize=1)
def get_tour_api_service() -> TourAPIService:
    return TourAPIService(get_settings())


@lru_cache(maxsize=1)
def get_tourism_query_event_logger() -> TourismQueryEventLogger:
    return TourismQueryEventLogger(get_settings())


@lru_cache(maxsize=1)
def get_tourism_chat_service() -> TourismChatService:
    return TourismChatService(
        settings=get_settings(),
        retriever=get_retriever(),
        query_service=get_tourism_query_service(),
        tour_api_service=get_tour_api_service(),
        llm_service=get_llm_service(),
        event_logger=get_tourism_query_event_logger(),
    )

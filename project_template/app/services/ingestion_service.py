from pathlib import Path
from typing import Any

from app.core.config import Settings
from app.services.document_loader import DocumentLoader
from app.services.embedding_service import EmbeddingService
from app.services.text_splitter import TextSplitter
from app.services.vector_store import VectorStore


class IngestionService:
    def __init__(
        self,
        settings: Settings,
        document_loader: DocumentLoader,
        text_splitter: TextSplitter,
        embedding_service: EmbeddingService,
        vector_store: VectorStore,
    ):
        self.settings = settings
        self.document_loader = document_loader
        self.text_splitter = text_splitter
        self.embedding_service = embedding_service
        self.vector_store = vector_store

    def ingest_directory(self, directory: Path | None = None, clear_existing: bool = False) -> dict[str, Any]:
        raw_data_path = Path(directory) if directory else self.settings.resolved_raw_data_path
        raw_data_path.mkdir(parents=True, exist_ok=True)

        if clear_existing:
            self.vector_store.clear_collection()

        documents = self.document_loader.load_directory(raw_data_path)
        chunks = []
        for document in documents:
            chunks.extend(self.text_splitter.split_document(document))

        batch_size = max(1, self.settings.embedding_batch_size)
        for start in range(0, len(chunks), batch_size):
            batch = chunks[start : start + batch_size]
            texts = [chunk.text for chunk in batch]
            embeddings = self.embedding_service.embed_documents(texts)

            records = []
            for chunk, embedding in zip(batch, embeddings, strict=True):
                records.append(
                    {
                        "id": chunk.chunk_id,
                        "text": chunk.text,
                        "metadata": chunk.metadata,
                        "embedding": embedding,
                    }
                )
            self.vector_store.upsert_records(records)

        return {
            "document_count": len(documents),
            "chunk_count": len(chunks),
            "collection_name": self.vector_store.collection_name,
            "raw_data_path": str(directory or self.settings.raw_data_path),
        }

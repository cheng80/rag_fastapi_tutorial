from pathlib import Path
from typing import Any

from ..core.config import Settings


class EmptyVectorCollection:
    def upsert(
        self,
        *,
        ids: list[str],
        embeddings: list[list[float]],
        documents: list[str],
        metadatas: list[dict[str, Any]],
    ) -> None:
        return

    def query(
        self,
        *,
        query_embeddings: list[list[float]],
        n_results: int,
        include: list[str],
    ) -> dict[str, list[list[Any]]]:
        return {"ids": [[]], "documents": [[]], "metadatas": [[]], "distances": [[]]}

    def count(self) -> int:
        return 0


class VectorStore:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.persist_path = settings.resolved_chroma_path
        self.persist_path.mkdir(parents=True, exist_ok=True)

        try:
            import chromadb

            self.client = chromadb.PersistentClient(path=str(self.persist_path))
            self.collection = self.client.get_or_create_collection(name=settings.chroma_collection)
        except ImportError:
            self.client = None
            self.collection = EmptyVectorCollection()

    @property
    def collection_name(self) -> str:
        return self.settings.chroma_collection

    def upsert_records(self, records: list[dict[str, Any]]) -> None:
        if not records:
            return

        ids = [record["id"] for record in records]
        embeddings = [record["embedding"] for record in records]
        documents = [record["text"] for record in records]
        metadatas = [record["metadata"] for record in records]

        self.collection.upsert(
            ids=ids,
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas,
        )

    def search(self, query_embedding: list[float], top_k: int = 5) -> list[dict[str, Any]]:
        result = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            include=["documents", "metadatas", "distances"],
        )

        ids = (result.get("ids") or [[]])[0]
        documents = (result.get("documents") or [[]])[0]
        metadatas = (result.get("metadatas") or [[]])[0]
        distances = (result.get("distances") or [[]])[0]

        items: list[dict[str, Any]] = []
        for index, document in enumerate(documents):
            metadata = metadatas[index] or {}
            items.append(
                {
                    "id": ids[index] if index < len(ids) else "",
                    "text": document,
                    "metadata": metadata,
                    "distance": distances[index] if index < len(distances) else None,
                }
            )

        return items

    def clear_collection(self) -> None:
        if self.client is None:
            self.collection = EmptyVectorCollection()
            return
        try:
            self.client.delete_collection(name=self.settings.chroma_collection)
        except Exception:
            pass
        self.collection = self.client.get_or_create_collection(name=self.settings.chroma_collection)

    def stats(self) -> dict[str, Any]:
        return {
            "collection_name": self.settings.chroma_collection,
            "document_count": self.collection.count(),
            "persist_path": str(self.settings.chroma_path),
        }

class FakeEmbeddingService:
    def embed_query(self, text: str):
        return [0.1, 0.2, 0.3]


class FakeVectorStore:
    def search(self, query_embedding, top_k):
        return [{"id": "1", "text": "hello", "metadata": {}, "distance": 0.0}]


class FakeSettings:
    top_k = 1


def test_retriever_returns_vector_store_results():
    from app.services.retriever import Retriever

    retriever = Retriever(FakeSettings(), FakeEmbeddingService(), FakeVectorStore())
    results = retriever.retrieve("질문")

    assert results[0]["text"] == "hello"

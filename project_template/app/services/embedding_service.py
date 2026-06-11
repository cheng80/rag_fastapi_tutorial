import requests

from app.core.config import Settings


class EmbeddingService:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.base_url = settings.ollama_base_url.rstrip("/")
        self.model = settings.ollama_embed_model
        self.timeout = settings.ollama_request_timeout

    def embed_query(self, text: str) -> list[float]:
        embeddings = self.embed_documents([text])
        if not embeddings:
            raise RuntimeError("질문 임베딩 생성에 실패했습니다.")
        return embeddings[0]

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        clean_texts = [text.strip() for text in texts if text and text.strip()]
        if not clean_texts:
            return []

        response = requests.post(
            f"{self.base_url}/api/embed",
            json={
                "model": self.model,
                "input": clean_texts,
            },
            timeout=self.timeout,
        )
        response.raise_for_status()
        data = response.json()

        embeddings = data.get("embeddings")
        if not isinstance(embeddings, list) or not embeddings:
            raise RuntimeError(f"Ollama 임베딩 응답 형식이 올바르지 않습니다: {data}")

        return embeddings

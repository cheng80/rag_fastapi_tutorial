from dataclasses import dataclass
from uuid import NAMESPACE_URL, uuid5

from app.services.document_loader import LoadedDocument


@dataclass(frozen=True)
class TextChunk:
    chunk_id: str
    text: str
    metadata: dict


class TextSplitter:
    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 150):
        if chunk_size <= 0:
            raise ValueError("chunk_size는 0보다 커야 합니다.")
        if chunk_overlap < 0:
            raise ValueError("chunk_overlap은 0 이상이어야 합니다.")
        if chunk_overlap >= chunk_size:
            raise ValueError("chunk_overlap은 chunk_size보다 작아야 합니다.")

        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def split_document(self, document: LoadedDocument) -> list[TextChunk]:
        text = document.text.strip()
        if not text:
            return []

        chunks: list[TextChunk] = []
        start = 0
        chunk_index = 0
        step = self.chunk_size - self.chunk_overlap

        while start < len(text):
            end = start + self.chunk_size
            chunk_text = text[start:end].strip()
            if chunk_text:
                metadata = {
                    "source": document.source,
                    "page": document.page if document.page is not None else -1,
                    "chunk_index": chunk_index,
                    **document.metadata,
                }
                chunk_id = self._make_chunk_id(document.source, document.page, chunk_index, chunk_text)
                chunks.append(TextChunk(chunk_id=chunk_id, text=chunk_text, metadata=metadata))
                chunk_index += 1

            start += step

        return chunks

    @staticmethod
    def _make_chunk_id(source: str, page: int | None, chunk_index: int, text: str) -> str:
        raw = f"{source}|{page}|{chunk_index}|{text[:80]}"
        return str(uuid5(NAMESPACE_URL, raw))

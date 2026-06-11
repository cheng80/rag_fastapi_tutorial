from dataclasses import dataclass, field
from pathlib import Path

from pypdf import PdfReader

from app.core.config import PROJECT_ROOT
from app.utils.text_utils import normalize_text


@dataclass(frozen=True)
class LoadedDocument:
    text: str
    source: str
    page: int | None = None
    metadata: dict = field(default_factory=dict)


class DocumentLoader:
    supported_extensions = {".pdf", ".txt", ".md"}

    def load_directory(self, directory: Path) -> list[LoadedDocument]:
        directory = Path(directory)
        if not directory.exists():
            raise FileNotFoundError(f"문서 디렉터리를 찾을 수 없습니다: {directory}")

        documents: list[LoadedDocument] = []
        for path in sorted(directory.rglob("*")):
            if path.is_file() and path.suffix.lower() in self.supported_extensions:
                documents.extend(self.load_file(path))

        return documents

    def load_file(self, path: Path) -> list[LoadedDocument]:
        path = Path(path)
        suffix = path.suffix.lower()

        if suffix == ".pdf":
            return self._load_pdf(path)
        if suffix in {".txt", ".md"}:
            return self._load_text(path)

        raise ValueError(f"지원하지 않는 문서 형식입니다: {path.suffix}")

    def _load_text(self, path: Path) -> list[LoadedDocument]:
        text = normalize_text(path.read_text(encoding="utf-8", errors="ignore"))
        if not text:
            return []

        return [
            LoadedDocument(
                text=text,
                source=self._display_path(path),
                metadata={"extension": path.suffix.lower()},
            )
        ]

    def _load_pdf(self, path: Path) -> list[LoadedDocument]:
        reader = PdfReader(str(path))
        documents: list[LoadedDocument] = []

        for page_index, page in enumerate(reader.pages, start=1):
            raw_text = page.extract_text() or ""
            text = normalize_text(raw_text)
            if not text:
                continue

            documents.append(
                LoadedDocument(
                    text=text,
                    source=self._display_path(path),
                    page=page_index,
                    metadata={"extension": ".pdf"},
                )
            )

        return documents

    @staticmethod
    def _display_path(path: Path) -> str:
        try:
            return str(path.resolve().relative_to(PROJECT_ROOT))
        except ValueError:
            return str(path)

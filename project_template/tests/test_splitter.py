from app.services.document_loader import LoadedDocument
from app.services.text_splitter import TextSplitter


def test_splitter_creates_chunks():
    splitter = TextSplitter(chunk_size=10, chunk_overlap=2)
    document = LoadedDocument(text="abcdefghijklmnopqrstuvwxyz", source="sample.txt")

    chunks = splitter.split_document(document)

    assert len(chunks) > 1
    assert chunks[0].metadata["source"] == "sample.txt"
    assert chunks[0].metadata["page"] == -1

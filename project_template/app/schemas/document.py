from pydantic import BaseModel


class DocumentIndexResponse(BaseModel):
    document_count: int
    chunk_count: int
    collection_name: str
    raw_data_path: str


class VectorStoreStatsResponse(BaseModel):
    collection_name: str
    document_count: int
    persist_path: str

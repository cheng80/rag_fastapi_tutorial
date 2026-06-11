from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.deps import get_ingestion_service, get_vector_store
from app.schemas.document import DocumentIndexResponse, VectorStoreStatsResponse
from app.services.ingestion_service import IngestionService
from app.services.vector_store import VectorStore

router = APIRouter()


@router.post("/reindex", response_model=DocumentIndexResponse)
def reindex_documents(
    clear_existing: bool = Query(default=False, description="기존 문서 모음을 비우고 다시 처리할지 여부"),
    ingestion_service: IngestionService = Depends(get_ingestion_service),
) -> DocumentIndexResponse:
    try:
        result = ingestion_service.ingest_directory(clear_existing=clear_existing)
        return DocumentIndexResponse(**result)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/stats", response_model=VectorStoreStatsResponse)
def vector_store_stats(
    vector_store: VectorStore = Depends(get_vector_store),
) -> VectorStoreStatsResponse:
    stats = vector_store.stats()
    return VectorStoreStatsResponse(**stats)

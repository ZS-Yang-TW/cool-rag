import logging
from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.schemas.admin import HealthResponse
from app.schemas.document import DocumentReindexRequest, DocumentReindexResponse
from app.services import SystemService

router = APIRouter(prefix="/api", tags=["admin"])
logger = logging.getLogger(__name__)


def get_system_service() -> SystemService:
    """Dependency for SystemService"""
    return SystemService()


@router.get("/health", response_model=HealthResponse)
async def health_check(
    db: Session = Depends(get_db),
    system_service: SystemService = Depends(get_system_service),
):
    """Health check endpoint"""
    db_status = system_service.check_database_health(db)
    openai_status = system_service.check_openai_health()
    overall_status = system_service.get_overall_health(db_status, openai_status)

    return HealthResponse(
        status=overall_status,
        database=db_status,
        openai=openai_status,
        timestamp=datetime.utcnow(),
    )


@router.post("/reindex/selective", response_model=DocumentReindexResponse)
async def reindex_documents_selective(
    request: DocumentReindexRequest,
    db: Session = Depends(get_db),
    system_service: SystemService = Depends(get_system_service),
):
    """
    Reindex specific documents or all new/modified documents

    - **filenames**: List of filenames to reindex. Empty means reindex all new/modified
    """
    from app.repositories.document_repository import DocumentRepository

    repo = DocumentRepository(db)

    # Determine which documents to reindex
    if request.filenames:
        # Reindex specific files
        documents_to_reindex = []
        for filename in request.filenames:
            doc = repo.get_document_by_filename(filename)
            if doc:
                documents_to_reindex.append(doc)
    else:
        # Reindex all new/modified documents
        documents_to_reindex = repo.get_documents_needing_reindex()

    if not documents_to_reindex:
        return DocumentReindexResponse(
            message="No documents to reindex", reindexed_count=0, failed_count=0
        )

    # Reindex documents
    result = system_service.trigger_selective_reindex(
        db, [doc.filename for doc in documents_to_reindex]
    )

    return DocumentReindexResponse(**result)


@router.get("/stats")
async def get_stats(
    db: Session = Depends(get_db),
    system_service: SystemService = Depends(get_system_service),
):
    """Get how many document chunks are stored in the database"""
    return system_service.get_database_stats(db)

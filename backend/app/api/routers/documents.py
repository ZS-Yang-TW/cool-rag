import os

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.models.document import DocumentStatus
from app.models.document_chunk import DocumentChunk
from app.repositories.document_repository import DocumentRepository
from app.schemas.document import (
    DocumentDetail,
    DocumentListItem,
    DocumentListResponse,
    DocumentStatusEnum,
    DocumentSyncResponse,
)

router = APIRouter(prefix="/documents", tags=["documents"])


@router.get("", response_model=DocumentListResponse)
async def list_documents(
    status_filter: DocumentStatusEnum | None = None, db: Session = Depends(get_db)
):
    """
    Get list of all documents with their status

    - **status_filter**: Optional filter by document status
    """
    repo = DocumentRepository(db)

    # Always get all documents for statistics
    all_documents = repo.get_all_documents()

    # Calculate statistics from all documents
    stats = {"indexed": 0, "modified": 0, "new": 0, "deleted": 0}
    for doc in all_documents:
        stats[doc.status.value] += 1

    # Apply filter if specified
    if status_filter:
        documents = repo.get_documents_by_status(
            DocumentStatus[status_filter.value.upper()]
        )
    else:
        documents = all_documents

    return DocumentListResponse(
        documents=[DocumentListItem.model_validate(doc) for doc in documents],
        total=len(documents),
        stats=stats,
    )


@router.get("/{filename}", response_model=DocumentDetail)
async def get_document(filename: str, db: Session = Depends(get_db)):
    """
    Get document details including content

    - **filename**: Document filename
    """
    repo = DocumentRepository(db)
    document = repo.get_document_by_filename(filename)

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document '{filename}' not found",
        )

    # Read document content from file
    documents_dir = settings.documents_dir
    file_path = os.path.join(documents_dir, filename)

    if not os.path.exists(file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document file '{filename}' not found on disk",
        )

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error reading document: {str(e)}",
        )

    # Convert to DocumentDetail
    doc_dict = DocumentListItem.model_validate(document).model_dump()
    doc_dict["content"] = content

    return DocumentDetail(**doc_dict)


@router.post("/sync", response_model=DocumentSyncResponse)
async def sync_documents(db: Session = Depends(get_db)):
    """
    Sync document records with files in documents directory

    This will:
    - Add new documents found in the directory
    - Mark modified documents (based on file hash)
    - Mark missing documents as deleted
    """
    repo = DocumentRepository(db)
    documents_dir = settings.documents_dir

    if not os.path.exists(documents_dir):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Documents directory '{documents_dir}' not found",
        )

    stats = repo.sync_documents_from_directory(documents_dir)
    documents = repo.get_all_documents()

    return DocumentSyncResponse(
        stats=stats,
        documents=[DocumentListItem.model_validate(doc) for doc in documents],
    )


@router.delete("/cleanup")
async def cleanup_deleted_documents(db: Session = Depends(get_db)):
    """
    Clean up documents marked as deleted

    This will:
    - Delete all document chunks for deleted documents
    - Remove document records marked as deleted
    """
    repo = DocumentRepository(db)
    deleted_docs = repo.get_documents_by_status(DocumentStatus.DELETED)

    if not deleted_docs:
        return {"message": "沒有需要清理的文件", "deleted_count": 0}

    deleted_count = 0
    for doc in deleted_docs:
        # Delete chunks for this document
        db.query(DocumentChunk).filter(
            DocumentChunk.source_file == doc.filename
        ).delete()

        # Delete document record
        repo.delete_document(doc)
        deleted_count += 1

    db.commit()

    return {
        "message": f"已清理 {deleted_count} 個已刪除的文件",
        "deleted_count": deleted_count,
    }

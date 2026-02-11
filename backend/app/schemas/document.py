from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class DocumentChunkCreate(BaseModel):
    """Schema for creating a document chunk"""

    content: str
    embedding: List[float]
    source_file: str
    heading_path: Optional[str] = None
    chunk_index: int
    chunk_metadata: Optional[dict] = None


class DocumentChunkResponse(BaseModel):
    """Schema for document chunk response"""

    id: int
    content: str
    source_file: str
    heading_path: Optional[str]
    chunk_index: int
    chunk_metadata: Optional[dict]
    created_at: datetime

    class Config:
        from_attributes = True


# Document management schemas


class DocumentStatusEnum(str, Enum):
    """Document status enum for API"""

    INDEXED = "indexed"
    MODIFIED = "modified"
    NEW = "new"
    DELETED = "deleted"


class DocumentBase(BaseModel):
    """Base document schema"""

    filename: str = Field(..., description="Document filename")


class DocumentListItem(DocumentBase):
    """Document list item schema"""

    id: int
    file_hash: str
    status: DocumentStatusEnum
    indexed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class DocumentDetail(DocumentListItem):
    """Document detail schema with content"""

    content: str = Field(..., description="Document content")


class DocumentListResponse(BaseModel):
    """Document list response"""

    documents: list[DocumentListItem]
    total: int
    stats: dict = Field(
        default_factory=dict, description="Statistics about document statuses"
    )


class DocumentSyncRequest(BaseModel):
    """Request to sync documents from directory"""

    pass


class DocumentSyncResponse(BaseModel):
    """Response from document sync"""

    stats: dict = Field(
        ..., description="Sync statistics (new, modified, deleted, unchanged)"
    )
    documents: list[DocumentListItem]


class DocumentReindexRequest(BaseModel):
    """Request to reindex specific documents"""

    filenames: list[str] = Field(
        default_factory=list,
        description="List of filenames to reindex. Empty list means reindex all new/modified documents",
    )


class DocumentReindexResponse(BaseModel):
    """Response from document reindex"""

    message: str
    reindexed_count: int
    failed_count: int
    failed_files: list[str] = Field(default_factory=list)

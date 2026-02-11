import enum
from datetime import datetime

from sqlalchemy import TIMESTAMP, Column, Enum, Integer, String

from app.db import Base


class DocumentStatus(str, enum.Enum):
    """Document status enum"""

    INDEXED = "indexed"
    MODIFIED = "modified"
    NEW = "new"
    DELETED = "deleted"


class Document(Base):
    """Document model for tracking document metadata and status"""

    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(255), nullable=False, unique=True, index=True)
    file_hash = Column(String(64), nullable=False)  # SHA256 hash
    status = Column(
        Enum(DocumentStatus, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        default=DocumentStatus.NEW,
    )
    indexed_at = Column(TIMESTAMP, nullable=True)
    created_at = Column(TIMESTAMP, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        TIMESTAMP, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

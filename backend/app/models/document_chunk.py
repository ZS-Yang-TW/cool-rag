from sqlalchemy import Column, Integer, String, Text, TIMESTAMP
from sqlalchemy.dialects.postgresql import JSONB
from pgvector.sqlalchemy import Vector
from datetime import datetime
from app.db import Base


class DocumentChunk(Base):
    """Document chunk model for storing embedded text chunks"""
    __tablename__ = "document_chunks"
    
    id = Column(Integer, primary_key=True, index=True)
    content = Column(Text, nullable=False)
    embedding = Column(Vector(1536), nullable=False)
    source_file = Column(String(255), nullable=False, index=True)
    heading_path = Column(Text)
    chunk_index = Column(Integer)
    chunk_metadata = Column(JSONB)
    created_at = Column(TIMESTAMP, default=datetime.utcnow)

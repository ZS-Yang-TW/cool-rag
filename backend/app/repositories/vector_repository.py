from typing import Dict, List, Tuple

from sqlalchemy.orm import Session

from app.core import settings
from app.models import DocumentChunk


class VectorRepository:
    """Repository for vector similarity search operations"""

    def __init__(self, top_k: int = None, similarity_threshold: float = None):
        self.top_k = top_k or settings.top_k_results
        self.similarity_threshold = (
            similarity_threshold or settings.similarity_threshold
        )

    def search_similar_chunks(
        self, query_embedding: List[float], db: Session
    ) -> List[Tuple[DocumentChunk, float]]:
        """
        Search for similar chunks using vector similarity

        Args:
            query_embedding: Query embedding vector
            db: Database session

        Returns:
            List of (chunk, similarity_score) tuples
        """
        # Use SQLAlchemy ORM query instead of raw SQL for proper type conversion
        from sqlalchemy import func
        
        # Calculate similarity and filter
        similarity = 1 - DocumentChunk.embedding.cosine_distance(query_embedding)
        
        results = (
            db.query(DocumentChunk, similarity.label("similarity"))
            .filter(similarity > self.similarity_threshold)
            .order_by(DocumentChunk.embedding.cosine_distance(query_embedding))
            .limit(self.top_k)
            .all()
        )
        
        # Results are already in the format [(chunk, similarity), ...]
        return results

    def add_chunk(
        self,
        content: str,
        embedding: List[float],
        source_file: str,
        heading_path: str,
        chunk_index: int,
        chunk_metadata: dict,
        db: Session,
    ) -> DocumentChunk:
        """
        Add a new document chunk to the database

        Args:
            content: Chunk text content
            embedding: Embedding vector
            source_file: Source file name
            heading_path: Heading hierarchy path
            chunk_index: Index of chunk in document
            chunk_metadata: Additional metadata
            db: Database session

        Returns:
            Created DocumentChunk
        """
        chunk = DocumentChunk(
            content=content,
            embedding=embedding,
            source_file=source_file,
            heading_path=heading_path,
            chunk_index=chunk_index,
            chunk_metadata=chunk_metadata,
        )
        db.add(chunk)
        db.commit()
        db.refresh(chunk)
        return chunk

    def bulk_add_chunks(self, chunks: List[Dict], db: Session):
        """
        Bulk insert document chunks

        Args:
            chunks: List of chunk dictionaries with all required fields
            db: Database session
        """
        chunk_objects = [
            DocumentChunk(
                content=chunk["content"],
                embedding=chunk["embedding"],
                source_file=chunk["source_file"],
                heading_path=chunk.get("heading_path"),
                chunk_index=chunk["chunk_index"],
                chunk_metadata=chunk.get("chunk_metadata"),
            )
            for chunk in chunks
        ]
        db.bulk_save_objects(chunk_objects)
        db.commit()

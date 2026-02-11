import logging
from pathlib import Path
from typing import Dict, List

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.clients import EmbeddingClient
from app.core import DatabaseUnavailableError, settings
from app.models import DocumentChunk
from app.repositories.document_repository import DocumentRepository
from app.services.rag_service import chunk_documents

logger = logging.getLogger(__name__)


class SystemService:
    """Service for handling system-related business logic"""

    def check_database_health(self, db: Session) -> str:
        """Check database connection health"""
        try:
            db.execute(text("SELECT 1"))
            return "connected"
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            raise DatabaseUnavailableError(f"Database connection failed: {str(e)}")

    def check_openai_health(self) -> str:
        """Check OpenAI API configuration"""
        return "available" if settings.openai_api_key else "not configured"

    def get_overall_health(self, db_status: str, openai_status: str) -> str:
        """Determine overall health status"""
        if db_status == "connected" and openai_status == "available":
            return "healthy"
        return "unhealthy"

    def _load_documents(self, documents_dir: Path) -> List[tuple]:
        """Load all markdown documents from directory"""
        documents = []

        for md_file in documents_dir.glob("*.md"):
            try:
                with open(md_file, "r", encoding="utf-8") as f:
                    content = f.read()

                if content.strip():
                    documents.append((md_file.name, content))
                    logger.info(f"Loaded {md_file.name}")
                else:
                    logger.warning(f"Skipped empty file: {md_file.name}")

            except Exception as e:
                logger.error(f"Error loading {md_file.name}: {e}")

        return documents

    def get_database_stats(self, db: Session) -> Dict:
        """Get database statistics"""
        # Get total chunks count
        total_chunks = db.query(DocumentChunk).count()

        # Get chunks per file
        result = db.execute(
            text(
                """
            SELECT source_file, COUNT(*) as count
            FROM document_chunks
            GROUP BY source_file
            ORDER BY count DESC
        """
            )
        )

        files_stats = [{"file": row.source_file, "chunks": row.count} for row in result]

        return {
            "total_chunks": total_chunks,
            "total_files": len(files_stats),
            "files": files_stats,
        }

    def trigger_selective_reindex(self, db: Session, filenames: List[str]) -> Dict:
        """
        Reindex specific documents

        Args:
            db: Database session
            filenames: List of filenames to reindex

        Returns:
            Dict with reindex results
        """
        try:
            logger.info(f"Starting selective reindex for {len(filenames)} documents...")

            documents_dir = Path(settings.documents_dir)

            if not documents_dir.exists():
                logger.error(f"Documents directory not found: {documents_dir}")
                return {
                    "message": f"文件目錄不存在: {documents_dir}",
                    "reindexed_count": 0,
                    "failed_count": len(filenames),
                    "failed_files": filenames,
                }

            repo = DocumentRepository(db)
            reindexed = 0
            failed = []
            failed_files = []

            # Load and process each document
            documents_to_process = []

            for filename in filenames:
                file_path = documents_dir / filename

                if not file_path.exists():
                    logger.warning(f"File not found: {filename}")
                    failed.append(filename)
                    failed_files.append(filename)
                    continue

                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        content = f.read()

                    if content.strip():
                        documents_to_process.append((filename, content))
                    else:
                        logger.warning(f"Skipped empty file: {filename}")
                        failed.append(filename)
                        failed_files.append(filename)

                except Exception as e:
                    logger.error(f"Error loading {filename}: {e}")
                    failed.append(filename)
                    failed_files.append(filename)

            if not documents_to_process:
                return {
                    "message": "沒有可索引的文件",
                    "reindexed_count": 0,
                    "failed_count": len(failed),
                    "failed_files": failed_files,
                }

            # Delete existing chunks for these documents
            logger.info(
                f"Deleting existing chunks for {len(documents_to_process)} documents..."
            )
            for filename, _ in documents_to_process:
                db.query(DocumentChunk).filter(
                    DocumentChunk.source_file == filename
                ).delete()
            db.commit()

            # Create document_id mapping for image storage
            document_id_map = {}
            for filename, _ in documents_to_process:
                doc = repo.get_document_by_filename(filename)
                if doc:
                    document_id_map[filename] = str(doc.id)

            # Chunk documents with image preprocessing
            logger.info(f"Chunking {len(documents_to_process)} documents...")
            chunks = chunk_documents(documents_to_process, document_id_map)
            logger.info(f"Created {len(chunks)} chunks")

            # Generate embeddings
            logger.info("Generating embeddings...")
            embedder = EmbeddingClient()
            chunk_texts = [chunk["content"] for chunk in chunks]
            embeddings = embedder.generate_embeddings_batch(chunk_texts)

            # Store in database
            for chunk, embedding in zip(chunks, embeddings):
                db_chunk = DocumentChunk(
                    content=chunk["content"],
                    embedding=embedding,
                    source_file=chunk["source_file"],
                    heading_path=chunk.get("heading_path"),
                    chunk_index=chunk["chunk_index"],
                    chunk_metadata=chunk.get("metadata"),
                )
                db.add(db_chunk)

            db.commit()

            # Update document status
            for filename, _ in documents_to_process:
                doc = repo.get_document_by_filename(filename)
                if doc:
                    repo.mark_as_indexed(doc)
                reindexed += 1

            logger.info(
                f"Successfully reindexed {reindexed} documents with {len(chunks)} chunks"
            )

            return {
                "message": f"成功重新索引 {reindexed} 個文件，共 {len(chunks)} 個區塊",
                "reindexed_count": reindexed,
                "failed_count": len(failed),
                "failed_files": failed_files,
            }

        except Exception as e:
            logger.error(f"Selective reindex failed: {e}", exc_info=True)
            db.rollback()
            return {
                "message": f"重新索引失敗: {str(e)}",
                "reindexed_count": 0,
                "failed_count": len(filenames),
                "failed_files": filenames,
            }

import hashlib
import os
from datetime import datetime
from typing import List, Optional

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.models.document import Document, DocumentStatus


class DocumentRepository:
    """Repository for document metadata operations"""

    def __init__(self, db: Session):
        self.db = db

    @staticmethod
    def calculate_file_hash(file_path: str) -> str:
        """Calculate SHA256 hash of a file"""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()

    def get_all_documents(self) -> List[Document]:
        """Get all documents"""
        return self.db.query(Document).order_by(Document.filename).all()

    def get_document_by_filename(self, filename: str) -> Optional[Document]:
        """Get document by filename"""
        return self.db.query(Document).filter(Document.filename == filename).first()

    def create_document(
        self, filename: str, file_hash: str, status: DocumentStatus = DocumentStatus.NEW
    ) -> Document:
        """Create a new document record"""
        document = Document(filename=filename, file_hash=file_hash, status=status)
        self.db.add(document)
        self.db.commit()
        self.db.refresh(document)
        return document

    def update_document(
        self,
        document: Document,
        file_hash: Optional[str] = None,
        status: Optional[DocumentStatus] = None,
        indexed_at: Optional[datetime] = None,
    ) -> Document:
        """Update document metadata"""
        if file_hash is not None:
            document.file_hash = file_hash
        if status is not None:
            document.status = status
        if indexed_at is not None:
            document.indexed_at = indexed_at

        document.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(document)
        return document

    def mark_as_indexed(self, document: Document) -> Document:
        """Mark document as indexed"""
        return self.update_document(
            document, status=DocumentStatus.INDEXED, indexed_at=datetime.utcnow()
        )

    def delete_document(self, document: Document) -> None:
        """Delete document record"""
        self.db.delete(document)
        self.db.commit()

    def sync_documents_from_directory(self, documents_dir: str) -> dict:
        """
        Sync document records with files in directory
        Returns stats about new, modified, and deleted documents
        """
        stats = {"new": 0, "modified": 0, "deleted": 0, "unchanged": 0}

        # Get all markdown files in directory
        if not os.path.exists(documents_dir):
            return stats

        files_in_dir = set()
        for filename in os.listdir(documents_dir):
            if filename.endswith(".md"):
                files_in_dir.add(filename)

        # Check existing documents
        existing_docs = {doc.filename: doc for doc in self.get_all_documents()}

        # Process files in directory
        for filename in files_in_dir:
            file_path = os.path.join(documents_dir, filename)
            current_hash = self.calculate_file_hash(file_path)

            if filename in existing_docs:
                doc = existing_docs[filename]
                if doc.file_hash != current_hash:
                    # File has been modified
                    self.update_document(
                        doc, file_hash=current_hash, status=DocumentStatus.MODIFIED
                    )
                    stats["modified"] += 1
                else:
                    stats["unchanged"] += 1
            else:
                # New file
                self.create_document(
                    filename=filename, file_hash=current_hash, status=DocumentStatus.NEW
                )
                stats["new"] += 1

        # Mark documents not in directory as deleted
        for filename, doc in existing_docs.items():
            if filename not in files_in_dir and doc.status != DocumentStatus.DELETED:
                self.update_document(doc, status=DocumentStatus.DELETED)
                stats["deleted"] += 1

        return stats

    def get_documents_by_status(self, status: DocumentStatus) -> List[Document]:
        """Get documents by status"""
        return self.db.query(Document).filter(Document.status == status).all()

    def get_documents_needing_reindex(self) -> List[Document]:
        """Get documents that need to be reindexed (new or modified)"""
        return (
            self.db.query(Document)
            .filter(Document.status.in_([DocumentStatus.NEW, DocumentStatus.MODIFIED]))
            .all()
        )

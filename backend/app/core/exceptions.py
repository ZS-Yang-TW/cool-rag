"""
Custom exceptions for the application
"""


class DomainError(Exception):
    """Base exception for domain-level errors"""
    error_code = "domain_error"
    status_code = 500

    def __init__(self, message: str, details: dict | None = None):
        super().__init__(message)
        self.details = details or {}


class DatabaseUnavailableError(DomainError):
    """Raised when database is unavailable"""
    error_code = "database_unavailable"
    status_code = 503


class DocumentNotFoundError(DomainError):
    """Raised when a document is not found"""
    error_code = "document_not_found"
    status_code = 404


class EmbeddingError(DomainError):
    """Raised when embedding generation fails"""
    error_code = "embedding_failed"
    status_code = 502

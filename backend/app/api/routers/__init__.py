from .admin import router as admin_router
from .assistant import router as assistant_router
from .documents import router as documents_router

__all__ = [
    "assistant_router",
    "admin_router",
    "documents_router",
]

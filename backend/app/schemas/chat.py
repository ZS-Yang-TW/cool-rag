from pydantic import BaseModel, Field
from typing import List, Optional


class ChatMessage(BaseModel):
    """Chat message from user"""
    message: str = Field(..., min_length=1, max_length=2000)
    conversation_id: Optional[str] = None


class Source(BaseModel):
    """Source reference for an answer"""
    file: str
    heading: Optional[str] = None
    relevance_score: float
    content_preview: Optional[str] = None


class ChatResponse(BaseModel):
    """Response to chat message"""
    answer: str
    sources: List[Source]
    conversation_id: str

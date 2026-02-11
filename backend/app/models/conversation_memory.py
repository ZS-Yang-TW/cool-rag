"""
Conversation memory models for hierarchical memory system.
"""

from sqlalchemy import JSON, Column, DateTime, Integer, String, Text
from sqlalchemy.sql import func

from app.db.base import Base


class ConversationMemory(Base):
    """
    Stores conversation summaries and structured memory for long-term context.

    Architecture:
    - summary: Compressed historical context (Layer 2)
    - structured_data: Key facts and user preferences (Layer 3)
    - session_id: Groups related conversations
    """

    __tablename__ = "conversation_memories"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(
        String(255), nullable=False, index=True, comment="會話 session ID"
    )

    # Layer 2: Summarized Memory
    summary = Column(Text, nullable=True, comment="對話摘要（壓縮的歷史脈絡）")
    summary_updated_at = Column(
        DateTime(timezone=True), nullable=True, comment="摘要最後更新時間"
    )
    message_count = Column(Integer, default=0, comment="已摘要的訊息數量")

    # Layer 3: Structured Memory
    structured_data = Column(
        JSON, nullable=True, comment="結構化長期記憶（專案資訊、使用者偏好等）"
    )

    # Metadata
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    def __repr__(self):
        return f"<ConversationMemory(session_id={self.session_id}, messages={self.message_count})>"

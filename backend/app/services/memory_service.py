"""
Memory service implementing hierarchical memory architecture.
Combines three layers:
- Layer 1: Recent Window (short-term, token-based)
- Layer 2: Summarized Memory (compressed historical context)
- Layer 3: Structured Memory (persistent facts and preferences)
"""

import logging
from datetime import datetime
from typing import Any

import tiktoken
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.conversation_memory import ConversationMemory
from app.services.conversation_summary_service import ConversationSummaryService

logger = logging.getLogger(__name__)


class MemoryService:
    """
    Production-ready memory service with hierarchical architecture.

    Architecture:
        Persistent DB Memory (Layer 3)
                ↓
        Conversation Summary (Layer 2)
                ↓
        Recent Window (Layer 1)
                ↓
        User Query

    Key Features:
    - Token-based memory management (not message count)
    - Progressive summarization for long conversations
    - Structured persistent memory for key facts
    - Automatic memory consolidation
    """

    def __init__(self, db: Session):
        self.db = db
        self.summary_service = ConversationSummaryService()

        # Initialize tokenizer for token counting
        try:
            self.tokenizer = tiktoken.get_encoding("cl100k_base")  # GPT-4 encoding
        except Exception as e:
            logger.warning(f"Failed to load tiktoken, using approximation: {e}")
            self.tokenizer = None

    def count_tokens(self, text: str) -> int:
        """
        Count tokens in text.

        Args:
            text: Text to count tokens for

        Returns:
            Number of tokens
        """
        if self.tokenizer:
            return len(self.tokenizer.encode(text))
        else:
            # Fallback: rough approximation (4 chars ≈ 1 token)
            return len(text) // 4

    def count_message_tokens(self, messages: list[dict[str, Any]]) -> int:
        """
        Count total tokens in message list.

        Args:
            messages: List of conversation messages

        Returns:
            Total token count
        """
        total = 0
        for msg in messages:
            content = msg.get("content", "")
            # Add role and formatting overhead (~4 tokens per message)
            total += self.count_tokens(content) + 4
        return total

    async def get_memory_context(
        self,
        session_id: str,
        conversation_history: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """
        Get hierarchical memory context for conversation.

        Returns a structured context containing:
        - summary: Compressed historical context
        - recent_messages: Token-limited recent window
        - structured_data: Persistent facts and preferences
        - metadata: Token usage stats

        Args:
            session_id: Conversation session ID
            conversation_history: Current conversation messages

        Returns:
            Memory context dictionary
        """
        # Get or create memory record
        memory = self._get_or_create_memory(session_id)

        # Check if we need to summarize
        total_messages = len(conversation_history)
        if self.summary_service.should_summarize(total_messages):
            await self._update_summary(memory, conversation_history)

        # Get recent window with token budget
        recent_messages = self._get_recent_window(
            conversation_history, max_tokens=settings.token_budget_memory
        )

        # Build memory context
        context = {
            "summary": memory.summary,
            "recent_messages": recent_messages,
            "structured_data": memory.structured_data or {},
            "metadata": {
                "session_id": session_id,
                "total_messages": total_messages,
                "summarized_messages": memory.message_count,
                "recent_message_count": len(recent_messages),
                "recent_tokens": self.count_message_tokens(recent_messages),
            },
        }

        logger.info(
            f"Memory context: {context['metadata']['recent_message_count']} recent msgs, "
            f"{context['metadata']['recent_tokens']} tokens"
        )

        return context

    def _get_recent_window(
        self,
        messages: list[dict[str, Any]],
        max_tokens: int,
    ) -> list[dict[str, Any]]:
        """
        Get recent messages within token budget.

        This is Layer 1: Recent Window
        Uses token-based truncation instead of message count.

        Args:
            messages: Full conversation history
            max_tokens: Maximum tokens for recent window

        Returns:
            Recent messages within budget
        """
        if not messages:
            return []

        # Start from most recent and work backwards
        recent = []
        total_tokens = 0

        for msg in reversed(messages):
            msg_tokens = self.count_tokens(msg.get("content", "")) + 4

            if total_tokens + msg_tokens > max_tokens:
                break

            recent.insert(0, msg)
            total_tokens += msg_tokens

        # Always include at least the last 2 messages (1 turn)
        if len(recent) < 2 and len(messages) >= 2:
            recent = messages[-2:]

        return recent

    async def _update_summary(
        self,
        memory: ConversationMemory,
        conversation_history: list[dict[str, Any]],
    ):
        """
        Update conversation summary.

        This is Layer 2: Summarized Memory
        Compresses old messages into summary.

        Args:
            memory: Memory record to update
            conversation_history: Full conversation history
        """
        # Get messages to summarize (all except recent window)
        recent_window_size = 10  # Keep last 10 messages out of summary
        messages_to_summarize = conversation_history[:-recent_window_size]

        if not messages_to_summarize:
            return

        # Generate new summary
        new_summary = await self.summary_service.generate_summary(
            messages_to_summarize, existing_summary=memory.summary
        )

        # Update memory record
        memory.summary = new_summary
        memory.summary_updated_at = datetime.utcnow()
        memory.message_count = len(messages_to_summarize)

        self.db.commit()
        logger.info(f"Updated summary for session {memory.session_id}")

    def update_structured_memory(
        self,
        session_id: str,
        key: str,
        value: Any,
    ):
        """
        Update structured memory (Layer 3).

        This stores persistent facts that shouldn't be lost:
        - User preferences
        - Project information
        - Long-term goals

        Args:
            session_id: Conversation session ID
            key: Memory key (e.g., "project", "user_language")
            value: Value to store
        """
        memory = self._get_or_create_memory(session_id)

        if not memory.structured_data:
            memory.structured_data = {}

        memory.structured_data[key] = value
        self.db.commit()

        logger.info(f"Updated structured memory: {key} = {value}")

    def _get_or_create_memory(self, session_id: str) -> ConversationMemory:
        """
        Get or create memory record for session.

        Args:
            session_id: Conversation session ID

        Returns:
            ConversationMemory record
        """
        memory = (
            self.db.query(ConversationMemory)
            .filter(ConversationMemory.session_id == session_id)
            .first()
        )

        if not memory:
            memory = ConversationMemory(
                session_id=session_id,
                summary=None,
                structured_data={},
                message_count=0,
            )
            self.db.add(memory)
            self.db.commit()
            logger.info(f"Created new memory for session {session_id}")

        return memory

    def format_memory_for_prompt(self, memory_context: dict[str, Any]) -> str:
        """
        Format memory context for system prompt injection.

        Args:
            memory_context: Memory context from get_memory_context()

        Returns:
            Formatted memory string for prompt
        """
        parts = []

        # Add summary if available
        if memory_context.get("summary"):
            parts.append("=== 對話脈絡 ===")
            parts.append(memory_context["summary"])

        # Add structured data if available
        structured = memory_context.get("structured_data", {})
        if structured:
            parts.append("\n=== 專案資訊 ===")
            for key, value in structured.items():
                parts.append(f"{key}: {value}")

        return "\n".join(parts) if parts else ""

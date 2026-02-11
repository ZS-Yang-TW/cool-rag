"""
Conversation summary service for hierarchical memory system.
Implements Layer 2: Summarized Memory
"""

import logging
from datetime import datetime
from typing import Any

from openai import OpenAI
from openai.types.chat import ChatCompletionMessageParam

from app.core import settings

logger = logging.getLogger(__name__)


SUMMARY_SYSTEM_PROMPT = """你是一個對話摘要助手。
你的任務是將長對話壓縮成簡潔的摘要，保留最重要的脈絡資訊。

摘要規則：
1. 保留核心主題和討論重點
2. 記錄使用者的目標和需求
3. 保留關鍵決策和結論
4. 忽略閒聊和重複內容
5. 使用繁體中文
6. 保持客觀和事實導向

摘要格式：
- 主題：[核心討論主題]
- 背景：[專案或任務背景]
- 重點：[關鍵討論點和決策]
- 狀態：[當前進度或待辦事項]"""


class ConversationSummaryService:
    """
    Service for generating conversation summaries.

    This implements the "progressive summarization" pattern:
    - When conversation exceeds threshold, summarize old messages
    - Keep summary + recent messages for context
    - Prevents token overflow while maintaining coherence
    """

    def __init__(self):
        self.client = OpenAI(
            api_key=settings.vllm_api_key,
            base_url=settings.vllm_base_url,
        )
        self.model = settings.vllm_model
        self.max_tokens = 1000  # Summaries should be concise
        self.temperature = 0.3  # Lower temperature for consistent summaries

    async def generate_summary(
        self,
        conversation_history: list[dict[str, Any]],
        existing_summary: str | None = None,
    ) -> str:
        """
        Generate a summary of conversation history.

        Args:
            conversation_history: List of conversation messages to summarize
            existing_summary: Previous summary to build upon (progressive summarization)

        Returns:
            Compressed summary of the conversation
        """
        try:
            messages: list[ChatCompletionMessageParam] = [
                {"role": "system", "content": SUMMARY_SYSTEM_PROMPT}
            ]

            # Add existing summary if available
            if existing_summary:
                messages.append(
                    {
                        "role": "user",
                        "content": f"以下是先前的對話摘要：\n\n{existing_summary}",
                    }
                )

            # Build conversation text to summarize
            conversation_text = self._format_conversation(conversation_history)

            messages.append(
                {"role": "user", "content": f"請摘要以下對話：\n\n{conversation_text}"}
            )

            # Generate summary
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
            )

            summary = response.choices[0].message.content or ""
            logger.info(f"Generated conversation summary ({len(summary)} chars)")

            return summary.strip()

        except Exception as e:
            logger.error(f"Error generating summary: {e}")
            # Fallback: return existing summary or empty
            return existing_summary or ""

    def _format_conversation(self, messages: list[dict[str, Any]]) -> str:
        """
        Format conversation messages into readable text.

        Args:
            messages: List of conversation messages

        Returns:
            Formatted conversation text
        """
        lines = []
        for msg in messages:
            role = msg.get("role", "unknown")
            content = msg.get("content", "")

            if role == "user":
                lines.append(f"使用者：{content}")
            elif role == "assistant":
                lines.append(f"助手：{content}")

        return "\n\n".join(lines)

    def should_summarize(self, message_count: int, threshold: int = 15) -> bool:
        """
        Determine if conversation should be summarized.

        Args:
            message_count: Total number of messages in conversation
            threshold: Number of messages before triggering summarization

        Returns:
            True if summarization should be triggered
        """
        return message_count >= threshold

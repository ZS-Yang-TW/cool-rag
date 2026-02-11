import logging
from typing import Any

from openai import OpenAI
from openai.types.chat import ChatCompletionMessageParam

from app.core import settings
from app.core.prompts import RAG_SYSTEM_PROMPT

logger = logging.getLogger(__name__)


class LLMClient:
    """Client for generating answers using VLLM"""

    def __init__(self):
        # Initialize VLLM client for chat completions
        self.client = OpenAI(
            api_key=settings.vllm_api_key,
            base_url=settings.vllm_base_url,
        )
        self.model = settings.vllm_model
        self.max_tokens = settings.vllm_max_output_tokens
        self.temperature = settings.openai_temperature

        # Initialize openai client for chat completions
        # self.client = OpenAI(
        #     api_key=settings.openai_api_key,
        # )
        # self.model = settings.openai_chat_model
        # self.max_tokens = settings.openai_max_tokens
        # self.temperature = settings.openai_temperature

    def _build_messages(
        self,
        query: str,
        context: str,
        conversation_history: list[dict[str, Any]] | None = None,
    ) -> list[ChatCompletionMessageParam]:
        """
        Build messages array for chat completion

        Note: conversation_history should already be processed by MemoryService
        with token budgeting. We just validate and use it as-is.

        Args:
            query: User's question
            context: Retrieved context from documents
            conversation_history: Token-limited recent messages from MemoryService

        Returns:
            List of ChatCompletionMessageParam
        """
        messages: list[ChatCompletionMessageParam] = [
            {"role": "system", "content": RAG_SYSTEM_PROMPT}
        ]

        # Add conversation history (already filtered by MemoryService)
        if conversation_history:
            for msg in conversation_history:
                role = msg.get("role")
                content = msg.get("content")

                if (
                    role in {"user", "assistant"}
                    and isinstance(content, str)
                    and content.strip()
                ):
                    messages.append({"role": role, "content": content})
                else:
                    logger.debug(f"Skipped invalid history message: {msg}")

        # Add current query with structured context (context may be empty)
        if context and context.strip():
            user_message = (
                "### Reference Documentation\n\n"
                f"{context}\n\n"
                "### User Question\n\n"
                f"{query}"
            )

        else:
            user_message = query

        messages.append({"role": "user", "content": user_message})

        logger.debug(
            f"Built {len(messages)} messages for LLM (1 system + {len(messages)-2} history + 1 query)"
        )

        return messages

    def generate_answer(
        self,
        query: str,
        context: str,
        conversation_history: list[dict[str, Any]] | None = None,
    ) -> str:
        """
        Generate answer based on query and context

        Args:
            query: User's question
            context: Retrieved context from documents
            conversation_history: Token-limited recent messages from MemoryService

        Returns:
            Generated answer

        Raises:
            OpenAIError: If API call fails
        """
        try:
            messages = self._build_messages(query, context, conversation_history)

            logger.debug(f"Sending {len(messages)} messages to LLM")

            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
            )

            answer = response.choices[0].message.content or ""
            logger.info(f"LLM generated answer ({len(answer)} chars)")

            return answer

        except Exception as e:
            logger.error(f"LLM generation failed: {e}")
            logger.error(f"Query: {query[:100]}...")
            logger.error(f"Context length: {len(context)} chars")
            logger.error(f"History messages: {len(conversation_history or [])}")
            raise

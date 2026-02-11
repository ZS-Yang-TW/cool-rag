import logging
from typing import Dict, List, Tuple
from uuid import uuid4

from sqlalchemy.orm import Session

from app.clients import LLMClient
from app.schemas.chat import Source
from app.services.memory_service import MemoryService
from app.services.rag_service import (
    VectorRetriever,
    extract_sources,
    format_context_for_llm,
)

logger = logging.getLogger(__name__)

# Simple in-memory conversation storage (for demo purposes)
# In production, use Redis or a proper database
conversations = {}


class AssistantService:
    """Service for handling assistant-related business logic with hierarchical memory"""

    def __init__(self, db: Session):
        self.retriever = VectorRetriever()
        self.memory_service = MemoryService(db)
        self.db = db

    def get_or_create_conversation_id(self, conversation_id: str | None = None) -> str:
        """Get existing or create new conversation ID"""
        return conversation_id or str(uuid4())

    def get_conversation_history(self, conversation_id: str) -> List[Dict]:
        """Get conversation history for a conversation ID"""
        return conversations.get(conversation_id, [])

    def update_conversation_history(
        self, conversation_id: str, user_message: str, assistant_message: str
    ):
        """Update conversation history with new messages"""
        history = conversations.get(conversation_id, [])
        history.append({"role": "user", "content": user_message})
        history.append({"role": "assistant", "content": assistant_message})
        conversations[conversation_id] = history

    def clear_conversation(self, conversation_id: str) -> bool:
        """Clear conversation history, returns True if found and deleted"""
        if conversation_id in conversations:
            del conversations[conversation_id]
            return True
        return False

    def retrieve_relevant_chunks(self, query: str, db: Session) -> List[Dict]:
        """Retrieve relevant document chunks for a query"""
        retrieved_chunks = self.retriever.retrieve_with_context(query, db)

        logger.info(f"Query: {query}")
        logger.info(f"Retrieved {len(retrieved_chunks)} chunks")
        for i, chunk in enumerate(retrieved_chunks[:3]):
            logger.info(
                f"  Chunk {i+1}: similarity={chunk.get('similarity_score', 0):.4f}, "
                f"file={chunk.get('source_file', 'N/A')}"
            )

        return retrieved_chunks

    def generate_no_results_message(self, query: str) -> str:
        """Generate a helpful message when no relevant chunks are found"""
        is_english = any(ord(c) < 128 for c in query) and not any(
            "\u4e00" <= c <= "\u9fff" for c in query
        )

        if is_english:
            return """I couldn't find relevant information in the documentation for your question.

You can try:
- Using more specific keywords, such as "conflict handling", "translation files", "cherry-pick"
- Asking about specific steps in the upgrade process, like "how to evaluate conflicts", "how to handle translation conflicts"
- Asking about technical details, such as "treesame commit", "progressive DB migration"

The documentation currently covers:
- Upgrade process and requirement evaluation
- Conflict handling (translation conflicts and feature conflicts)
- Upgrade development and testing
- Deployment and release process
- Local environment setup

Please try rephrasing your question, and I'll do my best to help!"""
        else:
            return """抱歉，我在文件中找不到與您問題相關的資訊。

您可以嘗試：
- 使用更具體的關鍵字，例如「衝突處理」、「翻譯檔」、「cherry-pick」
- 詢問進版流程的特定步驟，例如「如何評估衝突」、「如何處理翻譯衝突」
- 詢問技術細節，例如「treesame commit」、「progressive DB migration」

目前文件涵蓋的主題包括：
- 進版流程與需求評估
- 衝突處理（翻譯衝突與功能衝突）
- 進版開發與測試
- 部署與上線流程
- Local 環境建置

請換個方式提問，我會盡力協助您！"""

    def generate_answer(
        self, query: str, retrieved_chunks: List[Dict], conversation_history: List[Dict]
    ) -> Tuple[str, List[Dict]]:
        """Generate answer with sources from retrieved chunks using hierarchical memory"""
        context = format_context_for_llm(retrieved_chunks)
        sources = extract_sources(retrieved_chunks)

        # Note: Memory context will be prepared in the async endpoint
        # This method remains sync for now
        llm_client = LLMClient()
        answer = llm_client.generate_answer(query, context, conversation_history)

        return answer, sources

    def format_sources(self, sources: List[Dict]) -> List[Source]:
        """Format source dictionaries to Source schema objects"""
        return [
            Source(
                file=s["file"],
                heading=s["heading"],
                relevance_score=s["relevance_score"],
                content_preview=s.get("content_preview"),
            )
            for s in sources
        ]

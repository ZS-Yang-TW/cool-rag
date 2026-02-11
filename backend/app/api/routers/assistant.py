import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db
from app.schemas.chat import ChatMessage, ChatResponse
from app.services import AssistantService

router = APIRouter(prefix="/api", tags=["chat"])
logger = logging.getLogger(__name__)


def get_assistant_service(db: Session = Depends(get_db)) -> AssistantService:
    """Dependency for AssistantService with DB session"""
    return AssistantService(db)


@router.post("/chat", response_model=ChatResponse)
async def chat(
    message: ChatMessage,
    db: Session = Depends(get_db),
    assistant_service: AssistantService = Depends(get_assistant_service),
):
    """
    Chat endpoint with production-ready hierarchical memory system

    Memory Architecture:
    - Layer 1: Recent Window (token-based, last N messages)
    - Layer 2: Conversation Summary (compressed history)
    - Layer 3: Structured Memory (persistent facts)
    """
    try:
        # Generate or use existing conversation ID
        conversation_id = assistant_service.get_or_create_conversation_id(
            message.conversation_id if message.conversation_id else None
        )

        # Get conversation history
        conversation_history = assistant_service.get_conversation_history(
            conversation_id
        )

        # Get hierarchical memory context
        memory_context = await assistant_service.memory_service.get_memory_context(
            session_id=conversation_id,
            conversation_history=conversation_history,
        )

        # Retrieve relevant chunks (RAG Layer)
        # Note: Only use user query for retrieval, NOT conversation history
        retrieved_chunks = assistant_service.retrieve_relevant_chunks(
            message.message, db
        )

        # Use recent window from memory service instead of simple slice
        recent_window = memory_context["recent_messages"]

        logger.info(
            f"Memory stats - Total: {memory_context['metadata']['total_messages']}, "
            f"Recent: {memory_context['metadata']['recent_message_count']}, "
            f"Tokens: {memory_context['metadata']['recent_tokens']}"
        )

        # Debug: log recent window content
        logger.debug(f"Recent window: {recent_window}")

        # Generate answer with hierarchical memory
        answer, sources = assistant_service.generate_answer(
            message.message, retrieved_chunks, recent_window
        )

        # Update conversation history
        assistant_service.update_conversation_history(
            conversation_id, message.message, answer
        )

        # Format sources
        source_list = assistant_service.format_sources(sources)

        return ChatResponse(
            answer=answer, sources=source_list, conversation_id=conversation_id
        )

    except ValueError as e:
        # Handle specific embedding/configuration errors
        error_msg = str(e)
        if "Embedding service" in error_msg or "embedding" in error_msg.lower():
            logger.error(f"Embedding service error: {e}")
            raise HTTPException(
                status_code=503,
                detail="嵌入服務配置錯誤。請檢查 OPENAI_BASE_URL 設定，或移除該設定以使用 OpenAI 官方 API。",
            )
        logger.error(f"Error in chat endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"處理您的請求時發生錯誤: {str(e)}")
    except Exception as e:
        logger.error(f"Error in chat endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"處理您的請求時發生錯誤: {str(e)}")


@router.delete("/chat/{conversation_id}")
async def clear_conversation(
    conversation_id: str,
    assistant_service: AssistantService = Depends(get_assistant_service),
):
    """
    Clear conversation history
    """
    if assistant_service.clear_conversation(conversation_id):
        return {"status": "success", "message": "對話已清除"}
    else:
        raise HTTPException(status_code=404, detail="找不到該對話")

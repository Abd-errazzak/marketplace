"""
AI Chat assistant endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from app.core.database import get_db
from app.services.chat_service import ChatService

router = APIRouter()


class ChatMessage(BaseModel):
    role: str  # user, assistant, system
    content: str
    timestamp: Optional[str] = None


class ChatRequest(BaseModel):
    message: str
    user_id: Optional[int] = None
    session_id: Optional[str] = None
    context: Optional[Dict[str, Any]] = None


class ChatResponse(BaseModel):
    message: str
    suggestions: Optional[List[str]] = None
    related_products: Optional[List[Dict[str, Any]]] = None
    session_id: str


@router.post("/message", response_model=ChatResponse)
async def send_chat_message(
    request: ChatRequest,
    db: Session = Depends(get_db)
):
    """Send a message to the AI chat assistant"""
    try:
        chat_service = ChatService(db)
        
        response = await chat_service.process_message(
            message=request.message,
            user_id=request.user_id,
            session_id=request.session_id,
            context=request.context
        )
        
        return response
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process message: {str(e)}"
        )


@router.get("/suggestions")
async def get_chat_suggestions(
    user_id: Optional[int] = None,
    session_id: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Get chat suggestions based on user context"""
    try:
        chat_service = ChatService(db)
        
        suggestions = await chat_service.get_suggestions(
            user_id=user_id,
            session_id=session_id
        )
        
        return {"suggestions": suggestions}
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get suggestions: {str(e)}"
        )


@router.get("/history")
async def get_chat_history(
    user_id: Optional[int] = None,
    session_id: Optional[str] = None,
    limit: int = 20,
    db: Session = Depends(get_db)
):
    """Get chat history for a user or session"""
    try:
        chat_service = ChatService(db)
        
        history = await chat_service.get_chat_history(
            user_id=user_id,
            session_id=session_id,
            limit=limit
        )
        
        return {"history": history}
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get chat history: {str(e)}"
        )




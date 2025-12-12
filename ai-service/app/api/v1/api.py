"""
AI Service API v1 router configuration
"""

from fastapi import APIRouter
from app.api.v1.endpoints import recommendations, chat, classification

api_router = APIRouter()

# Include all endpoint routers
api_router.include_router(recommendations.router, prefix="/recommendations", tags=["recommendations"])
api_router.include_router(chat.router, prefix="/chat", tags=["chat"])
api_router.include_router(classification.router, prefix="/classification", tags=["classification"])




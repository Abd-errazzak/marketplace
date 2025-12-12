"""
Product recommendation endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from app.core.database import get_db
from app.core.config import settings
from app.services.recommendation_service import RecommendationService

router = APIRouter()


class RecommendationRequest(BaseModel):
    user_id: Optional[int] = None
    product_id: Optional[int] = None
    category_id: Optional[int] = None
    limit: int = 10
    session_id: Optional[str] = None


class RecommendationResponse(BaseModel):
    product_id: int
    title: str
    price: float
    image_url: Optional[str] = None
    score: float
    reason: str


@router.post("/products", response_model=List[RecommendationResponse])
async def get_product_recommendations(
    request: RecommendationRequest,
    db: Session = Depends(get_db)
):
    """Get product recommendations"""
    try:
        recommendation_service = RecommendationService(db)
        
        if request.user_id:
            # User-based recommendations
            recommendations = await recommendation_service.get_user_recommendations(
                user_id=request.user_id,
                limit=request.limit
            )
        elif request.product_id:
            # Product-based recommendations (similar products)
            recommendations = await recommendation_service.get_similar_products(
                product_id=request.product_id,
                limit=request.limit
            )
        elif request.category_id:
            # Category-based recommendations
            recommendations = await recommendation_service.get_category_recommendations(
                category_id=request.category_id,
                limit=request.limit
            )
        else:
            # Popular products
            recommendations = await recommendation_service.get_popular_products(
                limit=request.limit
            )
        
        return recommendations
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get recommendations: {str(e)}"
        )


@router.get("/trending", response_model=List[RecommendationResponse])
async def get_trending_products(
    limit: int = 10,
    category_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """Get trending products"""
    try:
        recommendation_service = RecommendationService(db)
        recommendations = await recommendation_service.get_trending_products(
            limit=limit,
            category_id=category_id
        )
        
        return recommendations
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get trending products: {str(e)}"
        )


@router.get("/new-arrivals", response_model=List[RecommendationResponse])
async def get_new_arrivals(
    limit: int = 10,
    category_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """Get new arrival products"""
    try:
        recommendation_service = RecommendationService(db)
        recommendations = await recommendation_service.get_new_arrivals(
            limit=limit,
            category_id=category_id
        )
        
        return recommendations
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get new arrivals: {str(e)}"
        )


@router.post("/personalized", response_model=List[RecommendationResponse])
async def get_personalized_recommendations(
    user_id: int,
    limit: int = 10,
    db: Session = Depends(get_db)
):
    """Get personalized recommendations for a user"""
    try:
        recommendation_service = RecommendationService(db)
        recommendations = await recommendation_service.get_personalized_recommendations(
            user_id=user_id,
            limit=limit
        )
        
        return recommendations
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get personalized recommendations: {str(e)}"
        )




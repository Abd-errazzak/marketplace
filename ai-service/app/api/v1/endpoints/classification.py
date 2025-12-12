"""
Product classification and auto-tagging endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from app.core.database import get_db
from app.services.classification_service import ClassificationService

router = APIRouter()


class ClassificationRequest(BaseModel):
    title: str
    description: Optional[str] = None
    images: Optional[List[str]] = None


class ClassificationResponse(BaseModel):
    category_id: int
    category_name: str
    confidence: float
    suggested_tags: List[str]
    suggested_price_range: Optional[Dict[str, float]] = None


class AutoTagRequest(BaseModel):
    title: str
    description: Optional[str] = None
    category_id: Optional[int] = None


class AutoTagResponse(BaseModel):
    tags: List[str]
    confidence_scores: Dict[str, float]


@router.post("/product", response_model=ClassificationResponse)
async def classify_product(
    request: ClassificationRequest,
    db: Session = Depends(get_db)
):
    """Classify a product and suggest category, tags, and price range"""
    try:
        classification_service = ClassificationService(db)
        
        result = await classification_service.classify_product(
            title=request.title,
            description=request.description,
            images=request.images
        )
        
        return result
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to classify product: {str(e)}"
        )


@router.post("/auto-tag", response_model=AutoTagResponse)
async def auto_tag_product(
    request: AutoTagRequest,
    db: Session = Depends(get_db)
):
    """Generate automatic tags for a product"""
    try:
        classification_service = ClassificationService(db)
        
        result = await classification_service.generate_tags(
            title=request.title,
            description=request.description,
            category_id=request.category_id
        )
        
        return result
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate tags: {str(e)}"
        )


@router.post("/bulk-classify")
async def bulk_classify_products(
    products: List[ClassificationRequest],
    db: Session = Depends(get_db)
):
    """Bulk classify multiple products"""
    try:
        classification_service = ClassificationService(db)
        
        results = []
        for product in products:
            result = await classification_service.classify_product(
                title=product.title,
                description=product.description,
                images=product.images
            )
            results.append(result)
        
        return {"results": results}
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to bulk classify products: {str(e)}"
        )


@router.get("/categories")
async def get_category_suggestions(
    query: Optional[str] = None,
    limit: int = 10,
    db: Session = Depends(get_db)
):
    """Get category suggestions based on query"""
    try:
        classification_service = ClassificationService(db)
        
        suggestions = await classification_service.get_category_suggestions(
            query=query,
            limit=limit
        )
        
        return {"suggestions": suggestions}
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get category suggestions: {str(e)}"
        )




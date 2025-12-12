"""
Product and category schemas
"""

from pydantic import BaseModel, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from decimal import Decimal


class CategoryBase(BaseModel):
    name: str
    description: Optional[str] = None
    parent_id: Optional[int] = None
    image_url: Optional[str] = None
    is_active: bool = True
    sort_order: int = 0


class CategoryCreate(CategoryBase):
    pass


class CategoryUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    parent_id: Optional[int] = None
    image_url: Optional[str] = None
    is_active: Optional[bool] = None
    sort_order: Optional[int] = None


class CategoryResponse(CategoryBase):
    id: int
    slug: str
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class ProductVariationBase(BaseModel):
    name: str
    value: str
    sku: Optional[str] = None
    price: Optional[Decimal] = None
    stock: int = 0
    image_url: Optional[str] = None
    is_active: bool = True


class ProductVariationCreate(ProductVariationBase):
    pass


class ProductVariationUpdate(BaseModel):
    name: Optional[str] = None
    value: Optional[str] = None
    sku: Optional[str] = None
    price: Optional[Decimal] = None
    stock: Optional[int] = None
    image_url: Optional[str] = None
    is_active: Optional[bool] = None


class ProductVariationResponse(ProductVariationBase):
    id: int
    product_id: int
    created_at: datetime
    
    class Config:
        from_attributes = True


class ProductBase(BaseModel):
    title: str
    description: Optional[str] = None
    short_description: Optional[str] = None
    category_id: int
    price: Decimal
    compare_price: Optional[Decimal] = None
    cost_price: Optional[Decimal] = None
    sku: Optional[str] = None
    barcode: Optional[str] = None
    stock: int = 0
    low_stock_threshold: int = 5
    weight: Optional[Decimal] = None
    dimensions: Optional[Dict[str, Any]] = None
    images: Optional[List[str]] = None
    tags: Optional[List[str]] = None
    is_featured: bool = False
    is_digital: bool = False
    download_url: Optional[str] = None
    seo_title: Optional[str] = None
    seo_description: Optional[str] = None


class ProductCreate(ProductBase):
    pass


class ProductUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    short_description: Optional[str] = None
    category_id: Optional[int] = None
    price: Optional[Decimal] = None
    compare_price: Optional[Decimal] = None
    cost_price: Optional[Decimal] = None
    sku: Optional[str] = None
    barcode: Optional[str] = None
    stock: Optional[int] = None
    low_stock_threshold: Optional[int] = None
    weight: Optional[Decimal] = None
    dimensions: Optional[Dict[str, Any]] = None
    images: Optional[List[str]] = None
    tags: Optional[List[str]] = None
    status: Optional[str] = None
    is_featured: Optional[bool] = None
    is_digital: Optional[bool] = None
    download_url: Optional[str] = None
    seo_title: Optional[str] = None
    seo_description: Optional[str] = None


class ProductResponse(ProductBase):
    id: int
    seller_id: int
    slug: str
    status: str
    view_count: int
    sales_count: int
    rating: float
    review_count: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class ProductWithDetails(ProductResponse):
    category: CategoryResponse
    variations: List[ProductVariationResponse] = []


class ProductSearchFilters(BaseModel):
    category_id: Optional[int] = None
    min_price: Optional[Decimal] = None
    max_price: Optional[Decimal] = None
    tags: Optional[List[str]] = None
    is_featured: Optional[bool] = None
    status: Optional[str] = None
    seller_id: Optional[int] = None


class ProductSearchRequest(BaseModel):
    query: Optional[str] = None
    filters: Optional[ProductSearchFilters] = None
    page: int = 1
    limit: int = 20
    sort_by: Optional[str] = None  # price, rating, created_at, sales_count
    sort_order: Optional[str] = None  # asc, desc


class CartItemBase(BaseModel):
    product_id: int
    variation_id: Optional[int] = None
    quantity: int = 1


class CartItemCreate(CartItemBase):
    pass


class CartItemUpdate(BaseModel):
    quantity: Optional[int] = None


class CartItemResponse(CartItemBase):
    id: int
    user_id: Optional[int] = None
    session_id: Optional[str] = None
    price: Decimal
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class CartItemWithProduct(CartItemResponse):
    product: ProductResponse
    variation: Optional[ProductVariationResponse] = None


class ProductReviewBase(BaseModel):
    rating: int
    title: Optional[str] = None
    comment: Optional[str] = None
    images: Optional[List[str]] = None


class ProductReviewCreate(ProductReviewBase):
    product_id: int
    order_id: int


class ProductReviewUpdate(BaseModel):
    rating: Optional[int] = None
    title: Optional[str] = None
    comment: Optional[str] = None
    images: Optional[List[str]] = None


class ProductReviewResponse(ProductReviewBase):
    id: int
    product_id: int
    user_id: int
    order_id: int
    is_verified: bool
    is_approved: bool
    helpful_count: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class ProductReviewWithUser(ProductReviewResponse):
    user: dict  # Basic user info


class WishlistItemCreate(BaseModel):
    product_id: int


class WishlistItemResponse(BaseModel):
    id: int
    user_id: int
    product_id: int
    created_at: datetime
    
    class Config:
        from_attributes = True


class WishlistItemWithProduct(WishlistItemResponse):
    product: ProductResponse


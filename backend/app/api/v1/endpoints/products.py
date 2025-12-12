"""
Product management endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, asc
from typing import List, Optional
from decimal import Decimal
from app.core.database import get_db
from app.core.security import get_current_active_user, require_seller, get_optional_current_user
from app.models.user import User, UserRole
from app.models.product import Product, Category, ProductVariation, CartItem, ProductReview, WishlistItem
from app.schemas.product import (
    ProductCreate, ProductUpdate, ProductResponse, ProductWithDetails,
    ProductSearchRequest, ProductSearchFilters, CartItemCreate, CartItemUpdate,
    CartItemResponse, CartItemWithProduct, ProductReviewCreate, ProductReviewUpdate,
    ProductReviewResponse, ProductReviewWithUser, WishlistItemCreate, WishlistItemResponse,
    WishlistItemWithProduct, CategoryCreate, CategoryUpdate, CategoryResponse
)
from app.core.exceptions import NotFoundError, ValidationError
from app.utils.slug import generate_slug
from app.utils.images import save_uploaded_image
import os

router = APIRouter()


# Category endpoints
@router.get("/categories", response_model=List[CategoryResponse])
async def get_categories(
    parent_id: Optional[int] = None,
    is_active: bool = True,
    db: Session = Depends(get_db)
):
    """Get all categories"""
    query = db.query(Category).filter(Category.is_active == is_active)
    
    if parent_id is not None:
        query = query.filter(Category.parent_id == parent_id)
    
    categories = query.order_by(Category.sort_order, Category.name).all()
    return categories


@router.post("/categories", response_model=CategoryResponse, status_code=status.HTTP_201_CREATED)
async def create_category(
    category_data: CategoryCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Create new category (admin only)"""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    
    # Generate slug
    slug = generate_slug(category_data.name)
    
    # Check if slug already exists
    existing_category = db.query(Category).filter(Category.slug == slug).first()
    if existing_category:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Category with this name already exists"
        )
    
    category = Category(
        **category_data.dict(),
        slug=slug
    )
    
    db.add(category)
    db.commit()
    db.refresh(category)
    
    return category


# Product endpoints
@router.get("/", response_model=List[ProductResponse])
async def get_products(
    skip: int = 0,
    limit: int = 20,
    category_id: Optional[int] = None,
    seller_id: Optional[int] = None,
    min_price: Optional[Decimal] = None,
    max_price: Optional[Decimal] = None,
    is_featured: Optional[bool] = None,
    status: Optional[str] = None,
    search: Optional[str] = None,
    sort_by: str = "created_at",
    sort_order: str = "desc",
    db: Session = Depends(get_db)
):
    """Get products with filtering and pagination"""
    query = db.query(Product)
    
    # Apply filters
    if category_id:
        query = query.filter(Product.category_id == category_id)
    
    if seller_id:
        query = query.filter(Product.seller_id == seller_id)
    
    if min_price is not None:
        query = query.filter(Product.price >= min_price)
    
    if max_price is not None:
        query = query.filter(Product.price <= max_price)
    
    if is_featured is not None:
        query = query.filter(Product.is_featured == is_featured)
    
    if status:
        query = query.filter(Product.status == status)
    
    if search:
        query = query.filter(
            or_(
                Product.title.contains(search),
                Product.description.contains(search),
                Product.tags.contains([search])
            )
        )
    
    # Apply sorting
    if sort_by == "price":
        if sort_order == "asc":
            query = query.order_by(asc(Product.price))
        else:
            query = query.order_by(desc(Product.price))
    elif sort_by == "rating":
        if sort_order == "asc":
            query = query.order_by(asc(Product.rating))
        else:
            query = query.order_by(desc(Product.rating))
    elif sort_by == "sales_count":
        if sort_order == "asc":
            query = query.order_by(asc(Product.sales_count))
        else:
            query = query.order_by(desc(Product.sales_count))
    else:  # created_at
        if sort_order == "asc":
            query = query.order_by(asc(Product.created_at))
        else:
            query = query.order_by(desc(Product.created_at))
    
    products = query.offset(skip).limit(limit).all()
    return products


@router.get("/{product_id}", response_model=ProductWithDetails)
async def get_product(
    product_id: int,
    db: Session = Depends(get_db)
):
    """Get product by ID with details"""
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise NotFoundError("Product not found")
    
    # Increment view count
    product.view_count += 1
    db.commit()
    
    return product


@router.post("/", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
async def create_product(
    product_data: ProductCreate,
    current_user: User = Depends(require_seller),
    db: Session = Depends(get_db)
):
    """Create new product (seller only)"""
    # Get seller profile
    from app.models.user import Seller
    seller = db.query(Seller).filter(Seller.user_id == current_user.id).first()
    if not seller:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Seller profile not found"
        )
    
    # Generate slug
    slug = generate_slug(product_data.title)
    
    # Check if slug already exists
    existing_product = db.query(Product).filter(Product.slug == slug).first()
    if existing_product:
        slug = f"{slug}-{product_data.sku or 'new'}"
    
    # Check if SKU already exists
    if product_data.sku:
        existing_sku = db.query(Product).filter(Product.sku == product_data.sku).first()
        if existing_sku:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="SKU already exists"
            )
    
    product = Product(
        **product_data.dict(),
        seller_id=seller.id,
        slug=slug
    )
    
    db.add(product)
    db.commit()
    db.refresh(product)
    
    return product


@router.put("/{product_id}", response_model=ProductResponse)
async def update_product(
    product_id: int,
    product_update: ProductUpdate,
    current_user: User = Depends(require_seller),
    db: Session = Depends(get_db)
):
    """Update product (seller only)"""
    # Get seller profile
    from app.models.user import Seller
    seller = db.query(Seller).filter(Seller.user_id == current_user.id).first()
    if not seller:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Seller profile not found"
        )
    
    product = db.query(Product).filter(
        Product.id == product_id,
        Product.seller_id == seller.id
    ).first()
    
    if not product:
        raise NotFoundError("Product not found")
    
    # Check SKU uniqueness if being updated
    if product_update.sku and product_update.sku != product.sku:
        existing_sku = db.query(Product).filter(
            Product.sku == product_update.sku,
            Product.id != product.id
        ).first()
        if existing_sku:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="SKU already exists"
            )
    
    # Update product fields
    for field, value in product_update.dict(exclude_unset=True).items():
        setattr(product, field, value)
    
    db.commit()
    db.refresh(product)
    
    return product


@router.delete("/{product_id}")
async def delete_product(
    product_id: int,
    current_user: User = Depends(require_seller),
    db: Session = Depends(get_db)
):
    """Delete product (seller only)"""
    # Get seller profile
    from app.models.user import Seller
    seller = db.query(Seller).filter(Seller.user_id == current_user.id).first()
    if not seller:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Seller profile not found"
        )
    
    product = db.query(Product).filter(
        Product.id == product_id,
        Product.seller_id == seller.id
    ).first()
    
    if not product:
        raise NotFoundError("Product not found")
    
    db.delete(product)
    db.commit()
    
    return {"message": "Product deleted successfully"}


# Cart endpoints
@router.get("/cart/items", response_model=List[CartItemWithProduct])
async def get_cart_items(
    current_user: Optional[User] = Depends(get_optional_current_user),
    session_id: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Get cart items"""
    if current_user:
        cart_items = db.query(CartItem).filter(CartItem.user_id == current_user.id).all()
    elif session_id:
        cart_items = db.query(CartItem).filter(CartItem.session_id == session_id).all()
    else:
        cart_items = []
    
    return cart_items


@router.post("/cart/items", response_model=CartItemResponse, status_code=status.HTTP_201_CREATED)
async def add_to_cart(
    cart_item_data: CartItemCreate,
    current_user: Optional[User] = Depends(get_optional_current_user),
    session_id: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Add item to cart"""
    # Get product
    product = db.query(Product).filter(Product.id == cart_item_data.product_id).first()
    if not product:
        raise NotFoundError("Product not found")
    
    # Check stock
    if product.stock < cart_item_data.quantity:
        raise ValidationError("Insufficient stock")
    
    # Check if item already in cart
    existing_item = None
    if current_user:
        existing_item = db.query(CartItem).filter(
            CartItem.user_id == current_user.id,
            CartItem.product_id == cart_item_data.product_id,
            CartItem.variation_id == cart_item_data.variation_id
        ).first()
    elif session_id:
        existing_item = db.query(CartItem).filter(
            CartItem.session_id == session_id,
            CartItem.product_id == cart_item_data.product_id,
            CartItem.variation_id == cart_item_data.variation_id
        ).first()
    
    if existing_item:
        # Update quantity
        existing_item.quantity += cart_item_data.quantity
        db.commit()
        db.refresh(existing_item)
        return existing_item
    
    # Create new cart item
    cart_item = CartItem(
        user_id=current_user.id if current_user else None,
        session_id=session_id,
        product_id=cart_item_data.product_id,
        variation_id=cart_item_data.variation_id,
        quantity=cart_item_data.quantity,
        price=product.price
    )
    
    db.add(cart_item)
    db.commit()
    db.refresh(cart_item)
    
    return cart_item


@router.put("/cart/items/{item_id}", response_model=CartItemResponse)
async def update_cart_item(
    item_id: int,
    cart_item_update: CartItemUpdate,
    current_user: Optional[User] = Depends(get_optional_current_user),
    session_id: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Update cart item quantity"""
    # Find cart item
    query = db.query(CartItem).filter(CartItem.id == item_id)
    
    if current_user:
        query = query.filter(CartItem.user_id == current_user.id)
    elif session_id:
        query = query.filter(CartItem.session_id == session_id)
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    
    cart_item = query.first()
    if not cart_item:
        raise NotFoundError("Cart item not found")
    
    # Update quantity
    if cart_item_update.quantity is not None:
        if cart_item_update.quantity <= 0:
            db.delete(cart_item)
            db.commit()
            return {"message": "Item removed from cart"}
        
        cart_item.quantity = cart_item_update.quantity
    
    db.commit()
    db.refresh(cart_item)
    
    return cart_item


@router.delete("/cart/items/{item_id}")
async def remove_from_cart(
    item_id: int,
    current_user: Optional[User] = Depends(get_optional_current_user),
    session_id: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Remove item from cart"""
    # Find cart item
    query = db.query(CartItem).filter(CartItem.id == item_id)
    
    if current_user:
        query = query.filter(CartItem.user_id == current_user.id)
    elif session_id:
        query = query.filter(CartItem.session_id == session_id)
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    
    cart_item = query.first()
    if not cart_item:
        raise NotFoundError("Cart item not found")
    
    db.delete(cart_item)
    db.commit()
    
    return {"message": "Item removed from cart"}


# Wishlist endpoints
@router.get("/wishlist", response_model=List[WishlistItemWithProduct])
async def get_wishlist(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get user wishlist"""
    wishlist_items = db.query(WishlistItem).filter(WishlistItem.user_id == current_user.id).all()
    return wishlist_items


@router.post("/wishlist", response_model=WishlistItemResponse, status_code=status.HTTP_201_CREATED)
async def add_to_wishlist(
    wishlist_data: WishlistItemCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Add item to wishlist"""
    # Check if product exists
    product = db.query(Product).filter(Product.id == wishlist_data.product_id).first()
    if not product:
        raise NotFoundError("Product not found")
    
    # Check if already in wishlist
    existing_item = db.query(WishlistItem).filter(
        WishlistItem.user_id == current_user.id,
        WishlistItem.product_id == wishlist_data.product_id
    ).first()
    
    if existing_item:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Product already in wishlist"
        )
    
    wishlist_item = WishlistItem(
        user_id=current_user.id,
        product_id=wishlist_data.product_id
    )
    
    db.add(wishlist_item)
    db.commit()
    db.refresh(wishlist_item)
    
    return wishlist_item


@router.delete("/wishlist/{product_id}")
async def remove_from_wishlist(
    product_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Remove item from wishlist"""
    wishlist_item = db.query(WishlistItem).filter(
        WishlistItem.user_id == current_user.id,
        WishlistItem.product_id == product_id
    ).first()
    
    if not wishlist_item:
        raise NotFoundError("Item not found in wishlist")
    
    db.delete(wishlist_item)
    db.commit()
    
    return {"message": "Item removed from wishlist"}


# Review endpoints
@router.get("/{product_id}/reviews", response_model=List[ProductReviewWithUser])
async def get_product_reviews(
    product_id: int,
    skip: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db)
):
    """Get product reviews"""
    reviews = db.query(ProductReview).filter(
        ProductReview.product_id == product_id,
        ProductReview.is_approved == True
    ).offset(skip).limit(limit).all()
    
    return reviews


@router.post("/{product_id}/reviews", response_model=ProductReviewResponse, status_code=status.HTTP_201_CREATED)
async def create_product_review(
    product_id: int,
    review_data: ProductReviewCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Create product review"""
    # Check if product exists
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise NotFoundError("Product not found")
    
    # Check if user has already reviewed this product for this order
    existing_review = db.query(ProductReview).filter(
        ProductReview.user_id == current_user.id,
        ProductReview.product_id == product_id,
        ProductReview.order_id == review_data.order_id
    ).first()
    
    if existing_review:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Review already exists for this order"
        )
    
    review = ProductReview(
        **review_data.dict(),
        user_id=current_user.id
    )
    
    db.add(review)
    db.commit()
    db.refresh(review)
    
    # Update product rating
    # TODO: Recalculate average rating
    
    return review


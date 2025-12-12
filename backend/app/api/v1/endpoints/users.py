"""
User management endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.core.database import get_db
from app.core.security import get_current_active_user, require_admin
from app.models.user import User, UserRole, Seller, UserAddress
from app.schemas.user import (
    UserResponse, UserUpdate, UserAddressCreate, UserAddressUpdate,
    UserAddressResponse, SellerCreate, SellerUpdate, SellerResponse
)
from app.core.exceptions import NotFoundError, ValidationError

router = APIRouter()


@router.get("/profile", response_model=UserResponse)
async def get_user_profile(
    current_user: User = Depends(get_current_active_user)
):
    """Get current user profile"""
    return current_user


@router.put("/profile", response_model=UserResponse)
async def update_user_profile(
    user_update: UserUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Update current user profile"""
    # Update user fields
    for field, value in user_update.dict(exclude_unset=True).items():
        setattr(current_user, field, value)
    
    db.commit()
    db.refresh(current_user)
    
    return current_user


@router.get("/addresses", response_model=List[UserAddressResponse])
async def get_user_addresses(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get user addresses"""
    addresses = db.query(UserAddress).filter(UserAddress.user_id == current_user.id).all()
    return addresses


@router.post("/addresses", response_model=UserAddressResponse, status_code=status.HTTP_201_CREATED)
async def create_user_address(
    address_data: UserAddressCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Create new user address"""
    # If this is set as default, unset other defaults of the same type
    if address_data.is_default:
        db.query(UserAddress).filter(
            UserAddress.user_id == current_user.id,
            UserAddress.type == address_data.type,
            UserAddress.is_default == True
        ).update({"is_default": False})
    
    address = UserAddress(
        user_id=current_user.id,
        **address_data.dict()
    )
    
    db.add(address)
    db.commit()
    db.refresh(address)
    
    return address


@router.put("/addresses/{address_id}", response_model=UserAddressResponse)
async def update_user_address(
    address_id: int,
    address_update: UserAddressUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Update user address"""
    address = db.query(UserAddress).filter(
        UserAddress.id == address_id,
        UserAddress.user_id == current_user.id
    ).first()
    
    if not address:
        raise NotFoundError("Address not found")
    
    # If setting as default, unset other defaults of the same type
    if address_update.is_default:
        db.query(UserAddress).filter(
            UserAddress.user_id == current_user.id,
            UserAddress.type == address.type,
            UserAddress.is_default == True
        ).update({"is_default": False})
    
    # Update address fields
    for field, value in address_update.dict(exclude_unset=True).items():
        setattr(address, field, value)
    
    db.commit()
    db.refresh(address)
    
    return address


@router.delete("/addresses/{address_id}")
async def delete_user_address(
    address_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Delete user address"""
    address = db.query(UserAddress).filter(
        UserAddress.id == address_id,
        UserAddress.user_id == current_user.id
    ).first()
    
    if not address:
        raise NotFoundError("Address not found")
    
    db.delete(address)
    db.commit()
    
    return {"message": "Address deleted successfully"}


@router.get("/seller-profile", response_model=SellerResponse)
async def get_seller_profile(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get seller profile (if user is a seller)"""
    if current_user.role not in [UserRole.SELLER, UserRole.ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is not a seller"
        )
    
    seller = db.query(Seller).filter(Seller.user_id == current_user.id).first()
    if not seller:
        raise NotFoundError("Seller profile not found")
    
    return seller


@router.post("/seller-profile", response_model=SellerResponse, status_code=status.HTTP_201_CREATED)
async def create_seller_profile(
    seller_data: SellerCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Create seller profile"""
    if current_user.role not in [UserRole.BUYER, UserRole.SELLER]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot create seller profile"
        )
    
    # Check if seller profile already exists
    existing_seller = db.query(Seller).filter(Seller.user_id == current_user.id).first()
    if existing_seller:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Seller profile already exists"
        )
    
    # Check if shop name is unique
    existing_shop = db.query(Seller).filter(Seller.shop_name == seller_data.shop_name).first()
    if existing_shop:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Shop name already taken"
        )
    
    # Create seller profile
    seller = Seller(
        user_id=current_user.id,
        **seller_data.dict()
    )
    
    # Update user role to seller
    current_user.role = UserRole.SELLER
    
    db.add(seller)
    db.commit()
    db.refresh(seller)
    
    return seller


@router.put("/seller-profile", response_model=SellerResponse)
async def update_seller_profile(
    seller_update: SellerUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Update seller profile"""
    if current_user.role not in [UserRole.SELLER, UserRole.ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is not a seller"
        )
    
    seller = db.query(Seller).filter(Seller.user_id == current_user.id).first()
    if not seller:
        raise NotFoundError("Seller profile not found")
    
    # Check shop name uniqueness if being updated
    if seller_update.shop_name and seller_update.shop_name != seller.shop_name:
        existing_shop = db.query(Seller).filter(
            Seller.shop_name == seller_update.shop_name,
            Seller.id != seller.id
        ).first()
        if existing_shop:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Shop name already taken"
            )
    
    # Update seller fields
    for field, value in seller_update.dict(exclude_unset=True).items():
        setattr(seller, field, value)
    
    db.commit()
    db.refresh(seller)
    
    return seller


# Admin endpoints
@router.get("/", response_model=List[UserResponse])
async def get_all_users(
    skip: int = 0,
    limit: int = 100,
    role: UserRole = None,
    admin_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Get all users (admin only)"""
    query = db.query(User)
    
    if role:
        query = query.filter(User.role == role)
    
    users = query.offset(skip).limit(limit).all()
    return users


@router.get("/{user_id}", response_model=UserResponse)
async def get_user_by_id(
    user_id: int,
    admin_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Get user by ID (admin only)"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise NotFoundError("User not found")
    
    return user


@router.put("/{user_id}/activate")
async def activate_user(
    user_id: int,
    admin_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Activate user (admin only)"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise NotFoundError("User not found")
    
    user.is_active = True
    db.commit()
    
    return {"message": "User activated successfully"}


@router.put("/{user_id}/deactivate")
async def deactivate_user(
    user_id: int,
    admin_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Deactivate user (admin only)"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise NotFoundError("User not found")
    
    user.is_active = False
    db.commit()
    
    return {"message": "User deactivated successfully"}


@router.put("/{user_id}/role")
async def update_user_role(
    user_id: int,
    new_role: UserRole,
    admin_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Update user role (admin only)"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise NotFoundError("User not found")
    
    user.role = new_role
    db.commit()
    
    return {"message": f"User role updated to {new_role}"}


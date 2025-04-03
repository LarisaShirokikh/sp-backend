# app/api/v1/group_buy/router.py

from itertools import product
import json
import logging
from typing import List, Optional
from sqlalchemy.orm import Session

from app.db.redis import get_redis_client
from app.crud.group_buy import group_buy

from fastapi import APIRouter, Depends, HTTPException, Path, status
from app.api.deps import get_current_user, get_db, get_current_organizer
from app.models.group_buy import GroupBuyCategory, GroupBuyStatus
from app.models.user import User
from app.schemas.group_buy import GroupBuyCreate, GroupBuyDetailResponse, GroupBuyResponse, GroupBuyUpdate, ProductCreate, ProductResponse, ProductUpdate

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)



# ========== Group Buy Routes ==========

router = APIRouter()

@router.post("/", response_model=GroupBuyResponse, status_code=status.HTTP_201_CREATED)
async def create_group_buy(
    *,
    db: Session = Depends(get_db),
    group_buy_in: GroupBuyCreate,
    current_user: User = Depends(get_current_organizer)
):
    """
    Create new group buy (only organizers or admins)
    """
    new_group_buy = group_buy.create(db=db, obj_in=group_buy_in, organizer_id=current_user.id)
    
    # Cache in Redis (separate from DB operations)
    redis = await get_redis_client()
    group_buy_key = f"group_buy:{new_group_buy.id}"
    group_buy_data = {
        "id": new_group_buy.id,
        "title": new_group_buy.title,
        "description": new_group_buy.description,
        "category": new_group_buy.category,
        "status": new_group_buy.status,
        "organizer_id": new_group_buy.organizer_id,
        "created_at": new_group_buy.created_at.isoformat(),
        "updated_at": new_group_buy.updated_at.isoformat(),
    }
    await redis.set(group_buy_key, json.dumps(group_buy_data), ex=3600) # 1 hour cache
    
    # Add to organizer's group buys set
    organizer_group_buys_key = f"user:{current_user.id}:group_buys"
    await redis.sadd(organizer_group_buys_key, new_group_buy.id)
    
    # Add to active group buys set if applicable
    if new_group_buy.is_visible and new_group_buy.status == GroupBuyStatus.active:
        await redis.sadd("active_group_buys", new_group_buy.id)
    
    return new_group_buy


@router.get("/", response_model=List[GroupBuyResponse])
def get_group_buys(
    *,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    skip: int = 0,
    limit: int = 100,
    status: Optional[GroupBuyStatus] = None,
    category: Optional[GroupBuyCategory] = None,
    organizer_id: Optional[int] = None,
    active_only: bool = False
):
    """
    Get all group buys with optional filters
    """
    filters = {}
    
    if status:
        filters["status"] = status
    
    if category:
        filters["category"] = category
    
    if organizer_id:
        filters["organizer_id"] = organizer_id
    
    if active_only:
        filters["active_only"] = True
    
    # Admins/organizers can see all group buys based on filters
    if any(role.name in ["organizer", "admin", "super_admin"] for role in current_user.roles):
        return group_buy.get_multi(db, skip=skip, limit=limit, filters=filters)
    
    # Regular users can only see active and visible group buys
    filters["is_visible"] = True
    filters["active_only"] = True
    
    return group_buy.get_multi(db, skip=skip, limit=limit, filters=filters)


@router.get("/my", response_model=List[GroupBuyResponse])
def get_my_group_buys(
    *,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_organizer),
    skip: int = 0,
    limit: int = 100,
    status: Optional[GroupBuyStatus] = None
):
    """
    Get current organizer's group buys
    """
    filters = {"organizer_id": current_user.id}
    
    if status:
        filters["status"] = status
    
    return group_buy.get_multi(db, skip=skip, limit=limit, filters=filters)


@router.get("/{group_buy_id}", response_model=GroupBuyDetailResponse)
async def get_group_buy_detail(
    *,
    db: Session = Depends(get_db),
    group_buy_id: int = Path(..., title="The ID of the group buy to get"),
    current_user: User = Depends(get_current_user)
):
    """
    Get detailed info about specific group buy
    """
    # Try to get from Redis cache first
    redis = await get_redis_client()
    cached_data = await redis.get(f"group_buy:{group_buy_id}")
    
    db_group_buy = None
    
    if cached_data:
        try:
            group_buy_data = json.loads(cached_data)
            
            # Check permissions based on cached data
            is_admin = any(r.role in ["admin", "super_admin"] for r in current_user.roles)
            is_organizer = any(r.role == "organizer" for r in current_user.roles)
            is_visible = group_buy_data.get("is_visible", False)
            
            if not (is_admin or is_organizer or is_visible):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You don't have permission to view this group buy"
                )
                
            # We still need to get from DB to include relationships and counts
            db_group_buy = group_buy.get(db, id=group_buy_id)
            
        except (json.JSONDecodeError, KeyError):
            # If cache is corrupted, fallback to DB
            pass
    
    # If not in cache or cache is corrupted, get from DB
    if not db_group_buy:
        db_group_buy = group_buy.get(db, id=group_buy_id)
        
        if not db_group_buy:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Group buy not found"
            )
        
        # Check permissions
        is_admin = any(r.role in ["admin", "super_admin"] for r in current_user.roles)
        is_organizer = db_group_buy.organizer_id == current_user.id
        is_visible = db_group_buy.is_visible
        
        if not (is_admin or is_organizer or is_visible):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to view this group buy"
            )
    
    # Get additional data for detailed response
    group_buy_with_counts = group_buy.get_with_products_count(db, id=group_buy_id)
    
    if not group_buy_with_counts:
        # This should never happen if db_group_buy exists
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Group buy not found"
        )
    
    return group_buy_with_counts


@router.put("/{group_buy_id}", response_model=GroupBuyResponse)
async def update_group_buy(
    *,
    db: Session = Depends(get_db),
    group_buy_id: int = Path(..., title="The ID of the group buy to update"),
    group_buy_in: GroupBuyUpdate,
    current_user: User = Depends(get_current_user)
):
    """
    Update a group buy (only organizer who created it or admin)
    """
    db_group_buy = group_buy.get(db, id=group_buy_id)
    
    if not db_group_buy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Group buy not found"
        )
    
    # Check permissions
    is_admin = any(r.role in ["admin", "super_admin"] for r in current_user.roles)
    is_organizer = db_group_buy.organizer_id == current_user.id
    
    if not (is_admin or is_organizer):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to update this group buy"
        )
    
    # Update group buy
    updated_group_buy = group_buy.update(db=db, db_obj=db_group_buy, obj_in=group_buy_in)
    
    # Update Redis cache
    redis = await get_redis_client()
    group_buy_key = f"group_buy:{updated_group_buy.id}"
    redis.delete(group_buy_key)  # Delete old cache
    
    # Update active_group_buys set
    if updated_group_buy.is_visible and updated_group_buy.status == group_buy.GroupBuyStatus.active:
        redis.sadd("active_group_buys", updated_group_buy.id)
    else:
        redis.srem("active_group_buys", updated_group_buy.id)
    
    return updated_group_buy


@router.delete("/{group_buy_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_group_buy(
    *,
    db: Session = Depends(get_db),
    group_buy_id: int = Path(..., title="The ID of the group buy to delete"),
    current_user: User = Depends(get_current_user)
):
    """
    Delete a group buy (only organizer who created it or admin)
    """
    db_group_buy = group_buy.get(db, id=group_buy_id)
    
    if not db_group_buy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Group buy not found"
        )
    
    # Check permissions
    is_admin = current_user.role in ["admin", "super_admin"]
    is_organizer = db_group_buy.organizer_id == current_user.id
    
    if not (is_admin or is_organizer):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to delete this group buy"
        )
    
    # Delete from DB
    group_buy.delete(db=db, id=group_buy_id)
    
    # Delete from Redis
    redis = get_redis_client()
    redis.delete(f"group_buy:{group_buy_id}")
    redis.srem("active_group_buys", group_buy_id)
    redis.srem(f"user:{db_group_buy.organizer_id}:group_buys", group_buy_id)
    
    # Delete associated products from Redis
    product_ids = redis.smembers(f"group_buy:{group_buy_id}:products")
    for product_id in product_ids:
        redis.delete(f"product:{product_id}")
    
    redis.delete(f"group_buy:{group_buy_id}:products")
    
    return None


# ========== Product Routes ==========

@router.post("/{group_buy_id}/products", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
def create_product(
    *,
    db: Session = Depends(get_db),
    group_buy_id: int = Path(..., title="The ID of the group buy"),
    product_in: ProductCreate,
    current_user: User = Depends(get_current_user)
):
    """
    Add a product to a group buy (only organizer or admin)
    """
    db_group_buy = group_buy.get(db, id=group_buy_id)
    
    if not db_group_buy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Group buy not found"
        )
    
    # Check permissions
    is_admin = current_user.role in ["admin", "super_admin"]
    is_organizer = db_group_buy.organizer_id == current_user.id
    
    if not (is_admin or is_organizer):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to add products to this group buy"
        )
    
    # Create product
    new_product = product.create(db=db, obj_in=product_in, group_buy_id=group_buy_id)
    
    # Cache in Redis
    redis = get_redis_client()
    product_key = f"product:{new_product.id}"
    product_data = {
        "id": new_product.id,
        "name": new_product.name,
        "price": new_product.price,
        "group_buy_id": new_product.group_buy_id,
        "created_at": new_product.created_at.isoformat(),
    }
    redis.set(product_key, json.dumps(product_data), ex=3600)  # 1 hour cache
    
    # Add to group buy's products set
    redis.sadd(f"group_buy:{group_buy_id}:products", new_product.id)
    
    return new_product


@router.get("/{group_buy_id}/products", response_model=List[ProductResponse])
def get_products(
    *,
    db: Session = Depends(get_db),
    group_buy_id: int = Path(..., title="The ID of the group buy"),
    current_user: User = Depends(get_current_user),
    skip: int = 0,
    limit: int = 100
):
    """
    Get all products for a specific group buy
    """
    db_group_buy = group_buy.get(db, id=group_buy_id)
    
    if not db_group_buy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Group buy not found"
        )
    
    # Check permissions for non-visible group buys
    if not db_group_buy.is_visible:
        is_admin = current_user.role in ["admin", "super_admin"]
        is_organizer = db_group_buy.organizer_id == current_user.id
        
        if not (is_admin or is_organizer):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to view products in this group buy"
            )
    
    return product.get_multi(db=db, group_buy_id=group_buy_id, skip=skip, limit=limit)


@router.get("/{group_buy_id}/products/{product_id}", response_model=ProductResponse)
def get_product(
    *,
    db: Session = Depends(get_db),
    group_buy_id: int = Path(..., title="The ID of the group buy"),
    product_id: int = Path(..., title="The ID of the product"),
    current_user: User = Depends(get_current_user)
):
    """
    Get a specific product
    """
    db_group_buy = group_buy.get(db, id=group_buy_id)
    
    if not db_group_buy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Group buy not found"
        )
    
    # Check permissions for non-visible group buys
    if not db_group_buy.is_visible:
        is_admin = current_user.role in ["admin", "super_admin"]
        is_organizer = db_group_buy.organizer_id == current_user.id
        
        if not (is_admin or is_organizer):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to view products in this group buy"
            )
    
    db_product = product.get(db, id=product_id)
    
    if not db_product or db_product.group_buy_id != group_buy_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found in this group buy"
        )
    
    return db_product


@router.put("/{group_buy_id}/products/{product_id}", response_model=ProductResponse)
def update_product(
    *,
    db: Session = Depends(get_db),
    group_buy_id: int = Path(..., title="The ID of the group buy"),
    product_id: int = Path(..., title="The ID of the product"),
    product_in: ProductUpdate,
    current_user: User = Depends(get_current_user)
):
    """
    Update a specific product (only organizer or admin)
    """
    db_group_buy = group_buy.get(db, id=group_buy_id)
    
    if not db_group_buy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Group buy not found"
        )
    
    # Check permissions
    is_admin = current_user.role in ["admin", "super_admin"]
    is_organizer = db_group_buy.organizer_id == current_user.id
    
    if not (is_admin or is_organizer):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to update products in this group buy"
        )
    
    db_product = product.get(db, id=product_id)
    
    if not db_product or db_product.group_buy_id != group_buy_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found in this group buy"
        )
    
    # Update product
    updated_product = product.update(db=db, db_obj=db_product, obj_in=product_in)
    
    # Update Redis cache
    redis = get_redis_client()
    redis.delete(f"product:{product_id}")
    
    return updated_product


@router.delete("/{group_buy_id}/products/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_product(
    *,
    db: Session = Depends(get_db),
    group_buy_id: int = Path(..., title="The ID of the group buy"),
    product_id: int = Path(..., title="The ID of the product"),
    current_user: User = Depends(get_current_user)
):
    """
    Delete a specific product (only organizer or admin)
    """
    db_group_buy = group_buy.get(db, id=group_buy_id)
    
    if not db_group_buy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Group buy not found"
        )
    
    # Check permissions
    is_admin = current_user.role in ["admin", "super_admin"]
    is_organizer = db_group_buy.organizer_id == current_user.id
    
    if not (is_admin or is_organizer):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to delete products from this group buy"
        )
    
    db_product = product.get(db, id=product_id)
    
    if not db_product or db_product.group_buy_id != group_buy_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found in this group buy"
        )
    
    # Delete product
    product.delete(db=db, id=product_id)
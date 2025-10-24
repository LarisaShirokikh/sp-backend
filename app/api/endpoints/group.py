# app/api/v1/group_buy/router.py

# Change this import
from datetime import datetime
from itertools import product as itertools_product
import json
import logging
from typing import List, Optional
from sqlalchemy import desc, func
from sqlalchemy.orm import Session

from app.crud import order
from app.db.redis import get_redis_client
from app.crud.group_buy import group_buy
# Add import for product CRUD operations
from app.crud.group_buy import product

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from app.api.deps import get_current_user, get_db, get_current_organizer
from app.models.group_buy import GroupBuyCategory, GroupBuyStatus
from app.models.user import User
from app.schemas.group_buy import GroupBuyCreate, GroupBuyDetailResponse, GroupBuyResponse, GroupBuyUpdate, ProductCreate, ProductResponse, ProductUpdate
from app.schemas.stats import NotificationResponse, StatsResponse

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)



# ========== Group Buy Routes ==========

router = APIRouter()

@router.get("/stats", response_model=StatsResponse)
async def get_stats(
    *,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_organizer)
):
    """
    Get organizer dashboard statistics
    """
    # Import the GroupBuy model directly
    from app.models.group_buy import GroupBuy
    
    # Check if stats are cached
    redis = await get_redis_client()
    stats_key = f"user:{current_user.id}:stats"
    cached_stats = await redis.get(stats_key)
    
    if cached_stats:
        try:
            return json.loads(cached_stats)
        except json.JSONDecodeError:
            # If cache is corrupted, regenerate stats
            pass
    
    # Calculate stats from database
    # 1. Active group buys count
    active_group_buys = group_buy.count(
        db, 
        filters={
            "organizer_id": current_user.id,
            "status": GroupBuyStatus.active
        }
    )
    
    # 2. Total participants
    total_participants = db.query(func.count(order.Order.id)).join(
        GroupBuy, order.Order.group_buy_id == GroupBuy.id
    ).filter(
        GroupBuy.organizer_id == current_user.id
    ).scalar() or 0
    
    # 3. Total amount (sum of all orders)
    total_amount = db.query(func.sum(order.Order.total_amount)).join(
        GroupBuy, order.Order.group_buy_id == GroupBuy.id
    ).filter(
        GroupBuy.organizer_id == current_user.id
    ).scalar() or 0
    
    # 4. Completed group buys count
    completed_group_buys = group_buy.count(
        db, 
        filters={
            "organizer_id": current_user.id,
            "status": GroupBuyStatus.completed
        }
    )
    
    # 5. Last month's growth (percentage increase in group buys)
    # This is a more complex calculation that may require comparing with previous month
    # For simplicity, we'll use a placeholder value or calculation
    # In a real implementation, you would compare with previous month's data
    
    # Example calculation for monthly growth:
    import datetime
    current_date = datetime.datetime.now()
    one_month_ago = current_date - datetime.timedelta(days=30)
    
    current_month_group_buys = group_buy.count(
        db,
        filters={
            "organizer_id": current_user.id,
            "created_after": one_month_ago
        }
    )
    
    two_months_ago = current_date - datetime.timedelta(days=60)
    previous_month_group_buys = group_buy.count(
        db,
        filters={
            "organizer_id": current_user.id,
            "created_after": two_months_ago,
            "created_before": one_month_ago
        }
    )
    
    last_month_growth = 0
    if previous_month_group_buys > 0:
        last_month_growth = ((current_month_group_buys - previous_month_group_buys) / previous_month_group_buys) * 100
    
    stats = {
        "activeGroupBuys": active_group_buys,
        "totalParticipants": total_participants,
        "totalAmount": total_amount,
        "completedGroupBuys": completed_group_buys,
        "lastMonthGrowth": round(last_month_growth, 2)
    }
    
    # Cache the stats for 15 minutes
    await redis.set(stats_key, json.dumps(stats), ex=900)
    print(f"Возвращаемые данные stats: {stats}")
    return stats


@router.get("/notifications", response_model=List[NotificationResponse])
async def get_notifications(
    *,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_organizer),
    limit: int = Query(10, ge=1, le=50)
):
    """
    Get organizer notifications
    """
    # Import the GroupBuy model directly
    from app.models.group_buy import GroupBuy
    from datetime import datetime, timedelta
    
    # Check if notifications are cached
    redis = await get_redis_client()
    notifications_key = f"user:{current_user.id}:notifications"
    cached_notifications = await redis.get(notifications_key)
    
    if cached_notifications:
        try:
            return json.loads(cached_notifications)
        except json.JSONDecodeError:
            # If cache is corrupted, regenerate notifications
            pass
    
    # Get recent activity for the organizer's group buys
    notifications = []
    
    # 1. Get recent order notifications
    recent_orders = db.query(order.Order).join(
        GroupBuy, order.Order.group_buy_id == GroupBuy.id
    ).filter(
        GroupBuy.organizer_id == current_user.id
    ).order_by(desc(order.Order.created_at)).limit(5).all()
    
    for recent_order in recent_orders:
        related_group_buy = group_buy.get(db, id=recent_order.group_buy_id)
        notifications.append({
            "id": f"order_{recent_order.id}",
            "message": f"Новый заказ в закупке \"{related_group_buy.title}\"",
            "type": "info",
            "date": recent_order.created_at.strftime("%d.%m.%Y")
        })
    
    # 2. Get upcoming deadlines
    now = datetime.now()
    upcoming_deadlines = db.query(GroupBuy).filter(
        GroupBuy.organizer_id == current_user.id,
        GroupBuy.status == GroupBuyStatus.active,
        # Using properly imported datetime
        GroupBuy.end_date <= now + timedelta(days=3)
    ).order_by(GroupBuy.end_date).limit(3).all()
    
    for deadline_group_buy in upcoming_deadlines:
        days_left = (deadline_group_buy.end_date - now).days
        notifications.append({
            "id": f"deadline_{deadline_group_buy.id}",
            "message": f"Срок оплаты закупки \"{deadline_group_buy.title}\" истекает через {days_left} дней",
            "type": "warning",
            "date": now.strftime("%d.%m.%Y")
        })
    
    # 3. Get recently completed group buys
    completed_group_buys = db.query(GroupBuy).filter(
        GroupBuy.organizer_id == current_user.id,
        GroupBuy.status == GroupBuyStatus.completed,
    ).order_by(desc(GroupBuy.updated_at)).limit(3).all()
    
    for completed in completed_group_buys:
        notifications.append({
            "id": f"completed_{completed.id}",
            "message": f"Закупка \"{completed.title}\" успешно завершена",
            "type": "success",
            "date": completed.updated_at.strftime("%d.%m.%Y")
        })
    
    # Sort by date (newest first) and limit
    notifications.sort(key=lambda x: datetime.strptime(x["date"], "%d.%m.%Y"), reverse=True)
    notifications = notifications[:limit]
    
    # Cache notifications for 15 minutes
    await redis.set(notifications_key, json.dumps(notifications), ex=900)
    
    return notifications

# Updated get_group_buys to include pagination and better filtering
@router.get("/", response_model=List[GroupBuyResponse])
def get_group_buys(
    *,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    status: Optional[GroupBuyStatus] = None,
    category: Optional[GroupBuyCategory] = None,
    organizer_id: Optional[int] = None,
    search: Optional[str] = None,
    sort_by: Optional[str] = "created_at",
    sort_order: Optional[str] = "desc"
):
    """
    Get all group buys with optional filters and sorting
    """
    filters = {}
    
    if status:
        filters["status"] = status
    
    if category:
        filters["category"] = category
    
    if organizer_id:
        filters["organizer_id"] = organizer_id
    
    if search:
        filters["search"] = search
    
    # Set sort parameters
    sort_params = {
        "sort_by": sort_by,
        "sort_order": sort_order
    }
    
    # Проверяем роли пользователя
    if any(role.role in ["organizer", "admin", "super_admin"] for role in current_user.roles):
        items = group_buy.get_multi(db, skip=skip, limit=limit, filters=filters, **sort_params)
    else:
        # Regular users can only see active and visible group buys
        filters["is_visible"] = True
        filters["active_only"] = True
        items = group_buy.get_multi(db, skip=skip, limit=limit, filters=filters, **sort_params)
    
    # Явно преобразуем все объекты модели в словари и устанавливаем значения по умолчанию
    result = []
    for item in items:
        # Преобразуем в словарь
        item_dict = {
            "id": item.id,
            "title": item.title,
            "description": item.description,
            "category": item.category,
            "supplier": item.supplier,
            "min_order_amount": item.min_order_amount,
            "end_date": item.end_date,
            "fee_percent": item.fee_percent,
            "delivery_time": 21 if item.delivery_time is None else item.delivery_time,
            "delivery_location": "Новосибирск" if item.delivery_location is None else item.delivery_location,
            "transportation_cost": item.transportation_cost,
            "participation_terms": item.participation_terms,
            "image_url": item.image_url,
            "allow_partial_purchase": item.allow_partial_purchase,
            "is_visible": item.is_visible,
            "status": item.status,
            "organizer_id": item.organizer_id,
            "created_at": item.created_at,
            "updated_at": item.updated_at,
            "total_participants": item.total_participants,
            "total_amount": item.total_amount
        }
        result.append(item_dict)
    
    return result

# New endpoint for group buy export
@router.get("/export")
async def export_group_buys(
    *,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_organizer),
    format: str = Query("csv", regex="^(csv|xlsx)$")
):
    """
    Export group buys data as CSV or Excel
    """
    # Get all group buys for the organizer
    user_group_buys = group_buy.get_multi(
        db, 
        filters={"organizer_id": current_user.id},
        limit=1000  # Reasonable limit for export
    )
    
    # Prepare data for export
    export_data = []
    for gb in user_group_buys:
        # Get participant count
        participant_count = db.query(func.count(order.Order.id)).filter(
            order.Order.group_buy_id == gb.id
        ).scalar() or 0
        
        # Get total amount
        total_amount = db.query(func.sum(order.Order.total_amount)).filter(
            order.Order.group_buy_id == gb.id
        ).scalar() or 0
        
        # Calculate progress (based on participants or amount targets if available)
        # For simplicity, we'll use a placeholder calculation
        progress = 0
        if hasattr(gb, 'target_participants') and gb.target_participants > 0:
            progress = min(100, int((participant_count / gb.target_participants) * 100))
        elif hasattr(gb, 'target_amount') and gb.target_amount > 0:
            progress = min(100, int((total_amount / gb.target_amount) * 100))
        
        # Add to export data
        export_data.append({
            "id": gb.id,
            "title": gb.title,
            "status": gb.status,
            "participants": participant_count,
            "amount": total_amount,
            "deadline": gb.end_date.strftime("%d.%m.%Y") if hasattr(gb, 'end_date') and gb.end_date else "",
            "progress": progress,
            "created_at": gb.created_at.strftime("%d.%m.%Y"),
            "category": gb.category
        })
    
    # Generate file based on format
    from fastapi.responses import StreamingResponse
    import io
    import csv
    
    if format == "csv":
        output = io.StringIO()
        fieldnames = export_data[0].keys() if export_data else []
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(export_data)
        
        output.seek(0)
        
        return StreamingResponse(
            io.StringIO(output.getvalue()),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=group_buys_export_{datetime.datetime.now().strftime('%Y%m%d')}.csv"}
        )
    else:  # xlsx
        try:
            import openpyxl
            from openpyxl import Workbook
            
            wb = Workbook()
            ws = wb.active
            ws.title = "Group Buys"
            
            # Add headers
            if export_data:
                headers = list(export_data[0].keys())
                ws.append(headers)
                
                # Add data rows
                for data_row in export_data:
                    ws.append([data_row[header] for header in headers])
            
            # Save to BytesIO
            output = io.BytesIO()
            wb.save(output)
            output.seek(0)
            
            return StreamingResponse(
                output,
                media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                headers={"Content-Disposition": f"attachment; filename=group_buys_export_{datetime.datetime.now().strftime('%Y%m%d')}.xlsx"}
            )
        except ImportError:
            # Fallback to CSV if openpyxl not available
            return HTTPException(
                status_code=status.HTTP_501_NOT_IMPLEMENTED,
                detail="Excel export is not available. Please use CSV format instead."
            )

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
        "fee_percent": new_group_buy.fee_percent,
        "delivery_time": new_group_buy.delivery_time,
        "delivery_location": new_group_buy.delivery_location,
        "transportation_cost": new_group_buy.transportation_cost,
        "participation_terms": new_group_buy.participation_terms,
        "image_url": new_group_buy.image_url,
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
    await redis.delete(group_buy_key)  # Delete old cache
    
    # Update active_group_buys set
    if updated_group_buy.is_visible and updated_group_buy.status == GroupBuyStatus.active:
        await redis.sadd("active_group_buys", updated_group_buy.id)
    else:
        await redis.srem("active_group_buys", updated_group_buy.id)
    
    return updated_group_buy


@router.delete("/{group_buy_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_group_buy(
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
    is_admin = any(r.role in ["admin", "super_admin"] for r in current_user.roles)
    is_organizer = db_group_buy.organizer_id == current_user.id
    
    if not (is_admin or is_organizer):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to delete this group buy"
        )
    
    # Delete from DB
    group_buy.delete(db=db, id=group_buy_id)
    
    # Delete from Redis
    redis = await get_redis_client()
    await redis.delete(f"group_buy:{group_buy_id}")
    await redis.srem("active_group_buys", group_buy_id)
    await redis.srem(f"user:{db_group_buy.organizer_id}:group_buys", group_buy_id)
    
    # Delete associated products from Redis
    product_ids = await redis.smembers(f"group_buy:{group_buy_id}:products")
    for product_id in product_ids:
        await redis.delete(f"product:{product_id}")
    
    await redis.delete(f"group_buy:{group_buy_id}:products")
    
    return None


@router.get("/{group_buy_id}/participants")
def get_participants(
    *,
    db: Session = Depends(get_db),
    group_buy_id: int = Path(..., title="The ID of the group buy"),
    current_user: User = Depends(get_current_user),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
):
    """
    Get all participants of a specific group buy
    """
    from app.models.group_buy import Order, OrderStatus
    
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
            detail="You don't have permission to view participants of this group buy"
        )
    
    # Get all users who have placed orders in this group buy
    # We include only orders that have been paid or completed
    orders = db.query(Order).filter(
        Order.group_buy_id == group_buy_id,
        Order.status.in_([OrderStatus.paid, OrderStatus.completed])
    ).offset(skip).limit(limit).all()
    
    # Format the response
    participants = []
    for order in orders:
        user = order.user
        
        # Format name and avatar
        avatar = user.image if hasattr(user, 'image') else None
        
        participant_data = {
            "id": str(user.id),
            "name": user.name,
            "avatar": avatar,
            "quantity": sum(item.quantity for item in order.items),
            "amount": order.total_amount,
            "isPaid": order.status in [OrderStatus.paid, OrderStatus.completed]
        }
        
        participants.append(participant_data)
    
    return participants

# ========== Product Routes ==========

@router.post("/{group_buy_id}/products", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
async def create_product(
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
    is_admin = any(r.role in ["admin", "super_admin"] for r in current_user.roles)
    is_organizer = db_group_buy.organizer_id == current_user.id
    
    if not (is_admin or is_organizer):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to add products to this group buy"
        )
    
    # Create product - using the imported product module, not itertools.product
    new_product = product.create(db=db, obj_in=product_in, group_buy_id=group_buy_id)
    
    # Calculate price with fee for caching
    fee_percent = db_group_buy.fee_percent
    price_with_fee = round(new_product.price * (1 + fee_percent / 100), 2)
    
    # Cache in Redis
    redis = await get_redis_client()
    product_key = f"product:{new_product.id}"
    product_data = {
        "id": new_product.id,
        "name": new_product.name,
        "price": new_product.price,
        "price_with_fee": price_with_fee,
        "fee_percent": fee_percent,
        "group_buy_id": new_product.group_buy_id,
        "created_at": new_product.created_at.isoformat(),
    }
    await redis.set(product_key, json.dumps(product_data), ex=3600)  # 1 hour cache
    
    # Add to group buy's products set
    await redis.sadd(f"group_buy:{group_buy_id}:products", new_product.id)
    
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
        is_admin = any(r.role in ["admin", "super_admin"] for r in current_user.roles)
        is_organizer = db_group_buy.organizer_id == current_user.id
        
        if not (is_admin or is_organizer):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to view products in this group buy"
            )
    
    products = product.get_multi(db=db, group_buy_id=group_buy_id, skip=skip, limit=limit)
    
    # Add price_with_fee to each product if not already calculated
    for p in products:
        if not hasattr(p, 'price_with_fee') or p.price_with_fee is None:
            p.price_with_fee = round(p.price * (1 + db_group_buy.fee_percent / 100), 2)
    
    return products


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
        is_admin = any(r.role in ["admin", "super_admin"] for r in current_user.roles)
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
    
    # Calculate price with fee if not already calculated
    if not hasattr(db_product, 'price_with_fee') or db_product.price_with_fee is None:
        db_product.price_with_fee = round(db_product.price * (1 + db_group_buy.fee_percent / 100), 2)
    
    return db_product


@router.put("/{group_buy_id}/products/{product_id}", response_model=ProductResponse)
async def update_product(
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
    is_admin = any(r.role in ["admin", "super_admin"] for r in current_user.roles)
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
    
    # Calculate price with fee
    updated_product.price_with_fee = round(updated_product.price * (1 + db_group_buy.fee_percent / 100), 2)
    
    # Update Redis cache
    redis = await get_redis_client()
    await redis.delete(f"product:{product_id}")
    
    return updated_product


@router.delete("/{group_buy_id}/products/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_product(
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
    is_admin = any(r.role in ["admin", "super_admin"] for r in current_user.roles)
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
    
    # Delete from Redis
    redis = await get_redis_client()
    await redis.delete(f"product:{product_id}")
    await redis.srem(f"group_buy:{group_buy_id}:products", product_id)
    
    return None
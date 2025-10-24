# app/crud/group_buy.py

from typing import Any, Dict, Optional, List, Union
from sqlalchemy.orm import Session
from sqlalchemy import desc, func, and_, or_
from fastapi.encoders import jsonable_encoder

from app.models.group_buy import GroupBuy, OrderItem, Product, Order, GroupBuyStatus
from app.schemas.group_buy import GroupBuyCreate, GroupBuyUpdate, ProductCreate, ProductUpdate



class GroupBuyCRUD:
    def __init__(self):
        # Define the model attribute to fix the error
        self.model = GroupBuy

    def get(self, db: Session, id: int) -> Optional[GroupBuy]:
        return db.query(GroupBuy).filter(GroupBuy.id == id).first()
    
    def get_multi(
        self, 
        db: Session, 
        *, 
        skip: int = 0, 
        limit: int = 100,
        filters: Optional[Dict[str, Any]] = None,
        sort_by: str = "created_at",
        sort_order: str = "desc"
    ) -> List[GroupBuy]:
        """
        Get multiple group buys with filtering and sorting
        """
        query = db.query(self.model)
        
        # Apply filters
        if filters:
            if "organizer_id" in filters:
                query = query.filter(self.model.organizer_id == filters["organizer_id"])
                
            if "status" in filters:
                query = query.filter(self.model.status == filters["status"])
                
            if "category" in filters:
                query = query.filter(self.model.category == filters["category"])
                
            if "is_visible" in filters:
                query = query.filter(self.model.is_visible == filters["is_visible"])
                
            if "active_only" in filters:
                query = query.filter(self.model.status.in_(["active", "collecting", "payment", "ordered"]))
                
            if "search" in filters and filters["search"]:
                search_term = f"%{filters['search']}%"
                query = query.filter(
                    or_(
                        self.model.title.ilike(search_term),
                        self.model.description.ilike(search_term)
                    )
                )
                
            if "created_after" in filters:
                query = query.filter(self.model.created_at >= filters["created_after"])
                
            if "created_before" in filters:
                query = query.filter(self.model.created_at <= filters["created_before"])
        
        # Apply sorting
        if sort_order.lower() == "desc":
            query = query.order_by(desc(getattr(self.model, sort_by)))
        else:
            query = query.order_by(getattr(self.model, sort_by))
            
        # Apply pagination
        query = query.offset(skip).limit(limit)
        
        # Get results
        return query.all()
    
    
    def count(
        self, 
        db: Session, 
        *,
        filters: Optional[Dict[str, Any]] = None
    ) -> int:
        """
        Count group buys with filtering
        """
        query = db.query(func.count(self.model.id))
        
        # Apply filters
        if filters:
            if "organizer_id" in filters:
                query = query.filter(self.model.organizer_id == filters["organizer_id"])
                
            if "status" in filters:
                query = query.filter(self.model.status == filters["status"])
                
            if "category" in filters:
                query = query.filter(self.model.category == filters["category"])
                
            if "is_visible" in filters:
                query = query.filter(self.model.is_visible == filters["is_visible"])
                
            if "active_only" in filters:
                query = query.filter(self.model.status.in_(["active", "collecting", "payment", "ordered"]))
                
            if "created_after" in filters:
                query = query.filter(self.model.created_at >= filters["created_after"])
                
            if "created_before" in filters:
                query = query.filter(self.model.created_at <= filters["created_before"])
        
        return query.scalar() or 0
    
    def get_with_products_count(self, db: Session, id: int) -> Optional[Dict]:
        # Get group buy with joined product count
        result = db.query(
            GroupBuy,
            func.count(Product.id).label("products_count")
        ).outerjoin(
            Product, Product.group_buy_id == GroupBuy.id
        ).filter(
            GroupBuy.id == id
        ).group_by(
            GroupBuy.id
        ).first()
        
        if not result:
            return None
        
        # Unpack result
        db_group_buy, products_count = result
        
        # Convert to dict and add products count
        group_buy_data = jsonable_encoder(db_group_buy)
        group_buy_data["products_count"] = products_count
        
        return group_buy_data
    
    def create(self, db: Session, *, obj_in: GroupBuyCreate, organizer_id: int) -> GroupBuy:
        obj_in_data = jsonable_encoder(obj_in)
        db_obj = GroupBuy(**obj_in_data, organizer_id=organizer_id)
        
        # If is_visible is True, set status to active
        if db_obj.is_visible:
            db_obj.status = GroupBuyStatus.active
        
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj
    
    def update(
        self, 
        db: Session, 
        *, 
        db_obj: GroupBuy,
        obj_in: Union[GroupBuyUpdate, Dict[str, Any]]
    ) -> GroupBuy:
        obj_data = jsonable_encoder(db_obj)
        
        if isinstance(obj_in, dict):
            update_data = obj_in
        else:
            update_data = obj_in.dict(exclude_unset=True)
        
        for field in obj_data:
            if field in update_data:
                setattr(db_obj, field, update_data[field])
        
        # If is_visible is updated to True and status is draft, set status to active
        if "is_visible" in update_data and update_data["is_visible"] and db_obj.status == GroupBuyStatus.draft:
            db_obj.status = GroupBuyStatus.active
        
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj
    
    def delete(self, db: Session, *, id: int) -> bool:
        obj = db.query(GroupBuy).get(id)
        if not obj:
            return False
        
        db.delete(obj)
        db.commit()
        return True



class ProductCRUD:
    def __init__(self):
        # Define the model attribute
        self.model = Product
        
    def get(self, db: Session, id: int) -> Optional[Product]:
        return db.query(Product).filter(Product.id == id).first()
    
    def get_multi(
        self, 
        db: Session, 
        *, 
        skip: int = 0, 
        limit: int = 100,
        group_buy_id: Optional[int] = None
    ) -> List[Product]:
        query = db.query(Product)
        
        if group_buy_id:
            query = query.filter(Product.group_buy_id == group_buy_id)
        
        return query.offset(skip).limit(limit).all()
    
    def create(self, db: Session, *, obj_in: ProductCreate, group_buy_id: int) -> Product:
        obj_in_data = jsonable_encoder(obj_in)
        db_obj = Product(**obj_in_data, group_buy_id=group_buy_id)
        
        # Get the group buy to access fee_percent
        db_group_buy = db.query(GroupBuy).filter(GroupBuy.id == group_buy_id).first()
        
        # Calculate price with fee
        if db_group_buy:
            # We don't store this in the DB, it will be calculated on demand
            db_obj.price_with_fee = round(db_obj.price * (1 + db_group_buy.fee_percent / 100), 2)
        
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj
    
    def update(
        self, 
        db: Session, 
        *, 
        db_obj: Product,
        obj_in: Union[ProductUpdate, Dict[str, Any]]
    ) -> Product:
        obj_data = jsonable_encoder(db_obj)
        
        if isinstance(obj_in, dict):
            update_data = obj_in
        else:
            update_data = obj_in.dict(exclude_unset=True)
        
        for field in obj_data:
            if field in update_data:
                setattr(db_obj, field, update_data[field])
        
        # Get the group buy to access fee_percent for recalculation
        db_group_buy = db.query(GroupBuy).filter(GroupBuy.id == db_obj.group_buy_id).first()
        
        # Recalculate price with fee if price was updated or group_buy was found
        if ("price" in update_data or not hasattr(db_obj, 'price_with_fee')) and db_group_buy:
            db_obj.price_with_fee = round(db_obj.price * (1 + db_group_buy.fee_percent / 100), 2)
        
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj
    
    def delete(self, db: Session, *, id: int) -> bool:
        obj = db.query(Product).get(id)
        if not obj:
            return False
        
        db.delete(obj)
        db.commit()
        return True
    


class ParticipantCRUD:
    def get_participants(
        self,
        db: Session,
        *,
        group_buy_id: int,
        skip: int = 0,
        limit: int = 100
    ) -> List[Dict]:
        """
        Get participants for a specific group buy
        """
        from app.models.group_buy import Order, OrderStatus
        from app.models.user import User
        
        # Query orders with users for this group buy
        orders_with_users = (
            db.query(Order, User)
            .join(User, Order.user_id == User.id)
            .filter(
                Order.group_buy_id == group_buy_id,
                Order.status.in_([OrderStatus.paid, OrderStatus.completed])
            )
            .offset(skip)
            .limit(limit)
            .all()
        )
        
        # Format the response
        participants = []
        for order, user in orders_with_users:
            # Calculate total quantity from order items
            total_quantity = db.query(func.sum(OrderItem.quantity)).filter(
                OrderItem.order_id == order.id
            ).scalar() or 0
            
            participant_data = {
                "id": str(user.id),
                "name": user.name,
                "avatar": user.image if hasattr(user, 'image') and user.image else None,
                "quantity": total_quantity,
                "amount": order.total_amount,
                "isPaid": order.status in [OrderStatus.paid, OrderStatus.completed]
            }
            
            participants.append(participant_data)
        
        return participants
    
    def count_participants(
        self,
        db: Session,
        *,
        group_buy_id: int
    ) -> int:
        """
        Count participants for a specific group buy
        """
        from app.models.group_buy import Order, OrderStatus
        
        # Count unique users with paid or completed orders
        participant_count = (
            db.query(func.count(func.distinct(Order.user_id)))
            .filter(
                Order.group_buy_id == group_buy_id,
                Order.status.in_([OrderStatus.paid, OrderStatus.completed])
            )
            .scalar()
        ) or 0
        
        return participant_count

# Create instance
participant = ParticipantCRUD()
group_buy = GroupBuyCRUD()
product = ProductCRUD()
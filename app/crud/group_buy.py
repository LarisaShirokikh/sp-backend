# app/crud/group_buy.py
from typing import List, Optional, Dict, Any, Union
from sqlalchemy.orm import Session
from sqlalchemy import func
from fastapi.encoders import jsonable_encoder
from datetime import datetime

from app.models.group_buy import GroupBuy, Product, Order, OrderItem
from app.models.group_buy import GroupBuyStatus
from app.schemas.group_buy import GroupBuyCreate, GroupBuyUpdate, ProductCreate, ProductUpdate


class GroupBuyCRUD:
    """CRUD operations for GroupBuy"""
    
    def create(self, db: Session, *, obj_in: GroupBuyCreate, organizer_id: int) -> GroupBuy:
        """Create a new group buy"""
        obj_in_data = jsonable_encoder(obj_in)
        db_obj = GroupBuy(
            **obj_in_data,
            organizer_id=organizer_id,
            status=GroupBuyStatus.active if obj_in.is_visible else GroupBuyStatus.draft
        )
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        
        # Cache in Redis
        self._cache_group_buy(db_obj)
        
        return db_obj
    
    def get(self, db: Session, id: int) -> Optional[GroupBuy]:
        """Get a group buy by ID"""
        return db.query(GroupBuy).filter(GroupBuy.id == id).first()
    
    def get_multi(
        self, db: Session, *, skip: int = 0, limit: int = 100, 
        filters: Optional[Dict[str, Any]] = None
    ) -> List[GroupBuy]:
        """Get multiple group buys with optional filters"""
        query = db.query(GroupBuy)
        
        if filters:
            if filters.get("organizer_id"):
                query = query.filter(GroupBuy.organizer_id == filters["organizer_id"])
            
            if filters.get("status"):
                query = query.filter(GroupBuy.status == filters["status"])
            
            if filters.get("category"):
                query = query.filter(GroupBuy.category == filters["category"])
            
            if filters.get("is_visible") is not None:
                query = query.filter(GroupBuy.is_visible == filters["is_visible"])
            
            if filters.get("active_only"):
                query = query.filter(
                    GroupBuy.status == GroupBuyStatus.active,
                    GroupBuy.is_visible == True,
                    GroupBuy.end_date > datetime.now(datetime.timezone.utc)
                )
        
        return query.order_by(GroupBuy.created_at.desc()).offset(skip).limit(limit).all()
    
    def update(
        self, db: Session, *, db_obj: GroupBuy, obj_in: Union[GroupBuyUpdate, Dict[str, Any]]
    ) -> GroupBuy:
        """Update a group buy"""
        obj_data = jsonable_encoder(db_obj)
        
        if isinstance(obj_in, dict):
            update_data = obj_in
        else:
            update_data = obj_in.dict(exclude_unset=True)
        
        for field in obj_data:
            if field in update_data:
                setattr(db_obj, field, update_data[field])
        
        db_obj.updated_at = datetime.now(datetime.timezone.utc)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        
        # Update cache in Redis
        self._cache_group_buy(db_obj)
        
        return db_obj
    
    def delete(self, db: Session, *, id: int) -> bool:
        """Delete a group buy"""
        obj = db.query(GroupBuy).get(id)
        if not obj:
            return False
        
        # Delete from Redis cache
        self._remove_from_cache(obj.id)
        
        db.delete(obj)
        db.commit()
        return True
    
    def get_by_organizer(
        self, db: Session, *, organizer_id: int, skip: int = 0, limit: int = 100
    ) -> List[GroupBuy]:
        """Get group buys by organizer ID"""
        return (
            db.query(GroupBuy)
            .filter(GroupBuy.organizer_id == organizer_id)
            .order_by(GroupBuy.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )
    
    def get_active(self, db: Session, *, skip: int = 0, limit: int = 100) -> List[GroupBuy]:
        """Get active and visible group buys"""
        return (
            db.query(GroupBuy)
            .filter(
                GroupBuy.status == GroupBuyStatus.active,
                GroupBuy.is_visible == True,
                GroupBuy.end_date > datetime.utcnow()
            )
            .order_by(GroupBuy.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )
    
    def get_with_products_count(self, db: Session, id: int) -> Optional[Dict[str, Any]]:
        """Get a group buy with products count"""
        result = (
            db.query(
                GroupBuy,
                func.count(Product.id).label("products_count")
            )
            .outerjoin(Product, GroupBuy.id == Product.group_buy_id)
            .filter(GroupBuy.id == id)
            .group_by(GroupBuy.id)
            .first()
        )
        
        if not result:
            return None
        
        group_buy, products_count = result
        group_buy_data = jsonable_encoder(group_buy)
        group_buy_data["products_count"] = products_count
        
        return group_buy_data
    
    def _cache_group_buy(self, group_buy: GroupBuy) -> None:
        """Cache group buy in Redis (implement this method based on your Redis setup)"""
        # This would be implemented with your Redis client
        # Example:
        # redis_client.set(
        #     f"group_buy:{group_buy.id}",
        #     json.dumps(jsonable_encoder(group_buy)),
        #     ex=3600  # expire in 1 hour
        # )
        pass
    
    def _remove_from_cache(self, group_buy_id: int) -> None:
        """Remove group buy from Redis cache"""
        # This would be implemented with your Redis client
        # Example:
        # redis_client.delete(f"group_buy:{group_buy_id}")
        pass


class ProductCRUD:
    """CRUD operations for Product"""
    
    def create(self, db: Session, *, obj_in: ProductCreate, group_buy_id: int) -> Product:
        """Create a new product"""
        obj_in_data = jsonable_encoder(obj_in)
        db_obj = Product(**obj_in_data, group_buy_id=group_buy_id)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj
    
    def get(self, db: Session, id: int) -> Optional[Product]:
        """Get a product by ID"""
        return db.query(Product).filter(Product.id == id).first()
    
    def get_multi(
        self, db: Session, *, group_buy_id: int, skip: int = 0, limit: int = 100
    ) -> List[Product]:
        """Get multiple products by group buy ID"""
        return (
            db.query(Product)
            .filter(Product.group_buy_id == group_buy_id)
            .offset(skip)
            .limit(limit)
            .all()
        )
    
    def update(
        self, db: Session, *, db_obj: Product, obj_in: Union[ProductUpdate, Dict[str, Any]]
    ) -> Product:
        """Update a product"""
        obj_data = jsonable_encoder(db_obj)
        
        if isinstance(obj_in, dict):
            update_data = obj_in
        else:
            update_data = obj_in.dict(exclude_unset=True)
        
        for field in obj_data:
            if field in update_data:
                setattr(db_obj, field, update_data[field])
        
        db_obj.updated_at = datetime.utcnow()
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj
    
    def delete(self, db: Session, *, id: int) -> bool:
        """Delete a product"""
        obj = db.query(Product).get(id)
        if not obj:
            return False
        db.delete(obj)
        db.commit()
        return True


class OrderCRUD:
    """CRUD operations for Order"""
    
    def create_or_update_cart(
        self, db: Session, *, user_id: int, group_buy_id: int, product_id: int, quantity: int
    ) -> Order:
        """Create a new order or update cart"""
        # Check if user already has a cart for this group buy
        order = (
            db.query(Order)
            .filter(
                Order.user_id == user_id,
                Order.group_buy_id == group_buy_id,
                Order.status == "cart"
            )
            .first()
        )
        
        # If no cart exists, create one
        if not order:
            order = Order(
                user_id=user_id,
                group_buy_id=group_buy_id,
                status="cart"
            )
            db.add(order)
            db.commit()
            db.refresh(order)
        
        # Check if the product is already in the cart
        order_item = (
            db.query(OrderItem)
            .filter(
                OrderItem.order_id == order.id,
                OrderItem.product_id == product_id
            )
            .first()
        )
        
        # Get product info for price
        product = db.query(Product).get(product_id)
        if not product:
            raise ValueError("Product not found")
        
        # If product already in cart, update quantity
        if order_item:
            if quantity <= 0:
                # Remove item if quantity is 0 or negative
                db.delete(order_item)
            else:
                order_item.quantity = quantity
                order_item.price = product.price
                db.add(order_item)
        else:
            # Add new item to cart
            if quantity > 0:
                order_item = OrderItem(
                    order_id=order.id,
                    product_id=product_id,
                    quantity=quantity,
                    price=product.price
                )
                db.add(order_item)
        
        # Recalculate order total
        self._recalculate_order_total(db, order)
        
        return order
    
    def get_user_orders(
        self, db: Session, *, user_id: int, skip: int = 0, limit: int = 100
    ) -> List[Order]:
        """Get orders by user ID"""
        return (
            db.query(Order)
            .filter(Order.user_id == user_id)
            .order_by(Order.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )
    
    def get_group_buy_orders(
        self, db: Session, *, group_buy_id: int, skip: int = 0, limit: int = 100
    ) -> List[Order]:
        """Get orders by group buy ID"""
        return (
            db.query(Order)
            .filter(Order.group_buy_id == group_buy_id)
            .order_by(Order.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )
    
    def _recalculate_order_total(self, db: Session, order: Order) -> None:
        """Recalculate order total"""
        total = db.query(func.sum(OrderItem.price * OrderItem.quantity)).filter(
            OrderItem.order_id == order.id
        ).scalar() or 0.0
        
        order.total_amount = total
        order.updated_at = datetime.utcnow()
        db.add(order)
        db.commit()
        db.refresh(order)


# Create instances for exports
group_buy = GroupBuyCRUD()
product = ProductCRUD()
order = OrderCRUD()
# app/crud/group_buy.py

from typing import Any, Dict, Optional, List, Union
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
from fastapi.encoders import jsonable_encoder

from app.models.group_buy import GroupBuy, Product, Order, GroupBuyStatus
from app.schemas.group_buy import GroupBuyCreate, GroupBuyUpdate, ProductCreate, ProductUpdate


# ========== GroupBuy CRUD ==========

class GroupBuyCRUD:
    def get(self, db: Session, id: int) -> Optional[GroupBuy]:
        return db.query(GroupBuy).filter(GroupBuy.id == id).first()
    
    def get_multi(
        self, 
        db: Session, 
        *, 
        skip: int = 0, 
        limit: int = 100,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[GroupBuy]:
        filters = filters or {}
        query = db.query(GroupBuy)
        
        # Apply filters
        if filters.get("category"):
            query = query.filter(GroupBuy.category == filters["category"])
        
        if filters.get("status"):
            query = query.filter(GroupBuy.status == filters["status"])
        
        if filters.get("organizer_id"):
            query = query.filter(GroupBuy.organizer_id == filters["organizer_id"])
        
        if filters.get("is_visible") is not None:
            query = query.filter(GroupBuy.is_visible == filters["is_visible"])
        
        if filters.get("active_only"):
            query = query.filter(GroupBuy.status == GroupBuyStatus.active)
        
        return query.offset(skip).limit(limit).all()
    
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


# ========== Product CRUD ==========

class ProductCRUD:
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


# Create instances
group_buy = GroupBuyCRUD()
product = ProductCRUD()
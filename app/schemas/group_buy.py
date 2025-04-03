# app/schemas/group_buy.py
from pydantic import BaseModel, Field, validator
from typing import Optional, List
from datetime import datetime
from app.models.group_buy import GroupBuyStatus, GroupBuyCategory


# ========== GroupBuy Schemas ==========
class GroupBuyBase(BaseModel):
    """Базовая схема групповой закупки"""
    title: str
    description: Optional[str] = None
    category: Optional[GroupBuyCategory] = GroupBuyCategory.other
    supplier: str
    min_order_amount: float = Field(default=5000.0, ge=0)
    end_date: datetime
    fee_percent: float = Field(default=5.0, ge=0, le=25.0)
    allow_partial_purchase: bool = True
    is_visible: bool = True


class GroupBuyCreate(GroupBuyBase):
    """Схема для создания групповой закупки"""
    pass


class GroupBuyUpdate(BaseModel):
    """Схема для обновления групповой закупки"""
    title: Optional[str] = None
    description: Optional[str] = None
    category: Optional[GroupBuyCategory] = None
    supplier: Optional[str] = None
    min_order_amount: Optional[float] = Field(default=None, ge=0)
    end_date: Optional[datetime] = None
    fee_percent: Optional[float] = Field(default=None, ge=0, le=25.0)
    allow_partial_purchase: Optional[bool] = None
    is_visible: Optional[bool] = None
    status: Optional[GroupBuyStatus] = None


class GroupBuyResponse(GroupBuyBase):
    """Схема для ответа о групповой закупке"""
    id: int
    organizer_id: int
    status: GroupBuyStatus
    created_at: datetime
    updated_at: datetime
    total_participants: int = 0
    total_amount: float = 0.0
    
    class Config:
        orm_mode = True


class GroupBuyDetailResponse(GroupBuyResponse):
    """Схема для детального ответа о групповой закупке"""
    products_count: int = 0
    
    class Config:
        orm_mode = True


# ========== Product Schemas ==========
class ProductBase(BaseModel):
    """Базовая схема продукта"""
    name: str
    description: Optional[str] = None
    price: float = Field(..., gt=0)
    image_url: Optional[str] = None
    vendor: Optional[str] = None
    vendor_code: Optional[str] = None
    available: bool = True


class ProductCreate(ProductBase):
    """Схема для создания продукта"""
    pass


class ProductUpdate(BaseModel):
    """Схема для обновления продукта"""
    name: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = Field(default=None, gt=0)
    image_url: Optional[str] = None
    vendor: Optional[str] = None
    vendor_code: Optional[str] = None
    available: Optional[bool] = None


class ProductResponse(ProductBase):
    """Схема для ответа о продукте"""
    id: int
    group_buy_id: int
    created_at: datetime
    updated_at: datetime
    quantity_ordered: int = 0
    
    class Config:
        orm_mode = True


# ========== Order Schemas ==========
class OrderItemCreate(BaseModel):
    """Схема для создания элемента заказа"""
    product_id: int
    quantity: int = Field(..., gt=0)


class OrderItemResponse(BaseModel):
    """Схема для ответа о элементе заказа"""
    id: int
    product_id: int
    quantity: int
    price: float
    product: ProductResponse
    
    class Config:
        orm_mode = True


class OrderCreate(BaseModel):
    """Схема для создания заказа"""
    group_buy_id: int
    items: List[OrderItemCreate]


class OrderUpdate(BaseModel):
    """Схема для обновления заказа"""
    status: Optional[str] = None


class OrderResponse(BaseModel):
    """Схема для ответа о заказе"""
    id: int
    user_id: int
    group_buy_id: int
    status: str
    total_amount: float
    created_at: datetime
    updated_at: datetime
    payment_date: Optional[datetime] = None
    completion_date: Optional[datetime] = None
    items: List[OrderItemResponse]
    
    class Config:
        orm_mode = True
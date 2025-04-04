# app/schemas/group_buy.py
from pydantic import BaseModel, Field, field_validator
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
    fee_percent: float = Field(
        default=5.0, 
        ge=0, 
        le=25.0, 
        description="Комиссия организатора в процентах (прибавляется к стоимости товаров)"
    )
    delivery_time: int = Field(default=21, ge=1, description="Ожидаемое время доставки в днях")
    delivery_location: str = "Новосибирск"
    transportation_cost: Optional[str] = None
    participation_terms: Optional[str] = None
    image_url: Optional[str] = None
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
    fee_percent: Optional[float] = Field(
        default=None, 
        ge=0, 
        le=25.0, 
        description="Комиссия организатора в процентах"
    )
    delivery_time: Optional[int] = Field(default=None, ge=1)
    delivery_location: Optional[str] = None
    transportation_cost: Optional[str] = None
    participation_terms: Optional[str] = None
    image_url: Optional[str] = None
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
    
    # Вычисляемое поле для отображения цены с учетом комиссии
    price_with_fee: Optional[float] = None
    
    @field_validator('price_with_fee')
    def calculate_price_with_fee(cls, v, info):
        price = info.data.get('price', 0)
        group_buy_id = info.data.get('group_buy_id')
        
        if price and group_buy_id:
            try:
                # Получаем данные о закупке из контекста
                from app.crud.group_buy import group_buy
                from app.db.session import SessionLocal
                
                with SessionLocal() as db:
                    db_group_buy = group_buy.get(db, id=group_buy_id)
                    if db_group_buy:
                        # Рассчитываем цену с учетом комиссии
                        fee_percent = db_group_buy.fee_percent
                        return round(price * (1 + fee_percent / 100), 2)
            except:
                pass
        return price 

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
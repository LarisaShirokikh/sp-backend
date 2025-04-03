# app/models/group_buy.py
from sqlalchemy import Boolean, Column, Integer, String, Text, Float, ForeignKey, DateTime, Enum
from sqlalchemy.orm import relationship
import enum
from datetime import datetime
from app.models import Base


class GroupBuyStatus(str, enum.Enum):
    draft = "draft"  # Черновик (не опубликован)
    active = "active"  # Активная закупка (принимает заказы)
    collecting = "collecting"  # Сбор средств (оплата заказов)
    ordered = "ordered"  # Заказ размещен у поставщика
    delivered = "delivered"  # Товар получен от поставщика
    distributing = "distributing"  # Раздача участникам
    completed = "completed"  # Закупка завершена
    cancelled = "cancelled"  # Закупка отменена


class GroupBuyCategory(str, enum.Enum):
    clothes = "clothes"  # Одежда и обувь
    home = "home"  # Товары для дома
    kids = "kids"  # Детские товары
    food = "food"  # Продукты питания
    beauty = "beauty"  # Косметика и парфюмерия
    other = "other"  # Другое


class GroupBuy(Base):
    """Модель групповой закупки"""
    __tablename__ = "group_buys"

    title = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    category = Column(Enum(GroupBuyCategory), default=GroupBuyCategory.other)
    supplier = Column(String(255), nullable=False)
    min_order_amount = Column(Float, default=5000.0)
    end_date = Column(DateTime, nullable=False)
    fee_percent = Column(Float, default=5.0)
    allow_partial_purchase = Column(Boolean, default=True)
    is_visible = Column(Boolean, default=True)
    status = Column(Enum(GroupBuyStatus), default=GroupBuyStatus.draft)
    
    # Связь с организатором
    organizer_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    organizer = relationship("User", back_populates="organized_group_buys")
    
    # Связь с продуктами
    products = relationship("Product", back_populates="group_buy", cascade="all, delete-orphan")
    
    # Связь с заказами
    orders = relationship("Order", back_populates="group_buy", cascade="all, delete-orphan")
    
    # Метаданные
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    total_participants = Column(Integer, default=0)
    total_amount = Column(Float, default=0.0)


class Product(Base):
    """Модель товара в закупке"""
    __tablename__ = "products"

    name = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    price = Column(Float, nullable=False)
    image_url = Column(String, nullable=True)
    vendor = Column(String(255), nullable=True)
    vendor_code = Column(String(255), nullable=True)
    available = Column(Boolean, default=True)
    
    # Связь с закупкой
    group_buy_id = Column(Integer, ForeignKey("group_buys.id"), nullable=False)
    group_buy = relationship("GroupBuy", back_populates="products")
    
    # Связь с элементами заказа
    order_items = relationship("OrderItem", back_populates="product")
    
    # Метаданные
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    quantity_ordered = Column(Integer, default=0)


class OrderStatus(str, enum.Enum):
    cart = "cart"  # В корзине
    pending = "pending"  # Ожидает оплаты
    paid = "paid"  # Оплачено
    cancelled = "cancelled"  # Отменено
    completed = "completed"  # Выполнено


class Order(Base):
    """Модель заказа пользователя"""
    __tablename__ = "orders"

    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    group_buy_id = Column(Integer, ForeignKey("group_buys.id"), nullable=False)
    status = Column(Enum(OrderStatus), default=OrderStatus.cart)
    total_amount = Column(Float, default=0.0)
    
    # Связи
    user = relationship("User", back_populates="orders")
    group_buy = relationship("GroupBuy", back_populates="orders")
    items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")
    
    # Метаданные
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    payment_date = Column(DateTime, nullable=True)
    completion_date = Column(DateTime, nullable=True)


class OrderItem(Base):
    """Модель элемента заказа"""
    __tablename__ = "order_items"

    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    quantity = Column(Integer, nullable=False, default=1)
    price = Column(Float, nullable=False)  # Цена на момент заказа
    
    # Связи
    order = relationship("Order", back_populates="items")
    product = relationship("Product", back_populates="order_items")
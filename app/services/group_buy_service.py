# app/services/group_buy_service.py
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models.group_buy import GroupBuy, Product, Order, OrderItem
from app.schemas.group_buy import GroupBuyCreate, GroupBuyUpdate, ProductCreate, OrderCreate
from app.models.user import User
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

# ========== GroupBuy Service Functions ==========

def get_group_buy_by_id(db: Session, group_buy_id: int) -> GroupBuy:
    """Получение закупки по ID"""
    return db.query(GroupBuy).filter(GroupBuy.id == group_buy_id).first()


def get_group_buys(
    db: Session, 
    skip: int = 0, 
    limit: int = 100, 
    category: str = None, 
    status: str = None,
    is_visible: bool = True
):
    """Получение списка закупок с фильтрацией"""
    query = db.query(GroupBuy)
    
    if category:
        query = query.filter(GroupBuy.category == category)
    
    if status:
        query = query.filter(GroupBuy.status == status)
    
    if is_visible is not None:
        query = query.filter(GroupBuy.is_visible == is_visible)
    
    return query.offset(skip).limit(limit).all()


def create_group_buy(db: Session, group_buy: GroupBuyCreate, user_id: int) -> GroupBuy:
    """Создание новой закупки"""
    db_group_buy = GroupBuy(
        title=group_buy.title,
        description=group_buy.description,
        category=group_buy.category,
        supplier=group_buy.supplier,
        min_order_amount=group_buy.min_order_amount,
        end_date=group_buy.end_date,
        fee_percent=group_buy.fee_percent,
        delivery_time=group_buy.delivery_time,
        delivery_location=group_buy.delivery_location,
        transportation_cost=group_buy.transportation_cost,
        participation_terms=group_buy.participation_terms,
        image_url=group_buy.image_url,
        allow_partial_purchase=group_buy.allow_partial_purchase,
        is_visible=group_buy.is_visible,
        organizer_id=user_id
    )
    
    db.add(db_group_buy)
    db.commit()
    db.refresh(db_group_buy)
    return db_group_buy


def update_group_buy(db: Session, group_buy_id: int, group_buy_update: GroupBuyUpdate) -> GroupBuy:
    """Обновление существующей закупки"""
    db_group_buy = get_group_buy_by_id(db, group_buy_id)
    
    if not db_group_buy:
        return None
    
    # Обновляем только указанные поля
    update_data = group_buy_update.dict(exclude_unset=True)
    
    for key, value in update_data.items():
        setattr(db_group_buy, key, value)
    
    db.commit()
    db.refresh(db_group_buy)
    return db_group_buy


def delete_group_buy(db: Session, group_buy_id: int) -> bool:
    """Удаление закупки"""
    db_group_buy = get_group_buy_by_id(db, group_buy_id)
    
    if not db_group_buy:
        return False
    
    db.delete(db_group_buy)
    db.commit()
    return True


# ========== Product Service Functions ==========

def get_product_by_id(db: Session, product_id: int) -> Product:
    """Получение товара по ID"""
    return db.query(Product).filter(Product.id == product_id).first()


def get_products_by_group_buy(db: Session, group_buy_id: int, skip: int = 0, limit: int = 100):
    """Получение товаров по ID закупки"""
    return db.query(Product).filter(Product.group_buy_id == group_buy_id).offset(skip).limit(limit).all()


def create_product(db: Session, product: ProductCreate, group_buy_id: int) -> Product:
    """Создание нового товара"""
    db_product = Product(
        name=product.name,
        description=product.description,
        price=product.price,
        image_url=product.image_url,
        vendor=product.vendor,
        vendor_code=product.vendor_code,
        available=product.available,
        group_buy_id=group_buy_id
    )
    
    db.add(db_product)
    db.commit()
    db.refresh(db_product)
    return db_product


# ========== Order Service Functions ==========

def get_order_by_id(db: Session, order_id: int) -> Order:
    """Получение заказа по ID"""
    return db.query(Order).filter(Order.id == order_id).first()


def get_orders_by_user(db: Session, user_id: int, skip: int = 0, limit: int = 100):
    """Получение заказов пользователя"""
    return db.query(Order).filter(Order.user_id == user_id).offset(skip).limit(limit).all()


def create_order(db: Session, order: OrderCreate, user_id: int) -> Order:
    """Создание нового заказа"""
    # Проверяем существование закупки
    group_buy = get_group_buy_by_id(db, order.group_buy_id)
    if not group_buy:
        raise ValueError(f"Закупка с ID {order.group_buy_id} не найдена")
    
    # Создаем заказ
    db_order = Order(
        user_id=user_id,
        group_buy_id=order.group_buy_id,
        status="cart"
    )
    
    db.add(db_order)
    db.flush()  # Получаем ID заказа без коммита
    
    total_amount = 0.0
    
    # Добавляем товары в заказ
    for item in order.items:
        product = get_product_by_id(db, item.product_id)
        if not product:
            db.rollback()
            raise ValueError(f"Товар с ID {item.product_id} не найден")
        
        # Расчет цены товара с учетом комиссии
        product_price = product.price
        price_with_fee = product_price * (1 + group_buy.fee_percent / 100)
        
        # Создаем элемент заказа
        order_item = OrderItem(
            order_id=db_order.id,
            product_id=item.product_id,
            quantity=item.quantity,
            price=price_with_fee  # Сохраняем цену с учетом комиссии
        )
        
        db.add(order_item)
        
        # Увеличиваем счетчик заказанных товаров
        product.quantity_ordered += item.quantity
        
        # Обновляем общую сумму заказа
        total_amount += price_with_fee * item.quantity
    
    # Обновляем общую сумму заказа
    db_order.total_amount = total_amount
    
    # Обновляем статистику закупки
    group_buy.total_participants = db.query(Order).filter(
        Order.group_buy_id == group_buy.id,
        Order.status != "cancelled"
    ).count()
    
    group_buy.total_amount = db.query(func.sum(Order.total_amount)).filter(
        Order.group_buy_id == group_buy.id,
        Order.status != "cancelled"
    ).scalar() or 0.0
    
    db.commit()
    db.refresh(db_order)
    return db_order
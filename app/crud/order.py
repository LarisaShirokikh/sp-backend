# app/crud/order.py
import random
import string
from typing import List, Optional, Dict, Any
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from sqlalchemy.orm import joinedload

from app.models.group_buy import Order
from app.models.user import User
from app.crud.base import CRUDBase


class CRUDOrder(CRUDBase[Order, Dict[str, Any], Dict[str, Any]]):
    async def get_multi(
        self, db: AsyncSession, *, skip: int = 0, limit: int = 100
    ) -> List[Order]:
        """
        Получение списка заказов с присоединением пользователей
        """
        query = (
            select(Order)
            .options(joinedload(Order.user))
            .order_by(desc(Order.created_at))
            .offset(skip)
            .limit(limit)
        )
        result = await db.execute(query)
        return result.scalars().all()

    async def create_with_user(
        self, db: AsyncSession, *, obj_in: Dict[str, Any], user_id: Optional[int] = None
    ) -> Order:
        """
        Создание заказа с указанием пользователя и генерацией номера заказа
        """
        # Генерируем уникальный номер заказа
        obj_in_data = dict(obj_in)
        if "order_number" not in obj_in_data:
            obj_in_data["order_number"] = self._generate_order_number()
        
        # Создаем объект заказа
        db_obj = Order(**obj_in_data)
        if user_id:
            db_obj.user_id = user_id
        
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def get_user_orders(
        self, db: AsyncSession, *, user_id: int, skip: int = 0, limit: int = 100
    ) -> List[Order]:
        """
        Получение заказов для конкретного пользователя
        """
        query = (
            select(Order)
            .filter(Order.user_id == user_id)
            .order_by(desc(Order.created_at))
            .offset(skip)
            .limit(limit)
        )
        result = await db.execute(query)
        return result.scalars().all()

    async def update_status(
        self, db: AsyncSession, *, order_id: int, status: str
    ) -> Optional[Order]:
        """
        Обновление статуса заказа
        """
        order = await self.get(db, id=order_id)
        if not order:
            return None
        
        order.status = status
        order.updated_at = datetime.utcnow()
        
        db.add(order)
        await db.commit()
        await db.refresh(order)
        return order

    async def count(self, db: AsyncSession) -> int:
        """
        Подсчет общего количества заказов
        """
        result = await db.execute(select(func.count(Order.id)))
        return result.scalar_one()

    async def count_by_status(self, db: AsyncSession, *, status: str) -> int:
        """
        Подсчет количества заказов по статусу
        """
        result = await db.execute(
            select(func.count(Order.id)).filter(Order.status == status)
        )
        return result.scalar_one()

    def _generate_order_number(self) -> str:
        """
        Генерация уникального номера заказа
        """
        # Пример: ORDER-20230717-ABCD
        timestamp = datetime.utcnow().strftime("%Y%m%d")
        random_suffix = ''.join(random.choices(string.ascii_uppercase, k=4))
        return f"ORDER-{timestamp}-{random_suffix}"


# Создаем экземпляр CRUD для использования в API
order_crud = CRUDOrder(Order)
# app/crud/activity.py
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from sqlalchemy.orm import joinedload

from app.models.activity import Activity
from app.models.user import User
from app.crud.base import CRUDBase
from app.schemas.activity import ActivityType


class CRUDActivity(CRUDBase[Activity, None, None]):
    async def get_multi(
        self, db: AsyncSession, *, skip: int = 0, limit: int = 100
    ) -> List[Activity]:
        """
        Получение списка активностей с присоединением пользователей
        """
        query = (
            select(Activity)
            .options(joinedload(Activity.user))
            .order_by(desc(Activity.timestamp))
            .offset(skip)
            .limit(limit)
        )
        result = await db.execute(query)
        return result.scalars().all()

    async def create_with_user(
        self, db: AsyncSession, *, obj_in_data: dict, user_id: Optional[int] = None
    ) -> Activity:
        """
        Создание активности с указанием пользователя
        """
        db_obj = Activity(**obj_in_data)
        if user_id:
            db_obj.user_id = user_id
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def get_user_activities(
        self, db: AsyncSession, *, user_id: int, skip: int = 0, limit: int = 100
    ) -> List[Activity]:
        """
        Получение активностей для конкретного пользователя
        """
        query = (
            select(Activity)
            .filter(Activity.user_id == user_id)
            .order_by(desc(Activity.timestamp))
            .offset(skip)
            .limit(limit)
        )
        result = await db.execute(query)
        return result.scalars().all()


    def get_activity_message(self, activity: Activity) -> str:
        if activity.type == ActivityType.POST:
            return f"Пользователь создал новую тему (ID: {activity.topic_id})"
        elif activity.type == ActivityType.REPLY:
            return f"Пользователь ответил в теме (ID: {activity.topic_id})"
        elif activity.type == ActivityType.LIKE:
            if activity.reply_id:
                return f"Пользователь поставил лайк на ответ (ID: {activity.reply_id})"
            elif activity.topic_id:
                return f"Пользователь поставил лайк на тему (ID: {activity.topic_id})"
            else:
                return "Пользователь поставил лайк"
        else:
            return "Неизвестная активность"
        
# Создаем экземпляр CRUD для использования в API
activity_crud = CRUDActivity(Activity)
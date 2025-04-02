from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, text
from sqlalchemy.orm import selectinload
from typing import List, Optional
import logging
from datetime import datetime
import traceback

from app.models.activity import Activity
from app.schemas.activity import ActivityType

# Настройка логирования с высоким уровнем детализации
logger = logging.getLogger(__name__)

class ActivityService:
    """
    Сервис для работы с активностями пользователей.
    Используется для автоматического создания записей об активности.
    """
    
    @staticmethod
    async def create_post_activity(
        db: AsyncSession, 
        user_id: int, 
        topic_id: int,
        topic_title: str
    ) -> Activity:
        """
        Создать запись об активности при создании новой темы.
        """
        logger.info(f"Creating POST activity: user_id={user_id}, topic_id={topic_id}")
        
        try:
            # Проверяем соединение с базой данных
            try:
                result = await db.execute(text("SELECT 1"))
                logger.info("Database connection test: SUCCESS")
            except Exception as e:
                logger.error(f"Database connection test: FAILED - {str(e)}")
                raise
            
            # Создаем объект активности
            activity = Activity(
                user_id=user_id,
                type=ActivityType.POST,
                topic_id=topic_id,
                created_at=datetime.utcnow()
            )
            
            # Логируем все поля объекта для проверки
            logger.info(f"Activity object created with fields: {vars(activity)}")
            
            # Добавляем в сессию
            logger.info("Adding activity to session...")
            db.add(activity)
            logger.info("Activity added to session. Calling commit...")
            
            # Пробуем прямой SQL-запрос вместо ORM (для отладки)
            # Раскомментируйте, если ORM метод не работает
            """
            raw_sql = text(
                "INSERT INTO activity (user_id, type, topic_id, created_at) "
                "VALUES (:user_id, :type, :topic_id, :created_at)"
            )
            await db.execute(
                raw_sql, 
                {
                    "user_id": user_id, 
                    "type": ActivityType.POST.value,  # Используем .value для enum
                    "topic_id": topic_id, 
                    "created_at": datetime.utcnow()
                }
            )
            """
            
            # Фиксируем транзакцию
            try:
                await db.commit()
                logger.info("Commit successful")
            except Exception as e:
                logger.error(f"Commit failed: {str(e)}")
                logger.error(traceback.format_exc())  # Полный стектрейс
                raise
            
            # Обновляем объект из БД
            try:
                await db.refresh(activity)
                logger.info(f"Activity refreshed from DB, id={activity.id}")
            except Exception as e:
                logger.error(f"Refresh failed: {str(e)}")
                raise
            
            # Проверяем, что активность действительно сохранилась
            try:
                check_query = select(Activity).where(Activity.id == activity.id)
                check_result = await db.execute(check_query)
                saved_activity = check_result.scalar_one_or_none()
                
                if saved_activity:
                    logger.info(f"Verification: Activity found in DB with id={saved_activity.id}")
                else:
                    logger.warning(f"Verification: Activity NOT found in DB despite successful commit!")
            except Exception as e:
                logger.error(f"Verification query failed: {str(e)}")
            
            return activity
        except Exception as e:
            logger.error(f"Error creating POST activity: {str(e)}")
            logger.error(traceback.format_exc())  # Полный стектрейс для отладки
            try:
                await db.rollback()
                logger.info("Transaction rolled back")
            except Exception as rollback_error:
                logger.error(f"Rollback failed: {str(rollback_error)}")
            raise
    
    @staticmethod
    async def create_reply_activity(
        db: AsyncSession, 
        user_id: int, 
        topic_id: int,
        reply_id: int
    ) -> Activity:
        """
        Создать запись об активности при ответе на тему.
        """
        logger.info(f"Creating REPLY activity: user_id={user_id}, topic_id={topic_id}, reply_id={reply_id}")
        
        try:
            activity = Activity(
                user_id=user_id,
                type=ActivityType.REPLY,
                topic_id=topic_id,
                reply_id=reply_id,
                created_at=datetime.utcnow()
            )
            
            logger.info(f"Activity object created with fields: {vars(activity)}")
            logger.info("Adding activity to session...")
            db.add(activity)
            logger.info("Activity added to session. Calling commit...")
            
            try:
                await db.commit()
                logger.info("Commit successful")
            except Exception as e:
                logger.error(f"Commit failed: {str(e)}")
                logger.error(traceback.format_exc())
                raise
                
            await db.refresh(activity)
            logger.info(f"Activity refreshed from DB, id={activity.id}")
            
            return activity
        except Exception as e:
            logger.error(f"Error creating REPLY activity: {str(e)}")
            logger.error(traceback.format_exc())
            try:
                await db.rollback()
                logger.info("Transaction rolled back")
            except Exception as rollback_error:
                logger.error(f"Rollback failed: {str(rollback_error)}")
            raise
    
    @staticmethod
    async def create_like_activity(
        db: AsyncSession, 
        user_id: int, 
        topic_id: Optional[int] = None,
        reply_id: Optional[int] = None
    ) -> Activity:
        """
        Создать запись об активности при лайке темы или ответа.
        """
        logger.info(f"Creating LIKE activity: user_id={user_id}, topic_id={topic_id}, reply_id={reply_id}")
        
        try:
            activity = Activity(
                user_id=user_id,
                type=ActivityType.LIKE,
                topic_id=topic_id,
                reply_id=reply_id,
                created_at=datetime.utcnow()
            )
            
            logger.info(f"Activity object created with fields: {vars(activity)}")
            logger.info("Adding activity to session...")
            db.add(activity)
            logger.info("Activity added to session. Calling commit...")
            
            try:
                await db.commit()
                logger.info("Commit successful")
            except Exception as e:
                logger.error(f"Commit failed: {str(e)}")
                logger.error(traceback.format_exc())
                raise
                
            await db.refresh(activity)
            logger.info(f"Activity refreshed from DB, id={activity.id}")
            
            return activity
        except Exception as e:
            logger.error(f"Error creating LIKE activity: {str(e)}")
            logger.error(traceback.format_exc())
            try:
                await db.rollback()
                logger.info("Transaction rolled back")
            except Exception as rollback_error:
                logger.error(f"Rollback failed: {str(rollback_error)}")
            raise
    
    @staticmethod
    async def get_recent_activities(
        db: AsyncSession, 
        limit: int = 5, 
        skip: int = 0
    ) -> List[Activity]:
        """
        Получить список последних активностей.
        """
        logger.info(f"Getting recent activities: limit={limit}, skip={skip}")
        
        try:
            query = (
                select(Activity)
                .options(
                    selectinload(Activity.user),
                    selectinload(Activity.topic),
                    selectinload(Activity.reply)
                )
                .order_by(desc(Activity.created_at))
                .offset(skip)
                .limit(limit)
            )
            
            result = await db.execute(query)
            activities = result.scalars().all()
            
            logger.info(f"Retrieved {len(activities)} activities")
            return activities
        except Exception as e:
            logger.error(f"Error getting recent activities: {str(e)}")
            logger.error(traceback.format_exc())
            raise
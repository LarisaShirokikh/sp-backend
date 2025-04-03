import logging
from aiohttp import request
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, text
from sqlalchemy.orm import selectinload
from typing import List
from datetime import datetime

from app.api.deps import get_db
from app.models.activity import Activity, ActivityType
from app.models.user import User
from app.api.deps import get_current_user
from app.schemas.activity import ActivityCreate, ActivityOut

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/test-db", status_code=status.HTTP_200_OK)
async def test_database_connection(db: AsyncSession = Depends(get_db)):
    """Проверка соединения с базой данных."""
    try:
        # Синхронный вызов execute без await
        result = db.execute(text("SELECT 1 as test"))
        value = result.scalar()
        
        return {
            "status": "success",
            "test_value": value,
            "message": "Соединение с базой данных работает"
        }
    except Exception as e:
        logger.error(f"Database connection test failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка соединения с базой данных: {str(e)}"
        )

@router.get("", response_model=List[ActivityOut])
async def get_activities(
    limit: int = Query(5, ge=1, le=50),
    skip: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db)
):
    """Получить список последних активностей пользователей."""
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
        
        # Синхронный вызов execute без await
        result = db.execute(query)
        activities = result.scalars().all()

        response = []
        for activity in activities:
            content = ""
            link = "#"
            entity_id = None

            if activity.type == ActivityType.POST and activity.topic:
                content = activity.topic.title
                link = f"/forum/topic/{activity.topic.id}"
                entity_id = activity.topic.id

            elif activity.type == ActivityType.REPLY and activity.reply and activity.topic:
                content = activity.topic.title
                link = f"/forum/topic/{activity.topic.id}#reply-{activity.reply.id}"
                entity_id = activity.topic.id

            elif activity.type == ActivityType.LIKE:
                if activity.topic:
                    content = activity.topic.title
                    link = f"/forum/topic/{activity.topic.id}"
                    entity_id = activity.topic.id
                elif activity.reply and activity.reply.topic:
                    content = "ответу в теме"
                    topic_id = activity.reply.topic_id
                    link = f"/forum/topic/{topic_id}#reply-{activity.reply.id}"
                    entity_id = topic_id

            response.append({
                "id": activity.id,
                "type": activity.type,
                "user": {
                    "id": activity.user.id,
                    "name": activity.user.name,
                    "avatar_url": activity.user.avatar_url
                },
                "content": content,
                "created_at": activity.created_at.isoformat(),
                "link": link,
                "entity_id": entity_id
            })

        return response
    except Exception as e:
        logger.exception(f"Ошибка при получении активностей: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка при получении активностей"
        )

@router.post("", response_model=ActivityOut, status_code=status.HTTP_201_CREATED)
async def create_activity(
    activity_data: ActivityCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Создать новую запись об активности пользователя."""
    try:
        logger.info(f"Activity request received. Headers: {request.headers}")
        logger.info(f"Activity data: {activity_data}")
        logger.info(f"Current user: {current_user.id}, {current_user.name}")
        
        activity = Activity(
            user_id=current_user.id,
            type=activity_data.type,
            topic_id=activity_data.topic_id,
            reply_id=activity_data.reply_id,
            created_at=datetime.utcnow()
        )

        logger.debug(f"Activity object created with fields: {vars(activity)}")
        
        db.add(activity)
        logger.debug("Activity added to session, committing...")
        
        # ВАЖНО: Используем sync методы без await
        db.commit()
        logger.debug("Commit successful")
        
        # ВАЖНО: Используем sync методы без await
        db.refresh(activity)
        logger.info(f"Activity created with ID: {activity.id}")

        return {
            "id": activity.id,
            "type": activity.type,
            "user": {
                "id": current_user.id,
                "name": current_user.name,
                "avatar_url": current_user.avatar_url
            },
            "created_at": activity.created_at.isoformat(),
            "link": activity_data.link or "#",
            "entity_id": activity_data.topic_id,
            "content": activity_data.content or ""
        }
    except Exception as e:
        logger.exception(f"Ошибка при создании активности: {str(e)}")
        
        # ВАЖНО: Используем sync методы без await
        db.rollback()
        
        # Пробуем создать через прямой SQL
        try:
            logger.info("Trying direct SQL insert as fallback...")
            
            sql = text("""
                INSERT INTO activity (user_id, type, topic_id, reply_id, created_at)
                VALUES (:user_id, :type, :topic_id, :reply_id, :created_at)
                RETURNING id
            """)
            
            # Синхронный вызов execute без await
            result = db.execute(
                sql,
                {
                    "user_id": current_user.id,
                    "type": activity_data.type.value, 
                    "topic_id": activity_data.topic_id,
                    "reply_id": activity_data.reply_id,
                    "created_at": datetime.utcnow()
                }
            )
            
            activity_id = result.scalar()
            # ВАЖНО: Используем sync методы без await
            db.commit()
            
            logger.info(f"Activity created via SQL with ID: {activity_id}")
            
            return {
                "id": activity_id,
                "type": activity_data.type,
                "user": {
                    "id": current_user.id,
                    "name": current_user.name,
                    "avatar_url": current_user.avatar_url
                },
                "created_at": datetime.utcnow().isoformat(),
                "link": activity_data.link or "#",
                "entity_id": activity_data.topic_id,
                "content": activity_data.content or ""
            }
        except Exception as sql_error:
            logger.error(f"SQL fallback also failed: {str(sql_error)}")
            # ВАЖНО: Используем sync методы без await
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Ошибка при создании активности"
            )

@router.delete("/{activity_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_activity(
    activity_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Удалить запись об активности. Только для модераторов и админов."""
    if not current_user.is_superuser and current_user.role != "moderator":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Недостаточно прав для выполнения операции"
        )

    try:
        # Синхронный вызов execute без await
        result = db.execute(select(Activity).where(Activity.id == activity_id))
        activity = result.scalar_one_or_none()

        if not activity:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Активность не найдена"
            )

        db.delete(activity)
        # ВАЖНО: Используем sync методы без await
        db.commit()
        
        return None
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Ошибка при удалении активности: {str(e)}")
        # ВАЖНО: Используем sync методы без await
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка при удалении активности"
        )
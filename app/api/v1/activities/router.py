import logging
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, text
from sqlalchemy.orm import selectinload
from typing import List, Optional
from datetime import datetime

from app.db.session import get_db
from app.models.activity import Activity
from app.models.user import User
from app.models.category_forum import TopicModel, ReplyModel
from app.api.deps import get_current_user
from app.schemas.activity import ActivityCreate, ActivityOut, ActivityType
from app.services.activity_service import ActivityService

# Настройка логирования
logging.basicConfig(level=logging.DEBUG)  # Повышаем уровень логирования для отладки
logger = logging.getLogger(__name__)

router = APIRouter()

# Тестовый эндпоинт для проверки соединения с БД
@router.get("/test-db", status_code=status.HTTP_200_OK)
async def test_database_connection(db: AsyncSession = Depends(get_db)):
    """
    Проверка соединения с базой данных.
    """
    try:
        # Простой SQL-запрос для проверки
        result = await db.execute(text("SELECT 1 as test"))
        value = result.scalar()
        
        # Проверяем существование таблицы activity
        tables_result = await db.execute(text(
            "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'activity')"
        ))
        table_exists = tables_result.scalar()
        
        return {
            "database_connection": "OK",
            "test_query_result": value,
            "activity_table_exists": table_exists
        }
    except Exception as e:
        logger.error(f"Database connection test failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка соединения с базой данных: {str(e)}"
        )

# Получение списка последних активностей
@router.get("", response_model=List[ActivityOut])
async def get_activities(
    limit: int = Query(5, ge=1, le=50),
    skip: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db)
):
    """
    Получить список последних активностей пользователей.
    
    - **limit**: Максимальное количество записей (по умолчанию 5, макс. 50)
    - **skip**: Сколько записей пропустить (для пагинации)
    """
    try:
        logger.debug(f"Getting activities: limit={limit}, skip={skip}")
        
        # Запрос к БД для получения активностей с присоединением таблицы пользователей
        query = (
            select(Activity)
            .options(
                # Загружаем связанного пользователя
                selectinload(Activity.user),
                # Загружаем связанные сущности в зависимости от типа активности
                selectinload(Activity.topic),
                selectinload(Activity.reply)
            )
            .order_by(desc(Activity.created_at))
            .offset(skip)
            .limit(limit)
        )
        
        # ВАЖНО: Используем await для db.execute
        result = await db.execute(query)
        activities = result.scalars().all()
        
        logger.debug(f"Found {len(activities)} activities")
        
        # Преобразуем данные для фронтенда
        activity_list = []
        for activity in activities:
            # Определяем содержимое и ссылку в зависимости от типа активности
            content = ""
            link = "#"
            entity_id = None
            
            if activity.type == ActivityType.POST:
                # Активность связана с созданием темы
                if activity.topic:
                    content = activity.topic.title
                    link = f"/forum/topic/{activity.topic.id}"
                    entity_id = activity.topic.id
                    
            elif activity.type == ActivityType.REPLY:
                # Активность связана с ответом на тему
                if activity.reply and activity.topic:
                    content = activity.topic.title
                    link = f"/forum/topic/{activity.topic.id}#reply-{activity.reply.id}"
                    entity_id = activity.topic.id
                    
            elif activity.type == ActivityType.LIKE:
                # Активность связана с лайком
                if activity.topic:
                    content = activity.topic.title
                    link = f"/forum/topic/{activity.topic.id}"
                    entity_id = activity.topic.id
                elif activity.reply and activity.reply.topic:
                    content = "ответу в теме"
                    topic_id = activity.reply.topic_id
                    link = f"/forum/topic/{topic_id}#reply-{activity.reply.id}"
                    entity_id = topic_id
                    
            activity_list.append({
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
        
        return activity_list
    except Exception as e:
        logger.error(f"Error in get_activities: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка при получении активностей: {str(e)}"
        )

# Создание записи об активности (для внутреннего использования)
@router.post("", response_model=ActivityOut, status_code=status.HTTP_201_CREATED)
async def create_activity(
    activity_data: ActivityCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Создать новую запись об активности пользователя.
    Обычно вызывается автоматически при действиях пользователя.
    """
    try:
        logger.info(f"Creating activity: type={activity_data.type}, user_id={current_user.id}")
        
        # Прямое создание активности для отладки
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
        
        await db.commit()
        logger.debug("Commit successful")
        
        await db.refresh(activity)
        logger.info(f"Activity created with ID: {activity.id}")
        
        # Подготавливаем данные для ответа
        response = {
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
        
        return response
    except Exception as e:
        logger.error(f"Error in create_activity: {str(e)}")
        await db.rollback()
        
        # Пробуем создать активность напрямую через SQL
        try:
            logger.info("Attempting direct SQL insert as fallback...")
            
            sql = text("""
                INSERT INTO activity (user_id, type, topic_id, reply_id, created_at)
                VALUES (:user_id, :type, :topic_id, :reply_id, :created_at)
                RETURNING id
            """)
            
            result = await db.execute(
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
            await db.commit()
            
            logger.info(f"Activity created via SQL with ID: {activity_id}")
            
            # Подготавливаем данные для ответа после SQL создания
            response = {
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
            
            return response
        except Exception as sql_error:
            logger.error(f"SQL fallback also failed: {str(sql_error)}")
            await db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Ошибка при создании активности: {str(sql_error)}"
            )
        
    except Exception as e:
        logger.error(f"Error in create_activity: {str(e)}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка при создании активности: {str(e)}"
        )

# Удаление активности (опционально, для модераторов)
@router.delete("/{activity_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_activity(
    activity_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Удалить запись об активности.
    Доступно только администраторам и модераторам.
    """
    try:
        # Проверяем права доступа
        if not current_user.is_superuser and current_user.role != "moderator":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Недостаточно прав для выполнения операции"
            )
        
        # Находим активность по ID
        query = select(Activity).where(Activity.id == activity_id)
        # ВАЖНО: Используем await для db.execute
        result = await db.execute(query)
        activity = result.scalar_one_or_none()
        
        if not activity:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Активность не найдена"
            )
        
        # Удаляем активность
        db.delete(activity)
        await db.commit()
        
        return None
    except HTTPException:
        # Пробрасываем HTTP-исключения как есть
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Error in delete_activity: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка при удалении активности: {str(e)}"
        )
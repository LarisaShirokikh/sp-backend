# Настройка логирования
import logging
from typing import Any, List, Optional
from sqlalchemy.orm import Session
from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import get_current_user
from app.db.session import get_db
from app.core.config import settings
from app.models.user import User
from app.schemas.category_forum import Topic, TopicCreate
from app.crud.topic_forum import crud_topic 


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/", response_model=Topic)
def create_topic(
    topic_in: TopicCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Создание нового топика на форуме с расширенной обработкой
    """
    try:
        # Подробное логирование входящих данных
        logger.info(f"Creating topic for user {current_user.id}")
        logger.info(f"Topic data: {topic_in}")

        # Проверка прав пользователя
        if not current_user.is_active:
            logger.error(f"Inactive user {current_user.id} attempted to create topic")
            raise HTTPException(status_code=403, detail="Пользователь не активен")
        
        # Создание топика
        topic = crud_topic.create(
            db=db, 
            obj_in=topic_in, 
            author_id=current_user.id
        )
        
        logger.info(f"Topic created successfully: {topic.id}")
        return topic
    
    except ValueError as e:
        logger.error(f"Validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error creating topic: {e}")
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")
     
@router.get("/category/{category_id}", response_model=List[Topic])
def read_topics_by_category(
    category_id: int,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """
    Получение списка топиков для определенной категории
    """
    topics = crud_topic.get_topics_by_category(
        db=db, 
        category_id=category_id, 
        skip=skip, 
        limit=limit
    )
    return topics

@router.get("/all", response_model=list[Topic])
def read_topics(
    skip: int = 0,
    limit: int = 100,
    category_id: Optional[int] = None,
    db: Session = Depends(get_db)
) -> Any:
    """
    Получение списка топиков с возможностью фильтрации по категории
    """
    if category_id is not None:
        return crud_topic.get_by_params(db=db, category_id=category_id, skip=skip, limit=limit)
    return crud_topic.get_multi(db=db, skip=skip, limit=limit)

@router.get("/{topic_id}", response_model=Topic)
def read_topic(
    topic_id: int,
    db: Session = Depends(get_db)
) -> Any:
    """
    Получение информации о топике по ID
    """
    topic = crud_topic.get(db=db, id=topic_id)
    if not topic:
        raise HTTPException(status_code=404, detail="Топик не найден")
    return topic


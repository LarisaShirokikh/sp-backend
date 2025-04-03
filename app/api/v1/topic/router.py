import logging
import os
import shutil
from typing import Any, List, Optional
from sqlalchemy import insert, select, delete
from sqlalchemy.orm import Session
from fastapi import APIRouter, Body, Depends, HTTPException, Request, UploadFile, File, Form
from fastapi.responses import JSONResponse

from app.api.deps import get_current_user
from app.db.session import get_db
from app.core.config import settings
from app.models.category_forum import TopicModel, topic_likes
from app.models.user import User
from app.schemas.category_forum import Reply, ReplyContent, Topic, TopicCreate, TopicFile
from app.crud.topic_forum import crud_topic
from app.schemas.response import TopicResponse
from app.services.activity_service import ActivityService


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()

# Путь для сохранения загруженных файлов
UPLOAD_DIR = "media/topics"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@router.post("/", response_model=TopicResponse)
async def create_topic(
    title: str = Form(...),
    content: str = Form(...),
    category_id: int = Form(...),
    files: List[UploadFile] = File(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    request: Request = None,
):
    """
    Создание нового топика на форуме с поддержкой загрузки файлов
    """
    try:
        # Подробное логирование входящих данных
        if request:
            logger.info(f"Заголовки запроса: {request.headers}")
            logger.info(f"IP клиента: {request.client.host}")

        # Проверка прав пользователя
        if not current_user.is_active:
            logger.error(f"Inactive user {current_user.id} attempted to create topic")
            raise HTTPException(status_code=403, detail="Пользователь не активен")
        
        # Создаем объект TopicCreate из полученных данных формы
        topic_in = TopicCreate(
            title=title,
            content=content,
            category_id=category_id,
            user_id=current_user.id
        )
        
        # Создание топика
        topic = crud_topic.create(
            db=db, 
            obj_in=topic_in, 
            author_id=current_user.id
        )
        
        # Важно: добавляем await для асинхронного вызова
        try:
            ActivityService.create_post_activity(
                db=db,
                user_id=current_user.id,
                topic_id=topic.id,
                topic_title=topic.title
            )
            logger.info(f"Activity for topic {topic.id} created successfully")
        except Exception as activity_error:
            # Логируем ошибку, но продолжаем выполнение
            logger.error(f"Failed to create activity: {str(activity_error)}")
        
        # Обработка загруженных файлов
        file_paths = []
        if files:
            # Создаем директорию для файлов этого топика
            topic_upload_dir = os.path.join(UPLOAD_DIR, f"topic_{topic.id}")
            os.makedirs(topic_upload_dir, exist_ok=True)
            
            for file in files:
                if file.filename:
                    # Генерируем безопасное имя файла
                    file_path = os.path.join(topic_upload_dir, file.filename)
                    
                    # Сохраняем файл
                    with open(file_path, "wb") as buffer:
                        shutil.copyfileobj(file.file, buffer)
                    
                    file_paths.append(file_path)
            
            # Сохраняем пути к файлам в БД, связывая их с топиком
            if file_paths:
                crud_topic.add_files_to_topic(
                    db=db,
                    topic_id=topic.id,
                    file_paths=file_paths
                )
        
        logger.info(f"Topic created successfully: {topic.id} with {len(file_paths)} files")
        
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

    logger.info(f"Fetching topics - skip: {skip}, limit: {limit}, category_id: {category_id}")

    if category_id is not None:
        topics = crud_topic.get_by_params(db=db, category_id=category_id, skip=skip, limit=limit)
    else:
        topics = crud_topic.get_multi(db=db, skip=skip, limit=limit)
    
    logger.info(f"Retrieved {len(topics)} topics")
    return topics

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

@router.get("/{topic_id}/replies", response_model=List[Reply])
def read_topic_replies(
    topic_id: int,
    db: Session = Depends(get_db)
) -> Any:
    """
    Получение всех ответов для топика по ID
    """
    replies = crud_topic.get_replies(db=db, topic_id=topic_id)
    if replies is None:
        raise HTTPException(status_code=404, detail="Топик не найден или ответы отсутствуют")
    return replies

@router.post("/{topic_id}/reply", response_model=Reply)
async def create_reply(
    topic_id: int,
    content_data: ReplyContent,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Добавление простого текстового ответа к топику
    """
    try:
        logger.info(f"Creating reply for topic {topic_id} by user {current_user.id}")
        logger.info(f"Content received: {content_data.content}")
        if not content_data.content.strip():
            raise HTTPException(status_code=400, detail="Пустое содержание ответа")
        
        # Проверка прав пользователя
        if not current_user.is_active:
            logger.error(f"Inactive user {current_user.id} attempted to create reply")
            raise HTTPException(status_code=403, detail="Пользователь не активен")
        
        # Проверка существования топика
        topic = crud_topic.get(db=db, id=topic_id)
        if not topic:
            raise HTTPException(status_code=404, detail="Топик не найден")
        
        # Создание ответа
        reply = crud_topic.create_reply(
            db=db,
            topic_id=topic_id,
            content=content_data.content,
            author_id=current_user.id
        )
         # Важно: добавляем await для асинхронного вызова
        try:
            ActivityService.create_post_activity(
                db=db,
                user_id=current_user.id,
                topic_id=topic.id,
                topic_title=content_data.content
            )
            logger.info(f"Activity for topic {topic.id} created successfully")
        except Exception as activity_error:
            # Логируем ошибку, но продолжаем выполнение
            logger.error(f"Failed to create activity: {str(activity_error)}")
        
        logger.info(f"Reply created successfully: {reply.id}")
        return reply
    
    except ValueError as e:
        logger.error(f"Validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error creating reply: {e}")
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")

@router.post("/{topic_id}/reply/with-media", response_model=Reply)
async def create_reply_with_media(
    topic_id: int,
    content: str = Form(...),
    media_files: List[UploadFile] = File(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Добавление ответа к топику с поддержкой загрузки медиа-файлов
    """
    try:
        # Подробное логирование входящих данных
        logger.info(f"Creating reply with media for topic {topic_id} by user {current_user.id}")
        logger.info(f"Reply data: content length={len(content)}, files_count={len(media_files) if media_files else 0}")

        # Проверка прав пользователя
        if not current_user.is_active:
            logger.error(f"Inactive user {current_user.id} attempted to create reply")
            raise HTTPException(status_code=403, detail="Пользователь не активен")
        
        # Проверка существования топика
        topic = crud_topic.get(db=db, id=topic_id)
        if not topic:
            raise HTTPException(status_code=404, detail="Топик не найден")
        
        # Создание ответа
        reply = crud_topic.create_reply(
            db=db,
            topic_id=topic_id,
            content=content,
            author_id=current_user.id
        )
        
        # Обработка загруженных файлов
        file_paths = []
        if media_files:
            # Создаем директорию для файлов этого ответа
            reply_upload_dir = os.path.join(UPLOAD_DIR, f"topic_{topic_id}/reply_{reply.id}")
            os.makedirs(reply_upload_dir, exist_ok=True)
            
            for file in media_files:
                if file.filename:
                    # Генерируем безопасное имя файла
                    # В реальном приложении стоит использовать UUID или другой метод
                    file_path = os.path.join(reply_upload_dir, file.filename)
                    
                    # Сохраняем файл
                    with open(file_path, "wb") as buffer:
                        shutil.copyfileobj(file.file, buffer)
                    
                    file_paths.append(file_path)
            
            # Сохраняем пути к файлам в БД, связывая их с ответом
            if file_paths:
                crud_topic.add_files_to_reply(
                    db=db,
                    reply_id=reply.id,
                    file_paths=file_paths
                )
        
        logger.info(f"Reply created successfully: {reply.id} with {len(file_paths)} files")
        
        # Получаем обновленный ответ с прикрепленными файлами
        updated_reply = crud_topic.get_reply(db=db, reply_id=reply.id)
        return updated_reply
    
    except ValueError as e:
        logger.error(f"Validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error creating reply with media: {e}")
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")


@router.get("/reply/{reply_id}/media", response_model=List[TopicFile])
def read_reply_media(
    reply_id: int,
    db: Session = Depends(get_db)
) -> Any:
    """
    Получение всех медиа-файлов, связанных с ответом по ID
    """
    media_files = crud_topic.get_reply_files(db=db, reply_id=reply_id)
    if media_files is None:
        raise HTTPException(status_code=404, detail="Медиа не найдены")
    return media_files


@router.post("/reply/{reply_id}/like")
def like_reply(
    reply_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Поставить лайк ответу
    """
    try:
        # Проверяем существование ответа
        reply = crud_topic.get_reply(db=db, reply_id=reply_id)
        if not reply:
            raise HTTPException(status_code=404, detail="Ответ не найден")
        
        # Добавляем лайк
        result = crud_topic.like_reply(
            db=db,
            reply_id=reply_id,
            user_id=current_user.id
        )
        
        
        # Создаем активность
        ActivityService.create_like_activity(
            db=db,
            user_id=current_user.id,
            reply_id=reply_id,
        )
        
    
    except Exception as e:
        logger.error(f"Error liking reply: {e}")
        raise HTTPException(status_code=500, detail="Ошибка при добавлении лайка")


@router.delete("/reply/{reply_id}/like")
def unlike_reply(
    reply_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Убрать лайк с ответа
    """
    try:
        # Проверяем существование ответа
        reply = crud_topic.get_reply(db=db, reply_id=reply_id)
        if not reply:
            raise HTTPException(status_code=404, detail="Ответ не найден")
        
        # Удаляем лайк
        result = crud_topic.unlike_reply(
            db=db,
            reply_id=reply_id,
            user_id=current_user.id
        )
        
        return {"success": True, "message": result}
    
    except Exception as e:
        logger.error(f"Error unliking reply: {e}")
        raise HTTPException(status_code=500, detail="Ошибка при удалении лайка")
    
@router.get("/{topic_id}/media", response_model=List[TopicFile])
def read_topic_media(
    topic_id: int,
    db: Session = Depends(get_db)
) -> Any:
    """
    Получение всех медиа-файлов, связанных с топиком по ID
    """
    media_files = crud_topic.get_topic_files(db=db, topic_id=topic_id)
    if media_files is None:
        raise HTTPException(status_code=404, detail="Медиа не найдены")
    return media_files

# Увеличение счетчика просмотров
@router.post("/{topic_id}/view")
def increment_view_count(topic_id: int, db: Session = Depends(get_db)):
    topic = db.query(TopicModel).filter(TopicModel.id == topic_id).first()
    if not topic:
        raise HTTPException(status_code=404, detail="Тема не найдена")
    
    topic.view_count = (topic.view_count or 0) + 1
    db.commit()
    return {"success": True}

# Проверка наличия лайка
@router.get("/{topic_id}/like")
def check_like(topic_id: int, userId: int, db: Session = Depends(get_db)):
    # Проверяем существует ли лайк с указанным topic_id и user_id
    stmt = select(topic_likes).where(
        topic_likes.c.topic_id == topic_id,
        topic_likes.c.user_id == userId,
        topic_likes.c.is_like == True  # Учитываем, что у вас есть колонка is_like
    )
    result = db.execute(stmt).first()
    
    return {"isLiked": result is not None}

# Добавление лайка
@router.post("/{topic_id}/like")
def add_like(
    topic_id: int, 
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Проверяем, существует ли топик
    topic = db.query(TopicModel).filter(TopicModel.id == topic_id).first()
    if not topic:
        raise HTTPException(status_code=404, detail="Тема не найдена")
    
    # Проверяем, не поставил ли пользователь уже лайк
    stmt = select(topic_likes).where(
        topic_likes.c.topic_id == topic_id,
        topic_likes.c.user_id == current_user.id,
        topic_likes.c.is_like == True
    )
    existing_like = db.execute(stmt).first()
    
    if existing_like:
        # Если лайк уже есть, просто возвращаем успех
        return {"success": True, "message": "Лайк уже поставлен"}
    
    # Если есть дизлайк, удаляем его
    stmt_delete = delete(topic_likes).where(
        topic_likes.c.topic_id == topic_id,
        topic_likes.c.user_id == current_user.id,
        topic_likes.c.is_like == False
    )
    db.execute(stmt_delete)
    
    # Добавляем новый лайк
    stmt_insert = insert(topic_likes).values(
        topic_id=topic_id,
        user_id=current_user.id,
        is_like=True
    )
    db.execute(stmt_insert)
    
    # Увеличиваем счетчик лайков
    topic.like_count = (topic.like_count or 0) + 1
    
    # Уменьшаем счетчик дизлайков, если был дизлайк
    if topic.dislike_count > 0:
        topic.dislike_count -= 1
    
    db.commit()

    # Создаем запись об активности после успешного добавления лайка
    try:
        ActivityService.create_like_activity(
            db=db,
            user_id=current_user.id,
            topic_id=topic_id
        )
        
    except Exception as e:
        # Логгируем ошибку, но не прерываем выполнение основного процесса
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Ошибка при создании активности лайка: {str(e)}")
    return {"success": True}

# Удаление лайка
@router.delete("/{topic_id}/like")
def remove_like(
    topic_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Проверяем, существует ли топик
    topic = db.query(TopicModel).filter(TopicModel.id == topic_id).first()
    if not topic:
        raise HTTPException(status_code=404, detail="Тема не найдена")
    
    # Проверяем, есть ли лайк
    stmt = select(topic_likes).where(
        topic_likes.c.topic_id == topic_id,
        topic_likes.c.user_id == current_user.id,
        topic_likes.c.is_like == True
    )
    existing_like = db.execute(stmt).first()
    
    if not existing_like:
        # Если лайка нет, просто возвращаем успех
        return {"success": True, "message": "Лайк не найден"}
    
    # Удаляем лайк
    stmt_delete = delete(topic_likes).where(
        topic_likes.c.topic_id == topic_id,
        topic_likes.c.user_id == current_user.id,
        topic_likes.c.is_like == True
    )
    db.execute(stmt_delete)
    
    # Уменьшаем счетчик лайков
    if topic.like_count > 0:
        topic.like_count -= 1
    
    db.commit()
    return {"success": True}
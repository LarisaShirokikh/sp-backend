import logging
from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, Body, Path, Query, UploadFile, logger
from sqlalchemy.orm import Session
from app.core.config import settings
from typing import Any, List, Optional
from app.api.deps import get_db, get_current_user
from app.models.user import User
from app.services.auth import (
    send_email_verification, 
    send_phone_verification, 
    verify_email_token_service, 
    verify_phone_code_service
)
from app.schemas.user import UserBase, UserProfileUpdate, UserProfileUpdate, UserResponse
from app.services.user import cleanup_old_avatar, cleanup_old_cover_photo, is_valid_file, save_avatar, save_cover_photo
from app.utils.serialization import serialize_user

ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "gif", "webp"}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/me", response_model=UserResponse)
async def get_current_user_route(current_user: User = Depends(get_current_user)):
    """Получение информации о текущем пользователе с корректными ролями"""
    print(f"DEBUG: User ID: {current_user.id}, is_superuser: {current_user.is_superuser}")
    if hasattr(current_user, "roles") and current_user.roles:
        print(f"DEBUG: User roles from DB: {[r.role for r in current_user.roles]}")
    else:
        print("DEBUG: User has no roles in DB")
    
    serialized_user = serialize_user(current_user)
    print(f"DEBUG: Serialized roles: {serialized_user['roles']}")
    
    return serialized_user

@router.patch("/me", response_model=UserProfileUpdate)
async def update_user_profile(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    user_data: Optional[str] = Form(None),
    avatar: Optional[UploadFile] = File(None),
    cover_photo: Optional[UploadFile] = File(None),
) -> Any:
    """
    Частичное обновление профиля пользователя.
    """
    # Проверяем наличие хотя бы одного параметра для обновления
    if not user_data and not avatar and not cover_photo:
        raise HTTPException(status_code=400, detail="Нет данных для обновления")
    
    update_data = {}
    
    # Обработка user_data
    if user_data:
        try:
            from json import loads
            user_update = UserProfileUpdate.model_validate(loads(user_data))
            update_data = user_update.model_dump(exclude_unset=True)
        except Exception as e:
            logger.error(f"Error parsing user data: {e}")
            raise HTTPException(status_code=400, detail="Неверный формат данных профиля")
    
    # Обработка аватара
    if avatar:
        # Проверка размера файла
        await avatar.seek(0)  # Перемещаемся в начало файла
        content = await avatar.read(MAX_FILE_SIZE + 1)
        if len(content) > MAX_FILE_SIZE:
            raise HTTPException(status_code=400, detail=f"Файл слишком большой (макс. {MAX_FILE_SIZE // 1024 // 1024} MB)")
            
        # Возвращаемся в начало файла для дальнейшей обработки
        await avatar.seek(0)
        
        # Проверка типа файла
        if not is_valid_file(avatar.filename, avatar.content_type):
            raise HTTPException(
                status_code=400, 
                detail=f"Недопустимый формат файла. Разрешены: {', '.join(ALLOWED_EXTENSIONS)}"
            )
            
        # Сохраняем новый аватар
        avatar_path = await save_avatar(current_user.id, avatar)
        print("✅ Сохранённый путь к аватару:", avatar_path)
        # Добавляем путь к аватару в данные для обновления
        update_data["avatar_url"] = avatar_path
        print("💾 Данные для обновления:", update_data)
        # Запланируем задачу на удаление старого аватара, если он был
        if current_user.avatar_url:
            logger.info(f"Запуск очистки старого аватара: {current_user.avatar_url}")
            background_tasks.add_task(cleanup_old_avatar, current_user.avatar_url)
        else:
            logger.info("У пользователя нет старого аватара для удаления")
    
    # Обработка обложки профиля
    if cover_photo:
        # Проверка размера файла
        await cover_photo.seek(0)  # Перемещаемся в начало файла
        content = await cover_photo.read(MAX_FILE_SIZE + 1)
        if len(content) > MAX_FILE_SIZE:
            raise HTTPException(status_code=400, detail=f"Файл слишком большой (макс. {MAX_FILE_SIZE // 1024 // 1024} MB)")
            
        # Возвращаемся в начало файла для дальнейшей обработки
        await cover_photo.seek(0)
        
        # Проверка типа файла
        if not is_valid_file(cover_photo.filename, cover_photo.content_type):
            raise HTTPException(
                status_code=400, 
                detail=f"Недопустимый формат файла. Разрешены: {', '.join(ALLOWED_EXTENSIONS)}"
            )
            
        # Сохраняем новую обложку
        cover_path = await save_cover_photo(current_user.id, cover_photo)
        
        # Добавляем путь к обложке в данные для обновления
        update_data["cover_photo"] = cover_path
        
        # Запланируем задачу на удаление старой обложки, если она была
        if hasattr(current_user, "cover_photo") and current_user.cover_photo:
            logger.info(f"Запуск очистки старой обложки: {current_user.cover_photo}")
            background_tasks.add_task(cleanup_old_cover_photo, current_user.cover_photo)
        else:
            logger.info("У пользователя нет старой обложки для удаления")

    # Выполняем обновление только если есть данные для обновления
    if update_data:
        for field, value in update_data.items():
            setattr(current_user, field, value)
            
        db.commit()
        db.refresh(current_user)
        logger.info("Профиль успешно обновлен")
        return {
            "status": "success",
            "message": "Профиль успешно обновлен",
            "data": current_user
        }
    else:
        raise HTTPException(status_code=400, detail="Нет данных для обновления")
    
@router.get("/", response_model=List[UserResponse])
def get_users_by_ids(
    ids: List[int] = Query(..., description="Список ID пользователей"),
    db: Session = Depends(get_db)
):
    users = db.query(User).filter(User.id.in_(ids)).all()
    if not users:
        raise HTTPException(status_code=404, detail="Пользователи не найдены")
    
    # Сериализуем пользователей с полем roles
    return [serialize_user(user) for user in users]
    
@router.post("/me/send-email-verification", response_model=Any)
def send_email_verification_request(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    Отправка ссылки для подтверждения email пользователя.
    """
    try:
        send_email_verification(db, current_user.id)
        return {"message": "Ссылка для подтверждения email отправлена"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/me/send-phone-verification", response_model=Any)
def send_phone_verification_request(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    Отправка кода для подтверждения номера телефона пользователя.
    """
    try:
        send_phone_verification(db, current_user.id)
        return {"message": "Код подтверждения отправлен на указанный номер телефона"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/me/verify-phone", response_model=Any)
def verify_phone(
    *,
    db: Session = Depends(get_db),
    code: str = Body(..., embed=True),
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    Подтверждение номера телефона с помощью кода.
    """
    try:
        verify_phone_code_service(db, current_user.id, code)
        return {"message": "Номер телефона успешно подтвержден"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

# Маршрут для проверки email остается публичным, так как пользователь переходит по ссылке
@router.get("/verify-email", response_model=Any)
def verify_email(
    token: str,
    db: Session = Depends(get_db)
) -> Any:
    """
    Верификация email по токену из ссылки.
    """
    try:
        user = verify_email_token_service(db, token)
        return {"message": "Email успешно подтвержден"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
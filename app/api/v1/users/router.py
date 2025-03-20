import logging
from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, Body, Path, UploadFile, logger
from sqlalchemy.orm import Session
from typing import Any, Optional
from app.api.deps import get_db, get_current_user
from app.models.user import User
from app.services.auth import (
    send_email_verification, 
    send_phone_verification, 
    verify_email_token_service, 
    verify_phone_code_service
)
from app.schemas.user import UserBase, UserProfileUpdate, UserProfileUpdate
from app.services.user import cleanup_old_avatar, is_valid_file, save_avatar

ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "gif", "webp"}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/me", response_model=UserBase)
def get_user_profile(
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    Получение профиля текущего пользователя.
    """
    return current_user

@router.patch("/me", response_model=UserProfileUpdate)
async def update_user_profile(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    user_data: Optional[str] = Form(None),
    avatar: Optional[UploadFile] = File(None)
) -> Any:
    """
    Частичное обновление профиля пользователя.
    """
    if not user_data and not avatar:
        raise HTTPException(status_code=400, detail="Нет данных для обновления")
    update_data = {}
    if user_data:
        try:
            from json import loads
            user_update = UserProfileUpdate.model_validate(loads(user_data))
            update_data = user_update.model_dump(exclude_unset=True)
        except Exception as e:
            logger.error(f"Error parsing user data: {e}")
            raise HTTPException(status_code=400, detail="Неверный формат данных профиля")
    # Обработка аватара, если он был отправлен
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
        # Добавляем путь к аватару в данные для обновления
        update_data["avatar"] = avatar_path
        # Запланируем задачу на удаление старого аватара, если он был
        if current_user.avatar:
            logger.info(f"Запуск очистки старого аватара: {current_user.avatar}")
            background_tasks.add_task(cleanup_old_avatar, current_user.avatar)
        else:
            logger.info("У пользователя нет старого аватара для удаления")

    # Выполняем обновление только если есть данные для обновления
    if update_data:
        for field, value in update_data.items():
            setattr(current_user, field, value)
            
        db.commit()
        db.refresh(current_user)
        
        return {
            "status": "success",
            "message": "Профиль успешно обновлен",
            "data": current_user
        }
    else:
        raise HTTPException(status_code=400, detail="Нет данных для обновления")

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
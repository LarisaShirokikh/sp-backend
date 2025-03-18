from fastapi import APIRouter, Depends, HTTPException, Body, Path
from sqlalchemy.orm import Session
from typing import Any
from app.api.deps import get_db, get_current_user
from app.models.user import User
from app.services.auth import (
    send_email_verification, 
    send_phone_verification, 
    verify_email_token_service, 
    verify_phone_code_service
)
from app.schemas.user import UserBase, UserUpdate

router = APIRouter()

@router.get("/me", response_model=UserBase)
def get_user_profile(
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    Получение профиля текущего пользователя.
    """
    return current_user

@router.put("/me", response_model=UserBase)
def update_user_profile(
    *,
    db: Session = Depends(get_db),
    user_in: UserUpdate,
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    Обновление профиля пользователя.
    """
    # Здесь должна быть логика обновления профиля
    return current_user

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
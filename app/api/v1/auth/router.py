# app/api/v1/auth/router.py
from datetime import timedelta
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from app.core.config import settings
from app.schemas.auth import AuthResponse
from app.schemas.token import Token
from app.schemas.user import UserCreate
from app.db.session import get_db
from app.services.auth import (
    login_user,
    register_new_user,
    verify_email_code_service,
    verify_phone_code_service,
    password_recovery_service,
)

router = APIRouter()

@router.post("/login", response_model=Token)
def login_access_token(
    db: Session = Depends(get_db),
    form_data: OAuth2PasswordRequestForm = Depends()
) -> Any:
    result = login_user(db, username=form_data.username, password=form_data.password)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный email или пароль",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token, user = result
    return {"access_token": token, "token_type": "bearer"}

@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
def register_user_endpoint(
    *,
    db: Session = Depends(get_db),
    user_in: UserCreate,
) -> Any:
    try:
        token, user = register_new_user(db, user_in)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    return {"access_token": token, "token_type": "bearer", "user": user}

@router.post("/verify-email", status_code=status.HTTP_200_OK)
def verify_email_endpoint(
    *,
    db: Session = Depends(get_db),
    email: str,
    code: str,
):
    try:
        verify_email_code_service(db, email, code)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"message": "Email успешно подтвержден"}

@router.post("/verify-phone", status_code=status.HTTP_200_OK)
def verify_phone_endpoint(
    *,
    db: Session = Depends(get_db),
    phone: str,
    code: str,
):
    try:
        verify_phone_code_service(db, phone, code)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"message": "Телефон успешно подтвержден"}

@router.post("/password-recovery/{email}")
def password_recovery_endpoint(
    email: str,
    db: Session = Depends(get_db),
) -> Any:
    try:
        password_recovery_service(db, email)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return {"message": "Инструкции по сбросу пароля отправлены на email"}
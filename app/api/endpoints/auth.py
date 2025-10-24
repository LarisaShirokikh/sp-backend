# app/api/v1/auth/router.py
from datetime import timedelta
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordRequestForm
from jose import jwt
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import settings
from app.core.security import ALGORITHM
from app.models.user import User
from app.schemas.response import AuthResponse
from app.schemas.token import Token
from app.schemas.user import UserCreate, UserLogin, UserResponse
from app.db.session import get_db
from app.services.auth import (
    login_user,
    register_new_user,
    verify_email_token_service,
    verify_phone_code_service,
    password_recovery_service,
)
from app.services.token_service import TokenService
from app.utils.serialization import serialize_user

router = APIRouter()


@router.post("/login", response_model=AuthResponse)
async def login_access_token(
    db: Session = Depends(get_db),
    form_data: OAuth2PasswordRequestForm = Depends(),
    request: Request = None
):
    result = login_user(db, username=form_data.username, password=form_data.password)
    if result is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Неверный email или пароль")
    
    _, user = result

    access_token = await TokenService.create_token(user.id, timedelta(minutes=15), "access", request)
    refresh_token = await TokenService.create_token(user.id, timedelta(days=30), "refresh", request)

    response = JSONResponse(content={
        "user": serialize_user(user),
        "description": "Authentication successful"
    })
    response.set_cookie("access_token", access_token, httponly=True, secure=True, samesite="Lax", max_age=15 * 60)
    response.set_cookie("refresh_token", refresh_token, httponly=True, secure=True, samesite="Lax", max_age=30 * 24 * 60 * 60)
    return response


@router.post("/login/email", response_model=AuthResponse)
async def login_email(
    *,
    db: Session = Depends(get_db),
    user_in: UserLogin,
    request: Request
):
    result = login_user(db, user_in.email, user_in.password)
    if not result:
        raise HTTPException(status_code=400, detail="Неверный email или пароль")

    _, user = result

    access_token = await TokenService.create_token(user.id, timedelta(minutes=15), "access", request)
    refresh_token = await TokenService.create_token(user.id, timedelta(days=30), "refresh", request)

    response = JSONResponse(content={
        "user": jsonable_encoder(serialize_user(user)),
        "description": "Authentication successful"
    })
    response.set_cookie("access_token", access_token, httponly=True, secure=True, samesite="Lax", max_age=15 * 60)
    response.set_cookie("refresh_token", refresh_token, httponly=True, secure=True, samesite="Lax", max_age=30 * 24 * 60 * 60)
    return response


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def register_user_endpoint(
    *,
    db: Session = Depends(get_db),
    user_in: UserCreate,
    request: Request
) -> AuthResponse:
    try:
        _, user = register_new_user(db, user_in)

        access_token = await TokenService.create_token(
            user.id, timedelta(minutes=15), "access", request
        )
        refresh_token = await TokenService.create_token(
            user.id, timedelta(days=30), "refresh", request
        )

       
        response = JSONResponse(
            status_code=status.HTTP_201_CREATED,
            content=jsonable_encoder({
                "user": user,
                "access_token": access_token,
                "token_type": "bearer",
            })
        )
        response.set_cookie(
            key="access_token",
            value=access_token,
            httponly=True,
            secure=True,
            samesite="Lax",
            max_age=15 * 60
        )
        response.set_cookie(
            key="refresh_token",
            value=refresh_token,
            httponly=True,
            secure=True,
            samesite="Lax",
            max_age=30 * 24 * 60 * 60
        )

        return response

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/logout")
async def logout(request: Request):
    access_token = request.cookies.get("access_token")
    refresh_token = request.cookies.get("refresh_token")

    if access_token:
        try:
            payload = jwt.decode(access_token, settings.SECRET_KEY, algorithms=[ALGORITHM])
            await TokenService.invalidate_token(payload["jti"], "access", int(payload["sub"]))
        except Exception:
            pass

    if refresh_token:
        try:
            payload = jwt.decode(refresh_token, settings.SECRET_KEY, algorithms=[ALGORITHM])
            await TokenService.invalidate_token(payload["jti"], "refresh", int(payload["sub"]))
        except Exception:
            pass

    response = JSONResponse(content={"msg": "Выход выполнен"})
    response.delete_cookie("access_token")
    response.delete_cookie("refresh_token")
    return response



@router.post("/refresh")
async def refresh_token(request: Request):
    refresh_token = request.cookies.get("refresh_token")
    if not refresh_token:
        raise HTTPException(status_code=401, detail="Нет refresh токена")

    try:
        payload = jwt.decode(refresh_token, settings.SECRET_KEY, algorithms=[ALGORITHM])
        user_id = int(payload["sub"])
        jti = payload["jti"]
    except Exception:
        raise HTTPException(status_code=401, detail="Невалидный refresh токен")

    await TokenService.invalidate_token(jti, "refresh", user_id)

    new_access_token = await TokenService.create_token(user_id, timedelta(minutes=15), "access", request)
    new_refresh_token = await TokenService.create_token(user_id, timedelta(days=30), "refresh", request)

    response = JSONResponse(content={"msg": "Токены обновлены"})
    response.set_cookie("access_token", new_access_token, httponly=True, secure=True, samesite="Lax", max_age=15 * 60)
    response.set_cookie("refresh_token", new_refresh_token, httponly=True, secure=True, samesite="Lax", max_age=30 * 24 * 60 * 60)
    return response



@router.get("/sessions")
async def list_sessions(current_user: User = Depends(get_current_user)):
    sessions = await TokenService.list_user_sessions(current_user.id)
    return {"sessions": sessions}


@router.post("/verify-email")
def verify_email_endpoint(
    *,
    db: Session = Depends(get_db),
    email: str,
    code: str,
):
    try:
        verify_email_token_service(db, email, code)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"message": "Email успешно подтвержден"}


@router.post("/verify-phone")
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
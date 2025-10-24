from datetime import datetime, timezone
import logging
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt
from sqlalchemy.orm import Session

from app import models, schemas
from app.core import security
from app.core.config import settings
from app.crud.user import user as user_crud
from app.db.redis import get_redis_client
from app.db.session import get_db
from app.models.user import User
from app.schemas.token import TokenPayload

import logging

from app.services.token_service import TokenService
logger = logging.getLogger(__name__)

# URL для получения токена
reusable_oauth2 = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/auth/login"
)


async def get_current_user(
    request: Request,
    db: Session = Depends(get_db)
) -> User:
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(status_code=401, detail="Нет access токена")

    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id: str = payload.get("sub")
        jti: str = payload.get("jti")
        token_type: str = payload.get("type", "access")

        if not all([user_id, jti]):
            raise HTTPException(status_code=401, detail="Неверный токен")

        is_valid = await TokenService.is_token_valid(jti, token_type, user_id)
        if not is_valid:
            raise HTTPException(status_code=401, detail="Недействительный токен")

        user = user_crud.get(db, id=int(user_id))
        if not user or not user_crud.is_active(user):
            raise HTTPException(status_code=403, detail="Пользователь не найден или неактивен")

        return user
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Токен истек")
    except jwt.JWTError:
        raise HTTPException(status_code=401, detail="Неверный токен")

def get_current_active_user(
    current_user: models.User = Depends(get_current_user),
) -> models.User:
    """
    Проверка активного статуса пользователя
    """
    if not user_crud.is_active(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="Неактивный пользователь"
        )
    return current_user


def get_current_organizer(
    current_user: models.User = Depends(get_current_active_user),
) -> models.User:
    """
    Проверка роли организатора
    """
    if not user_crud.is_organizer(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Недостаточно прав"
        )
    return current_user


def get_current_admin(
    current_user: models.User = Depends(get_current_active_user),
) -> models.User:
    """
    Проверка роли администратора
    """
    if not user_crud.is_admin(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Недостаточно прав"
        )
    return current_user


def get_current_active_superuser(
    current_user: models.User = Depends(get_current_active_user),
) -> models.User:
    """
    Проверка является ли пользователь суперадмином
    """
    if not user_crud.is_super_admin(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Пользователь не является суперадминистратором"
        )
    return current_user
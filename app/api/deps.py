from datetime import datetime, timezone
import logging
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt
from sqlalchemy.orm import Session

from app import models, schemas
from app.core import security
from app.core.config import settings
from app.crud.user import user as user_crud
from app.db.session import get_db
from app.models.user import User
from app.schemas.token import TokenPayload

import logging
logger = logging.getLogger(__name__)

# URL для получения токена
reusable_oauth2 = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/auth/login"
)


def get_current_user(
    db: Session = Depends(get_db), token: str = Depends(reusable_oauth2)
) -> models.User:
    """
    Получение текущего аутентифицированного пользователя с расширенной диагностикой.
    """
    try:
        # Подробное логирование токена для диагностики
        logger.info(f"Received token: {token}")
        logger.info(f"Secret Key: {settings.SECRET_KEY}")
        logger.info(f"Algorithm: {security.ALGORITHM}")

        # Декодирование токена с полной отладкой
        payload = jwt.decode(
            token, 
            settings.SECRET_KEY, 
            algorithms=[security.ALGORITHM]
        )
        
        # Подробное логирование payload
        logger.info(f"Decoded payload: {payload}")
        
        user_id: str = payload.get("sub")
        token_exp: int = payload.get("exp")
        
        # Проверка наличия обязательных полей
        if user_id is None or token_exp is None:
            logger.error("Отсутствуют обязательные поля в токене")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Некорректный токен",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Проверка истечения токена
        current_time = int(datetime.now(timezone.utc).timestamp())
        logger.info(f"Current time: {current_time}")
        logger.info(f"Token expiration: {token_exp}")
        
        if current_time > token_exp:
            logger.error("Токен истек")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Токен истек",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Получение пользователя
        user = user_crud.get(db, id=int(user_id))
        
        if user is None:
            logger.error(f"Пользователь с ID {user_id} не найден")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail="Пользователь не найден"
            )
        
        if not user_crud.is_active(user):
            logger.error(f"Пользователь {user_id} неактивен")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, 
                detail="Пользователь неактивен"
            )
        
        return user
    
    except jwt.ExpiredSignatureError:
        logger.error("Токен истек (ExpiredSignatureError)")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Токен истек",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.JWTError as e:
        logger.error(f"Ошибка декодирования JWT: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Не удалось проверить учетные данные",
            headers={"WWW-Authenticate": "Bearer"},
        )

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
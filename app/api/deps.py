from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt
from jose.exceptions import JWTError
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app import models, schemas
from app.core import security
from app.core.config import settings
from app.crud.user import user as user_crud
from app.db.session import get_db
from app.models.user import User
from app.schemas.token import TokenPayload

# URL для получения токена
reusable_oauth2 = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/auth/login"
)


def get_current_user(
    db: Session = Depends(get_db), token: str = Depends(reusable_oauth2)
) -> User:
    """
    Получение текущего аутентифицированного пользователя.
    """
    try:
        
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[security.ALGORITHM]
        )
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Не удалось проверить учетные данные",
                headers={"WWW-Authenticate": "Bearer"},
            )
    except (JWTError, ValidationError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Не удалось проверить учетные данные",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user = user_crud.get(db, id=int(user_id))
    if user is None:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    if not user_crud.is_active(user):
        raise HTTPException(status_code=400, detail="Пользователь неактивен")
    
    return user


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
# appcore/security.py
from datetime import datetime, timedelta
from typing import Any, Union, Optional

from jose import jwt
from passlib.context import CryptContext
from app.core.config import settings

# Контекст для хеширования паролей
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Алгоритм для JWT
ALGORITHM = "HS256"


def create_access_token(
    subject: Union[str, Any], expires_delta: Optional[timedelta] = None
) -> str:
    """
    Создание JWT токена доступа
    """
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
    to_encode = {"exp": expire, "sub": str(subject)}
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Проверка пароля
    """
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:

    """
    Хеширование пароля
    """
    return pwd_context.hash(password)

def create_verification_token(user_id: int, token_type: str, expires_delta: Optional[timedelta] = None) -> str:
    """
    Создает токен для верификации email или сброса пароля.
    
    Args:
        user_id: ID пользователя
        token_type: Тип токена ('email' или 'password')
        expires_delta: Срок действия токена
    """
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        # По умолчанию токен действителен 24 часа
        expire = datetime.utcnow() + timedelta(hours=24)
    
    to_encode = {
        "exp": expire,
        "sub": str(user_id),
        "type": token_type
    }
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

def verify_token(token: str, token_type: str) -> Optional[int]:
    """
    Проверяет токен верификации.
    
    Args:
        token: JWT токен
        token_type: Ожидаемый тип токена ('email' или 'password')
        
    Returns:
        ID пользователя если токен действителен, иначе None
    """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id = payload.get("sub")
        token_t = payload.get("type")
        
        if token_t != token_type or not user_id:
            return None
            
        return int(user_id)
    except jwt.PyJWTError:
        return None
import re
from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Optional
from datetime import datetime
from app.models.user import UserRole


# Базовая схема для всех моделей
class BaseSchema(BaseModel):
    class Config:
        orm_mode = True


# Общие поля пользователя
class UserBase(BaseSchema):
    """Базовая схема пользователя"""
    email: EmailStr
    name: str
    full_name: Optional[str] = None
    phone: Optional[str] = None
    description: Optional[str] = None
    role: UserRole
    is_active: bool = True
    is_verified: bool = False
    is_phone_verified: bool = False
    avatar_url: Optional[str] = None
    cover_photo: Optional[str] = None


# Схема для создания пользователя
class UserCreate(BaseModel):
    """Схема для создания пользователя"""
    name: str
    email: EmailStr
    password: str
    full_name: Optional[str] = None
    phone: str
    role: Optional[UserRole] = UserRole.user
    
    @field_validator("password")
    def password_min_length(cls, v):
        if len(v) < 8:
            raise ValueError("Пароль должен содержать минимум 8 символов")
        return v
    
    @field_validator("phone")
    def validate_phone(cls, v):
        if v is None:
            return v
            
        # Очистка от пробелов, дефисов и пр.
        cleaned = re.sub(r'[^0-9+]', '', v)
        
        # Проверка формата (должен начинаться с + или 7 или 8, всего 11-12 цифр)
        if not re.match(r'^(\+7|7|8)\d{10}$', cleaned):
            raise ValueError("Неверный формат номера телефона")
        
        # Приведение к формату 7XXXXXXXXXX
        if cleaned.startswith("+7"):
            return cleaned[1:]  # Убираем +
        elif cleaned.startswith("8"):
            return "7" + cleaned[1:]  # Заменяем 8 на 7
        
        return cleaned


# Схема для обновления пользователя
class UserProfileUpdate(BaseSchema):
    email: Optional[EmailStr] = None
    name: Optional[str] = None
    full_name: Optional[str] = None
    phone: Optional[str] = None
    description: Optional[str] = None
    avatar_url: Optional[str] = None
    password: Optional[str] = None
    cover_photo: Optional[str] = None
    
    @field_validator('password')
    def password_complexity(cls, v):
        if v is None:
            return v
        if len(v) < 8:
            raise ValueError('Пароль должен быть не менее 8 символов')
        if not any(char.isdigit() for char in v):
            raise ValueError('Пароль должен содержать хотя бы одну цифру')
        if not any(char.isupper() for char in v):
            raise ValueError('Пароль должен содержать хотя бы одну заглавную букву')
        return v


# Схема для ответа при получении пользователя
class UserResponse(UserBase):
    id: int
    name: str
    email: EmailStr
    avatar_url: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    is_verified: bool
    followers_count: int
    following_count: int

    class Config:
        orm_mode = True

# Схема для админ-ответа (с дополнительными полями)
class UserAdminResponse(UserResponse):
    is_superuser: bool

# Краткая информация о пользователе для публичных ответов
class UserPublic(BaseSchema):
    id: int
    name: str
    full_name: Optional[str]
    role: UserRole
    avatar_url: Optional[str]
    rating: Optional[int]
    followers_count: int
    following_count: int

class UserVerifyPhone(BaseModel):
    """Схема для верификации телефона"""
    phone: str
    code: str
    
    @field_validator("phone")
    def validate_phone(cls, v):
        # Очистка от пробелов, дефисов и пр.
        cleaned = re.sub(r'[^0-9+]', '', v)
        
        # Проверка формата (должен начинаться с + или 7 или 8, всего 11-12 цифр)
        if not re.match(r'^(\+7|7|8)\d{10}$', cleaned):
            raise ValueError("Неверный формат номера телефона")
        
        # Приведение к формату 7XXXXXXXXXX
        if cleaned.startswith("+7"):
            return cleaned[1:]  # Убираем +
        elif cleaned.startswith("8"):
            return "7" + cleaned[1:]  # Заменяем 8 на 7
        
        return cleaned
    
    @field_validator("code")
    def validate_code(cls, v):
        # Проверяем, что код состоит из 6 цифр
        if not re.match(r'^\d{6}$', v):
            raise ValueError("Код должен состоять из 6 цифр")
        return v
    
class UserLogin(BaseModel):
    """Схема для входа пользователя"""
    email: EmailStr
    password: str
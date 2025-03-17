from pydantic import BaseModel, EmailStr, Field, field_validator, validator
from typing import Optional
from datetime import datetime
from app.models.user import UserRole


# Базовая схема для всех моделей
class BaseSchema(BaseModel):
    class Config:
        orm_mode = True


# Общие поля пользователя
class UserBase(BaseSchema):
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    phone: Optional[str] = None
    role: Optional[UserRole] = None
    is_active: Optional[bool] = True
    description: Optional[str] = None
    avatar_url: Optional[str] = None


# Схема для создания пользователя
class UserCreate(BaseSchema):
    email: EmailStr
    password: str = Field(..., min_length=8)
    full_name: Optional[str] = None
    phone: Optional[str] = None
    role: Optional[UserRole] = UserRole.user
    
    @field_validator('password')
    def password_complexity(cls, v):
        # Проверка сложности пароля
        if len(v) < 8:
            raise ValueError('Пароль должен быть не менее 8 символов')
        if not any(char.isdigit() for char in v):
            raise ValueError('Пароль должен содержать хотя бы одну цифру')
        if not any(char.isupper() for char in v):
            raise ValueError('Пароль должен содержать хотя бы одну заглавную букву')
        return v


# Схема для обновления пользователя
class UserUpdate(BaseSchema):
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    phone: Optional[str] = None
    description: Optional[str] = None
    avatar_url: Optional[str] = None
    password: Optional[str] = None
    
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
    created_at: datetime
    updated_at: datetime
    is_verified: bool
    followers_count: int
    following_count: int


# Схема для админ-ответа (с дополнительными полями)
class UserAdminResponse(UserResponse):
    is_superuser: bool


# Краткая информация о пользователе для публичных ответов
class UserPublic(BaseSchema):
    id: int
    full_name: Optional[str]
    role: UserRole
    avatar_url: Optional[str]
    rating: Optional[int]
    followers_count: int
    following_count: int
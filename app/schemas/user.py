import re
from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Optional, List
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
    roles: List[UserRole] = []
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
    roles: Optional[List[UserRole]] = Field(default_factory=lambda: [UserRole.user])

    @field_validator("password")
    def password_min_length(cls, v):
        if len(v) < 8:
            raise ValueError("Пароль должен содержать минимум 8 символов")
        return v

    @field_validator("phone")
    def validate_phone(cls, v):
        if v is None:
            return v

        cleaned = re.sub(r'[^0-9+]', '', v)
        if not re.match(r'^(\+7|7|8)\d{10}$', cleaned):
            raise ValueError("Неверный формат номера телефона")

        if cleaned.startswith("+7"):
            return cleaned[1:]
        elif cleaned.startswith("8"):
            return "7" + cleaned[1:]
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
    roles: Optional[List[UserRole]] = None

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
    roles: List[str]
    avatar_url: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    is_verified: bool
    followers_count: int
    following_count: int

    class Config:
        orm_mode = True

# Схема для админ-ответа
class UserAdminResponse(UserResponse):
    is_superuser: bool

# Публичный профиль пользователя
class UserPublic(BaseSchema):
    id: int
    name: str
    full_name: Optional[str]
    roles: List[UserRole] = []
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
        cleaned = re.sub(r'[^0-9+]', '', v)
        if not re.match(r'^(\+7|7|8)\d{10}$', cleaned):
            raise ValueError("Неверный формат номера телефона")
        if cleaned.startswith("+7"):
            return cleaned[1:]
        elif cleaned.startswith("8"):
            return "7" + cleaned[1:]
        return cleaned

    @field_validator("code")
    def validate_code(cls, v):
        if not re.match(r'^\d{6}$', v):
            raise ValueError("Код должен состоять из 6 цифр")
        return v

class UserLogin(BaseModel):
    """Схема для входа пользователя"""
    email: EmailStr
    password: str


class UserUpdateRequest(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    full_name: Optional[str] = None
    phone: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None
    is_verified: Optional[bool] = None
    is_superuser: Optional[bool] = None
    
class UserRoleUpdateRequest(BaseModel):
    roles: List[str]
    
class UserStatusUpdateRequest(BaseModel):
    is_active: bool

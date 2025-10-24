# app/schemas/admin.py
from typing import Dict, List, Optional, Union, Any
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field

# Схемы для активностей в админке
class ActivityUser(BaseModel):
    id: int
    name: str

class AdminActivity(BaseModel):
    id: int
    type: str = Field(..., description="Тип активности: success, warning, error, info")
    message: str
    timestamp: datetime
    user: Optional[ActivityUser] = None
    details: Optional[str] = None

    class Config:
        orm_mode = True

# Схемы для статистики
class ChartPoint(BaseModel):
    name: str
    users: int

class DayData(BaseModel):
    day: str
    users: int

class DashboardStats(BaseModel):
    totalUsers: int
    activeUsers: int
    newUsers: int
    totalOrders: int
    userGrowth: Optional[List[ChartPoint]] = None
    activeUsersByDay: Optional[List[DayData]] = None

# Схемы для заказов в админке
class OrderBasic(BaseModel):
    id: int
    order_number: str
    customer_name: str
    amount: float
    status: str
    created_at: datetime

    class Config:
        orm_mode = True

# Схемы для пользователей в админке
class UserRole(BaseModel):
    role: str

class AdminUserBasic(BaseModel):
    id: int
    name: str
    email: str
    full_name: Optional[str] = None
    is_active: bool
    is_verified: bool
    is_superuser: bool
    roles: List[str] = []

    class Config:
        orm_mode = True

class AdminUserDetail(AdminUserBasic):
    phone: Optional[str] = None
    is_phone_verified: bool = False
    description: Optional[str] = None
    rating: int = 0
    avatar_url: Optional[str] = None
    followers_count: int = 0
    following_count: int = 0

    class Config:
        orm_mode = True

# Схемы для настроек сайта
class SiteSettings(BaseModel):
    site_name: str
    description: Optional[str] = None
    contact_email: EmailStr
    maintenance_mode: bool = False
    registration_enabled: bool = True
    theme: str = "light"
    social_media: Optional[Dict[str, str]] = None
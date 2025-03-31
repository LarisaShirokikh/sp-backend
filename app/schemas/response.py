# app/schemas/auth.py
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel
from app.schemas.token import Token  # если нужно, можно использовать Token вместо отдельных полей
from app.schemas.user import UserResponse

class AuthResponse(BaseModel):
    user: UserResponse
    access_token: str
    token_type: str = "bearer"

    class Config:
        orm_mode = True

class TagResponse(BaseModel):
    id: int
    name: str
    slug: Optional[str] = None
    description: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        orm_mode = True

class TopicResponse(BaseModel):
    id: int
    title: str
    content: str
    category_id: int
    user_id: int
    created_at: datetime
    updated_at: datetime
    tags: Optional[List[TagResponse]] = []

    class Config:
        orm_mode = True


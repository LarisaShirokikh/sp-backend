from typing import List, Optional
from pydantic import BaseModel, field_validator
from datetime import datetime

from app.schemas.base import ORMModel


class CategoryBase(BaseModel):
    
    name: Optional[str] = None
    description: Optional[str] = None
    is_visible: Optional[bool] = True
    order: Optional[int] = 0


class CategoryCreate(CategoryBase):
    name: str  # Только имя обязательно


class CategoryUpdate(CategoryBase):
    pass  # Всё опционально для PATCH


class Category(CategoryBase):
    id: int
    created_at: datetime
    updated_at: datetime
    topic_count: int = 0
    post_count: int = 0

    class Config:
        orm_mode = True


class TagBase(BaseModel):
    name: str
    description: Optional[str] = None
    color: Optional[str] = "#f3f4f6"  # светло-серый по умолчанию


class TagCreate(TagBase):
    pass


class TagUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    color: Optional[str] = None


class Tag(TagBase, ORMModel):
    id: int
    created_at: datetime


class TopicBase(BaseModel):
    title: str
    content: Optional[str] = None
    category_id: int


class TopicCreate(TopicBase):
    tags: Optional[List[int]] = None

    @field_validator('title')
    def validate_title(cls, v):
        """Валидация заголовка топика"""
        if len(v) < 3:
            raise ValueError('Заголовок должен содержать минимум 3 символа')
        if len(v) > 255:
            raise ValueError('Заголовок не может превышать 255 символов')
        return v
    
    @field_validator('content')
    def validate_content(cls, v):
        """Опциональная валидация контента"""
        if v and len(v) > 10000:
            raise ValueError('Содержание топика слишком длинное')
        return v

    @field_validator('tags')
    def validate_tags(cls, v):
        """Валидация списка тегов"""
        if v is not None:
            if len(v) > 5:
                raise ValueError('Нельзя добавить более 5 тегов')
            if len(set(v)) != len(v):
                raise ValueError('Теги не должны повторяться')
        return v


class TopicUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    category_id: Optional[str] = None
    tags: Optional[List[str]] = None


class Topic(ORMModel):
    id: int
    title: str
    content: Optional[str]
    user_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    view_count: int
    reply_count: int
    like_count: int
    dislike_count: int
    save_count: int
    is_pinned: bool
    is_locked: bool
    last_reply_at: Optional[datetime]

    tags: List[Tag] = []
    
    

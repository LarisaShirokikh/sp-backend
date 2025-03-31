from typing import List, Optional
from pydantic import BaseModel, Field, field_validator
from datetime import datetime

from app.schemas.base import ORMModel
from app.schemas.user import UserPublic


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


class TopicFile(BaseModel):
    id: int
    topic_id: Optional[int] = None
    reply_id: Optional[int] = None
    file_path: str
    file_name: str
    file_type: str
    created_at: datetime
    url: Optional[str] = None  # URL для доступа к файлу
    
    class Config:
        orm_mode = True


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

# Базовая схема для ответа
class ReplyBase(BaseModel):
    content: str


# Схема для создания ответа
class ReplyCreate(ReplyBase):
    topic_id: int

# Схема для ответа, возвращаемого API
class Reply(ReplyBase):
    id: int
    topic_id: int
    author_id: int
    created_at: datetime
    updated_at: datetime
    like_count: int = 0
    media: Optional[List[TopicFile]] = []
    
    class Config:
        orm_mode = True

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
    is_pinned: bool = False
    is_locked: bool = False
    last_reply_at: Optional[datetime] = None

    tags: List[Tag] = []
    files: List[TopicFile] = []  
    category: Optional[Category] = None
    replies: Optional[List[Reply]] = []
    media: Optional[List[TopicFile]] = []
    
    class Config:
        orm_mode = True


class TopicResponse(Topic):
    pass


class ReplyWithMedia(Reply):
    media: List[TopicFile] = []


# Определите класс ReplyContent перед объявлением роутов
class ReplyContent(BaseModel):
    """
    Схема для валидации содержимого ответа на тему форума
    """
    content: str = Field(..., description="Содержание ответа")
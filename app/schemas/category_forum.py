from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime

from app.schemas.base import ORMModel


class CategoryBase(ORMModel):
    name: Optional[str] = None
    description: Optional[str] = None
    is_visible: Optional[bool] = True
    order: Optional[int] = 0


class CategoryCreate(CategoryBase):
    name: str  # Только имя обязательно


class CategoryUpdate(CategoryBase):
    pass  # Всё опционально для PATCH


class Category(CategoryBase, ORMModel):
    
    created_at: datetime
    updated_at: datetime
    topic_count: int = 0
    post_count: int = 0


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
    tags: Optional[List[str]] = []  # список id тегов


class TopicUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    category_id: Optional[str] = None
    tags: Optional[List[str]] = None


class Topic(ORMModel):
    id: int
    title: str
    content: Optional[str]
    category_id: str
    author_id: Optional[str]
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
    
    

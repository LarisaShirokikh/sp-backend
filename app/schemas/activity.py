from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum


class ActivityType(str, Enum):
    """
    Типы активностей пользователей в системе.
    """
    POST = "post"     # Создание новой темы
    REPLY = "reply"   # Ответ на тему
    LIKE = "like"     # Лайк темы или ответа


class ActivityUserBase(BaseModel):
    """
    Базовая схема данных пользователя для активностей.
    """
    id: int
    name: str
    avatar_url: Optional[str] = None


class TopicBase(BaseModel):
    """
    Базовая схема данных темы для активностей.
    """
    id: int
    title: str


class ReplyBase(BaseModel):
    """
    Базовая схема данных ответа для активностей.
    """
    id: int
    content: str
    topic_id: int


class ActivityBase(BaseModel):
    """
    Базовая схема для активностей.
    """
    type: ActivityType
    content: Optional[str] = None
    link: Optional[str] = None


class ActivityCreate(ActivityBase):
    """
    Схема для создания новой записи активности.
    """
    topic_id: Optional[int] = None
    reply_id: Optional[int] = None


class ActivityUpdate(BaseModel):
    """
    Схема для обновления активности (если нужно).
    """
    content: Optional[str] = None
    link: Optional[str] = None


class ActivityOut(ActivityBase):
    """
    Схема для вывода данных активности.
    """
    id: int
    user: ActivityUserBase
    created_at: datetime
    entity_id: Optional[int] = None  # ID связанной сущности (темы или ответа)
    
    class Config:
        orm_mode = True


class ActivityDetailsOut(ActivityOut):
    """
    Расширенная схема для вывода данных активности с дополнительной информацией.
    """
    topic: Optional[TopicBase] = None
    reply: Optional[ReplyBase] = None
    
    class Config:
        orm_mode = True


class ActivityPaginationOut(BaseModel):
    """
    Схема для пагинации списка активностей.
    """
    items: List[ActivityOut]
    total: int
    page: int
    size: int
    pages: int
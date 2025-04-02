# app/models/activity.py
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Enum
from sqlalchemy.orm import relationship
import enum
from datetime import datetime

from app.models import Base


class ActivityType(str, enum.Enum):
    POST = "post"  # Создание новой темы
    REPLY = "reply"  # Ответ на тему
    LIKE = "like"  # Лайк темы или ответа


class Activity(Base):
    __tablename__ = "activities"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    type = Column(Enum(ActivityType), nullable=False)
    topic_id = Column(Integer, ForeignKey("topics.id"), nullable=True)
    reply_id = Column(Integer, ForeignKey("forum_replies.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Отношения
    user = relationship("User", back_populates="activities")
    topic = relationship("TopicModel", back_populates="activities")
    reply = relationship("ReplyModel", back_populates="activities")


# app/schemas/activity.py
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum


class ActivityType(str, Enum):
    POST = "post"
    REPLY = "reply"
    LIKE = "like"


class ActivityUserBase(BaseModel):
    id: int
    name: str
    avatar_url: Optional[str] = None


class ActivityBase(BaseModel):
    type: ActivityType
    content: Optional[str] = None
    link: Optional[str] = None


class ActivityCreate(ActivityBase):
    topic_id: Optional[int] = None
    reply_id: Optional[int] = None


class ActivityOut(ActivityBase):
    id: int
    user: ActivityUserBase
    created_at: datetime
    entity_id: Optional[int] = None

    class Config:
        orm_mode = True 
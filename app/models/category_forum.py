# app/models/category_forum.py

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Table, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from app.models import Base

# ✅ Ассоциативные таблицы

topic_tags = Table(
    "topic_tags",
    Base.metadata,
    Column("topic_id", Integer, ForeignKey("topics.id"), primary_key=True),
    Column("tag_id", Integer, ForeignKey("tags.id"), primary_key=True),
)

topic_saves = Table(
    "topic_saves",
    Base.metadata,
    Column("user_id", Integer, ForeignKey("users.id"), primary_key=True),
    Column("topic_id", Integer, ForeignKey("topics.id"), primary_key=True),
)

# Modified to ensure all columns are Integer type
topic_likes = Table(
    "topic_likes",
    Base.metadata,
    Column("user_id", Integer, ForeignKey("users.id"), primary_key=True),
    Column("topic_id", Integer, ForeignKey("topics.id"), primary_key=True),
    Column("is_like", Boolean, nullable=False),
)

# ✅ Category
class CategoryModel(Base):
    __tablename__ = "categories"

    name = Column(String(255), nullable=False, unique=True, index=True)
    description = Column(Text, nullable=True)
    is_visible = Column(Boolean, default=True)
    order = Column(Integer, default=0)
    topic_count = Column(Integer, default=0)
    post_count = Column(Integer, default=0)

    topics = relationship("TopicModel", back_populates="category")

# ✅ Topic
class TopicModel(Base):
    __tablename__ = "topics"

    title = Column(String(255), nullable=False, index=True)
    content = Column(Text, nullable=True)

    category_id = Column(Integer, ForeignKey("categories.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    is_pinned = Column(Boolean, default=False)
    is_locked = Column(Boolean, default=False)
    view_count = Column(Integer, default=0)
    reply_count = Column(Integer, default=0)
    last_reply_at = Column(DateTime, nullable=True)
    like_count = Column(Integer, default=0)
    dislike_count = Column(Integer, default=0)
    save_count = Column(Integer, default=0)

    category = relationship("CategoryModel", back_populates="topics")
    author = relationship("User", back_populates="topics")

    tags = relationship("TagModel", secondary=topic_tags, back_populates="topics")
    liked_by = relationship("User", secondary=topic_likes, back_populates="liked_topics")
    saved_by = relationship("User", secondary=topic_saves, back_populates="saved_topics")

# ✅ Tag
class TagModel(Base):
    __tablename__ = "tags"

    name = Column(String(100), unique=True, nullable=False)
    description = Column(Text, nullable=True)
    color = Column(String(20), nullable=True)

    topics = relationship("TopicModel", secondary=topic_tags, back_populates="tags")
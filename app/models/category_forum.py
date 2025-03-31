# app/models/category_forum.py

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Table, Text, func
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

# Таблица для лайков ответов
reply_likes = Table(
    "reply_likes",
    Base.metadata,
    Column("reply_id", Integer, ForeignKey("forum_replies.id")),
    Column("user_id", Integer, ForeignKey("users.id")),
    Column("is_like", Boolean, default=True),
)

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
    
    # Добавляем связь с файлами
    files = relationship("TopicFileModel", back_populates="topic", cascade="all, delete-orphan")
    replies = relationship("ReplyModel", back_populates="topic", cascade="all, delete-orphan")
    

# ✅ Tag
class TagModel(Base):
    __tablename__ = "tags"

    name = Column(String(100), unique=True, nullable=False)
    description = Column(Text, nullable=True)
    color = Column(String(20), nullable=True)

    topics = relationship("TopicModel", secondary=topic_tags, back_populates="tags")

# ✅ TopicFile - новая модель для файлов
class TopicFileModel(Base):
    __tablename__ = "topic_files"
    
    id = Column(Integer, primary_key=True, index=True)
    topic_id = Column(Integer, ForeignKey("topics.id", ondelete="CASCADE"), index=True)
    file_path = Column(String(255), nullable=False)
    file_name = Column(String(255), nullable=False)
    file_type = Column(String(50), nullable=False)  # image, video, document
    created_at = Column(DateTime, default=func.now())
    
    # Отношение к топику
    topic = relationship("TopicModel", back_populates="files")


# Модель ответа на тему
class ReplyModel(Base):
    __tablename__ = "forum_replies"
    
    id = Column(Integer, primary_key=True, index=True)
    # Исправленный ForeignKey - ссылка на таблицу topics вместо forum_topics
    topic_id = Column(Integer, ForeignKey("topics.id"), nullable=False)
    content = Column(Text, nullable=False)
    author_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    like_count = Column(Integer, default=0)
    dislike_count = Column(Integer, default=0)
    
    # Связи
    topic = relationship("TopicModel", back_populates="replies")
    author = relationship("User", backref="forum_replies")
    media = relationship("ReplyFileModel", back_populates="reply", cascade="all, delete-orphan")
    
    # Для учета лайков
    liked_by = relationship(
        "User",
        secondary=reply_likes,
        backref="liked_replies",
        overlaps="author,forum_replies",
    )


# Модель медиа-файла для ответа
class ReplyFileModel(Base):
    __tablename__ = "forum_reply_files"
    
    id = Column(Integer, primary_key=True, index=True)
    reply_id = Column(Integer, ForeignKey("forum_replies.id"), nullable=False)
    file_path = Column(String(255), nullable=False)
    file_name = Column(String(255), nullable=False)
    file_type = Column(String(50), nullable=False)  # image, video, document, pdf
    created_at = Column(DateTime, default=func.now())
    
    # Связь с ответом
    reply = relationship("ReplyModel", back_populates="media")


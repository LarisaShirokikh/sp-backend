# app/models/__init.py__
from app.db.base import Base

# Импортируем ВСЕ модели, чтобы SQLAlchemy успел их зарегистрировать
from .user import User, UserRole
from .category_forum import CategoryModel, TopicModel, TagModel

__all__ = [
    "User", "UserRole",
    "CategoryModel", "TopicModel", "TagModel"
]
# app/models/user.py
from sqlalchemy import Boolean, Column, Integer, String, Enum, Text
import enum
from app.models import Base

class UserRole(str, enum.Enum):
    user = "user"
    organizer = "organizer"
    admin = "admin"
    super_admin = "super_admin"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    password = Column(String, nullable=False)
    full_name = Column(String(255), nullable=True)
    phone = Column(String(20), nullable=True)
    role = Column(Enum(UserRole), default=UserRole.user, nullable=False)
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    
    # Дополнительные поля для организаторов
    description = Column(Text, nullable=True)
    rating = Column(Integer, default=0)
    avatar = Column(String, nullable=True)
    
    # Для социальной сети
    followers_count = Column(Integer, default=0)
    following_count = Column(Integer, default=0)
    
    # Для администрирования
    is_superuser = Column(Boolean, default=False)

    # Новые поля для верификации
    email_verification_code = Column(String, nullable=True)
    phone_verification_code = Column(String, nullable=True)
    is_phone_verified = Column(Boolean, default=False)
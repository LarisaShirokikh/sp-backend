# app/models/user.py
from sqlalchemy import Boolean, Column, Integer, String, Enum, Text
import enum
from sqlalchemy.orm import relationship
from app.models import Base

class UserRole(str, enum.Enum):
    user = "user"
    organizer = "organizer"
    admin = "admin"
    super_admin = "super_admin"
    moderator = "moderator"  
    verified = "verified"    
    premium = "premium"      
    author = "author"        
    editor = "editor"        

class User(Base):
    __tablename__ = "users"

    name = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    password = Column(String, nullable=False)
    full_name = Column(String(255), nullable=True)
    phone = Column(String(20), nullable=True)
    role = Column(Enum(UserRole), default=UserRole.user, nullable=False)
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    description = Column(Text, nullable=True)
    rating = Column(Integer, default=0)
    avatar_url = Column(String, nullable=True)
    cover_photo = Column(String, nullable=True)
    followers_count = Column(Integer, default=0)
    following_count = Column(Integer, default=0)
    is_superuser = Column(Boolean, default=False)
    email_verification_code = Column(String, nullable=True)
    phone_verification_code = Column(String, nullable=True)
    is_phone_verified = Column(Boolean, default=False)

    # ✅ связи
    topics = relationship("TopicModel", back_populates="author")
    liked_topics = relationship("TopicModel", secondary="topic_likes", back_populates="liked_by")
    saved_topics = relationship("TopicModel", secondary="topic_saves", back_populates="saved_by")
    activities = relationship("Activity", back_populates="user")
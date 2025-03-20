# app/crud/user.py
from typing import Any, Dict, Optional, Union

from sqlalchemy.orm import Session

from app.core.security import get_password_hash, verify_password
from app.crud.base import CRUDBase
from app.models.user import User
from app.schemas.user import UserCreate, UserProfileUpdate
from app.utils.code import generate_verification_code


class CRUDUser(CRUDBase[User, UserCreate, UserProfileUpdate]):
    def get(self, db: Session, id: int) -> Optional[User]:
        """Получение пользователя по ID"""
        return db.query(User).filter(User.id == id).first()
    
    def get_by_email(self, db: Session, *, email: str) -> Optional[User]:
        return db.query(User).filter(User.email == email).first()
    
    def get_by_phone(self, db: Session, *, phone: str) -> Optional[User]:
        return db.query(User).filter(User.phone == phone).first()

    def create(self, db: Session, *, obj_in: UserCreate) -> User:
        db_obj = User(
            name=obj_in.name,
            email=obj_in.email,
            password=get_password_hash(obj_in.password),
            full_name=obj_in.full_name,
            phone=obj_in.phone,
            phone_verification_code=generate_verification_code(),
            is_active=True,  # По умолчанию пользователь активен сразу
            is_verified=False,  # Email не подтвержден
            is_phone_verified=False,
        )
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def update(
        self, db: Session, *, db_obj: User, obj_in: Union[UserProfileUpdate, Dict[str, Any]]
    ) -> User:
        if isinstance(obj_in, dict):
            update_data = obj_in
        else:
            update_data = obj_in.model_dump(exclude_unset=True)
        if update_data.get("password"):
            hashed_password = get_password_hash(update_data["password"])
            del update_data["password"]
            update_data["password"] = hashed_password
        
        for field, value in update_data.items():
            setattr(db_obj, field, value)
        
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj
    
    def update_password(self, db: Session, *, db_obj: User, new_password: str) -> User:
        """Обновление пароля пользователя"""
        db_obj.hashed_password = get_password_hash(new_password)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def authenticate(self, db: Session, *, email: str, password: str) -> Optional[User]:
        user = self.get_by_email(db, email=email)
        if not user:
            return None
        if not verify_password(password, user.password):
            return None
        return user

    def is_active(self, user: User) -> bool:
        return user.is_active

    def is_admin(self, user: User) -> bool:
        return user.role == "admin"
    
    def is_organizer(self, user: User) -> bool:
        return user.role == "organizer" or user.role == "admin"
    
    # Получить общее количество пользователей
    def get_count(self, db: Session) -> int:
        return db.query(User).count()
    
    # Получить количество активных пользователей
    def get_active_count(self, db: Session) -> int:
        return db.query(User).filter(User.is_active == True).count()
    
    def is_verified(self, user: User) -> bool:
        """Проверка верификации email пользователя"""
        return user.is_verified

    def is_phone_verified(self, user: User) -> bool:
        """Проверка верификации телефона пользователя"""
        return user.is_phone_verified


user = CRUDUser(User)
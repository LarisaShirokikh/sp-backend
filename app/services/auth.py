# app/services/auth.py
from datetime import timedelta
from sqlalchemy.orm import Session
from app.core import security
from app.core.config import settings
from app.crud.user import user as user_crud
from app.utils.code import generate_verification_code
from app.utils.email import send_verification_email_code
from app.utils.sms import send_sms_verification_code

def login_user(db: Session, username: str, password: str):
    """
    Аутентификация пользователя.
    Возвращает кортеж (token, user), если аутентификация успешна, иначе None.
    """
    user = user_crud.authenticate(db, email=username, password=password)
    if not user or not user_crud.is_active(user):
        return None
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    token = security.create_access_token(user.id, expires_delta=access_token_expires)
    return token, user

def register_new_user(db: Session, user_in):
    """
    Регистрирует нового пользователя:
      - проверяет, существует ли пользователь с таким email;
      - создаёт пользователя;
      - генерирует JWT-токен;
      - генерирует 6-значные коды для подтверждения email (и телефона, если указан);
      - отправляет email и SMS с кодами;
      - сохраняет изменения в базе.
    Возвращает кортеж (token, user).
    """
    existing = user_crud.get_by_email(db, email=user_in.email)
    if existing:
        raise ValueError("Пользователь с таким email уже существует")
    
    user = user_crud.create(db, obj_in=user_in)
    
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    token = security.create_access_token(user.id, expires_delta=access_token_expires)
    
    # Генерация кода подтверждения email
    email_code = generate_verification_code()
    user.email_verification_code = email_code
    user.is_verified = False

    # Если указан телефон, генерируем код для него
    if user.phone:
        phone_code = generate_verification_code()
        user.phone_verification_code = phone_code
        user.is_phone_verified = False
    
    db.commit()
    db.refresh(user)
    
    # Отправляем код подтверждения на email и SMS
    send_verification_email_code(user.email, email_code)
    if user.phone:
        send_sms_verification_code(user.phone, user.phone_verification_code)
    
    return token, user

def verify_email_code_service(db: Session, email: str, code: str):
    """
    Проверяет код подтверждения email. При успешной проверке обновляет статус пользователя.
    """
    user = user_crud.get_by_email(db, email=email)
    if not user:
        raise ValueError("Пользователь не найден")
    if user.email_verification_code != code:
        raise ValueError("Неверный код подтверждения email")
    
    user.is_verified = True
    user.email_verification_code = None
    db.commit()
    db.refresh(user)
    return user

def verify_phone_code_service(db: Session, phone: str, code: str):
    """
    Проверяет код подтверждения телефона.
    """
    user = user_crud.get_by_phone(db, phone=phone) 
    if not user:
        raise ValueError("Пользователь не найден")
    if user.phone_verification_code != code:
        raise ValueError("Неверный код подтверждения телефона")
    
    user.is_phone_verified = True
    user.phone_verification_code = None
    db.commit()
    db.refresh(user)
    return user

def password_recovery_service(db: Session, email: str):
    """
    Обрабатывает запрос на восстановление пароля.
    """
    user = user_crud.get_by_email(db, email=email)
    if not user:
        raise ValueError("Пользователь не найден")
    # Здесь добавьте логику отправки письма для сброса пароля
    return user
# app/services/auth.py
from datetime import timedelta
from sqlalchemy.orm import Session
from app.core import security
from app.core.config import settings
from app.crud.user import user as user_crud
from app.utils.code import generate_verification_code
from app.utils.email import send_verification_email_link
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
    Регистрирует нового пользователя без подтверждения email и телефона.
    
    Args:
        db: Сессия базы данных
        user_in: Данные нового пользователя
        
    Returns:
        Кортеж (token, user)
    """
    existing = user_crud.get_by_email(db, email=user_in.email)
    if existing:
        raise ValueError("Пользователь с таким email уже существует")
    
    # Создаем пользователя без требования подтверждения
    user = user_crud.create(db, obj_in=user_in)
    
    # Устанавливаем флаги неподтвержденных контактов
    user.is_verified = False
    user.is_phone_verified = False
    
    # Но активируем аккаунт, чтобы пользователь мог сразу войти
    user.is_active = True
    
    db.commit()
    db.refresh(user)
    
    # Генерируем токен доступа
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    token = security.create_access_token(user.id, expires_delta=access_token_expires)
    
    return token, user

def send_email_verification(db: Session, user_id: int):
    """
    Отправляет ссылку для подтверждения email.
    
    Args:
        db: Сессия базы данных
        user_id: ID пользователя
        
    Returns:
        Пользователь с обновленными данными
    """
    user = user_crud.get(db, id=user_id)
    if not user:
        raise ValueError("Пользователь не найден")
    
    if user.is_verified:
        raise ValueError("Email уже подтвержден")
    
    # Отправляем ссылку для подтверждения
    send_verification_email_link(user.email, user.id)
    
    return user

def send_phone_verification(db: Session, user_id: int):
    """
    Отправляет SMS с кодом для подтверждения телефона.
    
    Args:
        db: Сессия базы данных
        user_id: ID пользователя
        
    Returns:
        Пользователь с обновленными данными
    """
    user = user_crud.get(db, id=user_id)
    if not user:
        raise ValueError("Пользователь не найден")
    
    if not user.phone:
        raise ValueError("Номер телефона не указан")
    
    if user.is_phone_verified:
        raise ValueError("Телефон уже подтвержден")
    
    # Генерируем и сохраняем код
    phone_code = generate_verification_code()
    user.phone_verification_code = phone_code
    db.commit()
    db.refresh(user)
    
    # Отправляем SMS с кодом
    send_sms_verification_code(user.phone, phone_code)
    
    return user

def verify_email_token_service(db: Session, token: str):
    """
    Проверяет токен подтверждения email.
    """
    user_id = security.verify_token(token, token_type="email")
    if not user_id:
        raise ValueError("Недействительный или просроченный токен")
    
    user = user_crud.get(db, id=user_id)
    if not user:
        raise ValueError("Пользователь не найден")
    
    user.is_verified = True
    db.commit()
    db.refresh(user)
    return user

def verify_phone_code_service(db: Session, user_id: int, code: str):
    """
    Проверяет код подтверждения телефона.
    """
    user = user_crud.get(db, id=user_id)
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
    
    # Генерируем токен для сброса пароля
    reset_token = security.create_verification_token(user.id, token_type="password")
    reset_link = f"{settings.FRONTEND_URL}/reset-password?token={reset_token}"
    
    # Логика отправки письма для сброса пароля
    # Здесь нужно добавить функцию для отправки email
    
    return user

def reset_password_service(db: Session, token: str, new_password: str):
    """
    Сбрасывает пароль пользователя с использованием токена.
    """
    user_id = security.verify_token(token, token_type="password")
    if not user_id:
        raise ValueError("Недействительный или просроченный токен")
    
    user = user_crud.get(db, id=user_id)
    if not user:
        raise ValueError("Пользователь не найден")
    
    user_crud.update_password(db, db_obj=user, new_password=new_password)
    return user
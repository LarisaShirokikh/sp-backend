import os
from pydantic_settings import BaseSettings
from pydantic import Field, PostgresDsn, ValidationInfo, field_validator, EmailStr, validator
from typing import Any, Dict, List, Optional, Union
import secrets
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = os.getenv('SECRET_KEY') or secrets.token_urlsafe(32)
    ALGORITHM: str = "HS256"
    # 60 минут * 24 часа * 7 дней = 7 дней
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7
    
    # CORS
    BACKEND_CORS_ORIGINS: List[str] = ["*"]

    # URL для фронтенда (используется в ссылках для верификации)
    FRONTEND_URL: str = os.getenv("FRONTEND_URL", "http://localhost:3000")
    MEDIA_URL: str = os.getenv('MEDIA_URL', 'http://localhost:8000')
    # Настройки PostgreSQL
    POSTGRES_HOST: str
    POSTGRES_PORT: int
    POSTGRES_USERNAME: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    SQLALCHEMY_DATABASE_URI: Optional[PostgresDsn] = None

    REDIS_HOST: str = Field(default="redis", env="REDIS_HOST")
    REDIS_PORT: int = Field(default=6379, env="REDIS_PORT")
    REDIS_DB: int = Field(default=0, env="REDIS_DB")
    REDIS_PASSWORD: str | None = Field(default=None, env="REDIS_PASSWORD")

    APP_NAME: str = "Портал совместных закупок"
    PROJECT_NAME: str = "SP"
    PROJECT_DESCRIPTION: str = "API для приложения SP"
    VERSION: str = "1.0.0"
    DEBUG: bool = True

    @field_validator("SQLALCHEMY_DATABASE_URI", mode="before")
    def assemble_db_connection(cls, v: str | None, info: ValidationInfo) -> str:
        if isinstance(v, str):
            return v
        data = info.data
        return "postgresql://{user}:{password}@{host}:{port}/{db}".format(
            
            user=data.get("POSTGRES_USERNAME"),
            password=data.get("POSTGRES_PASSWORD"),
            host=data.get("POSTGRES_HOST"),
            port=data.get("POSTGRES_PORT"),
            db=data.get("POSTGRES_DB"),
        )

    # Настройки для первого суперпользователя
    FIRST_SUPERUSER: EmailStr
    FIRST_SUPERUSER_PASSWORD: str
    FIRST_SUPERUSER_NAME: str = "Administrator"

    # Настройки электронной почты
    SMTP_TLS: bool = True
    SMTP_PORT: Optional[int] = None
    SMTP_HOST: Optional[str] = None
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    EMAILS_FROM_EMAIL: Optional[EmailStr] = None
    EMAILS_FROM_NAME: Optional[str] = None
    
    # Общие настройки приложения
    PROJECT_NAME: str = "Портал совместных закупок"

    # Настройки для отправки email
    # EMAIL_SENDER: EmailStr = os.getenv("EMAIL_SENDER", "noreply@example.com")
    # SMTP_SERVER: str = os.getenv("SMTP_SERVER", "smtp.example.com")
    # SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))
    # SMTP_USER: str = os.getenv("SMTP_USER", "user@example.com")
    # SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD", "password")
    
    # Настройки для SMS
    SMS_PROVIDER: str = os.getenv("SMS_PROVIDER", "sms.ru")  # или "smsc", "smsaero", "devino"
    
    # SMS.RU настройки
    SMSRU_API_KEY: Optional[str] = os.getenv("SMSRU_API_KEY")
    
    # SMSC настройки
    SMSC_LOGIN: Optional[str] = os.getenv("SMSC_LOGIN")
    SMSC_PASSWORD: Optional[str] = os.getenv("SMSC_PASSWORD")
    
    # SMS Aero настройки
    SMSAERO_EMAIL: Optional[str] = os.getenv("SMSAERO_EMAIL")
    SMSAERO_API_KEY: Optional[str] = os.getenv("SMSAERO_API_KEY")
    SMSAERO_SIGN: Optional[str] = os.getenv("SMSAERO_SIGN", "SMS Aero")
    
    # Devino Telecom настройки
    DEVINO_API_KEY: Optional[str] = os.getenv("DEVINO_API_KEY")
    DEVINO_SENDER: Optional[str] = os.getenv("DEVINO_SENDER", "Info")
    
    @field_validator("SMS_PROVIDER")
    def validate_sms_provider(cls, v):
        allowed_providers = ["sms.ru", "smsc", "smsaero", "devino"]
        if v.lower() not in allowed_providers:
            return "sms.ru"  # Установка по умолчанию, если указан неподдерживаемый провайдер
        return v
    
    class Config:
        case_sensitive = True
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "allow"




settings = Settings()
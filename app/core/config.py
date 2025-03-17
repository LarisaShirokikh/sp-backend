from pydantic_settings import BaseSettings
from pydantic import PostgresDsn, ValidationInfo, field_validator, EmailStr
from typing import Any, Dict, List, Optional, Union
import secrets
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = secrets.token_urlsafe(32)
    # 60 минут * 24 часа * 7 дней = 7 дней
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7
    
    # CORS
    BACKEND_CORS_ORIGINS: List[str] = ["*"]

    # Настройки PostgreSQL
    POSTGRES_HOST: str
    POSTGRES_PORT: int
    POSTGRES_USERNAME: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    SQLALCHEMY_DATABASE_URI: Optional[PostgresDsn] = None

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
    
    class Config:
        case_sensitive = True
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "allow"


settings = Settings()
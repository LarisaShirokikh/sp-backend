from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import settings



# Создание движка SQLAlchemy
engine = create_engine(str(settings.SQLALCHEMY_DATABASE_URI), pool_pre_ping=True)

# Создание локальной сессии
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    """
    Функция зависимости для получения сессии БД в эндпоинтах
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
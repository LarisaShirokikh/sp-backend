from datetime import datetime
import logging
import os
import uuid
import aiofiles
from fastapi import HTTPException, UploadFile, logger
from pathlib import Path as PathLib
from typing import Literal

# Настройки
MEDIA_DIR = PathLib("media")
AVATAR_DIR = MEDIA_DIR / "avatars"
COVER_DIR = MEDIA_DIR / "covers"
ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "gif", "webp"}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB

# Убедимся, что директории существуют
os.makedirs(AVATAR_DIR, exist_ok=True)
os.makedirs(COVER_DIR, exist_ok=True)

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def is_valid_file(filename: str, content_type: str) -> bool:
    """Проверяет допустимый формат файла"""
    extension = filename.split(".")[-1].lower() if "." in filename else ""
    return extension in ALLOWED_EXTENSIONS and "image" in content_type

async def save_user_file(
    user_id: int, 
    file: UploadFile, 
    file_type: Literal["avatar", "cover"]
) -> str:
    """
    Универсальная функция для сохранения файлов пользователя (аватар или обложка)
    
    Args:
        user_id: ID пользователя
        file: Загруженный файл
        file_type: Тип файла ("avatar" или "cover")
        
    Returns:
        Относительный путь к сохраненному файлу
    """
    # Определяем директорию для сохранения
    if file_type == "avatar":
        save_dir = AVATAR_DIR
        rel_path = "avatars"
    else:  # cover
        save_dir = COVER_DIR
        rel_path = "covers"
    
    # Создаем уникальное имя файла
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    unique_filename = f"{user_id}_{timestamp}_{uuid.uuid4()}.{file.filename.split('.')[-1]}"
    file_path = save_dir / unique_filename
    
    try:
        # Асинхронно сохраняем файл
        async with aiofiles.open(file_path, 'wb') as out_file:
            # Читаем и записываем по частям, чтобы не загружать большие файлы в память
            chunk_size = 1024 * 1024  # 1MB
            await file.seek(0)  # Перемещаемся в начало файла
            while content := await file.read(chunk_size):
                await out_file.write(content)
                
        # Возвращаем относительный путь для сохранения в БД
        return f"{rel_path}/{unique_filename}"
    except Exception as e:
        logger.error(f"Error saving {file_type}: {e}")
        # Если что-то пошло не так, удаляем файл, если он был создан
        if file_path.exists():
            os.unlink(file_path)
        raise HTTPException(status_code=500, detail=f"Ошибка при сохранении файла {file_type}")

async def cleanup_old_file(file_path: str, file_type: Literal["avatar", "cover"]) -> None:
    """
    Универсальная функция для удаления старых файлов пользователя
    
    Args:
        file_path: Относительный путь к файлу
        file_type: Тип файла ("avatar" или "cover")
    """
    if not file_path or file_path.strip() == "":
        logger.warning(f"cleanup_old_{file_type}: Путь пустой, удаление не требуется.")
        return  # Не выполнять удаление, если путь пуст
    
    try:
        full_path = MEDIA_DIR / file_path
        if full_path.exists():
            os.unlink(full_path)
            logger.info(f"Removed old {file_type}: {file_path}")
        else:
            logger.warning(f"{file_type.capitalize()} not found for removal: {full_path}")
    except Exception as e:
        logger.error(f"Failed to remove old {file_type} {file_path}: {e}")

# Для обратной совместимости с существующим кодом
async def save_avatar(user_id: int, file: UploadFile) -> str:
    """Сохраняет аватар пользователя"""
    return await save_user_file(user_id, file, "avatar")

async def save_cover_photo(user_id: int, file: UploadFile) -> str:
    """Сохраняет обложку профиля пользователя"""
    return await save_user_file(user_id, file, "cover")

async def cleanup_old_avatar(avatar_path: str) -> None:
    """Удаляет старый аватар пользователя"""
    return await cleanup_old_file(avatar_path, "avatar")

async def cleanup_old_cover_photo(cover_path: str) -> None:
    """Удаляет старую обложку профиля пользователя"""
    return await cleanup_old_file(cover_path, "cover")
from datetime import datetime
import logging
import os
import uuid
import aiofiles
from fastapi import HTTPException, Path, UploadFile, logger
from pathlib import Path as PathLib

# Настройки
UPLOAD_DIR = PathLib("media/avatars")
ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "gif", "webp"}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB

# Убедимся, что директория существует
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def is_valid_file(filename: str, content_type: str) -> bool:
    extension = filename.split(".")[-1].lower() if "." in filename else ""
    return extension in ALLOWED_EXTENSIONS and "image" in content_type

async def cleanup_old_avatar(avatar_path: str):
    """Удаляет старый аватар после успешного обновления"""
    if not avatar_path or avatar_path.strip() == "":
        logger.warning("cleanup_old_avatar: Путь пустой, удаление не требуется.")
        return  # Не выполнять удаление, если путь пуст
    
    try:
        full_path = Path("media") / avatar_path
        if full_path.exists():
            os.unlink(full_path)
            logger.info(f"Removed old avatar: {avatar_path}")
        else:
            logger.warning(f"Avatar not found for removal: {full_path}")
    except Exception as e:
        logger.error(f"Failed to remove old avatar {avatar_path}: {e}")

async def save_avatar(user_id: int, file: UploadFile) -> str:
    """Асинхронно сохраняет файл аватара и возвращает путь"""
    # Создаем уникальное имя файла
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    unique_filename = f"{user_id}_{timestamp}_{uuid.uuid4()}.{file.filename.split('.')[-1]}"
    file_path = UPLOAD_DIR / unique_filename
    
    try:
        # Асинхронно сохраняем файл
        async with aiofiles.open(file_path, 'wb') as out_file:
            # Читаем и записываем по частям, чтобы не загружать большие файлы в память
            chunk_size = 1024 * 1024  # 1MB
            while content := await file.read(chunk_size):
                await out_file.write(content)
                
        # Возвращаем относительный путь для сохранения в БД
        return f"avatars/{unique_filename}"
    except Exception as e:
        logger.error(f"Error saving avatar: {e}")
        # Если что-то пошло не так, удаляем файл, если он был создан
        if file_path.exists():
            os.unlink(file_path)
        raise HTTPException(status_code=500, detail="Ошибка при сохранении файла")
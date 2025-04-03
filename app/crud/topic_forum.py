from fastapi import logger
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from typing import List, Dict, Any, Optional
import os
from app.crud.base import CRUDBase
from app.models.category_forum import CategoryModel, ReplyModel, TopicModel, TagModel, TopicFileModel
from app.schemas.category_forum import TopicCreate, TopicUpdate


class CRUDTopic(CRUDBase[TopicModel, TopicCreate, TopicUpdate]):
    def create(self, db: Session, *, obj_in: TopicCreate, author_id: int) -> TopicModel:
        """
        Расширенный метод создания топика с улучшенной обработкой
        """
        # Проверка существования категории
        category = db.query(CategoryModel).filter(CategoryModel.id == obj_in.category_id).first()
        if not category:
            raise ValueError(f"Категория с ID {obj_in.category_id} не найдена")

        # Подготовка данных для создания топика
        topic_data = {
            "title": obj_in.title,
            "content": obj_in.content,
            "category_id": obj_in.category_id,
            "user_id": author_id,
            "view_count": 0,
            "reply_count": 0,
            "like_count": 0,
            "dislike_count": 0,
            "save_count": 0
        }

        db_obj = TopicModel(**topic_data)

        # Обработка тегов с дополнительной проверкой
        if obj_in.tags and len(obj_in.tags) > 0:
            try:
                # Проверяем существование всех тегов
                existing_tags = db.query(TagModel).filter(TagModel.id.in_(obj_in.tags)).all()
                if len(existing_tags) != len(obj_in.tags):
                    raise ValueError("Некоторые теги не существуют")
                
                db_obj.tags = existing_tags
            except SQLAlchemyError as e:
                db.rollback()
                raise ValueError(f"Ошибка при обработке тегов: {str(e)}")

        try:
            db.add(db_obj)
            db.commit()
            db.refresh(db_obj)
            
            # Обновляем счетчик топиков в категории
            category.topic_count += 1
            db.add(category)
            db.commit()
            
            return db_obj
        except IntegrityError as e:
            db.rollback()
            raise ValueError(f"Ошибка создания топика: {str(e)}")
        except SQLAlchemyError as e:
            db.rollback()
            raise ValueError(f"Неожиданная ошибка базы данных: {str(e)}")
    
    def add_files_to_topic(
        self, db: Session, *, topic_id: int, file_paths: List[str]
    ) -> List[TopicFileModel]:
        """
        Добавляет файлы к существующему топику
        """
        topic = db.query(TopicModel).filter(TopicModel.id == topic_id).first()
        if not topic:
            raise ValueError(f"Топик с ID {topic_id} не найден")
        
        file_models = []
        try:
            for file_path in file_paths:
                # Получаем имя файла из пути
                file_name = file_path.split("/")[-1]
                
                # Определяем тип файла на основе расширения
                file_extension = file_name.split(".")[-1].lower() if "." in file_name else ""
                
                file_type = "document"
                if file_extension in ["jpg", "jpeg", "png", "gif", "webp", "svg"]:
                    file_type = "image"
                elif file_extension in ["mp4", "webm", "avi", "mov", "wmv"]:
                    file_type = "video"
                
                # Создаем запись о файле
                file_obj = TopicFileModel(
                    topic_id=topic_id,
                    file_path=file_path,
                    file_name=file_name,
                    file_type=file_type
                )
                
                db.add(file_obj)
                file_models.append(file_obj)
                
            db.commit()
            for file_obj in file_models:
                db.refresh(file_obj)
                
            return file_models
        except SQLAlchemyError as e:
            db.rollback()
            raise ValueError(f"Ошибка при добавлении файлов к топику: {str(e)}")
        
    def get_by_params(
        self, db: Session, *, category_id: Optional[int] = None, 
        skip: int = 0, limit: int = 100
    ) -> List[TopicModel]:
        """
        Получение топиков с фильтрацией по категории
        """
        query = db.query(self.model)
        
        if category_id is not None:
            query = query.filter(self.model.category_id == category_id)
        
        return query.offset(skip).limit(limit).all()
    
    def update_view_count(self, db: Session, *, topic_id: int) -> TopicModel:
        """
        Увеличение счетчика просмотров топика
        """
        topic = db.query(self.model).filter(self.model.id == topic_id).first()
        if topic:
            topic.view_count += 1
            db.add(topic)
            db.commit()
            db.refresh(topic)
        return topic

    def get_topics_by_category(
        self, 
        db: Session, 
        category_id: int, 
        skip: int = 0, 
        limit: int = 100
    ) -> List[TopicModel]:
        """
        Получение топиков для определенной категории с пагинацией
        """
        return (
            db.query(self.model)
            .filter(self.model.category_id == category_id)
            .order_by(self.model.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )
        
    def get_topic_files(self, db: Session, *, topic_id: int) -> List[TopicFileModel]:
        """
        Получение всех файлов, прикрепленных к топику
        """
        return db.query(TopicFileModel).filter(TopicFileModel.topic_id == topic_id).all()

    def create_reply(self, db: Session, *, topic_id: int, content: str, author_id: int):
        """
        Создание ответа к топику
        """
        from app.models.category_forum import ReplyModel  # Импортируем модель ответа
        
        # Создаем новый ответ
        db_reply = ReplyModel(
            topic_id=topic_id,
            content=content,
            author_id=author_id
        )
    
        # Добавляем в базу данных
        db.add(db_reply)
        db.commit()
        db.refresh(db_reply)
        
        # Увеличиваем счетчик ответов в топике
        topic = db.query(self.model).filter(self.model.id == topic_id).first()
        if topic:
            topic.reply_count = (topic.reply_count or 0) + 1
            db.commit()
        
        return db_reply

    def get_reply(self, db: Session, reply_id: int):
        """
        Получение ответа по ID с присоединенными медиа-файлами
        """
        from app.models.category_forum import ReplyModel, ReplyFileModel  # Импортируем модели
        
        # Запрос для получения ответа с присоединенными файлами
        reply = db.query(ReplyModel).filter(ReplyModel.id == reply_id).first()
        
        if reply:
            # Получаем присоединенные файлы
            reply_files = db.query(ReplyFileModel).filter(ReplyFileModel.reply_id == reply_id).all()
            
            # Конвертируем модель в словарь
            reply_dict = reply.__dict__.copy()
            
            # Удаляем служебные поля SQLAlchemy
            if "_sa_instance_state" in reply_dict:
                del reply_dict["_sa_instance_state"]
            
            # Добавляем медиа-файлы
            if reply_files:
                media = []
                for file in reply_files:
                    # Преобразуем файл в словарь
                    file_dict = file.__dict__.copy()
                    if "_sa_instance_state" in file_dict:
                        del file_dict["_sa_instance_state"]
                    
                    # Определяем тип файла по расширению
                    file_extension = os.path.splitext(file.file_name)[1].lower()
                    if file_extension in ['.jpg', '.jpeg', '.png', '.gif', '.webp']:
                        file_dict['file_type'] = 'image'
                    elif file_extension in ['.mp4', '.webm', '.ogg', '.mov']:
                        file_dict['file_type'] = 'video'
                    elif file_extension == '.pdf':
                        file_dict['file_type'] = 'pdf'
                    else:
                        file_dict['file_type'] = 'document'
                    
                    # Добавляем URL для доступа к файлу
                    file_dict['url'] = f"/media/topics/topic_{reply.topic_id}/reply_{reply.id}/{file.file_name}"
                    
                    media.append(file_dict)
                
                reply_dict['media'] = media
            else:
                reply_dict['media'] = []
            
            return reply_dict
        
        return None

    def get_replies(self, db: Session, topic_id: int):
        """
        Получение всех ответов на топик по ID топика
        """
        from app.models.category_forum import ReplyModel  # Импортируем модель
        
        # Проверяем существование топика
        topic = db.query(self.model).filter(self.model.id == topic_id).first()
        if not topic:
            return None
        
        # Получаем все ответы для данного топика
        replies = db.query(ReplyModel).filter(ReplyModel.topic_id == topic_id).all()
        
        # Преобразуем объекты в словари и добавляем дополнительную информацию
        result = []
        for reply in replies:
            reply_dict = reply.__dict__.copy()
            
            # Удаляем служебные поля SQLAlchemy
            if "_sa_instance_state" in reply_dict:
                del reply_dict["_sa_instance_state"]
            
            # Добавляем пустой список медиа (если понадобится, можно загрузить позже)
            reply_dict['media'] = self.get_reply_files(db, reply.id) or []
            
            result.append(reply_dict)
        
        return result
    
    def add_files_to_reply(self, db: Session, reply_id: int, file_paths: list[str]):
        """
        Добавление медиа-файлов к ответу
        """
        from app.models.category_forum import ReplyFileModel, ReplyModel  # Импортируем модели
        
        # Проверяем существование ответа
        reply = db.query(ReplyModel).filter(ReplyModel.id == reply_id).first()
        if not reply:
            raise ValueError(f"Ответ с ID {reply_id} не найден")
        
        # Добавляем файлы в базу данных
        added_files = []
        for file_path in file_paths:
            # Получаем имя файла из пути
            file_name = os.path.basename(file_path)
            
            # Определяем тип файла по расширению
            file_extension = os.path.splitext(file_name)[1].lower()
            file_type = 'document'  # По умолчанию документ
            
            if file_extension in ['.jpg', '.jpeg', '.png', '.gif', '.webp']:
                file_type = 'image'
            elif file_extension in ['.mp4', '.webm', '.ogg', '.mov']:
                file_type = 'video'
            elif file_extension == '.pdf':
                file_type = 'pdf'
            
            # Создаем новую запись о файле
            db_file = ReplyFileModel(
                reply_id=reply_id,
                file_path=file_path,
                file_name=file_name,
                file_type=file_type
            )
            
            db.add(db_file)
            added_files.append(db_file)
        
        # Фиксируем изменения в базе данных
        db.commit()
        
        # Обновляем объекты
        for file in added_files:
            db.refresh(file)
        print(f"Добавляем файлы к ответу {reply_id}: {file_paths}")
        return added_files

    def get_reply_files(self, db: Session, reply_id: int):
        """
        Получение всех файлов, связанных с ответом
        """
        from app.models.category_forum import ReplyFileModel, ReplyModel  # Импортируем модели
        
        # Проверяем существование ответа
        reply = db.query(ReplyModel).filter(ReplyModel.id == reply_id).first()
        if not reply:
            return None
        
        # Получаем файлы
        files = db.query(ReplyFileModel).filter(ReplyFileModel.reply_id == reply_id).all()
        
        # Преобразуем модели в словари с дополнительной информацией
        result = []
        for file in files:
            file_dict = file.__dict__.copy()
            
            # Удаляем служебные поля SQLAlchemy
            if "_sa_instance_state" in file_dict:
                del file_dict["_sa_instance_state"]
            
            # Добавляем URL для доступа к файлу
            file_dict['url'] = f"/media/topics/topic_{reply.topic_id}/reply_{reply.id}/{file.file_name}"
            
            result.append(file_dict)
        return result

    def like_reply(self, db: Session, reply_id: int, user_id: int):
        """
        Добавление лайка к ответу
        """
        from app.models.category_forum import ReplyModel, reply_likes  # Импортируем модели
        from sqlalchemy import select, delete, insert
        
        # Проверяем существование ответа
        reply = db.query(ReplyModel).filter(ReplyModel.id == reply_id).first()
        if not reply:
            raise ValueError(f"Ответ с ID {reply_id} не найден")
        
        # Проверяем, не поставил ли пользователь уже лайк
        stmt = select(reply_likes).where(
            reply_likes.c.reply_id == reply_id,
            reply_likes.c.user_id == user_id,
            reply_likes.c.is_like == True
        )
        existing_like = db.execute(stmt).first()
        
        if existing_like:
            return "Лайк уже поставлен"
        
        # Если есть дизлайк, удаляем его
        stmt_delete = delete(reply_likes).where(
            reply_likes.c.reply_id == reply_id,
            reply_likes.c.user_id == user_id,
            reply_likes.c.is_like == False
        )
        db.execute(stmt_delete)
        
        # Добавляем лайк
        stmt_insert = insert(reply_likes).values(
            reply_id=reply_id,
            user_id=user_id,
            is_like=True
        )
        db.execute(stmt_insert)
        
        # Увеличиваем счетчик лайков
        reply.like_count = (reply.like_count or 0) + 1
        
        # Уменьшаем счетчик дизлайков, если был дизлайк
        if reply.dislike_count and reply.dislike_count > 0:
            reply.dislike_count -= 1
        
        db.commit()
        return "Лайк добавлен"

    def unlike_reply(self, db: Session, reply_id: int, user_id: int):
        """
        Удаление лайка с ответа
        """
        from app.models.category_forum import ReplyModel, reply_likes  # Импортируем модели
        from sqlalchemy import select, delete
        
        # Проверяем существование ответа
        reply = db.query(ReplyModel).filter(ReplyModel.id == reply_id).first()
        if not reply:
            raise ValueError(f"Ответ с ID {reply_id} не найден")
        
        # Проверяем, есть ли лайк
        stmt = select(reply_likes).where(
            reply_likes.c.reply_id == reply_id,
            reply_likes.c.user_id == user_id,
            reply_likes.c.is_like == True
        )
        existing_like = db.execute(stmt).first()
        
        if not existing_like:
            return "Лайк не найден"
        
        # Удаляем лайк
        stmt_delete = delete(reply_likes).where(
            reply_likes.c.reply_id == reply_id,
            reply_likes.c.user_id == user_id,
            reply_likes.c.is_like == True
        )
        db.execute(stmt_delete)
        
        # Уменьшаем счетчик лайков
        if reply.like_count and reply.like_count > 0:
            reply.like_count -= 1
        
        db.commit()
        return "Лайк удален"

crud_topic = CRUDTopic(TopicModel)
# app/crud/topic_forum.py
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from typing import List, Dict, Any, Optional

from app.crud.base import CRUDBase
from app.models.category_forum import CategoryModel, TopicModel, TagModel
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
# Инициализация CRUD-объекта для топиков
crud_topic = CRUDTopic(TopicModel)
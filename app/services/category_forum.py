from datetime import timedelta
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from app.models.category_forum import CategoryModel
from app.schemas.category_forum import  CategoryCreate


def category_create(db: Session, category_in: CategoryCreate) -> CategoryModel:
    category = CategoryModel(
        name=category_in.name,
        description=category_in.description,
        is_visible=category_in.is_visible if category_in.is_visible is not None else True,
        order=category_in.order if category_in.order is not None else 0,
    )
    try:
        db.add(category)
        db.commit()
        db.refresh(category)
        return category
    except IntegrityError:
        db.rollback()
        raise ValueError("Категория с таким именем уже существует")

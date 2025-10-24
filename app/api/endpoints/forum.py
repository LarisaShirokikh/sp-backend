# app/api/v1/category_forum
from datetime import datetime
import logging
from typing import Any, List
from uuid import uuid4
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_db

from app.models.category_forum import CategoryModel, TopicModel
from app.schemas.category_forum import Category, CategoryCreate, CategoryUpdate, Topic
from app.services.category_forum import category_create


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/categories", response_model=List[Category])
def get_categories(db: Session = Depends(get_db)):
    categories = db.query(CategoryModel).all()
    enriched = []
    for cat in categories:
        enriched.append(Category(
            id=cat.id,
            name=cat.name,
            description=cat.description,
            is_visible=cat.is_visible,
            order=cat.order,
            topic_count=db.query(TopicModel).filter(TopicModel.category_id == cat.id).count(),
            post_count=cat.post_count,
            created_at=cat.created_at,
            updated_at=cat.updated_at,
        ))
    return enriched

@router.post("/categories", response_model=Category)
def create_category(
    category_in: CategoryCreate, 
    db: Session = Depends(get_db)
) -> Any:
    try:
        return category_create(db, category_in)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/categories/{category_id}", response_model=Category)
def get_category(category_id: int, db: Session = Depends(get_db)):
    db_category = db.query(CategoryModel).filter(CategoryModel.id == category_id).first()
    
    if db_category is None:
        raise HTTPException(status_code=404, detail="Category not found")
    
    topic_count = db.query(TopicModel).filter(TopicModel.category_id == category_id).count()
    
    return {
        "id": db_category.id,
        "name": db_category.name,
        "description": db_category.description,
        "created_at": db_category.created_at,
        "updated_at": db_category.updated_at,
        "topicCount": topic_count
    }

@router.patch("/categories/{category_id}", response_model=Category)
def update_category(
    category_id: int, 
    category: CategoryUpdate, 
    db: Session = Depends(get_db)
    ) -> Any:

    db_category = db.query(CategoryModel).filter(CategoryModel.id == category_id).first()

    
    if db_category is None:
        raise HTTPException(status_code=404, detail="Category not found")
    
    # Update fields if provided
    if category.name is not None:
        db_category.name = category.name
    if category.description is not None:
        db_category.description = category.description
    if category.is_visible is not None:
        db_category.is_visible = category.is_visible
    if category.order is not None:
        db_category.order = category.order

    db_category.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(db_category)

    topic_count = db.query(TopicModel).filter(TopicModel.category_id == category_id).count()

    return Category(
        id=db_category.id,
        name=db_category.name,
        description=db_category.description,
        is_visible=db_category.is_visible,
        order=db_category.order,
        post_count=db_category.post_count,
        topic_count=topic_count,
        created_at=db_category.created_at,
        updated_at=db_category.updated_at
    )

@router.delete("/categories/{category_id}")
def delete_category(category_id: int, db: Session = Depends(get_db)):
    db_category = db.query(CategoryModel).filter(CategoryModel.id == category_id).first()

    if db_category is None:
        raise HTTPException(status_code=404, detail="Category not found")

    db.delete(db_category)
    db.commit()

    return {"message": "Category deleted successfully"}


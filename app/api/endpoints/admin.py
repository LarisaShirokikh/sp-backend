# app/api/v1/admin/router.py
import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import joinedload
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.api.deps import get_current_admin, get_db
from app.models.activity import Activity
from app.models.group_buy import Order
from app.models.user import User, UserRoleAssociation, UserRole
from app.crud.user import user
from app.crud.activity import activity_crud
from app.schemas.admin import (
    AdminUserBasic,
    AdminUserDetail
)
from app.schemas.user import UserRoleUpdateRequest, UserStatusUpdateRequest, UserUpdateRequest

# Создаем логгер
logger = logging.getLogger(__name__)

# Создаем роутер для эндпоинтов админки
router = APIRouter()

# Эндпоинт для получения статистики для дашборда
@router.get("/dashboard/stats")
def get_dashboard_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    logger.info("Fetching dashboard stats")

    try:
        # Общие пользователи
        total_users = user.get_count(db)
        active_users = user.get_active_count(db)

        # Новые пользователи за последние 30 дней
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        new_users = db.query(func.count(User.id)).filter(User.created_at >= thirty_days_ago).scalar()

        # Кол-во заказов (предполагаем, что есть таблица Order)
        total_orders = db.query(func.count(Order.id)).scalar()

        # Рост пользователей по месяцам за последние 6 месяцев
        six_months_ago = datetime.utcnow() - timedelta(days=180)
        growth_data = (
            db.query(
                func.date_trunc('month', User.created_at).label("month"),
                func.count(User.id).label("count")
            )
            .filter(User.created_at >= six_months_ago)
            .group_by("month")
            .order_by("month")
            .all()
        )
        user_growth = [
            {"name": month.strftime("%b"), "users": count}
            for month, count in growth_data
        ]

        # Активность пользователей по дням недели — если нет логов, оставить заглушку
        active_users_by_day = [
            {"day": "Пн", "users": int(active_users * 0.8)},
            {"day": "Вт", "users": int(active_users * 0.85)},
            {"day": "Ср", "users": int(active_users * 0.9)},
            {"day": "Чт", "users": int(active_users * 0.95)},
            {"day": "Пт", "users": active_users},
            {"day": "Сб", "users": int(active_users * 0.7)},
            {"day": "Вс", "users": int(active_users * 0.65)}
        ]

        return {
            "totalUsers": total_users,
            "activeUsers": active_users,
            "newUsers": new_users,
            "totalOrders": total_orders,
            "userGrowth": user_growth,
            "activeUsersByDay": active_users_by_day
        }
    except Exception as e:
        logger.error(f"Error fetching dashboard stats: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch dashboard statistics")

# Эндпоинт для получения последних активностей
@router.get("/activities")
def get_activities(
    limit: int = Query(10, ge=1, le=100),
    skip: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    logger.info(f"Fetching activities - limit: {limit}, skip: {skip}")

    try:
        activities = (
            db.query(Activity)
            .options(joinedload(Activity.user))
            .order_by(Activity.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )
        
        result = []
        for act in activities:
            result.append({
                "id": act.id,
                "type": act.type,
                "message": activity_crud.get_activity_message(act),
                "timestamp": act.created_at,
                "user": {
                    "id": act.user.id,
                    "name": act.user.name
                } if act.user else None
            })

        return result
    except Exception as e:
        logger.error(f"Error fetching activities: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch activities")

# Эндпоинты для управления пользователями
@router.get("/users")
def get_users(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    search: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    """
    Получение списка пользователей с пагинацией и возможностью поиска
    """
    skip = (page - 1) * limit
    
    try:
        # Получаем список пользователей
        query = db.query(User)
        
        # Добавляем поиск если указан
        if search:
            search_term = f"%{search}%"
            query = query.filter(
                (User.name.ilike(search_term)) | 
                (User.email.ilike(search_term)) | 
                (User.full_name.ilike(search_term))
            )
        
        total = query.count()
        users_list = query.offset(skip).limit(limit).all()
        
        # Преобразуем пользователей в формат для админки
        users_data = []
        for user_obj in users_list:
            # Получаем роли пользователя
            roles = [role_assoc.role for role_assoc in user_obj.roles]
            
            user_data = {
                "id": user_obj.id,
                "name": user_obj.name,
                "email": user_obj.email,
                "full_name": user_obj.full_name,
                "is_active": user_obj.is_active,
                "is_verified": user_obj.is_verified,
                "is_superuser": user_obj.is_superuser,
                "roles": roles,
                "created_at": user_obj.created_at.isoformat() if user_obj.created_at else None,
                "avatar_url": user_obj.avatar_url
            }
            users_data.append(user_data)
        
        return {
            "users": users_data,
            "total": total
        }
    except Exception as e:
        logger.error(f"Error fetching users: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch users"
        )

@router.get("/users/{user_id}", response_model=AdminUserDetail)
def get_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    """
    Получение информации о конкретном пользователе
    """
    try:
        user_obj = user.get(db, id=user_id)
        if not user_obj:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User with ID {user_id} not found"
            )
        
        # Получаем роли пользователя
        roles = [role_assoc.role for role_assoc in user_obj.roles]
        
        # Преобразуем пользователя в формат для админки
        user_data = {
            "id": user_obj.id,
            "name": user_obj.name,
            "email": user_obj.email,
            "full_name": user_obj.full_name,
            "phone": user_obj.phone,
            "is_active": user_obj.is_active,
            "is_verified": user_obj.is_verified,
            "is_phone_verified": user_obj.is_phone_verified,
            "is_superuser": user_obj.is_superuser,
            "description": user_obj.description,
            "rating": user_obj.rating,
            "avatar_url": user_obj.avatar_url,
            "followers_count": user_obj.followers_count,
            "following_count": user_obj.following_count,
            "roles": roles,
            "created_at": user_obj.created_at.isoformat() if user_obj.created_at else None
        }
        
        return user_data
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching user {user_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch user with ID {user_id}"
        )

# Эндпоинт для обновления пользователя
@router.put("/users/{user_id}", response_model=AdminUserDetail)
def update_user(
    user_id: int,
    user_data: UserUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    """
    Обновление информации о пользователе
    """
    try:
        # Проверяем существование пользователя
        user_obj = user.get(db, id=user_id)
        if not user_obj:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User with ID {user_id} not found"
            )
        
        # Подготавливаем данные для обновления
        update_data = user_data.model_dump(exclude_unset=True)
        
        # Если email обновляется, проверяем его уникальность
        if "email" in update_data and update_data["email"] != user_obj.email:
            existing_user = user.get_by_email(db, email=update_data["email"])
            if existing_user and existing_user.id != user_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Email already registered"
                )
        
        # Если имя пользователя обновляется, проверяем его уникальность
        if "name" in update_data and update_data["name"] != user_obj.name:
            existing_user = user.get_by_name(db, name=update_data["name"])
            if existing_user and existing_user.id != user_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Username already taken"
                )
                
        # Логируем операцию
        logger.info(f"Updating user {user_id} with data: {update_data}")
        
        # Обновляем пользователя через CRUD
        updated_user = user.update(db, db_obj=user_obj, obj_in=update_data)
        
        # Получаем роли обновленного пользователя
        roles = [role_assoc.role for role_assoc in updated_user.roles]
        
        # Преобразуем обновленные данные пользователя для ответа
        response_data = {
            "id": updated_user.id,
            "name": updated_user.name,
            "email": updated_user.email,
            "full_name": updated_user.full_name,
            "phone": updated_user.phone,
            "is_active": updated_user.is_active,
            "is_verified": updated_user.is_verified,
            "is_phone_verified": updated_user.is_phone_verified,
            "is_superuser": updated_user.is_superuser,
            "description": updated_user.description,
            "rating": updated_user.rating,
            "avatar_url": updated_user.avatar_url,
            "followers_count": updated_user.followers_count,
            "following_count": updated_user.following_count,
            "roles": roles,
            "created_at": updated_user.created_at.isoformat() if updated_user.created_at else None
        }
        
        return response_data
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating user {user_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update user with ID {user_id}"
        )

# Эндпоинт для обновления ролей пользователя
@router.put("/users/{user_id}/roles", response_model=AdminUserBasic)
def update_user_roles(
    user_id: int,
    role_data: UserRoleUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    """
    Обновление ролей пользователя
    """
    try:
        from sqlalchemy import text
        
        # Проверяем существование пользователя
        user_obj = user.get(db, id=user_id)
        if not user_obj:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User with ID {user_id} not found"
            )
        
        # Логируем операцию
        logger.info(f"Updating roles for user {user_id}: {role_data.roles}")
        
        # Начинаем транзакцию
        db.execute(text("BEGIN"))
        
        try:
            # Удаляем текущие роли
            db.execute(
                text("DELETE FROM user_roles WHERE user_id = :user_id"),
                {"user_id": user_id}
            )
            
            # Проверяем валидность ролей
            valid_roles = []
            for role_name in role_data.roles:
                try:
                    # Проверяем, является ли роль значением из перечисления
                    UserRole(role_name)
                    valid_roles.append(role_name)
                except ValueError:
                    logger.warning(f"Role '{role_name}' is not a valid UserRole, skipping")
            
            # Логируем валидные роли
            logger.info(f"Valid roles to add: {valid_roles}")
            
            # Проверяем наличие последовательности для id
            seq_exists = db.execute(text("""
                SELECT EXISTS (
                    SELECT 1 FROM information_schema.sequences 
                    WHERE sequence_name = 'user_roles_id_seq'
                )
            """)).scalar()
            
            logger.info(f"Sequence user_roles_id_seq exists: {seq_exists}")
            
            # Находим максимальный id, чтобы безопасно добавить новые записи
            max_id = db.execute(text("SELECT COALESCE(MAX(id), 0) FROM user_roles")).scalar()
            logger.info(f"Current max id in user_roles: {max_id}")
            
            # Добавляем новые роли по одной с указанием id
            for i, role_name in enumerate(valid_roles):
                # Используем новый id для каждой роли
                new_id = max_id + i + 1
                
                # Включаем id в запрос
                db.execute(
                    text("INSERT INTO user_roles (id, user_id, role) VALUES (:id, :user_id, :role)"),
                    {"id": new_id, "user_id": user_id, "role": role_name}
                )
            
            # Применяем изменения
            db.execute(text("COMMIT"))
            
        except Exception as e:
            # Откатываем транзакцию в случае ошибки
            db.execute(text("ROLLBACK"))
            logger.error(f"SQL transaction failed: {str(e)}")
            raise
        
        # Получаем обновленные роли пользователя
        result = db.execute(
            text("SELECT role FROM user_roles WHERE user_id = :user_id"),
            {"user_id": user_id}
        ).fetchall()
        
        roles = [row[0] for row in result]
        
        # Преобразуем обновленные данные пользователя для ответа
        response_data = {
            "id": user_obj.id,
            "name": user_obj.name,
            "email": user_obj.email,
            "full_name": user_obj.full_name,
            "is_active": user_obj.is_active,
            "is_verified": user_obj.is_verified,
            "is_superuser": user_obj.is_superuser,
            "roles": roles
        }
        
        return response_data
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating roles for user {user_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update roles for user with ID {user_id}: {str(e)}"
        )

# Эндпоинт для обновления статуса пользователя
@router.patch("/users/{user_id}/status", response_model=AdminUserBasic)
def update_user_status(
    user_id: int,
    status_data: UserStatusUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    """
    Обновление статуса активности пользователя
    """
    try:
        # Проверяем существование пользователя
        user_obj = user.get(db, id=user_id)
        if not user_obj:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User with ID {user_id} not found"
            )
        
        # Логируем операцию
        logger.info(f"Updating status for user {user_id} to is_active={status_data.is_active}")
        
        # Обновляем статус
        user_obj.is_active = status_data.is_active
        db.commit()
        db.refresh(user_obj)
        
        # Получаем роли пользователя
        roles = [role_assoc.role for role_assoc in user_obj.roles]
        
        # Преобразуем обновленные данные пользователя для ответа
        response_data = {
            "id": user_obj.id,
            "name": user_obj.name,
            "email": user_obj.email,
            "full_name": user_obj.full_name,
            "is_active": user_obj.is_active,
            "is_verified": user_obj.is_verified,
            "is_superuser": user_obj.is_superuser,
            "roles": roles
        }
        
        return response_data
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating status for user {user_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update status for user with ID {user_id}: {str(e)}"
        )

# Эндпоинты для управления заказами (заглушка, так как нет CRUD для заказов)
@router.get("/orders")
def get_orders(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    """
    Получение списка заказов с пагинацией (заглушка)
    """
    # В реальном приложении заменить на запрос к БД
    test_orders = [
        {
            "id": 1,
            "order_number": "ORDER-20230701-ABCD",
            "customer_name": "Иван Иванов",
            "amount": 12500.0,
            "status": "completed",
            "created_at": datetime.utcnow() - timedelta(days=5)
        },
        {
            "id": 2,
            "order_number": "ORDER-20230705-EFGH",
            "customer_name": "Петр Петров",
            "amount": 8300.0,
            "status": "pending",
            "created_at": datetime.utcnow() - timedelta(days=2)
        },
        {
            "id": 3,
            "order_number": "ORDER-20230707-IJKL",
            "customer_name": "Алексей Сидоров",
            "amount": 15750.0,
            "status": "processing",
            "created_at": datetime.utcnow() - timedelta(days=1)
        }
    ]
    
    return {
        "orders": test_orders,
        "total": 856  # В реальном приложении заменить на фактическое количество
    }

@router.get("/orders/{order_id}")
def get_order(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    """
    Получение информации о конкретном заказе (заглушка)
    """
    # В реальном приложении заменить на запрос к БД
    if order_id not in [1, 2, 3]:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Order with ID {order_id} not found"
        )
    
    test_orders = {
        1: {
            "id": 1,
            "order_number": "ORDER-20230701-ABCD",
            "customer_name": "Иван Иванов",
            "amount": 12500.0,
            "status": "completed",
            "created_at": datetime.utcnow() - timedelta(days=5)
        },
        2: {
            "id": 2,
            "order_number": "ORDER-20230705-EFGH",
            "customer_name": "Петр Петров",
            "amount": 8300.0,
            "status": "pending",
            "created_at": datetime.utcnow() - timedelta(days=2)
        },
        3: {
            "id": 3,
            "order_number": "ORDER-20230707-IJKL",
            "customer_name": "Алексей Сидоров",
            "amount": 15750.0,
            "status": "processing",
            "created_at": datetime.utcnow() - timedelta(days=1)
        }
    }
    
    return test_orders[order_id]

# Эндпоинт для настроек сайта (заглушка)
@router.get("/settings")
def get_site_settings(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    """
    Получение глобальных настроек сайта (заглушка)
    """
    # В реальном приложении заменить на запрос к БД
    return {
        "site_name": "Мой сайт",
        "description": "Описание сайта",
        "contact_email": "admin@example.com",
        "maintenance_mode": False,
        "registration_enabled": True,
        "theme": "light",
        "social_media": {
            "facebook": "https://facebook.com/mysite",
            "instagram": "https://instagram.com/mysite",
            "twitter": "https://twitter.com/mysite"
        }
    }

@router.put("/settings")
def update_site_settings(
    settings: Dict[str, Any],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    """
    Обновление глобальных настроек сайта (заглушка)
    """
    # В реальном приложении сохранить настройки в БД
    return settings
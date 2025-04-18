from app.models.user import User
from app.core.config import settings

# def serialize_user(user: User) -> dict:
#     user_dict = user.__dict__.copy()

#     # 💡 Обработка avatar_url (если он есть)
#     if user.avatar_url:
#         # Только добавляем префикс, если это относительный путь
#         if not user.avatar_url.startswith("http"):
#             user_dict["avatar_url"] = f"{settings.MEDIA_URL}/media/{user.avatar_url}"
#         else:
#             user_dict["avatar_url"] = user.avatar_url
#     else:
#         user_dict["avatar_url"] = None

#     # Остальные поля
#     if user_dict.get("description") is None:
#         user_dict["description"] = ""

#     user_dict.pop("_sa_instance_state", None)
#     return user_dict


def serialize_user(user: User):
    """Сериализует объект пользователя в словарь"""
    user_dict = {
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "full_name": user.full_name,
        "phone": user.phone,
        "description": user.description,
        "avatar_url": user.avatar_url,
        "cover_photo": user.cover_photo,
        "is_active": user.is_active,
        "is_verified": user.is_verified,
        "is_phone_verified": user.is_phone_verified,
        "is_superuser": user.is_superuser if hasattr(user, "is_superuser") else False,
        "rating": user.rating if hasattr(user, "rating") else 0,
        "created_at": user.created_at,
        "updated_at": user.updated_at,
        "followers_count": user.followers_count if hasattr(user, "followers_count") else 0,
        "following_count": user.following_count if hasattr(user, "following_count") else 0,
        # Добавляем поле roles
        "roles": [r.role for r in user.roles] if hasattr(user, "roles") and user.roles else ["user"]
    }

    roles = []
    if hasattr(user, "roles") and user.roles:
        roles = [r.role for r in user.roles]
    
    # Добавляем роль super_admin, если пользователь - суперпользователь
    if hasattr(user, "is_superuser") and user.is_superuser and "super_admin" not in roles:
        roles.append("super_admin")
    
    # Если ролей все еще нет, добавляем роль по умолчанию
    if not roles:
        roles.append("user")
        
    user_dict["roles"] = roles
    return user_dict
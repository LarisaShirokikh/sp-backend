from app.models.user import User
from app.core.config import settings

def serialize_user(user: User) -> dict:
    user_dict = user.__dict__.copy()

    # 💡 Обработка avatar_url (если он есть)
    if user.avatar_url:
        # Только добавляем префикс, если это относительный путь
        if not user.avatar_url.startswith("http"):
            user_dict["avatar_url"] = f"{settings.MEDIA_URL}/media/{user.avatar_url}"
        else:
            user_dict["avatar_url"] = user.avatar_url
    else:
        user_dict["avatar_url"] = None

    # Остальные поля
    if user_dict.get("description") is None:
        user_dict["description"] = ""

    user_dict.pop("_sa_instance_state", None)
    return user_dict
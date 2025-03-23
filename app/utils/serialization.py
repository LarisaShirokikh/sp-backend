from app.models.user import User
from app.core.config import settings

def serialize_user(user: User) -> dict:
    """
    Serialize a User model instance into a dictionary,
    ensuring all fields are properly formatted for API responses.
    """
    # Create a copy of the user's dictionary to avoid modifying the original
    user_dict = user.__dict__.copy()
    
    # Handle avatar URL construction
    if avatar := user_dict.get("avatar"):
        user_dict["avatar_url"] = f"{settings.MEDIA_URL}/media/{avatar}"
    else:
        user_dict["avatar_url"] = None
    
    # Fix the description field to ensure it's a string
    if user_dict.get("description") is None:
        user_dict["description"] = ""
    
    # Remove SQLAlchemy internal state
    user_dict.pop("_sa_instance_state", None)
    
    return user_dict
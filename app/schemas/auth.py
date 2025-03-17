# app/schemas/auth.py
from pydantic import BaseModel
from app.schemas.token import Token  # если нужно, можно использовать Token вместо отдельных полей
from app.schemas.user import UserResponse

class AuthResponse(BaseModel):
    access_token: str
    token_type: str
    user: UserResponse

    class Config:
        orm_mode = True
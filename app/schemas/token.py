from pydantic import BaseModel
from typing import Any, Dict, Optional


class Token(BaseModel):
    access_token: str
    token_type: str
    user: Optional[Dict[str, Any]] = None


class TokenPayload(BaseModel):
    sub: Optional[int] = None


class TokenData(BaseModel):
    user_id: Optional[int] = None
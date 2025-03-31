# app/services/token_service.py
import uuid
from datetime import datetime, timedelta, timezone
from jose import jwt
from fastapi import Request

from app.core.config import settings
from app.db.redis import get_redis_client

class TokenService:
    @staticmethod
    async def create_token(user_id: int, expires_delta: timedelta, token_type: str, request: Request):
        jti = str(uuid.uuid4())
        expire = datetime.now(timezone.utc) + expires_delta
        to_encode = {
            "exp": int(expire.timestamp()),
            "sub": str(user_id),
            "jti": jti,
            "type": token_type
        }
        token = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

        redis = await get_redis_client()
        key = f"{token_type}_token:{jti}"
        await redis.set(key, str(user_id), ex=int(expires_delta.total_seconds()))

        # Сохраняем мета-данные
        meta = {
            "ip": request.client.host,
            "user_agent": request.headers.get("user-agent", "unknown"),
            "created": datetime.now(timezone.utc).isoformat()
        }
        await redis.hset(f"session_meta:{jti}", mapping=meta)

        # Добавляем в активные сессии пользователя
        await redis.sadd(f"user_sessions:{user_id}", jti)

        return token

    @staticmethod
    async def invalidate_token(jti: str, token_type: str, user_id: int):
        redis = await get_redis_client()
        await redis.delete(f"{token_type}_token:{jti}")
        await redis.sadd("blacklist", jti)
        await redis.srem(f"user_sessions:{user_id}", jti)
        await redis.delete(f"session_meta:{jti}")

    @staticmethod
    async def is_token_valid(jti: str, token_type: str, user_id: str):
        redis = await get_redis_client()
        if await redis.sismember("blacklist", jti):
            return False
        stored_user_id = await redis.get(f"{token_type}_token:{jti}")
        return stored_user_id == user_id

    @staticmethod
    async def list_user_sessions(user_id: int):
        redis = await get_redis_client()
        sessions = await redis.smembers(f"user_sessions:{user_id}")
        data = []
        for jti in sessions:
            meta = await redis.hgetall(f"session_meta:{jti}")
            if meta:
                meta["jti"] = jti
                data.append(meta)
        return data
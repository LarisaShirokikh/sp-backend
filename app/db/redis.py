# app/db/redis.py
import redis.asyncio as redis
from app.core.config import settings

redis_client = None


async def get_redis_client():
    global redis_client
    if redis_client is None:
        redis_client = redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            db=settings.REDIS_DB,
            password=settings.REDIS_PASSWORD,
            decode_responses=True,
        )
    return redis_client

async def close_redis_client(redis):
    await redis.close()
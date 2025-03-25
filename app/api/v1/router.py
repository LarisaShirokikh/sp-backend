from fastapi import APIRouter
from app.api.v1.auth.router import router as auth_router
from app.api.v1.users.router import router as user_router
from app.api.v1.forum.router import router as forum_router
from app.api.v1.topic.router import router as topic_router

router = APIRouter()

router.include_router(auth_router, prefix="/auth", tags=["auth"])
router.include_router(user_router, prefix="/users", tags=["users"])
router.include_router(forum_router, prefix="/forum", tags=["forum"])
router.include_router(topic_router, prefix="/forum/topic", tags=["forum-topic"])
# router.include_router(users_router, prefix="/users", tags=["users"])
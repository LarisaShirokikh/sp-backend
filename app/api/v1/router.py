import logging
from fastapi import APIRouter
from app.api.v1.auth.router import router as auth_router
from app.api.v1.users.router import router as user_router
from app.api.v1.forum.router import router as forum_router
from app.api.v1.topic.router import router as topic_router
from app.api.v1.activities.router import router as activities_router
from app.api.v1.group_buy.router import router as group_buy_router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()

router.include_router(auth_router, prefix="/auth", tags=["auth"])
router.include_router(user_router, prefix="/users", tags=["users"])
router.include_router(forum_router, prefix="/forum", tags=["forum"])
router.include_router(topic_router, prefix="/forum/topic", tags=["forum-topic"])
router.include_router(activities_router, prefix="/activities", tags=["activities"])
router.include_router(group_buy_router, prefix="/group_buy", tags=["group_buy"])

# logging.info(f"All registered routes: {[route for route in router.routes]}")
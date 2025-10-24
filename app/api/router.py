from fastapi import APIRouter

from app.api.endpoints import activities, admin, auth, forum, group, topic, users

router = APIRouter()


router.include_router(auth.router, prefix="/auth", tags=["auth"])
router.include_router(users.router, prefix="/users", tags=["users"])
router.include_router(forum.router, prefix="/forum", tags=["forum"])
router.include_router(topic.router, prefix="/topics", tags=["topics"])
router.include_router(group.router, prefix="/groups", tags=["groups"])
router.include_router(activities.router, prefix="/activities", tags=["activities"])
router.include_router(admin.router, prefix="/admin", tags=["admin"])
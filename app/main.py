from fastapi import FastAPI
from app.core.config import settings
from app.api.v1.router import router

app = FastAPI(
    title=settings.PROJECT_NAME,
    description=settings.PROJECT_DESCRIPTION,
    version=settings.VERSION,
    debug=settings.DEBUG,
)

app.include_router(router, prefix="/api")

@app.get("/")
async def root():
    return {"message": "Project is working!"}
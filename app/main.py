from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.core.config import settings
from app.api.v1.router import router
from app.models import *

app = FastAPI(
    title=settings.PROJECT_NAME,
    description=settings.PROJECT_DESCRIPTION,
    version=settings.VERSION,
    debug=settings.DEBUG,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # URL вашего фронтенда
    allow_credentials=True,
    allow_methods=["*"],  # Или конкретные методы ["GET", "POST"]
    allow_headers=["*"],  # Или конкретные заголовки
)
app.mount("/media", StaticFiles(directory="media"), name="media")

app.include_router(router, prefix="/api")

@app.get("/")
async def root():
    return {"message": "Project is working!"}
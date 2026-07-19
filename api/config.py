import os
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class Settings(BaseSettings):
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql://sinagersat:12345678@127.0.0.1:5432/db_sinagersat",
    )
    JWT_SECRET: str = os.getenv("JWT_SECRET", "sinagersat-secret-key-change-in-production-2026")
    JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
    JWT_EXPIRE_MINUTES: int = int(os.getenv("JWT_EXPIRE_MINUTES", "480"))
    UPLOAD_DIR: str = os.getenv("UPLOAD_DIR", os.path.join(BASE_DIR, "uploads"))

    class Config:
        env_file = ".env"


settings = Settings()

import os
from dataclasses import dataclass
from typing import Optional

from dotenv import load_dotenv


load_dotenv()


@dataclass
class Config:
    SECRET_KEY: str = os.getenv("SECRET_KEY", "dev-secret-key")
    ADMIN_PASSWORD: str = os.getenv("ADMIN_PASSWORD", "change-me")
    DATABASE: str = os.getenv("DATABASE_PATH", os.path.join("data", "app.db"))
    UPLOAD_FOLDER: str = os.getenv("UPLOAD_FOLDER", os.path.join("storage"))
    ENCRYPTION_KEY: Optional[str] = os.getenv("ENCRYPTION_KEY")

    MAX_CONTENT_LENGTH: int = 50 * 1024 * 1024  # 50 MB limit per request
    SESSION_COOKIE_HTTPONLY: bool = True
    SESSION_COOKIE_SECURE: bool = False  # set True in production with HTTPS
    SESSION_COOKIE_SAMESITE: str = "Lax"

import os
from typing import Optional
from pydantic_settings import BaseSettings

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # app/core -> app
ENV_FILE = os.path.join(BASE_DIR, ".env")  # points to app/.env

class Settings(BaseSettings):
    PROJECT_NAME: str = "Order Service"
    DATABASE_URL: str = "sqlite:///./orders.db"

    # Optional. When set, every API request must send the same value in the X-Api-Key header
    # (set BACKEND_API_KEY in the bot to the same value). Leave empty to keep the old behaviour.
    API_KEY: Optional[str] = None
    # Optional secret for signing print links. Falls back to a hash of DATABASE_URL.
    PRINT_SECRET: Optional[str] = None
    # Optional public base url of this service (e.g. https://safos-backend-production.up.railway.app).
    # Railway sets RAILWAY_PUBLIC_DOMAIN automatically, which is used when this is empty.
    PUBLIC_URL: Optional[str] = None
    RAILWAY_PUBLIC_DOMAIN: Optional[str] = None

    class Config:
        env_file = ENV_FILE
        env_file_encoding = "utf-8"
        extra = "ignore"

settings = Settings()

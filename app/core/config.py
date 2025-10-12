import os
from pydantic_settings import BaseSettings

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # app/core -> app
ENV_FILE = os.path.join(BASE_DIR, ".env")  # points to app/.env

class Settings(BaseSettings):
    PROJECT_NAME: str = "Order Service"
    DATABASE_URL: str = "sqlite:///./orders.db"

    class Config:
        env_file = ENV_FILE
        env_file_encoding = "utf-8"

settings = Settings()

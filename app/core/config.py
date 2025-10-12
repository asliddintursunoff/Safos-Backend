from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "Order Service"
    DATABASE_URL: str = "sqlite:///./orders.db"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()

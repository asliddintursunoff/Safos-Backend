from pydantic import BaseModel

class Settings(BaseModel):
    PROJECT_NAME: str = "Order Service"
    DATABASE_URL: str = "sqlite:///./orders.db"

settings = Settings()
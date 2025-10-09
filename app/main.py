from fastapi import FastAPI
from app.api.router import api_router
from app.db.session import engine
from app.db.base import Base
from app.models.agent import Agent
from app.models.order import Order,OrderItem
from app.models.product import Product
app = FastAPI(title="Order Service")

Base.metadata.create_all(bind=engine)
app.include_router(api_router)

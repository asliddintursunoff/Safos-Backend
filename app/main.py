from fastapi import FastAPI
from app.api.router import api_router
from app.db.session import engine
from app.db.base import Base
from app.models.agent import Agent
from app.models.order import Order,OrderItem,OrderContribution
from app.models.product import Product
app = FastAPI(title="Order Service")

# create_all only creates missing tables (e.g. order_contributions); it never alters or drops existing ones
Base.metadata.create_all(bind=engine)
app.include_router(api_router)

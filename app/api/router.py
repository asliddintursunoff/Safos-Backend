from fastapi import APIRouter
from app.api.routes import products, orders,agent

api_router = APIRouter()
api_router.include_router(products.router, prefix="/products", tags=["products"])
api_router.include_router(orders.router, prefix="/orders", tags=["orders"])
api_router.include_router(agent.router, prefix="/agents", tags=["agents"])
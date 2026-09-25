from typing import Optional
import hmac
from fastapi import APIRouter, Depends, Header, HTTPException
from app.api.routes import products, orders,agent
from app.core.config import settings


def require_api_key(x_api_key: Optional[str] = Header(None)):
    # only enforced when API_KEY is configured, so nothing changes until both services have it
    if settings.API_KEY and not hmac.compare_digest(x_api_key or "", settings.API_KEY):
        raise HTTPException(status_code=401, detail="Invalid API key")


api_router = APIRouter()
api_router.include_router(products.router, prefix="/products", tags=["products"], dependencies=[Depends(require_api_key)])
api_router.include_router(orders.router, prefix="/orders", tags=["orders"], dependencies=[Depends(require_api_key)])
api_router.include_router(agent.router, prefix="/agents", tags=["agents"], dependencies=[Depends(require_api_key)])
api_router.include_router(orders.public_router)

from pydantic import BaseModel

from typing import List,Optional
from datetime import datetime
from app.schemas.product import ProductOut
from app.schemas.agent import AgentOut

class OrderItemCreate(BaseModel):
    product_id :int
    quantity: int

class OrderCreate(BaseModel):
    agent_id:int
    for_who:str
    items:List[OrderItemCreate]
    order_date:Optional[datetime] = None
    update_date:Optional[datetime] = None
    is_approved:Optional[bool] = False




class OrderItemOut(BaseModel):
    id:int
    product:Optional[ProductOut]
    quantity:int
    total_price: Optional[float]
    
    class Config:
        orm_mode = True


class OrderOut(BaseModel):
    id: int
    agent: AgentOut
    for_who:str
    items: List[OrderItemOut]   # 👈 FIXED
    order_date: datetime
    update_date: Optional[datetime] = None  # 👈 nullable in DB
    is_approved: bool
    get_total_price: Optional[float]

    class Config:
        orm_mode = True

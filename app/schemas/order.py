from pydantic import BaseModel

from typing import List,Optional
from datetime import datetime
from app.schemas.product import ProductOut
from app.schemas.agent import AgentBase

class OrderItemCreate(BaseModel):
    product_id :int
    quantity: int

class OrderCreate(BaseModel):
    agent_id:Optional[int] = None
    dostavchik_id:Optional[int] = None
    for_who:Optional[str]
    items:Optional[List[OrderItemCreate]]
    order_date:Optional[datetime] = None
    update_date:Optional[datetime] = None
    is_approved:Optional[bool] = True
    user_chat_id: Optional[str] = None
    user_message_id: Optional[int] = None
    channel_chat_id: Optional[str] = None
    channel_message_id: Optional[int] = None



class OrderItemOut(BaseModel):
    id:int
    product:Optional[ProductOut]
    quantity:int
    total_price: Optional[float]
    
    class Config:
        from_attributes = True



class OrderOut(BaseModel):
    id: int
    agent: Optional[AgentBase] = None
    dostavchik:Optional[AgentBase] = None
    for_who:str
    items: List[OrderItemOut]   # 👈 FIXED
    order_date: datetime
    update_date: Optional[datetime] = None  # 👈 nullable in DB
    is_approved: bool
    is_delivered:bool
    get_total_price: Optional[float]
    user_chat_id: Optional[str] = None
    user_message_id: Optional[int] = None
    channel_chat_id: Optional[str] = None
    channel_message_id: Optional[int] = None
    class Config:
        from_attributes = True



from pydantic import BaseModel
from typing import Optional

class OrderPatch(BaseModel):
    user_chat_id: Optional[str] = None
    user_message_id: Optional[str] = None
    channel_chat_id: Optional[str] = None
    channel_message_id: Optional[str] = None

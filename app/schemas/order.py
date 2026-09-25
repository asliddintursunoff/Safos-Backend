from pydantic import BaseModel

from typing import List,Optional
from datetime import datetime
from app.schemas.product import ProductOut
from app.models.agent import UserRole

class OrderItemCreate(BaseModel):
    product_id :int
    quantity: int

class OrderCreate(BaseModel):
    agent_id:Optional[int] = None
    dostavchik_id:Optional[int] = None
    for_who:Optional[str] = None
    items:Optional[List[OrderItemCreate]] = None
    order_date:Optional[datetime] = None
    update_date:Optional[datetime] = None
    delivered_date:Optional[datetime]=None 
    is_approved:Optional[bool] = True
    user_chat_id: Optional[str] = None
    user_message_id: Optional[int] = None
    channel_chat_id: Optional[str] = None
    channel_message_id: Optional[int] = None
    # update_date of the order when the user opened it for editing.
    # If the order was changed by someone else since then, the update is rejected with 409.
    base_update_date: Optional[datetime] = None


class OrderAgentOut(BaseModel):
    """Agent info inside an order (same fields as before, but tolerant to empty values)."""
    id: Optional[int] = None
    telegram_id: Optional[int] = None
    first_name: Optional[str] = ""
    last_name: Optional[str] = ""
    phone_number: Optional[str] = None
    percentage: Optional[float] = 0
    role: Optional[UserRole] = None

    class Config:
        from_attributes = True
        use_enum_values = True


class OrderItemOut(BaseModel):
    id:int
    product:Optional[ProductOut]
    quantity:int
    total_price: Optional[float]
    
    class Config:
        from_attributes = True



class OrderOut(BaseModel):
    id: int
    agent: Optional[OrderAgentOut] = None
    dostavchik:Optional[OrderAgentOut] = None
    for_who:Optional[str] = ""
    items: List[OrderItemOut]   # 👈 FIXED
    order_date: datetime
    update_date: Optional[datetime] = None
    delivered_date:Optional[datetime]=None  # 👈 nullable in DB
    is_approved: bool
    is_delivered:bool
    get_total_price: Optional[float]
    user_chat_id: Optional[str] = None
    user_message_id: Optional[int] = None
    channel_chat_id: Optional[str] = None
    channel_message_id: Optional[int] = None
    # short signed link that opens the same print page (used when the long print url does not fit in Telegram)
    print_url: Optional[str] = None
    class Config:
        from_attributes = True



class OrderPatch(BaseModel):
    user_chat_id: Optional[str] = None
    user_message_id: Optional[int] = None
    channel_chat_id: Optional[str] = None
    channel_message_id: Optional[int] = None

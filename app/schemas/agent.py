from pydantic import BaseModel
from enum import Enum
from app.models.agent import UserRole
from typing import Optional
class AgentBase(BaseModel):
    first_name:str
    last_name:str
    phone_number:str
    role:Optional[UserRole] = UserRole.agent
    
    class Config:
        use_enum_values = True
class CreateAgent(AgentBase):
    pass 

class AgentOut(AgentBase):
    id: int
    total_given_salary:float
    class Config:
        orm_mode = True



class PhoneCheckRequest(BaseModel):
    phone_number: str

class TelegramAttachRequest(BaseModel):
    phone_number: str
    telegram_id: int 
class PhoneCheckResponse(BaseModel):
    exists: bool

class AgentWithSalaryOut(AgentOut):
    remaining_salary: float
class RemainingSalary(BaseModel):
    remaining_salary:float

    class Config:
        schema_extra = {
            "example": {"remaining_salary": 1500.0}
        }

class TotalPrice(BaseModel):
    total_price:float

    class Config:
        schema_extra = {
            "example": {"total_price": 1500.0}
        }

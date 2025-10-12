from pydantic import BaseModel
from enum import Enum

class UnitEnum(str,Enum):
    KG = 'kg'
    DONA = 'dona'
class ProductBase(BaseModel):
    name:str
    price:float
    unit: UnitEnum 

class CreateProduct(ProductBase):
    pass 

class ProductOut(ProductBase):
    id:int

    class Config:
        from_attributes = True




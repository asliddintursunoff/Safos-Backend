from sqlalchemy import Column,Integer,String,Float,Enum
from app.db.base import Base
import enum

class ProductUnit(enum.Enum):
    KG = "kg"
    DONA = "dona"
class Product(Base):
    __tablename__ = "products"

    id = Column(Integer,primary_key=True,index=True)
    name = Column(String,nullable=False)
    unit = Column(String(20),default=ProductUnit.DONA)
    price = Column(Float,nullable=False)
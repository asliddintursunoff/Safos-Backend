from sqlalchemy import Column,Integer,String,Float,Enum as SQLEnum
from sqlalchemy.orm import relationship
from app.db.base import Base
import enum
class UserRole(str, enum.Enum):
    admin = "admin"
    agent = "agent"
class Agent(Base):
    __tablename__ = "agents"
    id = Column(Integer,primary_key=True,index=True)
    first_name = Column(String(50),nullable=False)
    last_name = Column(String(50),nullable=False)
    phone_number = Column(String(13),nullable=False,unique=True)
    total_given_salary = Column(Float,default= 0)
    role = Column(SQLEnum(UserRole), default=UserRole.agent)
    telegram_id = Column(Integer, unique=True, nullable=True)
    orders = relationship("Order",back_populates="agent")
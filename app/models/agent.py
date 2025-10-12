from sqlalchemy import Column,Integer,String,Float,Enum as SQLEnum
from sqlalchemy.orm import relationship
from sqlalchemy import BigInteger
from app.db.base import Base
import enum
class UserRole(str, enum.Enum):
    admin = "admin"
    agent = "agent"
    dostavchik = "dostavchik"
class Agent(Base):
    __tablename__ = "agents"
    id = Column(Integer,primary_key=True,index=True)
    first_name = Column(String(50),nullable=False)
    last_name = Column(String(50),nullable=False)
    phone_number = Column(String(13),nullable=False,unique=True)
    total_earned_salary = Column(Float,default= 0)
    percentage = Column(Float,default=0)
    total_given_salary = Column(Float, default=0)
    role = Column(SQLEnum(UserRole), default=UserRole.agent)
    telegram_id = Column(BigInteger, unique=True, nullable=False)
    orders = relationship("Order",back_populates="agent")
    
    orders = relationship(
        "Order",
        back_populates="agent",
        foreign_keys="[Order.agent_id]"  # explicitly use agent_id FK
    )

    dostavchik_orders = relationship(
        "Order",
        back_populates="dostavchik",
        foreign_keys="[Order.dostavchik_id]"
    )
    @property
    def remaining_salary(self):
        return self.total_earned_salary - self.total_given_salary
from sqlalchemy import Column,String,Float,Integer,DateTime,Boolean,ForeignKey,select,func
from sqlalchemy.ext.hybrid import hybrid_property
from app.models.product import Product
from sqlalchemy.orm import relationship
from datetime import datetime
from app.db.base import Base

class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer,primary_key=True,index=True)
    agent_id= Column(Integer,ForeignKey("agents.id"))
    for_who = Column(String(150))
    order_date = Column(DateTime,default=datetime.now)
    update_date = Column(DateTime,nullable=True)
    is_approved = Column(Boolean,default=False)

    items = relationship("OrderItem",back_populates="order")

    agent = relationship("Agent",back_populates="orders")

    @hybrid_property
    def get_total_price(self):
        if self.is_approved:
            return sum(item.total_price for item in self.items)
        return 0

    @get_total_price.expression
    def get_total_price(cls):
        return (
            select(func.coalesce(func.sum(OrderItem.quantity * Product.price), 0))
            .select_from(OrderItem)
            .join(Product, Product.id == OrderItem.product_id)
            .where(OrderItem.order_id == cls.id)
            .label("get_total_price")
        )
class OrderItem(Base):
    __tablename__ = "order_items"
    id = Column(Integer,primary_key=True,index=True)
    order_id = Column(Integer,ForeignKey("orders.id"))
    product_id = Column(Integer,ForeignKey("products.id"))
    quantity = Column(Float,default=0)

    order = relationship("Order",back_populates="items")
    product = relationship("Product")

    @property
    def total_price(self):
        return self.quantity * self.product.price
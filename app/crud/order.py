from sqlalchemy.orm import Session
from app.models.order import Order,OrderItem
from app.schemas.order import OrderCreate,OrderItemCreate
from datetime import datetime
def create_order(db:Session,order_in:OrderCreate):
    order = Order(agent_id = order_in.agent_id,for_who = order_in.for_who)
    db.add(order)
    db.commit()
    db.refresh(order)
    for item in order_in.items:
        db_item = OrderItem(order_id = order.id,product_id = item.product_id,quantity = item.quantity)
        db.add(db_item)
    db.commit()
    db.refresh(order)
    return order




def update_order(db: Session, order_id: int, order_in: OrderCreate):
    # 1️⃣ Get the existing order
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        return None  # or raise an HTTPException in FastAPI route

    # 2️⃣ Update basic fields
    order.agent_id = order_in.agent_id
    order.for_who = order_in.for_who
    order.is_approved = order_in.is_approved
    order.update_date = datetime.now()

    # 3️⃣ Delete old items (optional – depends on logic)
    db.query(OrderItem).filter(OrderItem.order_id == order.id).delete()

    # 4️⃣ Add new items
    for item in order_in.items:
        db_item = OrderItem(
            order_id=order.id,
            product_id=item.product_id,
            quantity=item.quantity,
        )
        db.add(db_item)

    # 5️⃣ Commit and refresh
    db.commit()
    db.refresh(order)

    return order

def order_approved(db:Session,order_id:int):
    order = db.query(Order).filter(Order.id ==order_id).first()
    order.is_approved = True
    db.commit()
    db.refresh(order)
    return order

def order_not_approved(db:Session,order_id:int):
    order = db.query(Order).filter(Order.id ==order_id).first()
    order.is_approved = False
    db.commit()
    db.refresh(order)
    return order


def get_order(db:Session,id:int):
    return db.query(Order).filter(Order.id == id).first()

#deleting order
def delete_order(db:Session,id:int):
    order = db.query(Order).filter(Order.id ==id).first()
    if not order:
        return None
    
    db.query(OrderItem).filter(OrderItem.order_id == order.id).delete()
    db.delete(order)
    db.commit()
    return {"message": f"Order order: {id} deleted successfully"}

    


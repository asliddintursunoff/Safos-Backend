from sqlalchemy.orm import Session
from app.models.order import Order,OrderItem
from app.schemas.order import OrderCreate
from datetime import datetime
from typing import Optional, Union
from app.models.agent import UserRole
from fastapi import HTTPException
from app.models.agent import Agent, UserRole

def get_all(db:Session):
    return db.query(Order).filter(Order.is_delivered==False and Order.is_approved ==True)

def create_order(db: Session, order_in: OrderCreate):
    # 1️⃣ Create the order object
    order = Order(
        agent_id=order_in.agent_id,
        dostavchik_id=order_in.dostavchik_id,
        for_who=order_in.for_who,
        order_date=datetime.now(),
        user_chat_id = order_in.user_chat_id,
        user_message_id = order_in.user_message_id,
        channel_chat_id = order_in.channel_chat_id,
        channel_message_id = order_in.channel_message_id,
        is_approved=order_in.is_approved or True
    )
    db.add(order)
    db.commit()
    db.refresh(order)

    # 2️⃣ Add items and calculate total product price
    total_price = 0
    for item in order_in.items:
        db_item = OrderItem(
            order_id=order.id,
            product_id=item.product_id,
            quantity=item.quantity
        )
        db.add(db_item)
        db.flush()  # so we can access db_item.product

        total_price += db_item.quantity * db_item.product.price

    # 3️⃣ Detect role of who created this order
    role = None
    if order.agent:  # agent_id exists
        role = order.agent.role.value
    else:
        # fallback if agent not attached (e.g. admin creates)
        role = UserRole.admin.value

    # 4️⃣ Assign price based on role
    if role == UserRole.agent.value:
        order.agent_locked_price = total_price
    elif role == UserRole.admin.value:
        order.admin_extra_price = total_price
    elif role == UserRole.dostavchik.value:
        order.dostavchik_extra_price = total_price
        order.dostavchik_id = order.agent_id

    # 5️⃣ Update timestamp
    order.update_date = datetime.now()

    # 6️⃣ Commit final order
    db.commit()
    db.refresh(order)
    return order







def update_order(db: Session, order_id: int, order_in: OrderCreate,updater_role: Optional[Union[str, UserRole]] = None,):
    """
    Update order items and adjust price logic automatically based on agent role.
    Roles:
      - agent       → modifies only agent_locked_price
      - admin       → modifies admin_extra_price first, then dostavchik, then agent if decreasing
      - dostavchik  → modifies dostavchik_extra_price first, then admin, then agent if decreasing
    """
    # 1️⃣ Fetch order
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        return None
    
    if order.is_delivered == True:
        raise HTTPException(status_code=406,detail="Yetqazib berilgan zakazni o'zgartirib bo'lmaydi!\nAgar o'zgartirish zarur bo'lsa birinchi yetqazilmadi tugmasini bosing!")
    
    # 2️⃣ Detect who is making the update (based on attached agent)
    if updater_role is None:
        role = order.agent.role if order.agent else UserRole.admin
    elif isinstance(updater_role, str):
        role = UserRole(updater_role)
    else: 
        raise HTTPException(status_code=404,detail="Role is not found")
    # 3️⃣ Update basic fields
    order.for_who = order_in.for_who
    order.update_date = datetime.now()

    if order_in.user_chat_id:
        order.user_chat_id = order_in.user_chat_id
    if order_in.user_message_id:
        order.user_message_id = order_in.user_message_id
    if order_in.channel_chat_id:
        order.channel_chat_id = order_in.channel_chat_id
    if order_in.channel_message_id:
        order.channel_message_id = order_in.channel_message_id

    # 4️⃣ Remove existing order items before adding new ones
    db.query(OrderItem).filter(OrderItem.order_id == order.id).delete()

    # 5️⃣ Add updated order items and calculate new total
    new_total = 0
    for item in order_in.items:
        db_item = OrderItem(
            order_id=order.id,
            product_id=item.product_id,
            quantity=item.quantity
        )
        db.add(db_item)
        db.flush()
        new_total += db_item.quantity * db_item.product.price

    # 6️⃣ Calculate current total components
    current_total = (
        order.agent_locked_price +
        order.admin_extra_price +
        order.dostavchik_extra_price
    )
    diff = new_total - current_total

    # 7️⃣ Role-based price update logic
    if role == UserRole.agent.value:
        # Agent can only control their locked price
        order.agent_locked_price = new_total

    elif role == UserRole.admin.value:
        if diff > 0:
            # Admin adds extra
            order.admin_extra_price += diff
        else:
            reduce_value = abs(diff)
            # Reduce admin part first
            reduce_admin = min(order.admin_extra_price, reduce_value)
            order.admin_extra_price -= reduce_admin
            reduce_value -= reduce_admin

            # Then dostavchik part
            if reduce_value > 0:
                reduce_dostavchik = min(order.dostavchik_extra_price, reduce_value)
                order.dostavchik_extra_price -= reduce_dostavchik
                reduce_value -= reduce_dostavchik

            # Finally agent locked price
            if reduce_value > 0:
                order.agent_locked_price -= reduce_value

    elif role == UserRole.dostavchik.value:
        order.dostavchik_id = order.agent_id
        if diff > 0:
            # Dostavchik adds extra
            order.dostavchik_extra_price += diff
        else:
            reduce_value = abs(diff)
            # Reduce dostavchik part first
            reduce_dostavchik = min(order.dostavchik_extra_price, reduce_value)
            order.dostavchik_extra_price -= reduce_dostavchik
            reduce_value -= reduce_dostavchik

            # Then admin
            if reduce_value > 0:
                reduce_admin = min(order.admin_extra_price, reduce_value)
                order.admin_extra_price -= reduce_admin
                reduce_value -= reduce_admin

            # Finally agent
            if reduce_value > 0:
                order.agent_locked_price -= reduce_value

    # 8️⃣ Commit the updates
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
    if order.agent:
        order.agent.total_earned_salary -= order.agent_locked_price * order.agent.percentage / 100
    if order.dostavchik:
        order.dostavchik.total_earned_salary -= order.dostavchik_extra_price * order.dostavchik.percentage/100
    if order.admin_extra_price > 0:
            admin = db.query(Agent).filter(Agent.role == UserRole.admin).first()
            if admin:
                admin.total_earned_salary -= order.admin_extra_price * admin.percentage / 100

    db.query(OrderItem).filter(OrderItem.order_id == order.id).delete()
    db.delete(order)
    db.commit()
    return {"message": f"Order order: {id} deleted successfully"}

    


def is_order_delivered(db: Session, order_id: int,current_user_id:int, b: bool):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    if b==True:  # mark as delivered
        if order.is_delivered:
            return order  # just return the order
        
        order.is_delivered = True
        order.dostavchik_id = current_user_id
        order.delivered_date = datetime.now()
        
        if order.agent:
            order.agent.total_earned_salary += order.agent_locked_price * order.agent.percentage / 100
        
        if order.admin_extra_price > 0:
            admin = db.query(Agent).filter(Agent.role == UserRole.admin).first()
            if admin:
                admin.total_earned_salary += order.admin_extra_price * admin.percentage / 100
        
        if order.dostavchik:
            order.dostavchik.total_earned_salary += order.dostavchik_extra_price * order.dostavchik.percentage / 100

    else:  # mark as not delivered
        if not order.is_delivered:
            return order  # just return the order
        
        order.is_delivered = False
        order.delivered_date = None
        order.dostavchik_id = None
        
        if order.agent:
            order.agent.total_earned_salary -= order.agent_locked_price * order.agent.percentage / 100
        
        if order.admin_extra_price > 0:
            admin = db.query(Agent).filter(Agent.role == UserRole.admin).first()
            if admin:
                admin.total_earned_salary -= order.admin_extra_price * admin.percentage / 100
        
        if order.dostavchik:
            order.dostavchik.total_earned_salary -= order.dostavchik_extra_price * order.dostavchik.percentage / 100

    db.commit()
    db.refresh(order)
    return order  # return full Order object

from sqlalchemy.orm import Session
from sqlalchemy import and_
from app.models.order import Order,OrderItem,OrderContribution
from app.models.product import Product
from app.schemas.order import OrderCreate
from datetime import datetime
from typing import Optional, Union, Dict
from fastapi import HTTPException
from app.models.agent import Agent, UserRole
from app.services import order_money as money


def get_all(db:Session):
    return db.query(Order).filter(and_(Order.is_delivered == False, Order.is_approved == True)).order_by(Order.id).all()


def get_order(db:Session,id:int):
    return db.query(Order).filter(Order.id == id).first()


def _lock_order(db: Session, order_id: int) -> Order:
    """Load the order and lock its row until commit, so two people can not change it at the same time."""
    order = db.query(Order).filter(Order.id == order_id).with_for_update().populate_existing().first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order


def _wanted_quantities(db: Session, items) -> Dict[int, tuple]:
    """{product_id: (product, quantity)} from request items; validates products and quantities."""
    wanted: Dict[int, list] = {}
    for item in items or []:
        if item.quantity is None or item.quantity < 0:
            raise HTTPException(status_code=400, detail="Mahsulot soni manfiy bo'lishi mumkin emas")
        if item.quantity == 0:
            continue
        if item.product_id not in wanted:
            product = db.query(Product).filter(Product.id == item.product_id).first()
            if not product:
                raise HTTPException(status_code=400, detail=f"Mahsulot topilmadi (id={item.product_id})")
            wanted[item.product_id] = [product, 0]
        wanted[item.product_id][1] += item.quantity
    if not wanted:
        raise HTTPException(status_code=400, detail="Zakazda kamida bitta mahsulot bo'lishi kerak")
    return {pid: (p, q) for pid, (p, q) in wanted.items()}


def create_order(db: Session, order_in: OrderCreate):
    wanted = _wanted_quantities(db, order_in.items)
    creator = db.query(Agent).filter(Agent.id == order_in.agent_id).first() if order_in.agent_id else None
    role = money.role_value(creator.role) if creator and creator.role else UserRole.admin.value

    try:
        order = Order(
            agent_id=order_in.agent_id,
            dostavchik_id=order_in.dostavchik_id,
            for_who=order_in.for_who,
            order_date=datetime.now(),
            user_chat_id = order_in.user_chat_id,
            user_message_id = order_in.user_message_id,
            channel_chat_id = order_in.channel_chat_id,
            channel_message_id = order_in.channel_message_id,
            is_approved=True if order_in.is_approved is None else order_in.is_approved,
            agent_locked_price=0,
            admin_extra_price=0,
            dostavchik_extra_price=0,
        )
        db.add(order)
        db.flush()  # get order.id, still inside the same transaction

        for product_id, (product, qty) in wanted.items():
            db.add(OrderItem(order_id=order.id, product_id=product_id, quantity=qty))
            money.add_quantity(db, order, creator, role, product, qty)

        if role == UserRole.dostavchik.value:
            order.dostavchik_id = order.agent_id

        money.recompute_role_totals(db, order)
        order.update_date = datetime.now()

        # one commit: the order is saved with all its items or not at all
        db.commit()
    except Exception:
        db.rollback()
        raise
    db.refresh(order)
    return order


def update_order(db: Session, order_id: int, order_in: OrderCreate,updater_role: Optional[Union[str, UserRole]] = None, updater: Optional[Agent] = None):
    """
    Update order items. Money of the change goes to the person who made it
    (see app/services/order_money.py for the rules).
    """
    try:
        order = _lock_order(db, order_id)

        if order.is_delivered == True:
            raise HTTPException(status_code=406,detail="Yetqazib berilgan zakazni o'zgartirib bo'lmaydi!\nAgar o'zgartirish zarur bo'lsa birinchi yetqazilmadi tugmasini bosing!")

        # someone else changed the order after this user opened it -> do not overwrite their change
        if order_in.base_update_date is not None and order.update_date is not None:
            if abs((order.update_date - order_in.base_update_date).total_seconds()) > 0.001:
                raise HTTPException(status_code=409, detail="Zakaz siz ochganingizdan keyin boshqa foydalanuvchi tomonidan o'zgartirildi. Qaytadan oching.")

        if updater is not None:
            role = money.role_value(updater.role)
        elif updater_role is None:
            role = money.role_value(order.agent.role) if order.agent else UserRole.admin.value
        else:
            role = money.role_value(updater_role)
        if role not in money.ROLE_COLUMNS:
            raise HTTPException(status_code=404,detail="Role is not found")

        wanted = _wanted_quantities(db, order_in.items)

        # 3️⃣ Update basic fields
        if order_in.for_who is not None:
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

        uses_ledger = money.ensure_ledger(db, order)

        # current quantities (one row per product)
        current_items = db.query(OrderItem).filter(OrderItem.order_id == order.id).all()
        current: Dict[Optional[int], OrderItem] = {}
        for item in current_items:
            if item.product_id in current:
                current[item.product_id].quantity = (current[item.product_id].quantity or 0) + (item.quantity or 0)
                db.delete(item)
            else:
                current[item.product_id] = item

        editor_id = updater.id if updater is not None else None
        for product_id, item in list(current.items()):
            if product_id not in wanted:
                if uses_ledger and product_id is not None:
                    money.remove_quantity(db, order, editor_id, product_id, item.quantity or 0)
                db.delete(item)

        for product_id, (product, qty) in wanted.items():
            item = current.get(product_id)
            old_qty = (item.quantity or 0) if item else 0
            delta = qty - old_qty
            if item is None:
                db.add(OrderItem(order_id=order.id, product_id=product_id, quantity=qty))
            else:
                item.quantity = qty
            if uses_ledger:
                if delta > 0:
                    money.add_quantity(db, order, updater, role, product, delta)
                elif delta < 0:
                    money.remove_quantity(db, order, editor_id, product_id, -delta)

        if uses_ledger:
            money.recompute_role_totals(db, order)
        else:
            new_total = sum((p.price or 0) * q for p, q in wanted.values())
            money.legacy_apply_diff(order, role, new_total)

        db.commit()
    except Exception:
        db.rollback()
        raise
    db.refresh(order)
    return order


def _change_status(db: Session, order_id: int, delivered: Optional[bool] = None, approved: Optional[bool] = None, deliverer_id: Optional[int] = None):
    """
    Change delivered/approved flags and give or take back salary exactly once.
    Salary is given while an order is delivered AND approved.
    """
    try:
        order = _lock_order(db, order_id)
        was_credited = money.is_credited(order)

        new_delivered = order.is_delivered if delivered is None else delivered
        new_approved = order.is_approved if approved is None else approved
        will_be_credited = bool(new_delivered) and bool(new_approved)

        # take back BEFORE changing dostavchik_id (legacy formula uses it)
        if was_credited and not will_be_credited:
            money.credit(db, order, -1)

        if delivered is not None and bool(delivered) != bool(order.is_delivered):
            order.is_delivered = delivered
            if delivered:
                order.dostavchik_id = deliverer_id
                order.delivered_date = datetime.now()
            else:
                order.dostavchik_id = None
                order.delivered_date = None
        if approved is not None:
            order.is_approved = approved

        db.flush()
        if will_be_credited and not was_credited:
            money.credit(db, order, +1)

        db.commit()
    except Exception:
        db.rollback()
        raise
    db.refresh(order)
    return order


def order_approved(db:Session,order_id:int):
    return _change_status(db, order_id, approved=True)


def order_not_approved(db:Session,order_id:int):
    return _change_status(db, order_id, approved=False)


def is_order_delivered(db: Session, order_id: int,current_user_id:int, b: bool):
    order = get_order(db, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    if b and order.is_approved == False:
        raise HTTPException(status_code=400,detail="Order is disapproved!")
    return _change_status(db, order_id, delivered=bool(b), deliverer_id=current_user_id)


#deleting order
def delete_order(db:Session,id:int):
    try:
        order = db.query(Order).filter(Order.id == id).with_for_update().populate_existing().first()
        if not order:
            return None
        # salary was given only if delivered and approved; take back only in that case
        if money.is_credited(order):
            money.credit(db, order, -1)
            db.flush()  # write the reversal before the ledger rows are removed

        db.query(OrderContribution).filter(OrderContribution.order_id == order.id).delete(synchronize_session=False)
        db.query(OrderItem).filter(OrderItem.order_id == order.id).delete(synchronize_session=False)
        db.delete(order)
        db.commit()
    except Exception:
        db.rollback()
        raise
    return {"message": f"Order order: {id} deleted successfully"}

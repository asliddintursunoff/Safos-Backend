from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.crud import order as crud
from app.schemas.order import OrderCreate, OrderOut
from app.api.deps import get_db
from app.models.agent import Agent
from app.core.security import get_current_user
from app.core.auth import require_admin, require_self_or_admin,require_self_or_dostavchik_or_admin,require_dostavchik_or_admin
from app.services.order import calculate_total_items
router = APIRouter()



from fastapi import  Depends, Query
from typing import Optional
from datetime import datetime,date
from sqlalchemy import func, and_

@router.get("/total-price")
def get_total_orders_price(
    which_day: Optional[datetime] = Query(None, description="Enter a specific day"),
    start_date: Optional[datetime] = Query(None, description="Start date filter"),
    end_date: Optional[datetime] = Query(None, description="End date filter"),
    today_only: bool = Query(False, description="Only today's total"),
    db: Session = Depends(get_db),
    current_user:Agent = Depends(get_current_user)

):
    """
    📊 Get total price of all orders.
    - `today_only=True` → total for today.
    - `which_day` → total for that specific day.
    - `start_date` & `end_date` → total for that range.
    - No filters → total for all orders.
    """
    require_admin(current_user)
    query = db.query(func.coalesce(func.sum(Order.get_total_price), 0))

    # 🕒 Today only
    if today_only:
        today_start = datetime.combine(date.today(), datetime.min.time())
        today_end = datetime.combine(date.today(), datetime.max.time())
        query = query.filter(and_(Order.order_date >= today_start, Order.order_date <= today_end))

    # 📅 Specific day
    elif which_day:
        day_start = datetime.combine(which_day.date(), datetime.min.time())
        day_end = datetime.combine(which_day.date(), datetime.max.time())
        query = query.filter(and_(Order.order_date >= day_start, Order.order_date <= day_end))

    # 📆 Date range
    elif start_date and end_date:
        query = query.filter(and_(Order.order_date >= start_date, Order.order_date <= end_date))

    total = query.scalar()
    return {"total_price": total or 0}



# ----------------- CREATE ORDER -----------------
@router.post("/", response_model=OrderOut)
def create_order(
    order_in: OrderCreate,
    db: Session = Depends(get_db),
    current_user: Agent = Depends(get_current_user)
):
    # Admin orders are auto-approved, agent orders are not
    if current_user.role == "admin":
        order_in.is_approved = True
    else:
        order_in.is_approved = True
        if order_in.agent_id != current_user.id:
            raise HTTPException(403, "Agents can only create orders for themselves")

    order = crud.create_order(db, order_in)
    return order

# ----------------- GET ALL ORDERS QUantity -----------------
@router.get("/calculating-existing-orders")
def calculating_existing_orders(db:Session=Depends(get_db)):
    orders = crud.get_all(db)
    
    return calculate_total_items(orders)


# ----------------- GET ALL ORDERS -----------------
@router.get("/", response_model=List[OrderOut])
def get_all_orders(db: Session = Depends(get_db), current_user: Agent = Depends(get_current_user)):
    
    return crud.get_all(db)
# ----------------- GET ORDER BY ID -----------------
@router.get("/{order_id}", response_model=OrderOut)
def get_order(order_id: int, db: Session = Depends(get_db), current_user: Agent = Depends(get_current_user)):
    order = crud.get_order(db, order_id)
    if not order:
        raise HTTPException(404, "Order not found")
    require_self_or_admin(current_user, order.agent_id)
    return order




# ----------------- UPDATE ORDER -----------------
@router.put("/{order_id}", response_model=OrderOut)
def update_order(
    order_id: int,
    order_in: OrderCreate,
    db: Session = Depends(get_db),
    current_user: Agent = Depends(get_current_user)
):
    order = crud.get_order(db, order_id)
    if not order:
        raise HTTPException(404, "Order not found")

    require_self_or_dostavchik_or_admin(current_user, order.agent_id)

    # agents cannot approve orders

    updated_order = crud.update_order(db, order_id, order_in,current_user.role)
    return updated_order

# ----------------- DELETE ORDER -----------------
@router.delete("/{order_id}")
def delete_order(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: Agent = Depends(get_current_user)
):
    order = crud.get_order(db, order_id)
    if not order:
        raise HTTPException(404, "Order not found")

    require_self_or_admin(current_user, order.agent_id)
    return crud.delete_order(db, order_id)

# ----------------- APPROVE ORDER -----------------
@router.post("/{order_id}/approve", response_model=OrderOut)
def approve_order(order_id: int, db: Session = Depends(get_db), current_user: Agent = Depends(get_current_user)):
    require_dostavchik_or_admin(current_user)
    return crud.order_approved(db, order_id)

# ----------------- DISAPPROVE ORDER -----------------
@router.post("/{order_id}/disapprove", response_model=OrderOut)
def disapprove_order(order_id: int, db: Session = Depends(get_db), current_user: Agent = Depends(get_current_user)):
    require_dostavchik_or_admin(current_user)
    return crud.order_not_approved(db, order_id)


@router.post("/{order_id}/delivered", response_model=OrderOut)
def delivered(order_id: int,is_delivered:bool, db: Session = Depends(get_db), current_user: Agent = Depends(get_current_user)):
        require_dostavchik_or_admin(current_user)
        return crud.is_order_delivered(db, order_id,is_delivered)


from app.models.order import Order
from app.schemas.order import OrderPatch
@router.patch("/patch/{order_id}", response_model=OrderOut)
def patch_order(order_id: int, patch_data: OrderPatch, db: Session = Depends(get_db)):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    update_data = patch_data.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(order, key, value)

    db.commit()
    db.refresh(order)
    return order


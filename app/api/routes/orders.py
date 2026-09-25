from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from typing import List, Optional
from datetime import datetime,date
from app.crud import order as crud
from app.schemas.order import OrderCreate, OrderOut, OrderPatch
from app.api.deps import get_db
from app.models.agent import Agent, UserRole
from app.models.order import Order
from app.core.security import get_current_user
from app.core.auth import require_admin, require_self_or_admin,require_self_or_dostavchik_or_admin,require_dostavchik_or_admin
from app.services.order import calculate_total_items
from app.services.printing import verify_order_signature, build_print_page_url
router = APIRouter()
# no X-Api-Key here: opened from the Telegram print button, protected by a signed token instead
public_router = APIRouter()


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
    # disapproved orders are worth 0 (same as Order.get_total_price for a single order)
    query = db.query(func.coalesce(func.sum(Order.get_total_price), 0)).filter(Order.is_approved == True)

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
    order_in.agent_id = current_user.id
    order_in.dostavchik_id = None
    order_in.is_approved = True

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
    require_self_or_dostavchik_or_admin(current_user, order.agent_id)
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

    updated_order = crud.update_order(db, order_id, order_in,current_user.role, updater=current_user)
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
        return crud.is_order_delivered(db, order_id,current_user.id,is_delivered)


@router.patch("/patch/{order_id}", response_model=OrderOut)
def patch_order(order_id: int, patch_data: OrderPatch, db: Session = Depends(get_db), current_user: Agent = Depends(get_current_user)):
    order = db.query(Order).filter(Order.id == order_id).with_for_update().populate_existing().first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    require_self_or_dostavchik_or_admin(current_user, order.agent_id)

    update_data = patch_data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(order, key, value)

    db.commit()
    db.refresh(order)
    return order


# ----------------- PRINT (short link for the 🖨 Print button) -----------------
@public_router.get("/print/orders/{order_id}", include_in_schema=False)
def print_order(order_id: int, t: str = Query(...), db: Session = Depends(get_db)):
    if not verify_order_signature(order_id, t):
        raise HTTPException(status_code=403, detail="Invalid print link")
    order = crud.get_order(db, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Zakaz topilmadi")
    return RedirectResponse(build_print_page_url(order), status_code=307)

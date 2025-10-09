from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.crud import order as crud
from app.schemas.order import OrderCreate, OrderOut
from app.api.deps import get_db
from app.models.agent import Agent
from app.core.security import get_current_user
from app.core.auth import require_admin, require_self_or_admin

router = APIRouter()

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
        order_in.is_approved = False
        if order_in.agent_id != current_user.id:
            raise HTTPException(403, "Agents can only create orders for themselves")

    order = crud.create_order(db, order_in)
    return order

# ----------------- GET ORDER BY ID -----------------
@router.get("/{order_id}", response_model=OrderOut)
def get_order(order_id: int, db: Session = Depends(get_db), current_user: Agent = Depends(get_current_user)):
    order = crud.get_order(db, order_id)
    if not order:
        raise HTTPException(404, "Order not found")
    require_self_or_admin(current_user, order.agent_id)
    return order

# ----------------- GET ALL ORDERS -----------------
@router.get("/", response_model=List[OrderOut])
def get_all_orders(db: Session = Depends(get_db), current_user: Agent = Depends(get_current_user)):
    if current_user.role == "admin":
        return db.query(crud.Order).all()
    else:
        return db.query(crud.Order).filter(crud.Order.agent_id == current_user.id).all()

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

    require_self_or_admin(current_user, order.agent_id)

    if current_user.role != "admin":
        order_in.is_approved = False  # agents cannot approve orders

    updated_order = crud.update_order(db, order_id, order_in)
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
    require_admin(current_user)
    return crud.order_approved(db, order_id)

# ----------------- DISAPPROVE ORDER -----------------
@router.post("/{order_id}/disapprove", response_model=OrderOut)
def disapprove_order(order_id: int, db: Session = Depends(get_db), current_user: Agent = Depends(get_current_user)):
    require_admin(current_user)
    return crud.order_not_approved(db, order_id)

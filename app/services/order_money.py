"""
Who earns what from an order.

Rules
-----
* Whoever ADDS quantity of a product (creating the order or editing it later) owns that
  added quantity. Their share is `quantity * unit_price` (price at the moment they added it).
* When somebody DECREASES a product, the quantity is taken back from that product only:
    1. first from the rows the editor added himself (newest first) - fixing your own mistake
       never touches other people's money,
    2. then from the other people's rows, newest first (the last person who added that
       product loses it first).
* Salary is given when the order is delivered AND approved, with each person's own
  percentage. The exact amount given is stored per ledger row, so un-deliver /
  disapprove / delete takes back exactly what was given (even if percentages changed).
* Order.agent_locked_price / admin_extra_price / dostavchik_extra_price stay as the
  role totals of the ledger, so the existing reports keep working.

Orders created before the ledger existed ("legacy" orders, no ledger rows) are moved to
the ledger on their first edit when the owner of the money is unambiguous. Otherwise
they keep the old column arithmetic so no money is re-assigned by guessing.
"""
from collections import defaultdict
from typing import Dict, Optional, Tuple

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.agent import Agent, UserRole
from app.models.order import Order, OrderContribution, OrderItem

EPS = 1e-9

ROLE_COLUMNS = {
    UserRole.agent.value: "agent_locked_price",
    UserRole.admin.value: "admin_extra_price",
    UserRole.dostavchik.value: "dostavchik_extra_price",
}


def role_value(role) -> str:
    return role.value if isinstance(role, UserRole) else str(role)


def _add_salary(db: Session, agent_id: Optional[int], amount: float):
    if not agent_id or abs(amount) < EPS:
        return
    # atomic "salary = salary + amount" in SQL, safe when many requests touch the same agent
    db.query(Agent).filter(Agent.id == agent_id).update(
        {Agent.total_earned_salary: func.coalesce(Agent.total_earned_salary, 0) + amount},
        synchronize_session=False,
    )


def _first_admin_id(db: Session) -> Optional[int]:
    admin = db.query(Agent).filter(Agent.role == UserRole.admin).order_by(Agent.id).first()
    return admin.id if admin else None


def _percentage(db: Session, agent_id: Optional[int], cache: Dict[int, float]) -> float:
    if not agent_id:
        return 0
    if agent_id not in cache:
        agent = db.query(Agent).filter(Agent.id == agent_id).first()
        cache[agent_id] = (agent.percentage or 0) if agent else 0
    return cache[agent_id]


# ---------------------------------------------------------------- ledger rows

def contributions(db: Session, order_id: int, product_id: Optional[int] = None, lock: bool = False):
    q = db.query(OrderContribution).filter(OrderContribution.order_id == order_id)
    if product_id is not None:
        q = q.filter(OrderContribution.product_id == product_id)
    if lock:
        q = q.with_for_update().populate_existing()
    return q.order_by(OrderContribution.id).all()


def has_ledger(db: Session, order_id: int) -> bool:
    return db.query(OrderContribution.id).filter(OrderContribution.order_id == order_id).first() is not None


def add_quantity(db: Session, order: Order, agent: Optional[Agent], role, product, quantity: float):
    if quantity <= EPS:
        return
    db.add(OrderContribution(
        order_id=order.id,
        agent_id=agent.id if agent else None,
        role=role_value(role),
        product_id=product.id,
        quantity=quantity,
        unit_price=product.price or 0,
        credited_salary=0,
    ))


def remove_quantity(db: Session, order: Order, editor_id: Optional[int], product_id: int, quantity: float):
    rows = [r for r in contributions(db, order.id, product_id, lock=True) if (r.quantity or 0) > EPS]
    own = [r for r in reversed(rows) if editor_id is not None and r.agent_id == editor_id]
    others = [r for r in reversed(rows) if not (editor_id is not None and r.agent_id == editor_id)]
    left = quantity
    for row in own + others:
        if left <= EPS:
            break
        take = min(row.quantity, left)
        row.quantity -= take
        left -= take
    # rows are kept with quantity 0 (not deleted) so the order stays marked as "ledger" order


def recompute_role_totals(db: Session, order: Order):
    db.flush()
    totals = defaultdict(float)
    for row in contributions(db, order.id):
        totals[row.role] += row.value
    for role, column in ROLE_COLUMNS.items():
        setattr(order, column, totals.get(role, 0))


# ---------------------------------------------------------------- legacy orders

def _legacy_single_owner(db: Session, order: Order) -> Tuple[bool, Optional[int], str]:
    """
    For a legacy order return (ok, agent_id, role) of the single person owning all its money.
    ok=False when money is split between roles (we can not know which products whose).
    """
    parts = {
        UserRole.agent.value: order.agent_locked_price or 0,
        UserRole.admin.value: order.admin_extra_price or 0,
        UserRole.dostavchik.value: order.dostavchik_extra_price or 0,
    }
    nonzero = [role for role, v in parts.items() if abs(v) > EPS]
    if len(nonzero) > 1:
        return False, None, ""

    creator = order.agent
    creator_role = role_value(creator.role) if creator and creator.role else UserRole.admin.value
    role = nonzero[0] if nonzero else creator_role

    if role == UserRole.agent.value:
        return True, order.agent_id, role
    if role == UserRole.dostavchik.value:
        if creator_role == UserRole.dostavchik.value:
            return True, order.agent_id, role
        return True, order.dostavchik_id, role
    # admin money: the creator if an admin created it, else the admin old code paid
    if creator_role == UserRole.admin.value:
        return True, order.agent_id, role
    return True, _first_admin_id(db), role


def ensure_ledger(db: Session, order: Order) -> bool:
    """True if the order uses the ledger (moving a legacy order to it when it is safe)."""
    if has_ledger(db, order.id):
        return True
    ok, owner_id, role = _legacy_single_owner(db, order)
    if not ok:
        return False
    owner = db.query(Agent).filter(Agent.id == owner_id).first() if owner_id else None
    items = db.query(OrderItem).filter(OrderItem.order_id == order.id).all()
    for item in items:
        if item.product and (item.quantity or 0) > EPS:
            add_quantity(db, order, owner, role, item.product, item.quantity)
    db.flush()
    return True


def legacy_apply_diff(order: Order, role: str, new_total: float):
    """Old column arithmetic (kept for legacy orders whose money is split between roles)."""
    current_total = (order.agent_locked_price or 0) + (order.admin_extra_price or 0) + (order.dostavchik_extra_price or 0)
    diff = new_total - current_total

    own_col = ROLE_COLUMNS[role]
    if diff > 0:
        setattr(order, own_col, (getattr(order, own_col) or 0) + diff)
        return

    # decrease: own part first, then the others (same order the old code used)
    if role == UserRole.agent.value:
        order_of_cols = ["agent_locked_price", "admin_extra_price", "dostavchik_extra_price"]
    elif role == UserRole.admin.value:
        order_of_cols = ["admin_extra_price", "dostavchik_extra_price", "agent_locked_price"]
    else:
        order_of_cols = ["dostavchik_extra_price", "admin_extra_price", "agent_locked_price"]

    reduce_value = -diff
    for col in order_of_cols:
        have = getattr(order, col) or 0
        take = min(max(have, 0), reduce_value)
        setattr(order, col, have - take)
        reduce_value -= take
    if reduce_value > EPS:
        order.agent_locked_price = (order.agent_locked_price or 0) - reduce_value


# ---------------------------------------------------------------- salary

def _credit_ledger(db: Session, order: Order, sign: int):
    cache: Dict[int, float] = {}
    per_agent = defaultdict(float)
    for row in contributions(db, order.id, lock=True):
        if sign > 0:
            amount = row.value * _percentage(db, row.agent_id, cache) / 100 if row.agent_id else 0
            row.credited_salary = amount
            per_agent[row.agent_id] += amount
        else:
            per_agent[row.agent_id] -= row.credited_salary or 0
            row.credited_salary = 0
    for agent_id, amount in per_agent.items():
        _add_salary(db, agent_id, amount)


def _credit_legacy(db: Session, order: Order, sign: int):
    """Exactly the old formula: agent, dostavchik (dostavchik_id) and the first admin."""
    cache: Dict[int, float] = {}
    if order.agent_id:
        _add_salary(db, order.agent_id, sign * (order.agent_locked_price or 0) * _percentage(db, order.agent_id, cache) / 100)
    if order.dostavchik_id:
        _add_salary(db, order.dostavchik_id, sign * (order.dostavchik_extra_price or 0) * _percentage(db, order.dostavchik_id, cache) / 100)
    if (order.admin_extra_price or 0) > 0:
        admin_id = _first_admin_id(db)
        _add_salary(db, admin_id, sign * order.admin_extra_price * _percentage(db, admin_id, cache) / 100)


def is_credited(order: Order) -> bool:
    return bool(order.is_delivered) and bool(order.is_approved)


def credit(db: Session, order: Order, sign: int):
    if has_ledger(db, order.id):
        _credit_ledger(db, order, sign)
    else:
        _credit_legacy(db, order, sign)

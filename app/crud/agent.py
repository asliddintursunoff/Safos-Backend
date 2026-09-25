from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from app.schemas.agent import CreateAgent
from app.models.agent import Agent, UserRole
from sqlalchemy import func, and_, exists
from fastapi import HTTPException
from app.models.order import Order, OrderContribution
from datetime import datetime, date


def normalize_phone(phone_num: str) -> str:
    return ''.join(filter(str.isdigit, phone_num or ""))


def get_all(db:Session):
    return db.query(Agent).order_by(Agent.id).all()

def get_by_id(db:Session,id:int):
    agent = db.query(Agent).filter(Agent.id == id).first()
    if not agent:
        raise HTTPException(status_code=404,detail=f"Agent id:{id} is not found")

    return agent

def agent_exists_by_phone(db: Session, phone_num: str) -> bool:
    normalized = normalize_phone(phone_num)
    return db.query(Agent).filter(Agent.phone_number == normalized).first() is not None

def verify_and_attach_telegram_id(db: Session, phone_number: str, telegram_id: int):
    normalized = normalize_phone(phone_number)
    agent = db.query(Agent).filter(Agent.phone_number == normalized).with_for_update().first()
    if not agent:
        return None
    if agent.telegram_id != telegram_id:
        # this Telegram account may be linked to an old/other agent record; move it here
        db.query(Agent).filter(Agent.telegram_id == telegram_id, Agent.id != agent.id).update(
            {Agent.telegram_id: None}, synchronize_session=False
        )
        agent.telegram_id = telegram_id
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Telegram akkaunt boshqa agentga biriktirilgan")
    db.refresh(agent)
    return agent


def create(db: Session, agent_in: CreateAgent):
    if agent_exists_by_phone(db, agent_in.phone_number):
        raise HTTPException(status_code=409, detail="Bunday raqam bilan oldin ruyhatdan otilgan")

    agent = Agent(
        first_name=agent_in.first_name,
        last_name=agent_in.last_name,
        phone_number=normalize_phone(agent_in.phone_number),
        role = agent_in.role,
        percentage = agent_in.percentage,
        total_earned_salary=0,
        total_given_salary=0,
    )
    db.add(agent)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Bunday raqam bilan oldin ruyhatdan otilgan")
    db.refresh(agent)
    return agent


def get_agent_salary_price(db: Session, agent_id: int):

    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail=f"Agent id:{agent_id} is not found")
    remaining_salary = (agent.total_earned_salary or 0) - (agent.total_given_salary or 0)
    return remaining_salary


def add_salary(db: Session, agent_id: int, salary_amount: float):
    updated = db.query(Agent).filter(Agent.id == agent_id).update(
        {Agent.total_given_salary: func.coalesce(Agent.total_given_salary, 0) + salary_amount},
        synchronize_session=False,
    )
    if not updated:
        raise HTTPException(status_code=404, detail=f"Agent id:{agent_id} is not found")
    db.commit()
    return db.query(Agent).filter(Agent.id == agent_id).first()



def update(db:Session,agent_in:CreateAgent,id:int):
    agent = db.query(Agent).filter(Agent.id == id).first()
    if not agent:
        raise HTTPException(status_code=404,detail=f"Agent id:{id} is not found")

    agent.first_name = agent_in.first_name
    agent.last_name = agent_in.last_name
    agent.phone_number = normalize_phone(agent_in.phone_number)
    agent.percentage = agent_in.percentage
    agent.role = agent_in.role

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Bu telefon raqam boshqa agentda bor")
    db.refresh(agent)
    return agent

def delete(db:Session,id:int):
    agent = db.query(Agent).filter(Agent.id == id).first()
    if not agent:
        raise HTTPException(status_code=404,detail=f"Agent id:{id} is not found")

    db.delete(agent)
    db.commit()
    return {"message": f"agent: {id} deleted successfully"}


# ---------------- REPORTS ----------------

def _date_filter(query, which_day=None, start_date=None, end_date=None, today_only=False):
    if today_only:
        today_start = datetime.combine(date.today(), datetime.min.time())
        today_end = datetime.combine(date.today(), datetime.max.time())
        query = query.filter(and_(Order.order_date >= today_start, Order.order_date <= today_end))
    if which_day:
        day_start = datetime.combine(which_day.date(), datetime.min.time())
        day_end = datetime.combine(which_day.date(), datetime.max.time())
        query = query.filter(and_(Order.order_date >= day_start, Order.order_date <= day_end))
    if start_date:
        query = query.filter(Order.order_date >= start_date)
    if end_date:
        query = query.filter(Order.order_date <= end_date)
    return query


_has_ledger = exists().where(OrderContribution.order_id == Order.id)


def get_person_total(db: Session, agent: Agent, which_day=None, start_date=None, end_date=None, today_only=False):
    """
    Money of the orders that belongs to this person:
      - new orders: everything this person added (order_contributions)
      - old orders: the old column of their role
    """
    role = agent.role.value if isinstance(agent.role, UserRole) else agent.role

    ledger_q = db.query(func.coalesce(func.sum(OrderContribution.quantity * OrderContribution.unit_price), 0)) \
        .join(Order, Order.id == OrderContribution.order_id) \
        .filter(OrderContribution.agent_id == agent.id)
    ledger_total = _date_filter(ledger_q, which_day, start_date, end_date, today_only).scalar() or 0

    if role == UserRole.dostavchik.value:
        legacy_q = db.query(func.coalesce(func.sum(Order.dostavchik_extra_price), 0)).filter(Order.dostavchik_id == agent.id)
    elif role == UserRole.admin.value:
        legacy_q = db.query(func.coalesce(func.sum(Order.admin_extra_price), 0)).filter(Order.agent_id == agent.id)
    else:
        legacy_q = db.query(func.coalesce(func.sum(Order.agent_locked_price), 0)).filter(Order.agent_id == agent.id)
    legacy_q = legacy_q.filter(~_has_ledger)
    legacy_total = _date_filter(legacy_q, which_day, start_date, end_date, today_only).scalar() or 0

    return ledger_total + legacy_total


def get_agent_total_price(
    db: Session,
    agent_id: int,
    which_day: datetime = None,
    start_date: datetime = None,
    end_date: datetime = None,
    today_only: bool = False
):
    agent = get_by_id(db, agent_id)
    return get_person_total(db, agent, which_day, start_date, end_date, today_only)


# ---------------- ADMIN TOTAL ----------------
def get_admin_total_price(
    db: Session,
    which_day: datetime = None,
    start_date: datetime = None,
    end_date: datetime = None,
    today_only: bool = False
):
    # all admin money of the company (unchanged behaviour); the column is kept in sync with the ledger
    query = db.query(func.sum(Order.admin_extra_price))
    total_price = _date_filter(query, which_day, start_date, end_date, today_only).scalar()
    return total_price or 0


# ---------------- DOSTAVCHIK TOTAL ----------------
def get_dostavchik_total_price(
    db: Session,
    dostavchik_id: int,
    which_day: datetime = None,
    start_date: datetime = None,
    end_date: datetime = None,
    today_only: bool = False
):
    agent = get_by_id(db, dostavchik_id)
    return get_person_total(db, agent, which_day, start_date, end_date, today_only)


def get_users_price(
    db: Session,
    agent: int,
    which_day: datetime = None,
    start_date: datetime = None,
    end_date: datetime = None,
    today_only: bool = False
):
    agent_obj = db.query(Agent).filter(Agent.id == agent).first()
    if not agent_obj:
        return 0  # no agent found
    return get_person_total(db, agent_obj, which_day, start_date, end_date, today_only)

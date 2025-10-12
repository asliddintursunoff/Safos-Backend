from sqlalchemy.orm import Session
from app.schemas.agent import CreateAgent,PhoneCheckRequest
from app.models.agent import Agent
from sqlalchemy import func
from fastapi import HTTPException
from app.models.order import Order
def get_all(db:Session):
    return db.query(Agent).all()

def get_by_id(db:Session,id:int):
    agent = db.query(Agent).filter(Agent.id == id).first()
    if not agent:
        raise HTTPException(status_code=404,detail=f"Agent id:{id} is not found")
    
    return agent

def agent_exists_by_phone(db: Session, phone_num: str) -> bool:
    normalized = ''.join(filter(str.isdigit, phone_num))
    return db.query(Agent).filter(Agent.phone_number == normalized).first() is not None

def verify_and_attach_telegram_id(db: Session, phone_number: str, telegram_id: int):
    normalized = ''.join(filter(str.isdigit, phone_number))
    agent = db.query(Agent).filter(Agent.phone_number == normalized).first()
    if not agent:
        return None  # or raise HTTPException if you prefer
    agent.telegram_id = telegram_id
    db.commit()
    db.refresh(agent)
    return agent


def create(db: Session, agent_in: CreateAgent):
    if agent_exists_by_phone(db, agent_in.phone_number):
        raise HTTPException(status_code=409, detail="Bunday raqam bilan oldin ruyhatdan otilgan")
    
    normalized_phone = ''.join(filter(str.isdigit, agent_in.phone_number))
    agent = Agent(
        first_name=agent_in.first_name,
        last_name=agent_in.last_name,
        phone_number=normalized_phone,
        role = agent_in.role,
        percentage = agent_in.percentage
    )
    db.add(agent)
    db.commit()
    db.refresh(agent)
    return agent





from datetime import datetime, date
from fastapi import HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func, and_



def get_agent_salary_price(db: Session, agent_id: int):
    
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail=f"Agent id:{agent_id} is not found")
    remaining_salary = (agent.total_earned_salary or 0) - (agent.total_given_salary or 0)
    return remaining_salary


def add_salary(db: Session, agent_id: int, salary_amount: float):
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail=f"Agent id:{agent_id} is not found")
    
    agent.total_given_salary += salary_amount
    db.commit()
    db.refresh(agent)
    return agent



def update(db:Session,agent_in:CreateAgent,id:int):
    agent = db.query(Agent).filter(Agent.id == id).first()
    if not agent:
        raise HTTPException(status_code=404,detail=f"Agent id:{id} is not found")
    
    agent.first_name = agent_in.first_name
    agent.last_name = agent_in.last_name
    agent.phone_number = agent_in.phone_number
    agent.percentage = agent_in.percentage
    agent.role = agent_in.role

    db.commit()
    db.refresh(agent)
    return agent

def delete(db:Session,id:int):
    agent = db.query(Agent).filter(Agent.id == id).first()
    if not agent:
        raise HTTPException(status_code=404,detail=f"Agent id:{id} is not found")
    
    db.delete(agent)
    db.commit()
    return {"message": f"agent: {id} deleted successfully"}



def get_agent_total_price(
    db: Session, 
    agent_id: int, 
    which_day: datetime = None,
    start_date: datetime = None, 
    end_date: datetime = None, 
    today_only: bool = False
):
    query = db.query(func.sum(Order.agent_locked_price)).filter(Order.agent_id == agent_id)

    if today_only:
        today_start = datetime.combine(date.today(), datetime.min.time())
        today_end = datetime.combine(date.today(), datetime.max.time())
        query = query.filter(and_(Order.order_date >= today_start, Order.order_date <= today_end))
    if which_day:
        day_start = datetime.combine(which_day.date(), datetime.min.time())
        day_end = datetime.combine(which_day.date(), datetime.max.time())
        query = query.filter(Order.order_date >= day_start, Order.order_date <= day_end)
    if start_date:
        query = query.filter(Order.order_date >= start_date)
    if end_date:
        query = query.filter(Order.order_date <= end_date)

    total_price = query.scalar()
    return total_price or 0


# ---------------- ADMIN TOTAL ----------------
def get_admin_total_price(
    db: Session,
    which_day: datetime = None,
    start_date: datetime = None,
    end_date: datetime = None,
    today_only: bool = False
):
    query = db.query(func.sum(Order.admin_extra_price))

    if today_only:
        today_start = datetime.combine(date.today(), datetime.min.time())
        today_end = datetime.combine(date.today(), datetime.max.time())
        query = query.filter(and_(Order.order_date >= today_start, Order.order_date <= today_end))
    if which_day:
        day_start = datetime.combine(which_day.date(), datetime.min.time())
        day_end = datetime.combine(which_day.date(), datetime.max.time())
        query = query.filter(Order.order_date >= day_start, Order.order_date <= day_end)
    if start_date:
        query = query.filter(Order.order_date >= start_date)
    if end_date:
        query = query.filter(Order.order_date <= end_date)

    total_price = query.scalar()
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
    query = db.query(func.sum(Order.dostavchik_extra_price)).filter(Order.dostavchik_id == dostavchik_id)

    if today_only:
        today_start = datetime.combine(date.today(), datetime.min.time())
        today_end = datetime.combine(date.today(), datetime.max.time())
        query = query.filter(and_(Order.order_date >= today_start, Order.order_date <= today_end))
    if which_day:
        day_start = datetime.combine(which_day.date(), datetime.min.time())
        day_end = datetime.combine(which_day.date(), datetime.max.time())
        query = query.filter(Order.order_date >= day_start, Order.order_date <= day_end)
    if start_date:
        query = query.filter(Order.order_date >= start_date)
    if end_date:
        query = query.filter(Order.order_date <= end_date)
    
    total_price = query.scalar()
    return total_price or 0



from sqlalchemy import func, case, and_
from datetime import datetime, date

def get_users_price(
    db: Session,
    agent: int,
    which_day: datetime = None,
    start_date: datetime = None,
    end_date: datetime = None,
    today_only: bool = False
):
    # 🧑 Get agent role first
    agent_obj = db.query(Agent).filter(Agent.id == agent).first()
    if not agent_obj:
        return 0  # no agent found

    # 🎯 Determine which column to sum based on role
    if agent_obj.role == "dostavchik":
        price_column = Order.dostavchik_extra_price
        filter_column = Order.dostavchik_id
    else:
        # fallback to agent if not dostavchik
        price_column = Order.agent_locked_price
        filter_column = Order.agent_id

    # 🧮 Build query
    query = db.query(func.sum(price_column)).filter(filter_column == agent)

    # 🕒 Date filters
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

    total_price = query.scalar()
    return total_price or 0
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
        role = agent_in.role
    )
    db.add(agent)
    db.commit()
    db.refresh(agent)
    return agent



def get_agent_total_price(db: Session, agent_id: int):
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail=f"Agent id:{agent_id} is not found")
    
    total_price = (
        db.query(func.sum(Order.get_total_price))
        .filter(Order.agent_id == agent.id)
        .scalar()
    )

    return total_price or 0


def get_agent_salary_price(db: Session, agent_id: int):
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail=f"Agent id:{agent_id} is not found")
    
    total_price = (
        db.query(func.sum(Order.get_total_price))
        .filter(Order.agent_id == agent.id)
        .scalar()
        or 0
    )


    remaining_salary = total_price - (agent.total_given_salary or 0)
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
    agent.last_name = agent.last_name
    agent.phone_number = agent_in.phone_number

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



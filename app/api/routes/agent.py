from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.schemas.agent import CreateAgent, AgentOut,AgentWithSalaryOut,RemainingSalary,TotalPrice,TelegramAttachRequest
from app.crud import agent as crud
from app.api.deps import get_db
from typing import List
from app.models.agent import Agent
from app.core.security import get_current_user
from app.core.auth import require_admin,require_self_or_admin
router = APIRouter()


@router.post("/verify-telegram", response_model=AgentOut)
def verify_and_attach(request: TelegramAttachRequest, db: Session = Depends(get_db)):
    agent = crud.verify_and_attach_telegram_id(db, request.phone_number, request.telegram_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent with this phone number not found")
    return agent

# #creating all agents
@router.post('/create', response_model=AgentWithSalaryOut)
# def create_agent(agent_in: CreateAgent, db: Session = Depends(get_db),current_user:Agent = Depends(get_current_user)):
#     require_admin(current_user)
#     agent = crud.create(db, agent_in)
#     remaining = crud.get_agent_salary_price(db, agent.id)
#     return {**agent.__dict__, "remaining_salary": remaining}

@router.post('/create', response_model=AgentWithSalaryOut)
def create_agent(agent_in: CreateAgent, db: Session = Depends(get_db)):

    agent = crud.create(db, agent_in)
    remaining = crud.get_agent_salary_price(db, agent.id)
    return {**agent.__dict__, "remaining_salary": remaining}


@router.put('/update',response_model = AgentOut)
def update_agent(agent_in:CreateAgent,db:Session = Depends(get_db),current_user:Agent = Depends(get_current_user)):
    require_admin(current_user)
    return crud.update(db,agent_in)



#getting all agents
@router.get("/all", response_model=List[AgentWithSalaryOut])
def get_agent_all(
    db: Session = Depends(get_db),
    current_user: Agent = Depends(get_current_user)
):
    require_admin(current_user)
    agents = crud.get_all(db)
    result = []
    for agent in agents:
        remaining = crud.get_agent_salary_price(db, agent.id)
        result.append({**agent.__dict__, "remaining_salary": remaining})
    return result



@router.get("/{agent_id}",response_model=AgentOut)
def get_agent(  agent_id:int,
                db:Session = Depends(get_db),
                current_user:Agent = Depends(get_current_user),
                
            ):
    require_self_or_admin(current_user,current_user.id)
    return crud.get_by_id(db,agent_id)


@router.delete("/delete/{agent_id}")
def delete_agent(agent_id:int,
                 db:Session = Depends(get_db),
                 current_user:Agent = Depends(get_current_user)):
    require_admin(current_user)
    return crud.delete(db,agent_id)


#salary part
@router.post('/add-salary/{agent_id}',response_model = AgentWithSalaryOut)
def add_salary(agent_id:int,
               salary_amount:int,
               db:Session = Depends(get_db),
    current_user:Agent = Depends(get_current_user)):
    require_admin(current_user)
    agent = crud.add_salary(db,agent_id,salary_amount)
    remaining= crud.get_agent_salary_price(db,agent_id)
    return {**agent.__dict__, "remaining_salary": remaining}

@router.get("/total-price/{agent_id}",response_model=TotalPrice)
def get_total_money(agent_id:int,
                    db:Session = Depends(get_db),
                    current_user:Agent = Depends(get_current_user)):
    require_admin(current_user)
    return {"total_price": crud.get_agent_total_price(db, agent_id)}



@router.get("/salary/{agent_id}",response_model=RemainingSalary)
def get_remaining_salary(agent_id:int,
                    db:Session = Depends(get_db),
                    current_user:Agent = Depends(get_current_user)):
    require_self_or_admin(current_user,current_user.id)
    return {"remaining_salary": crud.get_agent_salary_price(db, agent_id)}
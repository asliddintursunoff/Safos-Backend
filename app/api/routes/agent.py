from fastapi import APIRouter, Depends, HTTPException,Query
from sqlalchemy.orm import Session
from app.schemas.agent import CreateAgent, AgentOut,AgentWithSalaryOut,RemainingSalary,TotalPrice,TelegramAttachRequest
from app.crud import agent as crud
from app.api.deps import get_db
from typing import List
from app.models.agent import Agent
from typing import Optional
from datetime import datetime
from app.core.security import get_current_user
from app.core.auth import require_admin,require_self_or_admin,require_dostavchik_or_admin,require_self_or_dostavchik_or_admin
from app.models.agent import UserRole
router = APIRouter()

@router.get("/my-orders-total-price", summary="Get total price for current user based on role")
def get_total_price(
    db: Session = Depends(get_db),
    current_user: Agent = Depends(get_current_user),
    which_day: Optional[datetime] = Query(None,description="which day for get"),
    start_date: Optional[datetime] = Query(None, description="Start date filter"),
    end_date: Optional[datetime] = Query(None, description="End date filter"),
    today_only: Optional[bool] = Query(False, description="Only today orders")
):
    if current_user.role == UserRole.agent:
        total = crud.get_agent_total_price(db, current_user.id,which_day,start_date, end_date, today_only)
    elif current_user.role == UserRole.admin:
        total = crud.get_admin_total_price(db,which_day, start_date, end_date, today_only)
    elif current_user.role == UserRole.dostavchik:
        total = crud.get_dostavchik_total_price(db, current_user.id,which_day, start_date, end_date, today_only)
    else:
        raise HTTPException(status_code=403, detail="Role not allowed")
    
    return {"role": current_user.role, "total_price": total}
from app.models.order import Order
from sqlalchemy import func, and_
from datetime import datetime, date
@router.get("/earnings")
def get_agents_earnings(
    today_only: bool = Query(None),
    which_day: Optional[datetime] = Query(None),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    db: Session = Depends(get_db),
    current_user: Agent = Depends(get_current_user)
):
    """
    📊 Har bir agent, dostavchik va admin uchun daromadni hisoblash.
    Filtrlar:
    - `today_only` → bugun
    - `which_day` → aniq sana
    - `start_date` va `end_date` → oraliq
    """
    require_admin(current_user)

    query = db.query(
        Agent.id.label("agent_id"),
        Agent.first_name,
        Agent.last_name,
        Agent.role,
        func.coalesce(func.sum(Order.agent_locked_price), 0).label("agent_total"),
        func.coalesce(func.sum(Order.dostavchik_extra_price), 0).label("dostavchik_total"),
        func.coalesce(func.sum(Order.admin_extra_price), 0).label("admin_total")
    ).join(Agent, Agent.id == Order.agent_id, isouter=True)

    # 🕒 Apply date filters
    if today_only:
        today_start = datetime.combine(date.today(), datetime.min.time())
        today_end = datetime.combine(date.today(), datetime.max.time())
        query = query.filter(and_(Order.order_date >= today_start, Order.order_date <= today_end))

    elif which_day:
        day_start = datetime.combine(which_day.date(), datetime.min.time())
        day_end = datetime.combine(which_day.date(), datetime.max.time())
        query = query.filter(and_(Order.order_date >= day_start, Order.order_date <= day_end))

    elif start_date and end_date:
        query = query.filter(and_(Order.order_date >= start_date, Order.order_date <= end_date))

    query = query.group_by(Agent.id, Agent.first_name, Agent.last_name, Agent.role)
    results = query.all()

    # 🧮 Format output based on role
    output = []
    for row in results:
        if row.role == "agent":
            earnings = row.agent_total
        elif row.role == "dostavchik":
            earnings = row.dostavchik_total
        elif row.role == "admin":
            earnings = row.admin_total
        else:
            earnings = 0

        output.append({
            "agent_id": row.agent_id,
            "full_name": f"{row.first_name or ''} {row.last_name or ''}".strip(),
            "role": row.role,
            "earnings": earnings
        })

    return {"results": output}
@router.get("/taking-users-price-with-id")
def get_each_user_total_price(
    agent_id:int,
    db: Session = Depends(get_db),
    current_user: Agent = Depends(get_current_user),
    which_day: Optional[datetime] = Query(None,description="which day for get"),
    start_date: Optional[datetime] = Query(None, description="Start date filter"),
    end_date: Optional[datetime] = Query(None, description="End date filter"),
    today_only: Optional[bool] = Query(False, description="Only today orders")
):
    require_admin(current_user)
    return crud.get_users_price(db,agent_id,which_day,start_date,end_date,today_only)


    
@router.get("/salary", response_model=RemainingSalary)
def get_remaining_salary(
    agent_id: Optional[int] = None,  # now optional
    db: Session = Depends(get_db),
    current_user: Agent = Depends(get_current_user)
):
    # If agent_id is not provided, use current user's ID
    if agent_id is None:
        agent_id = current_user.id
    
    require_self_or_admin(current_user, agent_id)
    return {"remaining_salary": crud.get_agent_salary_price(db, agent_id)}



@router.post("/verify-telegram", response_model=AgentOut)
def verify_and_attach(request: TelegramAttachRequest, db: Session = Depends(get_db)):
    agent = crud.verify_and_attach_telegram_id(db, request.phone_number, request.telegram_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent with this phone number not found")
    return agent

# #creating all agents
#@router.post('/create', response_model=AgentWithSalaryOut)
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


@router.put('/update/{id}',response_model = AgentOut)
def update_agent(agent_in:CreateAgent,id:int,db:Session = Depends(get_db),current_user:Agent = Depends(get_current_user)):
    require_admin(current_user)
    return crud.update(db,agent_in,id)



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

from fastapi import Body
#salary part
@router.post('/add-salary/{agent_id}',response_model = AgentWithSalaryOut)
def add_salary(agent_id:int,
               salary_amount:int=Body(..., embed=True), 
               db:Session = Depends(get_db),
    current_user:Agent = Depends(get_current_user)):
    require_admin(current_user)
    agent = crud.add_salary(db,agent_id,salary_amount)
    remaining= crud.get_agent_salary_price(db,agent_id)
    return {**agent.__dict__, "remaining_salary": remaining}







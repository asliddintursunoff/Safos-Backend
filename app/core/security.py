from fastapi import Depends,Header,HTTPException
from sqlalchemy.orm import Session
from app.api.deps import get_db
from app.models.agent import Agent

def get_current_user(
        db:Session = Depends(get_db),
        x_telegram_id: int = Header(...),
    
        )->Agent:
    user = db.query(Agent).filter(Agent.telegram_id == x_telegram_id).first()
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return user

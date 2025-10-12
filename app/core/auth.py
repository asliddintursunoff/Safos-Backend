from app.models.agent import Agent,UserRole
from fastapi.exceptions import HTTPException
def require_admin(user:Agent):
    if user.role != UserRole.admin:
        raise HTTPException(status_code=403,detail="This method for only admins")
    
def require_self_or_admin(user:Agent,agent_id:int):
    if user.role !=UserRole.admin and user.id!=agent_id:
        raise HTTPException(status_code=403,detail="Not authorized")
    
def require_dostavchik_or_admin(user: Agent):
    """Allow dostavchik or admins."""
    if user.role not in [UserRole.dostavchik, UserRole.admin]:
        raise HTTPException(status_code=403, detail="This method is only for dostavchik or admin")

def require_self_or_dostavchik_or_admin(user: Agent, agent_id: int):
    """Allow self, dostavchik or admins."""
    if user.id != agent_id and user.role not in [UserRole.dostavchik, UserRole.admin]:
        raise HTTPException(status_code=403, detail="Not authorized")
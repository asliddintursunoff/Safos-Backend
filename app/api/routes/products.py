from fastapi import APIRouter,Depends
from sqlalchemy.orm import Session
from typing import List
from app.schemas.product import ProductOut,CreateProduct
from app.crud import product as crud
from app.api.deps import get_db
from app.core.auth import require_admin,require_self_or_admin
from app.core.security import get_current_user
from app.models.agent import Agent


router = APIRouter()

@router.get("/",response_model=List[ProductOut])
def list_products(db:Session = Depends(get_db)):
    return crud.get_all(db)

@router.get("/{product_id}",response_model=ProductOut)
def get_product(product_id:int,db:Session = Depends(get_db)):
    return crud.get_by_id(db,product_id)

@router.post("/create", response_model=ProductOut)
def create_product(product_in: CreateProduct, db: Session = Depends(get_db),current_user:Agent = Depends(get_current_user)):
    require_admin(current_user)
    return crud.create(db, product_in)

@router.put("/update/{product_id}", response_model=ProductOut)
def update_product(product_in: CreateProduct,product_id:int, db: Session = Depends(get_db),current_user:Agent = Depends(get_current_user)):
    require_admin(current_user)
    return crud.update(db,product_id,product_in)

@router.delete("/delete/{product_id}")
def delete_product(product_id:int, db: Session = Depends(get_db),current_user:Agent = Depends(get_current_user)):
    require_admin(current_user)
    return crud.delete(db,product_id)
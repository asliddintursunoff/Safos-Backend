from app.models.product import Product
from sqlalchemy.orm import Session
from app.schemas.product import CreateProduct
from fastapi import HTTPException
from fastapi import HTTPException,status

def get_by_id(db: Session, product_id: int):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product id {product_id} not found"
        )
    return product

def get_all(db: Session):
    products = db.query(Product).all()
    if not products:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No products found"
        )
    return products
def create(db:Session,product_in:CreateProduct):
    product = Product(name = product_in.name,unit = product_in.unit,price = product_in.price)
    db.add(product)
    db.commit()
    db.refresh(product)
    return product




def update(db: Session, product_id: int, product_in: CreateProduct):
    # 1. Find the existing product
    product = db.query(Product).filter(Product.id == product_id).first()
    
    # 2. Handle not found
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # 3. Update the fields
    product.name = product_in.name
    product.unit = product_in.unit
    product.price = product_in.price

    # 4. Save changes
    db.commit()
    db.refresh(product)
    return product

def delete(db:Session,id:int):
    product = db.query(Product).filter(Product.id == id).first()
    if not product:
        raise HTTPException(status_code=404,detail="Product Not Found")
    
    db.delete(product)
    db.commit()
    return {"message":"product deleted successfully"}


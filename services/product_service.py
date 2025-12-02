"""
Product Service - Product catalog management
"""
from typing import List, Optional
from sqlalchemy.orm import Session
from database import Product


def get_all_products(db: Session) -> List[Product]:
    """Get all products from database"""
    return db.query(Product).all()


def find_product_by_name(db: Session, product_name: str) -> Optional[Product]:
    """
    Find product by name (fuzzy matching)
    
    Args:
        db: Database session
        product_name: Product name to search for
        
    Returns:
        Product object or None
    """
    # Try exact match first
    product = db.query(Product).filter(Product.name == product_name).first()
    
    if product:
        return product
    
    # Try partial match
    product = db.query(Product).filter(
        Product.name.like(f"%{product_name}%")
    ).first()
    
    return product


def get_product_by_id(db: Session, product_id: int) -> Optional[Product]:
    """Get product by ID"""
    return db.query(Product).filter(Product.id == product_id).first()


def create_product(db: Session, name: str, price: float, description: str = None) -> Product:
    """Create new product"""
    product = Product(name=name, price=price, description=description)
    db.add(product)
    db.commit()
    db.refresh(product)
    return product


def update_product_price(db: Session, product_id: int, new_price: float) -> Optional[Product]:
    """Update product price"""
    product = get_product_by_id(db, product_id)
    if product:
        product.price = new_price
        db.commit()
        db.refresh(product)
    return product


def delete_product(db: Session, product_id: int) -> bool:
    """Delete product"""
    product = get_product_by_id(db, product_id)
    if product:
        db.delete(product)
        db.commit()
        return True
    return False

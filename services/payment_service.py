"""Payment Service - placeholder integration for Tap payments

This module abstracts payment link creation and payment confirmation so
we can later plug in Tap's real API without changing business logic.
"""
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from database import Order


def create_payment_link(db: Session, order: Order) -> Order:
    """Create or update a payment link for the given order.

    For now we generate a dummy URL; later this will call Tap API.
    """
    if not order.id:
        raise ValueError("Order must be persisted before creating payment link")

    dummy_url = f"https://pay.example.com/order/{order.id}"
    order.payment_url = dummy_url
    order.payment_status = "Pending"

    db.commit()
    db.refresh(order)
    return order


def mark_order_paid(db: Session, order_id: int) -> Order:
    """Mark order as paid. In real world this is called from Tap webhook."""
    order = db.query(Order).get(order_id)
    if not order:
        raise ValueError(f"Order {order_id} not found")

    order.payment_status = "Paid"
    order.status = "Paid"
    order.paid_at = datetime.utcnow()

    db.commit()
    db.refresh(order)
    return order

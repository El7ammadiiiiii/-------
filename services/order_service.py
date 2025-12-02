"""Order Service - simple helpers for creating and updating orders.

This module is intentionally simple and uses the existing SQLAlchemy
session and models from `database.py` so that imports and types work
cleanly with Pylance.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session
from database import SessionLocal
from services.order_service import create_order_from_state

from database import ConversationState, Order
from services.conversation_service import ConversationManager


def create_order_from_state(db: Session, state: ConversationState) -> Order:
    """Create an Order row from the current conversation state.

    The price is not decided here; management will set it later and
    update `approved_amount` / `total_amount`.
    """
    manager = ConversationManager(db)
    summary: Dict[str, Any] = manager.get_order_summary(state)

    order = Order(
        customer_phone=state.phone_number,
        customer_name=state.customer_name or "عميل بدون اسم",
        business_name=None,
        order_details=summary,
        total_amount=None,
        status="PendingApproval",
        payment_status="Pending",
        created_at=datetime.utcnow(),
    )

    db.add(order)
    db.commit()
    db.refresh(order)
    return order


def set_management_decision(
    db: Session,
    order_id: int,
    has_capacity: bool,
    approved_amount: Optional[float] = None,
    estimated_days: Optional[int] = None,
) -> Order:
    """Set management decision for an order: capacity and approved price."""
    order = db.query(Order).get(order_id)
    if not order:
        raise ValueError(f"Order {order_id} not found")

    order.has_capacity = has_capacity

    if not has_capacity:
        order.status = "RejectedNoCapacity"
    else:
        order.approved_amount = approved_amount
        order.estimated_days = estimated_days
        order.total_amount = approved_amount
        order.status = "ApprovedWaitingPayment"

    db.commit()
    db.refresh(order)
    return order


def get_orders_by_status(db: Session, status: str) -> List[Order]:
    """Return orders filtered by status."""
    return (
        db.query(Order)
        .filter(Order.status == status)
        .order_by(Order.created_at.desc())
        .all()
    )


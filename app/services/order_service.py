from typing import List

from sqlalchemy.orm import Session

from app.models.order import Order


def list_orders_for_user(db: Session, user_id: int) -> List[Order]:
    return (
        db.query(Order)
        .filter(Order.user_id == user_id)
        .order_by(Order.created_at.desc())
        .all()
    )

from typing import List, Optional

from sqlalchemy.orm import Session, selectinload

from app.models.order import Order, OrderStatus


# TODO: add unit tests for admin order listing filters.
def list_orders(
    db: Session,
    status: Optional[OrderStatus] = None,
    user_id: Optional[int] = None,
    limit: int = 20,
    offset: int = 0,
) -> List[Order]:
    """Return orders filtered by status or user."""

    normalized_limit = max(1, min(limit, 50))
    query = (
        db.query(Order)
        .options(selectinload(Order.items))
        .order_by(Order.created_at.desc())
    )
    if status is not None:
        query = query.filter(Order.status == status)
    if user_id is not None:
        query = query.filter(Order.user_id == user_id)

    # TODO: expand filters to include date ranges and fulfillment state.
    return query.offset(max(0, offset)).limit(normalized_limit).all()

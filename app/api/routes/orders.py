"""Order checkout and management endpoints."""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user, get_current_staff_or_admin_user, get_db
from app.models.order import OrderStatusHistory
from app.models.user import UserRole
from app.schemas.order import OrderCreateFromCart, OrderOut, OrderStatusUpdate
from app.schemas.order_tracking import OrderStatusEvent
from app.services.order_service import (
    EmptyCartError,
    ItemUnavailableError,
    OrderNotFoundError,
    create_order_from_cart,
    get_order_by_id,
    update_order_status,
)

router = APIRouter(prefix="/orders", tags=["orders"])


@router.post("/checkout", response_model=OrderOut, status_code=status.HTTP_201_CREATED)
def checkout(
    order_in: OrderCreateFromCart,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_active_user),
) -> OrderOut:
    """Create a provisional order from the authenticated user's cart."""

    try:
        return create_order_from_cart(db, current_user.id, order_in)
    except EmptyCartError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except ItemUnavailableError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.patch("/{order_id}/status", response_model=OrderOut)
def update_order_status_endpoint(
    order_id: int,
    status_in: OrderStatusUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_staff_or_admin_user),
) -> OrderOut:
    """Update an order status (staff/admin only)."""

    try:
        return update_order_status(
            db,
            order_id=order_id,
            new_status=status_in.status,
            staff_user_id=current_user.id,
        )
    except OrderNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.get("/{order_id}/status", response_model=OrderStatusEvent)
def get_order_status(
    order_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_active_user),
) -> OrderStatusEvent:
    """Return the latest status for an order (polling fallback)."""

    try:
        order = get_order_by_id(db, order_id)
    except OrderNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    if order.user_id != current_user.id and current_user.role not in (UserRole.STAFF, UserRole.ADMIN):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not allowed to view this order",
        )

    last_history = (
        db.query(OrderStatusHistory)
        .filter(OrderStatusHistory.order_id == order.id)
        .order_by(OrderStatusHistory.changed_at.desc())
        .first()
    )

    timestamp = last_history.changed_at if last_history else datetime.utcnow()

    return OrderStatusEvent(orderId=order.id, status=order.status, time=timestamp)

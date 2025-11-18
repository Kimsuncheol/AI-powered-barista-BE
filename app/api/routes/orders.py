"""Order checkout and management endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user, get_db
from app.models.user import UserRole
from app.schemas.order import OrderCreateFromCart, OrderOut, OrderStatusUpdate
from app.services.order_service import (
    EmptyCartError,
    ItemUnavailableError,
    OrderNotFoundError,
    create_order_from_cart,
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


def _ensure_staff_or_admin(user) -> None:
    if user.role not in (UserRole.STAFF, UserRole.ADMIN):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Staff or Admin privileges required",
        )


@router.patch("/{order_id}/status", response_model=OrderOut)
def update_order_status_endpoint(
    order_id: int,
    status_in: OrderStatusUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_active_user),
) -> OrderOut:
    """Update an order status (staff/admin only)."""

    _ensure_staff_or_admin(current_user)

    try:
        return update_order_status(
            db,
            order_id=order_id,
            new_status=status_in.status,
            staff_user_id=current_user.id,
        )
    except OrderNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

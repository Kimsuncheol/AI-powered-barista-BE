from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_staff_or_admin_user, get_db
from app.models.order import OrderStatus
from app.schemas.order import OrderOut, OrderStatusUpdate
from app.services.admin_order_service import list_orders
from app.services.order_service import OrderNotFoundError, update_order_status

router = APIRouter(prefix="/admin/orders", tags=["admin-orders"])


@router.get("", response_model=list[OrderOut])
def admin_list_orders(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_staff_or_admin_user),
    status_filter: Optional[OrderStatus] = Query(None, alias="status"),
    limit: int = Query(20, ge=1, le=50),
    offset: int = Query(0, ge=0),
):
    orders = list_orders(db, status=status_filter, limit=limit, offset=offset)
    # TODO: implement richer filters (date ranges, user lookup, payment state).
    return orders


@router.patch("/{order_id}/status", response_model=OrderOut)
def admin_update_order_status(
    order_id: int,
    status_in: OrderStatusUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_staff_or_admin_user),
) -> OrderOut:
    try:
        return update_order_status(
            db,
            order_id=order_id,
            new_status=status_in.status,
            staff_user_id=current_user.id,
        )
    except OrderNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

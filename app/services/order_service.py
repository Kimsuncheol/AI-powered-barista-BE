"""Service layer for cart checkout and order management."""

import asyncio
from datetime import datetime, timezone
from decimal import Decimal
from typing import List, Tuple

from anyio import from_thread
from sqlalchemy.orm import Session, selectinload

from app.models.cart import CartItem
from app.models.menu import MenuItem
from app.models.order import Order, OrderItem, OrderStatus, OrderStatusHistory
from app.schemas.order import OrderCreateFromCart
from app.schemas.order_tracking import OrderStatusEvent
from app.services.cart_service import clear_cart, get_cart_items_for_user
from app.services.order_tracking_service import order_ws_manager


class EmptyCartError(Exception):
    """Raised when checkout is attempted with no items."""


class ItemUnavailableError(Exception):
    """Raised when a menu item is not available during checkout."""


class OrderNotFoundError(Exception):
    """Raised when the requested order does not exist."""


def list_orders_for_user(db: Session, user_id: int) -> List[Order]:
    """Return orders for the user sorted by recency."""

    return (
        db.query(Order)
        .options(selectinload(Order.items))
        .filter(Order.user_id == user_id)
        .order_by(Order.created_at.desc())
        .all()
    )


def _validate_and_build_order_items(
    db: Session,
    cart_items: List[CartItem],
) -> Tuple[List[OrderItem], Decimal]:
    """Ensure each cart line references an available menu item and snapshot pricing."""

    order_items: List[OrderItem] = []
    total = Decimal("0.00")

    for cart_item in cart_items:
        menu_item = db.query(MenuItem).filter(MenuItem.id == cart_item.menu_item_id).first()
        if not menu_item or not menu_item.is_available:
            raise ItemUnavailableError(f"Menu item {cart_item.menu_item_id} is unavailable")

        # TODO: enforce seasonal windows and decrement stock quantities when inventory is modeled.
        unit_price = Decimal(str(menu_item.price))
        line_total = unit_price * cart_item.quantity

        order_items.append(
            OrderItem(
                menu_item_id=menu_item.id,
                quantity=cart_item.quantity,
                unit_price=unit_price,
                line_total=line_total,
            )
        )
        total += line_total

    return order_items, total


def create_order_from_cart(
    db: Session,
    user_id: int,
    order_in: OrderCreateFromCart,
) -> Order:
    """Create a provisional PENDING order from the user's cart."""

    cart_items = get_cart_items_for_user(db, user_id)
    if not cart_items:
        raise EmptyCartError("Cart is empty")

    order_items, total_amount = _validate_and_build_order_items(db, cart_items)

    order = Order(
        user_id=user_id,
        status=OrderStatus.PENDING,
        total_amount=total_amount,
    )
    db.add(order)
    db.flush()

    for item in order_items:
        item.order_id = order.id
        db.add(item)

    history = OrderStatusHistory(
        order_id=order.id,
        status=OrderStatus.PENDING,
        changed_by_user_id=user_id,
    )
    db.add(history)

    db.commit()
    db.refresh(order)

    clear_cart(db, user_id)
    return order


def get_order_by_id(db: Session, order_id: int) -> Order:
    """Fetch an order or raise if missing."""

    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise OrderNotFoundError("Order not found")
    return order


def update_order_status(
    db: Session,
    order_id: int,
    new_status: OrderStatus,
    staff_user_id: int,
) -> Order:
    """Update the order status and record the change history."""

    order = get_order_by_id(db, order_id)
    order.status = new_status
    db.add(order)

    history = OrderStatusHistory(
        order_id=order.id,
        status=new_status,
        changed_by_user_id=staff_user_id,
    )
    db.add(history)

    db.commit()
    db.refresh(order)

    event = OrderStatusEvent(
        orderId=order.id,
        status=order.status,
        time=datetime.now(timezone.utc),
    )

    try:
        from_thread.run(order_ws_manager.broadcast_status, event)
    except RuntimeError:
        loop = asyncio.get_running_loop()
        loop.create_task(order_ws_manager.broadcast_status(event))
    except Exception:
        # TODO: log broadcast failures
        pass

    return order


# TODO: implement staff/admin order listing endpoints, plus auditing exports.

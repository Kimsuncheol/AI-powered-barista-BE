"""Schemas for order APIs and service layer."""

from datetime import datetime
from decimal import Decimal
from typing import List

from pydantic import BaseModel, Field

from app.models.order import OrderStatus


class OrderItemOut(BaseModel):
    id: int
    menu_item_id: int
    quantity: int
    unit_price: Decimal
    line_total: Decimal

    class Config:
        orm_mode = True


class OrderStatusHistoryOut(BaseModel):
    status: OrderStatus
    changed_by_user_id: int
    changed_at: datetime

    class Config:
        orm_mode = True


class OrderOut(BaseModel):
    id: int
    user_id: int
    status: OrderStatus
    total_amount: Decimal
    created_at: datetime
    updated_at: datetime
    items: List[OrderItemOut] = Field(default_factory=list)
    status_history: List[OrderStatusHistoryOut] = Field(default_factory=list)

    class Config:
        orm_mode = True


class OrderCreateFromCart(BaseModel):
    """Placeholder for future checkout metadata (pickup time, etc.)."""

    pass


class OrderStatusUpdate(BaseModel):
    status: OrderStatus


class OrderSummary(BaseModel):
    id: int
    status: OrderStatus
    total_amount: Decimal
    created_at: datetime

    class Config:
        orm_mode = True

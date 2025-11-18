from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel

from app.models.order import OrderStatus


class OrderSummary(BaseModel):
    id: int
    status: OrderStatus
    total_amount: Decimal
    created_at: datetime

    class Config:
        orm_mode = True

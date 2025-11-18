from datetime import datetime

from pydantic import BaseModel

from app.models.order import OrderStatus


class OrderStatusEvent(BaseModel):
    orderId: int
    status: OrderStatus
    time: datetime

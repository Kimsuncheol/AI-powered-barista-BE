"""Schemas for PayPal payment endpoints."""

from typing import Optional

from pydantic import BaseModel


class PayPalCreateRequest(BaseModel):
    orderId: int


class PayPalCreateResponse(BaseModel):
    paypalOrderId: str
    status: str


class PayPalCaptureRequest(BaseModel):
    orderId: int
    paypalOrderId: str


class PayPalCaptureResponse(BaseModel):
    status: str
    transactionId: str
    message: Optional[str] = None

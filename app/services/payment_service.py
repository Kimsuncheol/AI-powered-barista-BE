"""Service layer for PayPal payments."""

import logging
from decimal import Decimal
from typing import Tuple

import httpx
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.order import Order, OrderStatus
from app.services.order_service import get_order_by_id, update_order_status

logger = logging.getLogger(__name__)


class OrderPaymentError(Exception):
    """Raised when payment flow encounters a business rule violation."""


class PayPalAPIError(Exception):
    """Raised when PayPal APIs respond with an error."""

    def __init__(self, message: str, retryable: bool = False):
        super().__init__(message)
        self.retryable = retryable


PAYPAL_CURRENCY = "USD"  # TODO: support multiple currencies per tenant.


def _http_post(*args, **kwargs):
    """Wrapper to centralize transient error detection (# RELIABILITY)."""

    try:
        response = httpx.post(*args, **kwargs)
        return response
    except httpx.RequestError as exc:  # pragma: no cover - network guard
        logger.warning("PayPal network error: %s", exc)
        raise PayPalAPIError("TRANSIENT_ERROR", retryable=True) from exc


def _get_paypal_access_token() -> str:
    """Retrieve an OAuth token from PayPal."""

    resp = _http_post(
        f"{settings.PAYPAL_BASE_URL}/v1/oauth2/token",
        auth=(settings.PAYPAL_CLIENT_ID, settings.PAYPAL_CLIENT_SECRET),
        data={"grant_type": "client_credentials"},
    )
    if resp.status_code != 200:
        raise PayPalAPIError("Failed to obtain PayPal access token", retryable=resp.status_code >= 500)
    return resp.json()["access_token"]


def _ensure_order_owner(order: Order, expected_user_id: int) -> None:
    if order.user_id != expected_user_id:
        raise OrderPaymentError("You do not have access to this order")


def create_paypal_order(db: Session, order_id: int, user_id: int) -> Tuple[str, str]:
    """Create a PayPal order for the specified internal order."""

    order = get_order_by_id(db, order_id)
    _ensure_order_owner(order, user_id)

    if order.status != OrderStatus.PENDING:
        raise OrderPaymentError("Order must be PENDING before initiating payment")

    amount = Decimal(str(order.total_amount))
    if amount <= 0:
        raise OrderPaymentError("Order total must be greater than zero")

    access_token = _get_paypal_access_token()
    payload = {
        "intent": "CAPTURE",
        "purchase_units": [
            {
                "reference_id": str(order.id),
                "amount": {
                    "currency_code": PAYPAL_CURRENCY,
                    "value": str(amount),
                },
                "custom_id": str(order.id),
            }
        ],
    }
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }

    resp = _http_post(
        f"{settings.PAYPAL_BASE_URL}/v2/checkout/orders",
        headers=headers,
        json=payload,
    )
    if resp.status_code not in (200, 201):
        raise PayPalAPIError("PayPal create order failed", retryable=resp.status_code >= 500)

    data = resp.json()
    paypal_order_id = data["id"]
    status = data.get("status", "CREATED")

    order.payment_provider = "PAYPAL"
    order.payment_status = status
    order.paypal_order_id = paypal_order_id
    db.add(order)
    db.commit()
    db.refresh(order)

    return paypal_order_id, status


def _cancel_order_due_to_payment(
    db: Session,
    order: Order,
    status_label: str,
    message: str,
) -> None:
    order.payment_provider = "PAYPAL"
    order.payment_status = status_label
    db.add(order)
    db.commit()
    # TODO: allow system/staff user context for automated status updates.
    update_order_status(db, order.id, new_status=OrderStatus.CANCELED, staff_user_id=order.user_id)
    raise PayPalAPIError(message, retryable=False)


def capture_paypal_order(
    db: Session,
    order_id: int,
    paypal_order_id: str,
    user_id: int,
) -> Tuple[str, str]:
    """Capture a PayPal payment and transition order state."""

    order = get_order_by_id(db, order_id)
    _ensure_order_owner(order, user_id)

    if order.paypal_order_id and order.paypal_order_id != paypal_order_id:
        raise OrderPaymentError("PayPal order ID mismatch")

    access_token = _get_paypal_access_token()
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }

    resp = _http_post(
        f"{settings.PAYPAL_BASE_URL}/v2/checkout/orders/{paypal_order_id}/capture",
        headers=headers,
    )
    if resp.status_code >= 500:
        raise PayPalAPIError("TRANSIENT_ERROR", retryable=True)
    data = resp.json()
    if resp.status_code not in (200, 201):
        _cancel_order_due_to_payment(db, order, "FAILED", "PayPal capture failed")

    status = data.get("status", "")
    if status != "COMPLETED":
        _cancel_order_due_to_payment(db, order, status or "FAILED", "PayPal capture not completed")

    try:
        purchase_units = data["purchase_units"]
        first_unit = purchase_units[0]
        custom_id = first_unit.get("custom_id")
        if custom_id and str(custom_id) != str(order.id):
            _cancel_order_due_to_payment(db, order, "FAILED", "Custom ID mismatch")
        payments = first_unit["payments"]
        captures = payments["captures"]
        capture = captures[0]
        transaction_id = capture["id"]
        capture_amount = Decimal(capture["amount"]["value"])
    except Exception as exc:  # pragma: no cover - defensive guard
        _cancel_order_due_to_payment(db, order, "FAILED", "Unexpected PayPal capture response")

    if capture_amount != order.total_amount:
        _cancel_order_due_to_payment(db, order, "AMOUNT_MISMATCH", "Captured amount mismatch")

    order.payment_provider = "PAYPAL"
    order.payment_status = status
    order.paypal_order_id = paypal_order_id
    order.paypal_capture_id = transaction_id
    db.add(order)
    db.commit()

    update_order_status(db, order_id, new_status=OrderStatus.ACCEPTED, staff_user_id=order.user_id)
    return status, transaction_id


# TODO: add PayPal webhook verification for refunds/disputes.

"""Payment related endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user, get_db
from app.schemas.payment import (
    PayPalCaptureRequest,
    PayPalCaptureResponse,
    PayPalCreateRequest,
    PayPalCreateResponse,
)
from app.services.payment_service import (
    OrderPaymentError,
    PayPalAPIError,
    capture_paypal_order,
    create_paypal_order,
)

router = APIRouter(prefix="/payments", tags=["payments"])


@router.post("/paypal/create", response_model=PayPalCreateResponse)
def create_paypal_order_endpoint(
    payload: PayPalCreateRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_active_user),
) -> PayPalCreateResponse:
    """Create a PayPal order for the authenticated user's order."""

    try:
        paypal_order_id, status_str = create_paypal_order(db, payload.orderId, current_user.id)
        return PayPalCreateResponse(paypalOrderId=paypal_order_id, status=status_str)
    except OrderPaymentError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except PayPalAPIError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc


@router.post("/paypal/capture", response_model=PayPalCaptureResponse)
def capture_paypal_order_endpoint(
    payload: PayPalCaptureRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_active_user),
) -> PayPalCaptureResponse:
    """Capture a PayPal order and update order/payment state."""

    try:
        status_str, transaction_id = capture_paypal_order(
            db,
            order_id=payload.orderId,
            paypal_order_id=payload.paypalOrderId,
            user_id=current_user.id,
        )
        return PayPalCaptureResponse(
            status=status_str,
            transactionId=transaction_id,
            message="Payment captured successfully.",
        )
    except PayPalAPIError as exc:
        return PayPalCaptureResponse(status="FAILED", transactionId="", message=str(exc))
    except OrderPaymentError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

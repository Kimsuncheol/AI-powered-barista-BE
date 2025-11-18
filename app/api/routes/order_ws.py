from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user_from_token, get_db
from app.models.user import UserRole
from app.services.order_service import OrderNotFoundError, get_order_by_id
from app.services.order_tracking_service import order_ws_manager

router = APIRouter()


@router.websocket("/ws/orders/{order_id}")
async def websocket_order_status(
    websocket: WebSocket,
    order_id: int,
    db: Session = Depends(get_db),
):
    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    try:
        user = get_current_user_from_token(token, db)
        order = get_order_by_id(db, order_id)
    except (OrderNotFoundError, Exception):
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    if order.user_id != user.id and user.role not in (UserRole.STAFF, UserRole.ADMIN):
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    # TODO: Move WebSocket authorization/session affinity to a shared store when scaling horizontally.
    await order_ws_manager.connect(order_id, websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        await order_ws_manager.disconnect(order_id, websocket)
    except Exception:
        await order_ws_manager.disconnect(order_id, websocket)

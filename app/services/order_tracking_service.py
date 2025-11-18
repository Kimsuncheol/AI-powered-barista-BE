from typing import Dict, List

from fastapi import WebSocket

from app.schemas.order_tracking import OrderStatusEvent


class OrderWebSocketManager:
    """
    Manages WebSocket connections per order_id.

    # NFR-BE-4 Scalability: this in-memory registry works for a single worker.
    # Move to Redis pub/sub or another broker for multi-instance deployments.
    """

    def __init__(self):
        self.active_connections: Dict[int, List[WebSocket]] = {}

    async def connect(self, order_id: int, websocket: WebSocket):
        await websocket.accept()
        if order_id not in self.active_connections:
            self.active_connections[order_id] = []
        self.active_connections[order_id].append(websocket)

    def _remove_connection(self, order_id: int, websocket: WebSocket):
        if order_id in self.active_connections:
            if websocket in self.active_connections[order_id]:
                self.active_connections[order_id].remove(websocket)
            if not self.active_connections[order_id]:
                del self.active_connections[order_id]

    async def disconnect(self, order_id: int, websocket: WebSocket):
        self._remove_connection(order_id, websocket)

    async def broadcast_status(self, event: OrderStatusEvent):
        """
        Send the given status event to all clients subscribed to event.orderId.
        """
        connections = self.active_connections.get(event.orderId, [])
        dead_connections = []
        for websocket in connections:
            try:
                await websocket.send_json(event.dict())
            except Exception:
                dead_connections.append(websocket)
        for dead in dead_connections:
            self._remove_connection(event.orderId, dead)


order_ws_manager = OrderWebSocketManager()

"""Modular alert dispatch and client connection management service."""
import json
import logging
from typing import List, Dict, Any, Callable, Optional
from fastapi import WebSocket, WebSocketDisconnect
from app.schemas.alert import MedreaAlert, ClientAcknowledgment

logger = logging.getLogger("medrea.alert_service")
logging.basicConfig(level=logging.INFO)

class ConnectionManager:
    """Manages real-time WebSocket connections for physical pagers and dashboards."""

    def __init__(self):
        self.active_pagers: List[WebSocket] = []

    async def connect_pager(self, websocket: WebSocket):
        await websocket.accept()
        self.active_pagers.append(websocket)
        logger.info(f"[WS] Physical pager connected. Total active pagers: {len(self.active_pagers)}")

    def disconnect_pager(self, websocket: WebSocket):
        if websocket in self.active_pagers:
            self.active_pagers.remove(websocket)
            logger.info(f"[WS] Physical pager disconnected. Remaining active pagers: {len(self.active_pagers)}")

    async def broadcast_to_pagers(self, message_dict: Dict[str, Any]) -> int:
        """Broadcasts a JSON-serializable message dictionary to all connected pagers."""
        if not self.active_pagers:
            logger.warning("[WS] No active pagers connected. Alert held in memory.")
            return 0

        payload = json.dumps(message_dict)
        disconnected = []
        sent_count = 0

        for connection in self.active_pagers:
            try:
                await connection.send_text(payload)
                sent_count += 1
            except Exception as e:
                logger.error(f"[WS] Failed to send to pager: {e}")
                disconnected.append(connection)

        for dead_conn in disconnected:
            self.disconnect_pager(dead_conn)

        return sent_count


class AlertService:
    """Central service responsible for routing clinical reconciliation alerts across delivery channels."""

    def __init__(self, connection_manager: Optional[ConnectionManager] = None):
        self.manager = connection_manager or ConnectionManager()
        # Handlers registered for incoming client messages (e.g. acknowledgments)
        self._ack_handlers: List[Callable[[ClientAcknowledgment], None]] = []

    # ------------------------------------------------------------------------
    # Outbound Dispatching
    # ------------------------------------------------------------------------
    async def dispatch_alert(self, alert: MedreaAlert) -> int:
        """
        Dispatches a clinical alert to all configured channels.
        In Vertical Slice 1, the primary channel is the ESP32 physical pager.
        """
        alert_payload = alert.model_dump()

        # Channel 1: Physical ESP32 Pager via WebSocket
        delivered_count = await self._dispatch_to_pager(alert_payload)

        # Pluggable hooks for future channels
        await self._dispatch_to_dashboard(alert_payload)
        await self._dispatch_to_inbox(alert_payload)
        await self._dispatch_to_email(alert_payload)

        return delivered_count

    async def _dispatch_to_pager(self, payload: Dict[str, Any]) -> int:
        logger.info(f"[AlertService] Broadcasting to pagers: Pt={payload.get('patient_id')}, Sev={payload.get('severity')}")
        return await self.manager.broadcast_to_pagers(payload)

    async def _dispatch_to_dashboard(self, payload: Dict[str, Any]):
        """Future Hook: Broadcast to Doctor Web Dashboard (Module M11)."""
        pass

    async def _dispatch_to_inbox(self, payload: Dict[str, Any]):
        """Future Hook: Store in Patient/Doctor Notification Inbox (Module M12)."""
        pass

    async def _dispatch_to_email(self, payload: Dict[str, Any]):
        """Future Hook: Optional external notification channel."""
        pass

    # ------------------------------------------------------------------------
    # Inbound Client Handling & Acknowledgment Architecture
    # ------------------------------------------------------------------------
    def register_ack_handler(self, handler: Callable[[ClientAcknowledgment], None]):
        """Registers a callback for client acknowledgment packets."""
        self._ack_handlers.append(handler)

    async def handle_incoming_client_message(self, raw_message: str):
        """
        Processes inbound messages sent by connected hardware or dashboard clients.
        Supports structured acknowledgment (ALERT_ACK) and telemetry.
        """
        try:
            data = json.loads(raw_message)
            msg_type = data.get("type")

            if msg_type == "ALERT_ACK":
                ack = ClientAcknowledgment(**data)
                logger.info(f"[AlertService] Received acknowledgment for patient {ack.patient_id} from {ack.device_ip}")
                for handler in self._ack_handlers:
                    try:
                        handler(ack)
                    except Exception as ex:
                        logger.error(f"[AlertService] Error in ack handler: {ex}")
            else:
                logger.info(f"[AlertService] Received client message: {data}")
        except Exception as e:
            logger.warning(f"[AlertService] Could not parse incoming client message: {raw_message}, error: {e}")


# Global singleton instance
alert_service = AlertService()

import asyncio
import json
import time
from datetime import datetime, timezone
from typing import Any

from fastapi import WebSocket

from backend.api.schemas import Alert, WebSocketMessage
from backend.utils.config import settings


class WebSocketManager:
    def __init__(self):
        self.connections: dict[str, set[WebSocket]] = {
            "alerts": set(),
            "transactions": set(),
            "metrics": set(),
        }
        self.connection_count = 0
        self._heartbeat_task = None

    async def connect(self, websocket: WebSocket, channel: str = "alerts") -> None:
        await websocket.accept()
        if channel not in self.connections:
            self.connections[channel] = set()
        self.connections[channel].add(websocket)
        self.connection_count += 1

    async def disconnect(self, websocket: WebSocket, channel: str = "alerts") -> None:
        if channel in self.connections:
            self.connections[channel].discard(websocket)
        else:
            for ch in self.connections:
                self.connections[ch].discard(websocket)
        self.connection_count = max(0, self.connection_count - 1)

    async def broadcast(self, channel: str, message: dict[str, Any]) -> int:
        if channel not in self.connections:
            return 0

        msg = WebSocketMessage(
            type=channel.rstrip("s"),
            data=message,
            timestamp=datetime.now(timezone.utc),
        ).model_dump()

        disconnected = set()
        sent_count = 0

        for ws in self.connections[channel]:
            try:
                await ws.send_json(msg)
                sent_count += 1
            except Exception:
                disconnected.add(ws)

        for ws in disconnected:
            self.connections[channel].discard(ws)
            self.connection_count = max(0, self.connection_count - 1)

        return sent_count

    async def broadcast_alert(self, alert: Alert) -> int:
        return await self.broadcast("alerts", alert.model_dump())

    async def broadcast_transaction(self, transaction_data: dict[str, Any]) -> int:
        return await self.broadcast("transactions", transaction_data)

    async def broadcast_metrics(self, metrics: dict[str, Any]) -> int:
        return await self.broadcast("metrics", metrics)

    async def send_personal(self, websocket: WebSocket, message: dict[str, Any]) -> None:
        try:
            msg = WebSocketMessage(
                type="message",
                data=message,
                timestamp=datetime.now(timezone.utc),
            ).model_dump()
            await websocket.send_json(msg)
        except Exception:
            pass

    async def start_heartbeat(self) -> None:
        async def _heartbeat():
            while True:
                try:
                    await asyncio.sleep(settings.WS_HEARTBEAT_INTERVAL)
                    for channel, clients in self.connections.items():
                        dead = set()
                        for ws in clients:
                            try:
                                await ws.send_json({
                                    "type": "heartbeat",
                                    "data": {"timestamp": datetime.now(timezone.utc).isoformat(), "channel": channel},
                                    "timestamp": datetime.now(timezone.utc).isoformat(),
                                })
                            except Exception:
                                dead.add(ws)
                        for ws in dead:
                            clients.discard(ws)
                            self.connection_count = max(0, self.connection_count - 1)
                except asyncio.CancelledError:
                    break
                except Exception:
                    pass

        self._heartbeat_task = asyncio.create_task(_heartbeat())

    async def stop_heartbeat(self) -> None:
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
            try:
                await self._heartbeat_task
            except asyncio.CancelledError:
                pass

    async def cleanup(self) -> None:
        await self.stop_heartbeat()
        for channel in list(self.connections.keys()):
            for ws in list(self.connections[channel]):
                try:
                    await ws.close()
                except Exception:
                    pass
            self.connections[channel].clear()
        self.connection_count = 0

    def get_connection_count(self) -> int:
        return self.connection_count

    def get_channel_counts(self) -> dict[str, int]:
        return {ch: len(clients) for ch, clients in self.connections.items()}


ws_manager = WebSocketManager()
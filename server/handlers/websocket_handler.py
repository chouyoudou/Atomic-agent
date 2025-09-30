import asyncio
import json
import logging
from typing import Dict, Set, Any, Optional
import websockets
from websockets.server import WebSocketServerProtocol
from datetime import datetime
import uuid

from core.session_manager import SessionManager
from core.ase_engine import ASEEngine
from models.structure import WebSocketMessage

logger = logging.getLogger(__name__)


class WebSocketManager:
    """WebSocket connection manager"""

    def __init__(self, session_manager: SessionManager):
        self.session_manager = session_manager
        self.ase_engine = ASEEngine()
        self.connections: Dict[str, WebSocketServerProtocol] = {}
        self.session_subscribers: Dict[str, Set[str]] = {}  # session_id -> {client_ids}
        self.client_sessions: Dict[str, str] = {}  # client_id -> session_id

    async def register(self, websocket: WebSocketServerProtocol, client_id: str = None) -> str:
        """Register new WebSocket connection"""
        if not client_id:
            client_id = str(uuid.uuid4())

        self.connections[client_id] = websocket
        logger.info(f"WebSocket client connected: {client_id}")

        # Send connection confirmation
        await self.send_to_client(client_id, {
            "type": "connection_established",
            "client_id": client_id,
            "data": {"message": "WebSocket connection successful"}
        })

        return client_id

    async def unregister(self, client_id: str):
        """Unregister WebSocket connection"""
        if client_id in self.connections:
            del self.connections[client_id]

        # Cancel session subscriptions
        if client_id in self.client_sessions:
            session_id = self.client_sessions[client_id]
            await self.unsubscribe_session(client_id, session_id)

        logger.info(f"WebSocket client disconnected: {client_id}")

    async def subscribe_session(self, client_id: str, session_id: str):
        """Subscribe to session updates"""
        if session_id not in self.session_subscribers:
            self.session_subscribers[session_id] = set()

        self.session_subscribers[session_id].add(client_id)
        self.client_sessions[client_id] = session_id

        logger.info(f"Client {client_id} subscribed to session {session_id}")

        # Send current session status
        await self.send_session_state(client_id, session_id)

    async def unsubscribe_session(self, client_id: str, session_id: str):
        """Unsubscribe from session"""
        if session_id in self.session_subscribers:
            self.session_subscribers[session_id].discard(client_id)
            if not self.session_subscribers[session_id]:
                del self.session_subscribers[session_id]

        if client_id in self.client_sessions:
            del self.client_sessions[client_id]

        logger.info(f"Client {client_id} unsubscribed from session {session_id}")

    async def send_to_client(self, client_id: str, message: Dict[str, Any]):
        """Send message to specific client"""
        if client_id not in self.connections:
            return False

        try:
            websocket = self.connections[client_id]
            message_data = json.dumps(message, default=self._json_serializer)
            await websocket.send(message_data)
            return True
        except Exception as e:
            logger.error(f"Failed to send message to client {client_id}: {e}")
            await self.unregister(client_id)
            return False

    async def broadcast_to_session(self, session_id: str, message: Dict[str, Any]):
        """Broadcast message to all clients subscribed to specific session"""
        if session_id not in self.session_subscribers:
            return

        subscribers = list(self.session_subscribers[session_id])
        message["session_id"] = session_id

        for client_id in subscribers:
            await self.send_to_client(client_id, message)

    async def send_session_state(self, client_id: str, session_id: str):
        """Send current session status"""
        try:
            session_data = await self.session_manager.get_session(session_id)
            if not session_data:
                await self.send_to_client(client_id, {
                    "type": "error",
                    "session_id": session_id,
                    "data": {"message": f"Session does not exist: {session_id}"}
                })
                return

            # Get structure data
            atoms = await self.session_manager.get_structure(session_id)
            structure_data = None
            if atoms:
                structure_data = self.ase_engine.convert_to_dict(atoms)

            # Send complete status
            await self.send_to_client(client_id, {
                "type": "session_state",
                "session_id": session_id,
                "data": {
                    "session": session_data,
                    "structure": structure_data,
                    "timestamp": datetime.now().isoformat()
                }
            })

        except Exception as e:
            logger.error(f"Failed to send session status: {e}")
            await self.send_to_client(client_id, {
                "type": "error",
                "session_id": session_id,
                "data": {"message": f"Failed to get session status: {str(e)}"}
            })

    async def notify_structure_update(self, session_id: str, atoms, operation_info: Dict[str, Any]):
        """Notify structure update"""
        try:
            structure_data = self.ase_engine.convert_to_dict(atoms)
            structure_info = self.ase_engine.get_structure_info(atoms)

            message = {
                "type": "structure_update",
                "data": {
                    "structure": structure_data,
                    "structure_info": structure_info,
                    "operation": operation_info,
                    "timestamp": datetime.now().isoformat()
                }
            }

            await self.broadcast_to_session(session_id, message)

        except Exception as e:
            logger.error(f"Failed to notify structure update: {e}")

    async def notify_property_update(self, session_id: str, properties: Dict[str, Any]):
        """Notify property update"""
        try:
            message = {
                "type": "property_update",
                "data": {
                    "properties": properties,
                    "timestamp": datetime.now().isoformat()
                }
            }

            await self.broadcast_to_session(session_id, message)

        except Exception as e:
            logger.error(f"Failed to notify property update: {e}")

    async def handle_message(self, client_id: str, message: str):
        """Handle client messages"""
        try:
            data = json.loads(message)
            message_type = data.get("type")
            session_id = data.get("session_id")

            if message_type == "subscribe":
                if session_id:
                    await self.subscribe_session(client_id, session_id)
                else:
                    await self.send_to_client(client_id, {
                        "type": "error",
                        "data": {"message": "Missing session_id parameter"}
                    })

            elif message_type == "unsubscribe":
                if session_id:
                    await self.unsubscribe_session(client_id, session_id)

            elif message_type == "get_sessions":
                await self.handle_get_sessions(client_id, data)

            elif message_type == "ping":
                await self.send_to_client(client_id, {
                    "type": "pong",
                    "data": {"timestamp": datetime.now().isoformat()}
                })

            else:
                await self.send_to_client(client_id, {
                    "type": "error",
                    "data": {"message": f"Unknown message type: {message_type}"}
                })

        except json.JSONDecodeError:
            await self.send_to_client(client_id, {
                "type": "error",
                "data": {"message": "Invalid JSON format"}
            })
        except Exception as e:
            logger.error(f"Failed to handle client message: {e}")
            await self.send_to_client(client_id, {
                "type": "error",
                "data": {"message": f"Failed to process message: {str(e)}"}
            })

    async def handle_get_sessions(self, client_id: str, data: Dict[str, Any]):
        """Handle get session list request"""
        try:
            limit = data.get("limit", 20)
            offset = data.get("offset", 0)
            status_filter = data.get("status_filter")

            sessions = await self.session_manager.list_sessions(
                limit=limit, offset=offset, status_filter=status_filter
            )

            await self.send_to_client(client_id, {
                "type": "sessions_list",
                "data": {
                    "sessions": sessions,
                    "pagination": {
                        "limit": limit,
                        "offset": offset,
                        "total": len(sessions)
                    }
                }
            })

        except Exception as e:
            logger.error(f"Failed to get session list: {e}")
            await self.send_to_client(client_id, {
                "type": "error",
                "data": {"message": f"Failed to get session list: {str(e)}"}
            })

    def _json_serializer(self, obj):
        """JSON serializer"""
        if hasattr(obj, 'isoformat'):
            return obj.isoformat()
        elif hasattr(obj, 'tolist'):
            return obj.tolist()
        raise TypeError(f"Object of type {type(obj)} is not JSON serializable")


class WebSocketServer:
    """WebSocket server"""

    def __init__(self, session_manager: SessionManager, host: str = "localhost", port: int = 8001):
        self.host = host
        self.port = port
        self.manager = WebSocketManager(session_manager)
        self.server = None
        self.running = False

    async def handle_client(self, websocket: WebSocketServerProtocol, path: str = None):
        """Handle client connection"""
        client_id = None
        try:
            # Register client
            client_id = await self.manager.register(websocket)

            # Listen for messages
            async for message in websocket:
                await self.manager.handle_message(client_id, message)

        except websockets.exceptions.ConnectionClosed:
            logger.info(f"Client connection closed: {client_id}")
        except Exception as e:
            logger.error(f"WebSocket connection error: {e}")
        finally:
            if client_id:
                await self.manager.unregister(client_id)

    async def start(self):
        """Start WebSocket server"""
        if self.running:
            logger.info(f"WebSocket server already running: {self.host}:{self.port}")
            return

        logger.info(f"Starting WebSocket server: {self.host}:{self.port}")

        self.server = await websockets.serve(
            self.handle_client,
            self.host,
            self.port,
            ping_interval=30,
            ping_timeout=10
        )

        self.running = True
        logger.info(f"WebSocket server running on ws://{self.host}:{self.port}")

    async def stop(self):
        """Stop WebSocket server"""
        if self.server:
            self.server.close()
            await self.server.wait_closed()
            self.running = False
            logger.info("WebSocket server stopped")

    def get_manager(self) -> WebSocketManager:
        """Get WebSocket manager"""
        return self.manager


# WebSocket notification decorator
def websocket_notify(websocket_manager: WebSocketManager):
    """WebSocket notification decorator for automatically sending notifications after session operations"""

    def decorator(func):
        async def wrapper(*args, **kwargs):
            result = await func(*args, **kwargs)

            # Check if this is a session operation
            if len(args) >= 2 and isinstance(args[1], str):  # Assume second parameter is session_id
                session_id = args[1]

                try:
                    # Get current structure and notify
                    session_manager = args[0]  # Assume first parameter is session_manager
                    atoms = await session_manager.get_structure(session_id)

                    if atoms:
                        operation_info = {
                            "function": func.__name__,
                            "timestamp": datetime.now().isoformat()
                        }
                        await websocket_manager.notify_structure_update(
                            session_id, atoms, operation_info
                        )
                except Exception as e:
                    logger.error(f"WebSocket notification failed: {e}")

            return result
        return wrapper
    return decorator
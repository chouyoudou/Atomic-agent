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
    """WebSocket连接管理器"""

    def __init__(self, session_manager: SessionManager):
        self.session_manager = session_manager
        self.ase_engine = ASEEngine()
        self.connections: Dict[str, WebSocketServerProtocol] = {}
        self.session_subscribers: Dict[str, Set[str]] = {}  # session_id -> {client_ids}
        self.client_sessions: Dict[str, str] = {}  # client_id -> session_id

    async def register(self, websocket: WebSocketServerProtocol, client_id: str = None) -> str:
        """注册新的WebSocket连接"""
        if not client_id:
            client_id = str(uuid.uuid4())

        self.connections[client_id] = websocket
        logger.info(f"WebSocket客户端连接: {client_id}")

        # 发送连接确认
        await self.send_to_client(client_id, {
            "type": "connection_established",
            "client_id": client_id,
            "data": {"message": "WebSocket连接成功"}
        })

        return client_id

    async def unregister(self, client_id: str):
        """注销WebSocket连接"""
        if client_id in self.connections:
            del self.connections[client_id]

        # 取消会话订阅
        if client_id in self.client_sessions:
            session_id = self.client_sessions[client_id]
            await self.unsubscribe_session(client_id, session_id)

        logger.info(f"WebSocket客户端断开: {client_id}")

    async def subscribe_session(self, client_id: str, session_id: str):
        """订阅会话更新"""
        if session_id not in self.session_subscribers:
            self.session_subscribers[session_id] = set()

        self.session_subscribers[session_id].add(client_id)
        self.client_sessions[client_id] = session_id

        logger.info(f"客户端 {client_id} 订阅会话 {session_id}")

        # 发送当前会话状态
        await self.send_session_state(client_id, session_id)

    async def unsubscribe_session(self, client_id: str, session_id: str):
        """取消订阅会话"""
        if session_id in self.session_subscribers:
            self.session_subscribers[session_id].discard(client_id)
            if not self.session_subscribers[session_id]:
                del self.session_subscribers[session_id]

        if client_id in self.client_sessions:
            del self.client_sessions[client_id]

        logger.info(f"客户端 {client_id} 取消订阅会话 {session_id}")

    async def send_to_client(self, client_id: str, message: Dict[str, Any]):
        """发送消息给特定客户端"""
        if client_id not in self.connections:
            return False

        try:
            websocket = self.connections[client_id]
            message_data = json.dumps(message, default=self._json_serializer)
            await websocket.send(message_data)
            return True
        except Exception as e:
            logger.error(f"发送消息给客户端 {client_id} 失败: {e}")
            await self.unregister(client_id)
            return False

    async def broadcast_to_session(self, session_id: str, message: Dict[str, Any]):
        """向订阅特定会话的所有客户端广播消息"""
        if session_id not in self.session_subscribers:
            return

        subscribers = list(self.session_subscribers[session_id])
        message["session_id"] = session_id

        for client_id in subscribers:
            await self.send_to_client(client_id, message)

    async def send_session_state(self, client_id: str, session_id: str):
        """发送会话当前状态"""
        try:
            session_data = await self.session_manager.get_session(session_id)
            if not session_data:
                await self.send_to_client(client_id, {
                    "type": "error",
                    "session_id": session_id,
                    "data": {"message": f"会话不存在: {session_id}"}
                })
                return

            # 获取结构数据
            atoms = await self.session_manager.get_structure(session_id)
            structure_data = None
            if atoms:
                structure_data = self.ase_engine.convert_to_dict(atoms)

            # 发送完整状态
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
            logger.error(f"发送会话状态失败: {e}")
            await self.send_to_client(client_id, {
                "type": "error",
                "session_id": session_id,
                "data": {"message": f"获取会话状态失败: {str(e)}"}
            })

    async def notify_structure_update(self, session_id: str, atoms, operation_info: Dict[str, Any]):
        """通知结构更新"""
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
            logger.error(f"通知结构更新失败: {e}")

    async def notify_property_update(self, session_id: str, properties: Dict[str, Any]):
        """通知属性更新"""
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
            logger.error(f"通知属性更新失败: {e}")

    async def handle_message(self, client_id: str, message: str):
        """处理客户端消息"""
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
                        "data": {"message": "缺少session_id参数"}
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
                    "data": {"message": f"未知的消息类型: {message_type}"}
                })

        except json.JSONDecodeError:
            await self.send_to_client(client_id, {
                "type": "error",
                "data": {"message": "无效的JSON格式"}
            })
        except Exception as e:
            logger.error(f"处理客户端消息失败: {e}")
            await self.send_to_client(client_id, {
                "type": "error",
                "data": {"message": f"处理消息失败: {str(e)}"}
            })

    async def handle_get_sessions(self, client_id: str, data: Dict[str, Any]):
        """处理获取会话列表请求"""
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
            logger.error(f"获取会话列表失败: {e}")
            await self.send_to_client(client_id, {
                "type": "error",
                "data": {"message": f"获取会话列表失败: {str(e)}"}
            })

    def _json_serializer(self, obj):
        """JSON序列化器"""
        if hasattr(obj, 'isoformat'):
            return obj.isoformat()
        elif hasattr(obj, 'tolist'):
            return obj.tolist()
        raise TypeError(f"Object of type {type(obj)} is not JSON serializable")


class WebSocketServer:
    """WebSocket服务器"""

    def __init__(self, session_manager: SessionManager, host: str = "localhost", port: int = 8001):
        self.host = host
        self.port = port
        self.manager = WebSocketManager(session_manager)
        self.server = None
        self.running = False

    async def handle_client(self, websocket: WebSocketServerProtocol, path: str = None):
        """处理客户端连接"""
        client_id = None
        try:
            # 注册客户端
            client_id = await self.manager.register(websocket)

            # 监听消息
            async for message in websocket:
                await self.manager.handle_message(client_id, message)

        except websockets.exceptions.ConnectionClosed:
            logger.info(f"客户端连接关闭: {client_id}")
        except Exception as e:
            logger.error(f"WebSocket连接错误: {e}")
        finally:
            if client_id:
                await self.manager.unregister(client_id)

    async def start(self):
        """启动WebSocket服务器"""
        if self.running:
            logger.info(f"WebSocket服务器已在运行: {self.host}:{self.port}")
            return

        logger.info(f"启动WebSocket服务器: {self.host}:{self.port}")

        self.server = await websockets.serve(
            self.handle_client,
            self.host,
            self.port,
            ping_interval=30,
            ping_timeout=10
        )

        self.running = True
        logger.info(f"WebSocket服务器运行在 ws://{self.host}:{self.port}")

    async def stop(self):
        """停止WebSocket服务器"""
        if self.server:
            self.server.close()
            await self.server.wait_closed()
            self.running = False
            logger.info("WebSocket服务器已停止")

    def get_manager(self) -> WebSocketManager:
        """获取WebSocket管理器"""
        return self.manager


# WebSocket通知装饰器
def websocket_notify(websocket_manager: WebSocketManager):
    """WebSocket通知装饰器，用于在会话操作后自动发送通知"""

    def decorator(func):
        async def wrapper(*args, **kwargs):
            result = await func(*args, **kwargs)

            # 检查是否是会话操作
            if len(args) >= 2 and isinstance(args[1], str):  # 假设第二个参数是session_id
                session_id = args[1]

                try:
                    # 获取当前结构并通知
                    session_manager = args[0]  # 假设第一个参数是session_manager
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
                    logger.error(f"WebSocket通知失败: {e}")

            return result
        return wrapper
    return decorator
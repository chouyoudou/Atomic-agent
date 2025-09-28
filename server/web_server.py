#!/usr/bin/env python3
"""
ASE MCP Web服务器
提供WebSocket实时通信和可选的REST API
"""

import asyncio
import logging
from typing import Optional
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import uvicorn
import os

from core.session_manager import SessionManager
from handlers.websocket_handler import WebSocketServer, WebSocketManager
from models.structure import (
    CreateStructureRequest,
    StructureResponse,
    ErrorResponse
)
from models.session import SessionSummary

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ASEWebServer:
    """ASE Web服务器类"""

    def __init__(
        self,
        redis_url: str = "redis://localhost:6379",
        host: str = "0.0.0.0",
        port: int = 8000,
        websocket_port: int = 8001,
        session_manager: Optional[SessionManager] = None,
        websocket_server: Optional[WebSocketServer] = None,
        serve_static: bool = True,
        allowed_origins: list = None
    ):
        self.redis_url = redis_url
        self.host = host
        self.port = port
        self.websocket_port = websocket_port
        self.serve_static = serve_static
        self.allowed_origins = allowed_origins or ["*"]

        # 使用传入的实例或创建新的
        self.session_manager = session_manager or SessionManager(redis_url)
        self.websocket_server = websocket_server or WebSocketServer(
            self.session_manager, host, websocket_port
        )
        self.app = self.create_app()

    def create_app(self) -> FastAPI:
        """创建FastAPI应用"""

        @asynccontextmanager
        async def lifespan(app: FastAPI):
            # 启动时初始化
            # 如果session_manager未初始化，则初始化
            if not hasattr(self.session_manager, 'redis') or self.session_manager.redis is None:
                await self.session_manager.initialize()

            # 如果WebSocket服务器还未启动，则启动
            if not self.websocket_server.running:
                await self.websocket_server.start()

            logger.info("ASE Web服务器启动完成")

            yield

            # 关闭时清理（只在standalone模式下）
            if not hasattr(self, '_external_services'):
                await self.websocket_server.stop()
                await self.session_manager.close()
            logger.info("ASE Web服务器关闭完成")

        app = FastAPI(
            title="ASE MCP Web Server",
            description="原子模拟环境MCP服务器的Web接口",
            version="0.1.0",
            lifespan=lifespan
        )

        # CORS配置 - 支持前后端分离
        app.add_middleware(
            CORSMiddleware,
            allow_origins=self.allowed_origins,  # 可配置的前端域名
            allow_credentials=True,
            allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            allow_headers=["*"],
        )

        self.setup_routes(app)

        # 可选的静态文件服务 (仅在serve_static=True时启用)
        if self.serve_static:
            static_path = os.path.join(os.path.dirname(__file__), "../client/build")
            if os.path.exists(static_path):
                app.mount("/", StaticFiles(directory=static_path, html=True), name="frontend")
                logger.info(f"静态文件服务已启用: {static_path}")
            else:
                logger.warning(f"静态文件目录不存在: {static_path}")
        else:
            logger.info("静态文件服务已禁用 - 运行在纯API模式")

        return app

    def setup_routes(self, app: FastAPI):
        """设置API路由"""

        @app.get("/api")
        async def root():
            return {"message": "ASE MCP Web服务器运行中"}

        @app.get("/debug")
        async def debug_page():
            from fastapi.responses import HTMLResponse
            import os
            debug_path = os.path.join(os.path.dirname(__file__), "../../debug.html")
            if os.path.exists(debug_path):
                with open(debug_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                return HTMLResponse(content=content)
            else:
                return {"error": "Debug page not found"}

        @app.get("/health")
        async def health_check():
            """健康检查"""
            try:
                # 检查Redis连接
                await self.session_manager.redis.ping()
                return {"status": "healthy", "redis": "connected"}
            except Exception as e:
                return {"status": "unhealthy", "error": str(e)}

        @app.get("/api/sessions", response_model=dict)
        async def list_sessions(
            limit: int = 20,
            offset: int = 0,
            status_filter: Optional[str] = None
        ):
            """获取会话列表"""
            try:
                sessions = await self.session_manager.list_sessions(
                    limit=limit, offset=offset, status_filter=status_filter
                )

                return {
                    "success": True,
                    "sessions": sessions,
                    "pagination": {
                        "limit": limit,
                        "offset": offset,
                        "total": len(sessions)
                    }
                }
            except Exception as e:
                logger.error(f"获取会话列表失败: {e}")
                raise HTTPException(status_code=500, detail=str(e))

        @app.get("/api/sessions/{session_id}")
        async def get_session(session_id: str):
            """获取特定会话信息"""
            try:
                session_data = await self.session_manager.get_session(session_id)
                if not session_data:
                    raise HTTPException(status_code=404, detail="会话不存在")

                # 获取结构数据
                atoms = await self.session_manager.get_structure(session_id)
                structure_data = None
                if atoms:
                    structure_data = self.session_manager.ase_engine.convert_to_dict(atoms)

                return {
                    "success": True,
                    "session": session_data,
                    "structure": structure_data
                }
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"获取会话信息失败: {e}")
                raise HTTPException(status_code=500, detail=str(e))

        @app.delete("/api/sessions/{session_id}")
        async def delete_session(session_id: str):
            """删除会话"""
            try:
                success = await self.session_manager.delete_session(session_id)
                if not success:
                    raise HTTPException(status_code=404, detail="会话不存在")

                # 通知WebSocket客户端
                await self.websocket_server.get_manager().broadcast_to_session(
                    session_id,
                    {
                        "type": "session_deleted",
                        "data": {"message": "会话已被删除"}
                    }
                )

                return {"success": True, "message": "会话已删除"}
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"删除会话失败: {e}")
                raise HTTPException(status_code=500, detail=str(e))

        @app.websocket("/ws/{client_id}")
        async def websocket_endpoint(websocket: WebSocket, client_id: str):
            """WebSocket端点(备用方案，主要WebSocket服务在独立端口)"""
            await websocket.accept()
            manager = self.websocket_server.get_manager()

            try:
                # 注册连接
                await manager.register(websocket, client_id)

                while True:
                    # 接收消息
                    data = await websocket.receive_text()
                    await manager.handle_message(client_id, data)

            except WebSocketDisconnect:
                await manager.unregister(client_id)
            except Exception as e:
                logger.error(f"WebSocket错误: {e}")
                await manager.unregister(client_id)

        @app.post("/api/structures")
        async def create_structure(request: CreateStructureRequest):
            """直接通过Web API创建结构"""
            try:
                # 使用session_manager的ASE引擎创建结构
                ase_engine = self.session_manager.ase_engine

                if request.type == "bulk":
                    # 为bulk结构添加默认晶格常数
                    if not hasattr(request, 'lattice_constant') or request.lattice_constant is None:
                        # 根据材料设置默认晶格常数
                        default_lattice = {
                            "Cu": 3.61, "Al": 4.05, "Fe": 2.87,
                            "Ni": 3.52, "Au": 4.08, "Ag": 4.09
                        }
                        lattice_constant = default_lattice.get(request.formula, 4.0)
                    else:
                        lattice_constant = request.lattice_constant

                    atoms = ase_engine.create_bulk_structure(
                        formula=request.formula,
                        crystal_structure=request.crystal_structure,
                        size=request.size,
                        lattice_constant=lattice_constant
                    )
                elif request.type == "molecule":
                    atoms = ase_engine.create_molecule_structure(request.formula)
                elif request.type == "surface":
                    atoms = ase_engine.create_surface(
                        formula=request.formula,
                        indices=getattr(request, 'indices', [1,1,1]),
                        layers=getattr(request, 'layers', 4),
                        size=getattr(request, 'size', [2,2])
                    )
                else:
                    raise HTTPException(status_code=400, detail=f"不支持的结构类型: {request.type}")

                # 创建新会话
                session_id = await self.session_manager.create_session(
                    metadata={
                        "type": request.type,
                        "formula": request.formula,
                        "description": f"{request.type}结构: {request.formula}"
                    }
                )

                # 保存结构到会话
                await self.session_manager.set_structure(session_id, atoms)

                # 获取结构信息
                structure_info = ase_engine.get_structure_info(atoms)
                structure_data = ase_engine.convert_to_dict(atoms)

                # 通知WebSocket客户端
                await self.websocket_server.get_manager().notify_structure_update(
                    session_id, atoms, {
                        "operation": "create_structure",
                        "type": request.type,
                        "formula": request.formula,
                        "source": "web_api"
                    }
                )

                return {
                    "success": True,
                    "session_id": session_id,
                    "structure_info": structure_info,
                    "structure_data": structure_data,
                    "message": f"成功创建{request.type}结构"
                }

            except Exception as e:
                logger.error(f"Web API创建结构失败: {e}")
                raise HTTPException(status_code=500, detail=f"创建结构失败: {str(e)}")

        @app.post("/api/structures/{session_id}/modify")
        async def modify_structure(session_id: str, request: dict):
            """修改现有结构"""
            try:
                # 获取当前结构
                atoms = await self.session_manager.get_structure(session_id)
                if not atoms:
                    raise HTTPException(status_code=404, detail="会话或结构不存在")

                # 执行修改操作
                operation = request.get("operation")
                parameters = request.get("parameters", {})

                ase_engine = self.session_manager.ase_engine

                if operation == "rotate":
                    modified_atoms = ase_engine.modify_structure(
                        atoms,
                        operation="rotate",
                        parameters={
                            "angle": parameters.get("angle", 90),
                            "axis": parameters.get("axis", [0, 0, 1])
                        }
                    )
                elif operation == "translate":
                    modified_atoms = ase_engine.modify_structure(
                        atoms,
                        operation="translate",
                        parameters={
                            "vector": parameters.get("vector", [1, 0, 0])
                        }
                    )
                elif operation == "scale":
                    modified_atoms = ase_engine.modify_structure(
                        atoms,
                        operation="scale",
                        parameters={
                            "factor": parameters.get("factor", 1.1)
                        }
                    )
                else:
                    raise HTTPException(status_code=400, detail=f"不支持的操作: {operation}")

                # 保存修改后的结构
                await self.session_manager.set_structure(session_id, modified_atoms)

                # 获取结构信息
                structure_info = ase_engine.get_structure_info(modified_atoms)
                structure_data = ase_engine.convert_to_dict(modified_atoms)

                # 通知WebSocket客户端
                await self.websocket_server.get_manager().notify_structure_update(
                    session_id, modified_atoms, {
                        "operation": operation,
                        "parameters": parameters,
                        "source": "web_api"
                    }
                )

                return {
                    "success": True,
                    "structure_info": structure_info,
                    "structure_data": structure_data,
                    "message": f"成功执行{operation}操作"
                }

            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Web API修改结构失败: {e}")
                raise HTTPException(status_code=500, detail=f"修改结构失败: {str(e)}")

        @app.get("/api/websocket/info")
        async def websocket_info():
            """获取WebSocket连接信息"""
            return {
                "websocket_url": f"ws://{self.host}:{self.websocket_port}",
                "active_connections": len(self.websocket_server.get_manager().connections),
                "active_sessions": len(self.websocket_server.get_manager().session_subscribers)
            }

    async def run(self):
        """运行Web服务器"""
        config = uvicorn.Config(
            app=self.app,
            host=self.host,
            port=self.port,
            log_level="info",
            access_log=True
        )

        server = uvicorn.Server(config)
        await server.serve()


def main():
    """主函数"""
    import sys
    import os

    # 从环境变量获取配置
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    websocket_port = int(os.getenv("WEBSOCKET_PORT", "8001"))

    # 创建并运行服务器
    server = ASEWebServer(
        redis_url=redis_url,
        host=host,
        port=port,
        websocket_port=websocket_port
    )

    try:
        asyncio.run(server.run())
    except KeyboardInterrupt:
        logger.info("Web服务器停止")
    except Exception as e:
        logger.error(f"Web服务器运行错误: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
#!/usr/bin/env python3
"""
ASE MCP Web Server
Provides WebSocket real-time communication and optional REST API
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
from api.structure_validation import router as validation_router

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ASEWebServer:
    """ASE Web Server class"""

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

        # Use provided instances or create new ones
        self.session_manager = session_manager or SessionManager(redis_url)
        self.websocket_server = websocket_server or WebSocketServer(
            self.session_manager, host, websocket_port
        )
        self.app = self.create_app()

    def create_app(self) -> FastAPI:
        """Create FastAPI application"""

        @asynccontextmanager
        async def lifespan(app: FastAPI):
            # Initialize on startup
            # If session_manager is not initialized, initialize it
            if not hasattr(self.session_manager, 'redis') or self.session_manager.redis is None:
                await self.session_manager.initialize()

            # If WebSocket server is not started yet, start it
            if not self.websocket_server.running:
                await self.websocket_server.start()

            logger.info("ASE Web server started successfully")

            yield

            # Cleanup on shutdown (only in standalone mode)
            if not hasattr(self, '_external_services'):
                await self.websocket_server.stop()
                await self.session_manager.close()
            logger.info("ASE Web server closed successfully")

        app = FastAPI(
            title="ASE MCP Web Server",
            description="Web interface for the Atomic Simulation Environment MCP Server",
            version="0.1.0",
            lifespan=lifespan
        )

        # CORS configuration - supports frontend-backend separation
        app.add_middleware(
            CORSMiddleware,
            allow_origins=self.allowed_origins,  # Configurable frontend domains
            allow_credentials=True,
            allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            allow_headers=["*"],
        )

        self.setup_routes(app)
        app.include_router(validation_router)

        # Optional static file serving (only enabled when serve_static=True)
        if self.serve_static:
            static_path = os.path.join(os.path.dirname(__file__), "../client/build")
            if os.path.exists(static_path):
                app.mount("/", StaticFiles(directory=static_path, html=True), name="frontend")
                logger.info(f"Static file serving enabled: {static_path}")
            else:
                logger.warning(f"Static file directory does not exist: {static_path}")
        else:
            logger.info("Static file serving disabled - running in pure API mode")

        return app

    def setup_routes(self, app: FastAPI):
        """Setup API routes"""

        @app.get("/api")
        async def root():
            return {"message": "ASE MCP Web server running"}

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
            """Health check"""
            try:
                # Check Redis connection
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
            """Get session list"""
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
                logger.error(f"Failed to get session list: {e}")
                raise HTTPException(status_code=500, detail=str(e))

        @app.get("/api/sessions/{session_id}")
        async def get_session(session_id: str):
            """Get specific session information"""
            try:
                session_data = await self.session_manager.get_session(session_id)
                if not session_data:
                    raise HTTPException(status_code=404, detail="Session does not exist")

                # Get structure data
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
                logger.error(f"Failed to get session information: {e}")
                raise HTTPException(status_code=500, detail=str(e))

        @app.delete("/api/sessions/{session_id}")
        async def delete_session(session_id: str):
            """Delete session"""
            try:
                success = await self.session_manager.delete_session(session_id)
                if not success:
                    raise HTTPException(status_code=404, detail="Session does not exist")

                # Notify WebSocket clients
                await self.websocket_server.get_manager().broadcast_to_session(
                    session_id,
                    {
                        "type": "session_deleted",
                        "data": {"message": "Session has been deleted"}
                    }
                )

                return {"success": True, "message": "Session deleted"}
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Failed to delete session: {e}")
                raise HTTPException(status_code=500, detail=str(e))

        @app.websocket("/ws/{client_id}")
        async def websocket_endpoint(websocket: WebSocket, client_id: str):
            """WebSocket endpoint (backup solution, main WebSocket service on separate port)"""
            await websocket.accept()
            manager = self.websocket_server.get_manager()

            try:
                # Register connection
                await manager.register(websocket, client_id)

                while True:
                    # Receive messages
                    data = await websocket.receive_text()
                    await manager.handle_message(client_id, data)

            except WebSocketDisconnect:
                await manager.unregister(client_id)
            except Exception as e:
                logger.error(f"WebSocket error: {e}")
                await manager.unregister(client_id)

        @app.post("/api/structures")
        async def create_structure(request: CreateStructureRequest):
            """Create structure directly via Web API"""
            try:
                # Use session_manager's ASE engine to create structure
                ase_engine = self.session_manager.ase_engine

                if request.type == "bulk":
                    # Add default lattice constant for bulk structure
                    if not hasattr(request, 'lattice_constant') or request.lattice_constant is None:
                        # Set default lattice constant based on material
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
                    raise HTTPException(status_code=400, detail=f"Unsupported structure type: {request.type}")

                # Create new session
                session_id = await self.session_manager.create_session(
                    metadata={
                        "type": request.type,
                        "formula": request.formula,
                        "description": f"{request.type} structure: {request.formula}"
                    }
                )

                # Save structure to session
                await self.session_manager.set_structure(session_id, atoms)

                # Get structure information
                structure_info = ase_engine.get_structure_info(atoms)
                structure_data = ase_engine.convert_to_dict(atoms)

                # Notify WebSocket clients
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
                    "message": f"Successfully created {request.type} structure"
                }

            except Exception as e:
                logger.error(f"Web API structure creation failed: {e}")
                raise HTTPException(status_code=500, detail=f"Structure creation failed: {str(e)}")

        @app.post("/api/structures/{session_id}/modify")
        async def modify_structure(session_id: str, request: dict):
            """Modify existing structure"""
            try:
                # Get current structure
                atoms = await self.session_manager.get_structure(session_id)
                if not atoms:
                    raise HTTPException(status_code=404, detail="Session or structure does not exist")

                # Execute modification operation
                operation = request.get("operation")
                parameters = request.get("parameters", {})

                ase_engine = self.session_manager.ase_engine

                # List of supported operations
                supported_operations = [
                    "rotate", "translate", "scale", "supercell", "remove_atoms",
                    "add_atom", "modify_cell", "modify_positions", "replace_atoms",
                    "change_species", "duplicate_atoms", "create_vacancy"
                ]

                if operation not in supported_operations:
                    raise HTTPException(status_code=400, detail=f"Unsupported operation: {operation}")

                # Execute modification operation
                modified_atoms = ase_engine.modify_structure(
                    atoms, operation, parameters
                )

                # Save modified structure
                await self.session_manager.set_structure(session_id, modified_atoms)

                # Get structure information
                structure_info = ase_engine.get_structure_info(modified_atoms)
                structure_data = ase_engine.convert_to_dict(modified_atoms)

                # Notify WebSocket clients
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
                    "message": f"Successfully executed {operation} operation"
                }

            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Web API structure modification failed: {e}")
                raise HTTPException(status_code=500, detail=f"Structure modification failed: {str(e)}")

        @app.get("/api/websocket/info")
        async def websocket_info():
            """Get WebSocket connection information"""
            return {
                "websocket_url": f"ws://{self.host}:{self.websocket_port}",
                "active_connections": len(self.websocket_server.get_manager().connections),
                "active_sessions": len(self.websocket_server.get_manager().session_subscribers)
            }

    async def run(self):
        """Run Web server"""
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
    """Main function"""
    import sys
    import os

    # Get configuration from environment variables
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    websocket_port = int(os.getenv("WEBSOCKET_PORT", "8001"))

    # Create and run server
    server = ASEWebServer(
        redis_url=redis_url,
        host=host,
        port=port,
        websocket_port=websocket_port
    )

    try:
        asyncio.run(server.run())
    except KeyboardInterrupt:
        logger.info("Web server stopped")
    except Exception as e:
        logger.error(f"Web server runtime error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
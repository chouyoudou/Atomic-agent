"""
MCP工具处理器
将MCP工具调用与WebSocket通知集成
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from core.session_manager import SessionManager
from core.ase_engine import ASEEngine
from core.structure_ops import StructureOperations
from handlers.websocket_handler import WebSocketManager
from models.structure import (
    CreateStructureRequest,
    ModifyStructureRequest,
    CalculatePropertiesRequest,
    OptimizeStructureRequest,
    SaveStructureRequest,
    PreviewStructureRequest,
    StructureResponse,
    ErrorResponse
)

logger = logging.getLogger(__name__)


class MCPHandlers:
    """MCP工具处理器类，集成WebSocket通知"""

    def __init__(
        self,
        session_manager: SessionManager,
        websocket_manager: Optional[WebSocketManager] = None
    ):
        self.session_manager = session_manager
        self.websocket_manager = websocket_manager
        self.ase_engine = ASEEngine()
        self.structure_ops = StructureOperations()

    async def handle_create_structure(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """处理创建结构请求"""
        try:
            req = CreateStructureRequest(**arguments)
            logger.info(f"创建结构: {req.type} - {req.formula}")

            # 获取或创建会话
            session_id = req.session_id
            if not session_id:
                session_id = await self.session_manager.create_session()
            elif not await self.session_manager.session_exists(session_id):
                session_id = await self.session_manager.create_session(session_id)

            # 创建结构
            atoms = await self._create_structure_by_type(req)

            # 保存到会话
            operation_info = {
                "type": "create_structure",
                "parameters": arguments,
                "timestamp": datetime.now().isoformat()
            }

            success = await self.session_manager.set_structure(
                session_id, atoms, operation_info
            )

            if success:
                structure_data = self.ase_engine.convert_to_dict(atoms)
                structure_info = self.ase_engine.get_structure_info(atoms)

                # WebSocket通知
                if self.websocket_manager:
                    await self.websocket_manager.notify_structure_update(
                        session_id, atoms, operation_info
                    )

                response = StructureResponse(
                    success=True,
                    message=f"成功创建{req.type}结构",
                    session_id=session_id,
                    structure_data=structure_data,
                    structure_info=structure_info
                )
            else:
                response = ErrorResponse(
                    error="session_error",
                    message="保存结构到会话失败"
                )

            return response.dict()

        except Exception as e:
            logger.error(f"创建结构失败: {e}")
            response = ErrorResponse(
                error="structure_creation_error",
                message=f"创建结构失败: {str(e)}"
            )
            return response.dict()

    async def handle_modify_structure(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """处理修改结构请求"""
        try:
            req = ModifyStructureRequest(**arguments)
            logger.info(f"修改结构: {req.session_id} - {req.operation}")

            # 获取当前结构
            atoms = await self.session_manager.get_structure(req.session_id)
            if not atoms:
                response = ErrorResponse(
                    error="session_not_found",
                    message=f"会话不存在或无结构数据: {req.session_id}"
                )
                return response.dict()

            # 修改结构
            modified_atoms = self.ase_engine.modify_structure(
                atoms, req.operation, req.parameters
            )

            # 保存修改
            operation_info = {
                "type": "modify_structure",
                "operation": req.operation,
                "parameters": req.parameters,
                "timestamp": datetime.now().isoformat()
            }

            success = await self.session_manager.set_structure(
                req.session_id, modified_atoms, operation_info
            )

            if success:
                structure_data = self.ase_engine.convert_to_dict(modified_atoms)
                structure_info = self.ase_engine.get_structure_info(modified_atoms)

                # WebSocket通知
                if self.websocket_manager:
                    await self.websocket_manager.notify_structure_update(
                        req.session_id, modified_atoms, operation_info
                    )

                response = StructureResponse(
                    success=True,
                    message=f"成功执行{req.operation}操作",
                    session_id=req.session_id,
                    structure_data=structure_data,
                    structure_info=structure_info
                )
            else:
                response = ErrorResponse(
                    error="session_error",
                    message="保存修改后的结构失败"
                )

            return response.dict()

        except Exception as e:
            logger.error(f"修改结构失败: {e}")
            response = ErrorResponse(
                error="structure_modification_error",
                message=f"修改结构失败: {str(e)}"
            )
            return response.dict()

    async def handle_calculate_properties(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """处理计算属性请求"""
        try:
            req = CalculatePropertiesRequest(**arguments)
            logger.info(f"计算属性: {req.session_id} - {req.properties}")

            # 获取结构
            atoms = await self.session_manager.get_structure(req.session_id)
            if not atoms:
                response = ErrorResponse(
                    error="session_not_found",
                    message=f"会话不存在或无结构数据: {req.session_id}"
                )
                return response.dict()

            # 计算属性
            properties = self.ase_engine.calculate_properties(
                atoms, req.calculator, req.properties
            )

            # 更新会话属性
            await self.session_manager.update_session(
                req.session_id, properties={"calculated": properties}
            )

            # WebSocket通知
            if self.websocket_manager:
                await self.websocket_manager.notify_property_update(
                    req.session_id, properties
                )

            response = StructureResponse(
                success=True,
                message="属性计算完成",
                session_id=req.session_id,
                properties=properties
            )

            return response.dict()

        except Exception as e:
            logger.error(f"计算属性失败: {e}")
            response = ErrorResponse(
                error="property_calculation_error",
                message=f"计算属性失败: {str(e)}"
            )
            return response.dict()

    async def handle_optimize_structure(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """处理结构优化请求"""
        try:
            req = OptimizeStructureRequest(**arguments)
            logger.info(f"优化结构: {req.session_id}")

            # 获取结构
            atoms = await self.session_manager.get_structure(req.session_id)
            if not atoms:
                response = ErrorResponse(
                    error="session_not_found",
                    message=f"会话不存在或无结构数据: {req.session_id}"
                )
                return response.dict()

            # 优化结构
            optimized_atoms, optimization_info = self.ase_engine.optimize_structure(
                atoms, req.calculator, req.fmax, req.steps
            )

            # 保存优化结果
            operation_info = {
                "type": "optimize_structure",
                "parameters": arguments,
                "optimization_info": optimization_info,
                "timestamp": datetime.now().isoformat()
            }

            success = await self.session_manager.set_structure(
                req.session_id, optimized_atoms, operation_info
            )

            if success:
                structure_data = self.ase_engine.convert_to_dict(optimized_atoms)

                # WebSocket通知
                if self.websocket_manager:
                    await self.websocket_manager.notify_structure_update(
                        req.session_id, optimized_atoms, operation_info
                    )

                response = StructureResponse(
                    success=True,
                    message="结构优化完成",
                    session_id=req.session_id,
                    structure_data=structure_data,
                    properties={"optimization": optimization_info}
                )
            else:
                response = ErrorResponse(
                    error="session_error",
                    message="保存优化结果失败"
                )

            return response.dict()

        except Exception as e:
            logger.error(f"结构优化失败: {e}")
            response = ErrorResponse(
                error="structure_optimization_error",
                message=f"结构优化失败: {str(e)}"
            )
            return response.dict()

    async def handle_undo_operation(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """处理撤销操作请求"""
        try:
            session_id = arguments["session_id"]
            logger.info(f"撤销操作: {session_id}")

            success = await self.session_manager.undo(session_id)

            if success:
                # 获取当前结构
                atoms = await self.session_manager.get_structure(session_id)
                structure_data = self.ase_engine.convert_to_dict(atoms) if atoms else None

                # WebSocket通知
                if self.websocket_manager and atoms:
                    operation_info = {
                        "type": "undo",
                        "timestamp": datetime.now().isoformat()
                    }
                    await self.websocket_manager.notify_structure_update(
                        session_id, atoms, operation_info
                    )

                response = StructureResponse(
                    success=True,
                    message="撤销操作成功",
                    session_id=session_id,
                    structure_data=structure_data
                )
            else:
                response = ErrorResponse(
                    error="undo_error",
                    message="撤销操作失败，可能没有可撤销的操作"
                )

            return response.dict()

        except Exception as e:
            logger.error(f"撤销操作失败: {e}")
            response = ErrorResponse(
                error="undo_error",
                message=f"撤销操作失败: {str(e)}"
            )
            return response.dict()

    async def handle_redo_operation(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """处理重做操作请求"""
        try:
            session_id = arguments["session_id"]
            logger.info(f"重做操作: {session_id}")

            success = await self.session_manager.redo(session_id)

            if success:
                # 获取当前结构
                atoms = await self.session_manager.get_structure(session_id)
                structure_data = self.ase_engine.convert_to_dict(atoms) if atoms else None

                # WebSocket通知
                if self.websocket_manager and atoms:
                    operation_info = {
                        "type": "redo",
                        "timestamp": datetime.now().isoformat()
                    }
                    await self.websocket_manager.notify_structure_update(
                        session_id, atoms, operation_info
                    )

                response = StructureResponse(
                    success=True,
                    message="重做操作成功",
                    session_id=session_id,
                    structure_data=structure_data
                )
            else:
                response = ErrorResponse(
                    error="redo_error",
                    message="重做操作失败，可能没有可重做的操作"
                )

            return response.dict()

        except Exception as e:
            logger.error(f"重做操作失败: {e}")
            response = ErrorResponse(
                error="redo_error",
                message=f"重做操作失败: {str(e)}"
            )
            return response.dict()

    async def _create_structure_by_type(self, req: CreateStructureRequest):
        """根据类型创建结构"""
        if req.type == "bulk":
            return self.ase_engine.create_bulk_structure(
                formula=req.formula,
                crystal_structure=req.crystal_structure or "fcc",
                lattice_constant=req.lattice_constant,
                size=tuple(req.size) if req.size else (1, 1, 1)
            )
        elif req.type == "molecule":
            return self.ase_engine.create_molecule_structure(req.formula)
        elif req.type == "surface":
            return self.ase_engine.create_surface_structure(
                symbol=req.formula,
                crystal_structure=req.crystal_structure or "fcc",
                size=tuple(req.size[:2]) if req.size else (2, 2)
            )
        elif req.type == "nanoparticle":
            return self.structure_ops.create_nanoparticle(
                element=req.formula,
                size=req.size[0] if req.size else 100
            )
        else:
            raise ValueError(f"不支持的结构类型: {req.type}")

    def set_websocket_manager(self, websocket_manager: WebSocketManager):
        """设置WebSocket管理器"""
        self.websocket_manager = websocket_manager
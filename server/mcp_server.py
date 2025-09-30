#!/usr/bin/env python3
"""
ASE MCP Server - MCP Server for Atomic Simulation Environment
Provides MCP tool interface for ASE functionality, supporting generation, modification and analysis of crystal structures
"""

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import (
    Tool,
    TextContent,
    ImageContent,
    EmbeddedResource,
    LoggingLevel
)
import os
from pathlib import Path

from core.session_manager import SessionManager
from core.ase_engine import ASEEngine
from core.structure_ops import StructureOperations
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

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ASEMCPServer:
    """ASE MCP Server class"""

    def __init__(self, redis_url: str = "redis://localhost:6379"):
        self.server = Server("ase-mcp-server")
        self.session_manager = SessionManager(redis_url)
        self.ase_engine = ASEEngine()
        self.structure_ops = StructureOperations()
        self.setup_tools()
        self.setup_handlers()

    def setup_tools(self):
        """设置MCP工具定义"""

        # 定义工具列表
        tools = [
            Tool(
                name="create_structure",
                description="创建新的原子结构(晶体、分子、表面等)",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "type": {
                            "type": "string",
                            "enum": ["bulk", "molecule", "surface", "nanoparticle"],
                            "description": "结构类型"
                        },
                        "formula": {
                            "type": "string",
                            "description": "化学式，如 'Cu', 'H2O', 'NaCl'"
                        },
                        "crystal_structure": {
                            "type": "string",
                            "enum": ["fcc", "bcc", "hcp", "diamond", "sc"],
                            "description": "晶体结构类型(仅用于bulk类型)"
                        },
                        "size": {
                            "type": "array",
                            "items": {"type": "integer"},
                            "description": "超胞大小 [nx, ny, nz]"
                        },
                        "lattice_constant": {
                            "type": "number",
                            "description": "晶格常数"
                        },
                        "session_id": {
                            "type": "string",
                            "description": "可选的会话ID，如不提供将创建新会话"
                        }
                    },
                    "required": ["type", "formula"]
                }
            ),

            Tool(
                name="modify_structure",
                description="修改现有的原子结构",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "session_id": {
                            "type": "string",
                            "description": "会话ID"
                        },
                        "operation": {
                            "type": "string",
                            "enum": ["rotate", "translate", "scale", "supercell", "remove_atoms", "add_atom"],
                            "description": "修改操作类型"
                        },
                        "parameters": {
                            "type": "object",
                            "description": "操作参数",
                            "properties": {
                                "axis": {
                                    "type": "array",
                                    "items": {"type": "number"},
                                    "description": "旋转轴(对于rotate操作)"
                                },
                                "angle": {
                                    "type": "number",
                                    "description": "旋转角度(度)"
                                },
                                "vector": {
                                    "type": "array",
                                    "items": {"type": "number"},
                                    "description": "平移向量(对于translate操作)"
                                },
                                "factor": {
                                    "type": "number",
                                    "description": "缩放因子(对于scale操作)"
                                },
                                "size": {
                                    "type": "array",
                                    "items": {"type": "integer"},
                                    "description": "超胞大小(对于supercell操作)"
                                }
                            }
                        }
                    },
                    "required": ["session_id", "operation", "parameters"]
                }
            ),

            Tool(
                name="calculate_properties",
                description="计算结构的物理化学属性",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "session_id": {
                            "type": "string",
                            "description": "会话ID"
                        },
                        "calculator": {
                            "type": "string",
                            "enum": ["emt"],
                            "default": "emt",
                            "description": "计算器类型"
                        },
                        "properties": {
                            "type": "array",
                            "items": {
                                "type": "string",
                                "enum": ["energy", "forces", "stress", "dipole"]
                            },
                            "default": ["energy"],
                            "description": "要计算的属性列表"
                        }
                    },
                    "required": ["session_id"]
                }
            ),

            Tool(
                name="optimize_structure",
                description="优化结构几何",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "session_id": {
                            "type": "string",
                            "description": "会话ID"
                        },
                        "calculator": {
                            "type": "string",
                            "enum": ["emt"],
                            "default": "emt",
                            "description": "计算器类型"
                        },
                        "fmax": {
                            "type": "number",
                            "default": 0.01,
                            "description": "收敛阈值(eV/Å)"
                        },
                        "steps": {
                            "type": "integer",
                            "default": 100,
                            "description": "最大优化步数"
                        }
                    },
                    "required": ["session_id"]
                }
            ),

            Tool(
                name="preview_structure",
                description="预览当前结构",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "session_id": {
                            "type": "string",
                            "description": "会话ID"
                        },
                        "format": {
                            "type": "string",
                            "enum": ["json", "cif", "xyz"],
                            "default": "json",
                            "description": "预览格式"
                        }
                    },
                    "required": ["session_id"]
                }
            ),

            Tool(
                name="save_structure",
                description="保存结构到文件",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "session_id": {
                            "type": "string",
                            "description": "会话ID"
                        },
                        "filename": {
                            "type": "string",
                            "description": "文件名(包含路径)"
                        },
                        "format": {
                            "type": "string",
                            "enum": ["cif", "xyz", "pdb", "json"],
                            "description": "文件格式,如不指定则从文件扩展名推断"
                        }
                    },
                    "required": ["session_id", "filename"]
                }
            ),

            Tool(
                name="list_sessions",
                description="列出所有会话",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "limit": {
                            "type": "integer",
                            "default": 20,
                            "description": "返回数量限制"
                        },
                        "offset": {
                            "type": "integer",
                            "default": 0,
                            "description": "偏移量"
                        },
                        "status_filter": {
                            "type": "string",
                            "enum": ["active", "inactive", "completed"],
                            "description": "状态过滤器"
                        }
                    }
                }
            ),

            Tool(
                name="get_session_info",
                description="获取会话详细信息",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "session_id": {
                            "type": "string",
                            "description": "会话ID"
                        }
                    },
                    "required": ["session_id"]
                }
            ),

            Tool(
                name="delete_session",
                description="删除会话",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "session_id": {
                            "type": "string",
                            "description": "会话ID"
                        }
                    },
                    "required": ["session_id"]
                }
            ),

            Tool(
                name="undo_operation",
                description="撤销上一个操作",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "session_id": {
                            "type": "string",
                            "description": "会话ID"
                        }
                    },
                    "required": ["session_id"]
                }
            ),

            Tool(
                name="redo_operation",
                description="重做下一个操作",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "session_id": {
                            "type": "string",
                            "description": "会话ID"
                        }
                    },
                    "required": ["session_id"]
                }
            ),

            Tool(
                name="get_structure_info",
                description="获取结构的详细信息",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "session_id": {
                            "type": "string",
                            "description": "会话ID"
                        }
                    },
                    "required": ["session_id"]
                }
            )
        ]

        # 注册工具到MCP服务器
        @self.server.list_tools()
        async def list_tools():
            return tools

    def setup_handlers(self):
        """设置工具处理器"""

        @self.server.call_tool()
        async def call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
            """工具调用处理器"""
            try:
                if name == "create_structure":
                    return await self.handle_create_structure(arguments)
                elif name == "modify_structure":
                    return await self.handle_modify_structure(arguments)
                elif name == "calculate_properties":
                    return await self.handle_calculate_properties(arguments)
                elif name == "optimize_structure":
                    return await self.handle_optimize_structure(arguments)
                elif name == "preview_structure":
                    return await self.handle_preview_structure(arguments)
                elif name == "save_structure":
                    return await self.handle_save_structure(arguments)
                elif name == "list_sessions":
                    return await self.handle_list_sessions(arguments)
                elif name == "get_session_info":
                    return await self.handle_get_session_info(arguments)
                elif name == "delete_session":
                    return await self.handle_delete_session(arguments)
                elif name == "undo_operation":
                    return await self.handle_undo_operation(arguments)
                elif name == "redo_operation":
                    return await self.handle_redo_operation(arguments)
                elif name == "get_structure_info":
                    return await self.handle_get_structure_info(arguments)
                else:
                    return [TextContent(
                        type="text",
                        text=json.dumps({
                            "success": False,
                            "error": "unknown_tool",
                            "message": f"未知的工具: {name}"
                        })
                    )]

            except Exception as e:
                logger.error(f"工具调用失败 {name}: {e}")
                return [TextContent(
                    type="text",
                    text=json.dumps({
                        "success": False,
                        "error": "tool_execution_error",
                        "message": f"工具执行失败: {str(e)}"
                    })
                )]

    async def handle_create_structure(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """处理创建结构请求"""
        try:
            req = CreateStructureRequest(**arguments)

            # 获取或创建会话
            session_id = req.session_id
            if not session_id:
                session_id = await self.session_manager.create_session()
            elif not await self.session_manager.session_exists(session_id):
                session_id = await self.session_manager.create_session(session_id)

            # 创建结构
            if req.type == "bulk":
                atoms = self.ase_engine.create_bulk_structure(
                    formula=req.formula,
                    crystal_structure=req.crystal_structure or "fcc",
                    lattice_constant=req.lattice_constant,
                    size=tuple(req.size) if req.size else (1, 1, 1)
                )
            elif req.type == "molecule":
                atoms = self.ase_engine.create_molecule_structure(req.formula)
            elif req.type == "surface":
                atoms = self.ase_engine.create_surface_structure(
                    symbol=req.formula,
                    crystal_structure=req.crystal_structure or "fcc",
                    size=tuple(req.size[:2]) if req.size else (2, 2)
                )
            elif req.type == "nanoparticle":
                atoms = self.structure_ops.create_nanoparticle(
                    element=req.formula,
                    size=req.size[0] if req.size else 100
                )
            else:
                raise ValueError(f"不支持的结构类型: {req.type}")

            # 保存到会话
            operation_info = {
                "type": "create_structure",
                "parameters": arguments
            }

            success = await self.session_manager.set_structure(
                session_id, atoms, operation_info
            )

            if success:
                structure_data = self.ase_engine.convert_to_dict(atoms)
                structure_info = self.ase_engine.get_structure_info(atoms)

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

            return [TextContent(type="text", text=json.dumps(response.dict()))]

        except Exception as e:
            logger.error(f"创建结构失败: {e}")
            response = ErrorResponse(
                error="structure_creation_error",
                message=f"创建结构失败: {str(e)}"
            )
            return [TextContent(type="text", text=json.dumps(response.dict()))]

    async def handle_modify_structure(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """处理修改结构请求"""
        try:
            req = ModifyStructureRequest(**arguments)

            # 获取当前结构
            atoms = await self.session_manager.get_structure(req.session_id)
            if not atoms:
                response = ErrorResponse(
                    error="session_not_found",
                    message=f"会话不存在或无结构数据: {req.session_id}"
                )
                return [TextContent(type="text", text=json.dumps(response.dict()))]

            # 修改结构
            modified_atoms = self.ase_engine.modify_structure(
                atoms, req.operation, req.parameters
            )

            # 保存修改
            operation_info = {
                "type": "modify_structure",
                "operation": req.operation,
                "parameters": req.parameters
            }

            success = await self.session_manager.set_structure(
                req.session_id, modified_atoms, operation_info
            )

            if success:
                structure_data = self.ase_engine.convert_to_dict(modified_atoms)
                structure_info = self.ase_engine.get_structure_info(modified_atoms)

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

            return [TextContent(type="text", text=json.dumps(response.dict()))]

        except Exception as e:
            logger.error(f"修改结构失败: {e}")
            response = ErrorResponse(
                error="structure_modification_error",
                message=f"修改结构失败: {str(e)}"
            )
            return [TextContent(type="text", text=json.dumps(response.dict()))]

    async def handle_calculate_properties(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """处理计算属性请求"""
        try:
            req = CalculatePropertiesRequest(**arguments)

            # 获取结构
            atoms = await self.session_manager.get_structure(req.session_id)
            if not atoms:
                response = ErrorResponse(
                    error="session_not_found",
                    message=f"会话不存在或无结构数据: {req.session_id}"
                )
                return [TextContent(type="text", text=json.dumps(response.dict()))]

            # 计算属性
            properties = self.ase_engine.calculate_properties(
                atoms, req.calculator, req.properties
            )

            # 更新会话属性
            await self.session_manager.update_session(
                req.session_id, properties={"calculated": properties}
            )

            response = StructureResponse(
                success=True,
                message="属性计算完成",
                session_id=req.session_id,
                properties=properties
            )

            return [TextContent(type="text", text=json.dumps(response.dict()))]

        except Exception as e:
            logger.error(f"计算属性失败: {e}")
            response = ErrorResponse(
                error="property_calculation_error",
                message=f"计算属性失败: {str(e)}"
            )
            return [TextContent(type="text", text=json.dumps(response.dict()))]

    async def handle_optimize_structure(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """处理结构优化请求"""
        try:
            req = OptimizeStructureRequest(**arguments)

            # 获取结构
            atoms = await self.session_manager.get_structure(req.session_id)
            if not atoms:
                response = ErrorResponse(
                    error="session_not_found",
                    message=f"会话不存在或无结构数据: {req.session_id}"
                )
                return [TextContent(type="text", text=json.dumps(response.dict()))]

            # 优化结构
            optimized_atoms, optimization_info = self.ase_engine.optimize_structure(
                atoms, req.calculator, req.fmax, req.steps
            )

            # 保存优化结果
            operation_info = {
                "type": "optimize_structure",
                "parameters": arguments,
                "optimization_info": optimization_info
            }

            success = await self.session_manager.set_structure(
                req.session_id, optimized_atoms, operation_info
            )

            if success:
                structure_data = self.ase_engine.convert_to_dict(optimized_atoms)

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

            return [TextContent(type="text", text=json.dumps(response.dict()))]

        except Exception as e:
            logger.error(f"结构优化失败: {e}")
            response = ErrorResponse(
                error="structure_optimization_error",
                message=f"结构优化失败: {str(e)}"
            )
            return [TextContent(type="text", text=json.dumps(response.dict()))]

    async def handle_preview_structure(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """处理预览结构请求"""
        try:
            req = PreviewStructureRequest(**arguments)

            # 获取结构
            atoms = await self.session_manager.get_structure(req.session_id)
            if not atoms:
                response = ErrorResponse(
                    error="session_not_found",
                    message=f"会话不存在或无结构数据: {req.session_id}"
                )
                return [TextContent(type="text", text=json.dumps(response.dict()))]

            # 根据格式生成预览
            if req.format == "json":
                structure_data = self.ase_engine.convert_to_dict(atoms)
                structure_info = self.ase_engine.get_structure_info(atoms)
                preview_data = {
                    "structure_data": structure_data,
                    "structure_info": structure_info
                }
            else:
                # 保存为临时文件并读取内容
                import tempfile
                with tempfile.NamedTemporaryFile(suffix=f".{req.format}", delete=False) as tmp:
                    self.ase_engine.save_structure(atoms, tmp.name, req.format)
                    with open(tmp.name, 'r') as f:
                        preview_data = {"content": f.read(), "format": req.format}
                    os.unlink(tmp.name)

            response = StructureResponse(
                success=True,
                message=f"结构预览({req.format}格式)",
                session_id=req.session_id,
                structure_data=preview_data
            )

            return [TextContent(type="text", text=json.dumps(response.dict()))]

        except Exception as e:
            logger.error(f"预览结构失败: {e}")
            response = ErrorResponse(
                error="structure_preview_error",
                message=f"预览结构失败: {str(e)}"
            )
            return [TextContent(type="text", text=json.dumps(response.dict()))]

    async def handle_save_structure(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """处理保存结构请求"""
        try:
            req = SaveStructureRequest(**arguments)

            # 获取结构
            atoms = await self.session_manager.get_structure(req.session_id)
            if not atoms:
                response = ErrorResponse(
                    error="session_not_found",
                    message=f"会话不存在或无结构数据: {req.session_id}"
                )
                return [TextContent(type="text", text=json.dumps(response.dict()))]

            # 保存文件
            saved_path = self.ase_engine.save_structure(
                atoms, req.filename, req.format
            )

            response = StructureResponse(
                success=True,
                message=f"结构已保存到: {saved_path}",
                session_id=req.session_id,
                properties={"saved_path": saved_path}
            )

            return [TextContent(type="text", text=json.dumps(response.dict()))]

        except Exception as e:
            logger.error(f"保存结构失败: {e}")
            response = ErrorResponse(
                error="structure_save_error",
                message=f"保存结构失败: {str(e)}"
            )
            return [TextContent(type="text", text=json.dumps(response.dict()))]

    async def handle_list_sessions(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """处理列出会话请求"""
        try:
            limit = arguments.get("limit", 20)
            offset = arguments.get("offset", 0)
            status_filter = arguments.get("status_filter")

            sessions = await self.session_manager.list_sessions(
                limit=limit, offset=offset, status_filter=status_filter
            )

            response = {
                "success": True,
                "message": f"找到 {len(sessions)} 个会话",
                "sessions": sessions,
                "pagination": {
                    "limit": limit,
                    "offset": offset,
                    "total": len(sessions)
                }
            }

            return [TextContent(type="text", text=json.dumps(response))]

        except Exception as e:
            logger.error(f"列出会话失败: {e}")
            response = ErrorResponse(
                error="session_list_error",
                message=f"列出会话失败: {str(e)}"
            )
            return [TextContent(type="text", text=json.dumps(response.dict()))]

    async def handle_get_session_info(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """处理获取会话信息请求"""
        try:
            session_id = arguments["session_id"]

            session_data = await self.session_manager.get_session(session_id)
            if not session_data:
                response = ErrorResponse(
                    error="session_not_found",
                    message=f"会话不存在: {session_id}"
                )
                return [TextContent(type="text", text=json.dumps(response.dict()))]

            # 获取历史记录摘要
            history = await self.session_manager.get_history(session_id)

            response = {
                "success": True,
                "message": "会话信息获取成功",
                "session": session_data,
                "history": history
            }

            return [TextContent(type="text", text=json.dumps(response))]

        except Exception as e:
            logger.error(f"获取会话信息失败: {e}")
            response = ErrorResponse(
                error="session_info_error",
                message=f"获取会话信息失败: {str(e)}"
            )
            return [TextContent(type="text", text=json.dumps(response.dict()))]

    async def handle_delete_session(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """处理删除会话请求"""
        try:
            session_id = arguments["session_id"]

            success = await self.session_manager.delete_session(session_id)

            if success:
                response = {
                    "success": True,
                    "message": f"会话已删除: {session_id}"
                }
            else:
                response = ErrorResponse(
                    error="session_delete_error",
                    message=f"删除会话失败: {session_id}"
                )

            return [TextContent(type="text", text=json.dumps(response))]

        except Exception as e:
            logger.error(f"删除会话失败: {e}")
            response = ErrorResponse(
                error="session_delete_error",
                message=f"删除会话失败: {str(e)}"
            )
            return [TextContent(type="text", text=json.dumps(response.dict()))]

    async def handle_undo_operation(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """处理撤销操作请求"""
        try:
            session_id = arguments["session_id"]

            success = await self.session_manager.undo(session_id)

            if success:
                # 获取当前结构
                atoms = await self.session_manager.get_structure(session_id)
                structure_data = self.ase_engine.convert_to_dict(atoms) if atoms else None

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

            return [TextContent(type="text", text=json.dumps(response.dict()))]

        except Exception as e:
            logger.error(f"撤销操作失败: {e}")
            response = ErrorResponse(
                error="undo_error",
                message=f"撤销操作失败: {str(e)}"
            )
            return [TextContent(type="text", text=json.dumps(response.dict()))]

    async def handle_redo_operation(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """处理重做操作请求"""
        try:
            session_id = arguments["session_id"]

            success = await self.session_manager.redo(session_id)

            if success:
                # 获取当前结构
                atoms = await self.session_manager.get_structure(session_id)
                structure_data = self.ase_engine.convert_to_dict(atoms) if atoms else None

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

            return [TextContent(type="text", text=json.dumps(response.dict()))]

        except Exception as e:
            logger.error(f"重做操作失败: {e}")
            response = ErrorResponse(
                error="redo_error",
                message=f"重做操作失败: {str(e)}"
            )
            return [TextContent(type="text", text=json.dumps(response.dict()))]

    async def handle_get_structure_info(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """处理获取结构信息请求"""
        try:
            session_id = arguments["session_id"]

            atoms = await self.session_manager.get_structure(session_id)
            if not atoms:
                response = ErrorResponse(
                    error="session_not_found",
                    message=f"会话不存在或无结构数据: {session_id}"
                )
                return [TextContent(type="text", text=json.dumps(response.dict()))]

            # 获取详细结构信息
            structure_info = self.ase_engine.get_structure_info(atoms)
            bonds = self.structure_ops.get_bonds(atoms)
            coordination = self.structure_ops.get_coordination_numbers(atoms)

            response = StructureResponse(
                success=True,
                message="结构信息获取成功",
                session_id=session_id,
                structure_info={
                    **structure_info,
                    "bonds": bonds[:10],  # 限制键数量
                    "coordination_numbers": coordination,
                    "total_bonds": len(bonds)
                }
            )

            return [TextContent(type="text", text=json.dumps(response.dict()))]

        except Exception as e:
            logger.error(f"获取结构信息失败: {e}")
            response = ErrorResponse(
                error="structure_info_error",
                message=f"获取结构信息失败: {str(e)}"
            )
            return [TextContent(type="text", text=json.dumps(response.dict()))]

    async def initialize(self):
        """初始化服务器"""
        await self.session_manager.initialize()
        logger.info("ASE MCP服务器初始化完成")

    async def run(self):
        """运行服务器"""
        await self.initialize()
        async with stdio_server() as streams:
            await self.server.run(
                streams[0], streams[1], self.server.create_initialization_options()
            )


def main():
    """主函数"""
    import sys

    # 配置Redis URL
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")

    server = ASEMCPServer(redis_url)

    try:
        asyncio.run(server.run())
    except KeyboardInterrupt:
        logger.info("服务器停止")
    except Exception as e:
        logger.error(f"服务器运行错误: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
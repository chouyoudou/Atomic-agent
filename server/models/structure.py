from typing import Dict, List, Optional, Any, Tuple
from pydantic import BaseModel, Field
from datetime import datetime
import numpy as np


class AtomData(BaseModel):
    """单个原子的数据模型"""
    symbol: str = Field(..., description="元素符号")
    position: List[float] = Field(..., description="原子位置坐标")
    atomic_number: int = Field(..., description="原子序数")
    mass: float = Field(..., description="原子质量")


class CellData(BaseModel):
    """晶胞数据模型"""
    vectors: List[List[float]] = Field(..., description="晶胞向量")
    volume: Optional[float] = Field(None, description="晶胞体积")
    pbc: List[bool] = Field([False, False, False], description="周期性边界条件")


class StructureData(BaseModel):
    """原子结构数据模型"""
    symbols: List[str] = Field(..., description="元素符号列表")
    positions: List[List[float]] = Field(..., description="原子位置列表")
    cell: List[List[float]] = Field(..., description="晶胞矩阵")
    pbc: List[bool] = Field([False, False, False], description="周期性边界条件")
    numbers: List[int] = Field(..., description="原子序数列表")
    masses: List[float] = Field(..., description="原子质量列表")
    total_atoms: int = Field(..., description="原子总数")
    formula: str = Field(..., description="化学式")
    center_of_mass: List[float] = Field(..., description="质心")
    volume: Optional[float] = Field(None, description="体积")

    class Config:
        json_encoders = {
            np.ndarray: lambda v: v.tolist(),
            np.integer: int,
            np.floating: float
        }


class StructureOperation(BaseModel):
    """结构操作数据模型"""
    operation: str = Field(..., description="操作类型")
    parameters: Dict[str, Any] = Field(..., description="操作参数")
    timestamp: datetime = Field(default_factory=datetime.now, description="操作时间")


class PropertyData(BaseModel):
    """属性数据模型"""
    energy: Optional[float] = Field(None, description="能量")
    forces: Optional[List[List[float]]] = Field(None, description="力")
    stress: Optional[List[float]] = Field(None, description="应力")
    dipole: Optional[List[float]] = Field(None, description="偶极矩")
    calculated_at: datetime = Field(default_factory=datetime.now, description="计算时间")
    calculator: str = Field("emt", description="计算器类型")


class StructureInfo(BaseModel):
    """结构信息数据模型"""
    formula: str = Field(..., description="化学式")
    total_atoms: int = Field(..., description="原子总数")
    unique_elements: List[str] = Field(..., description="唯一元素列表")
    cell_volume: Optional[float] = Field(None, description="晶胞体积")
    center_of_mass: List[float] = Field(..., description="质心")
    cell_parameters: List[List[float]] = Field(..., description="晶胞参数")
    periodic_boundary_conditions: List[bool] = Field(..., description="周期性边界条件")
    atomic_numbers: List[int] = Field(..., description="原子序数")
    masses: List[float] = Field(..., description="原子质量")
    min_distance: Optional[float] = Field(None, description="最小原子间距")
    max_distance: Optional[float] = Field(None, description="最大原子间距")
    avg_distance: Optional[float] = Field(None, description="平均原子间距")


class BondData(BaseModel):
    """键连接数据模型"""
    atom1: int = Field(..., description="原子1索引")
    atom2: int = Field(..., description="原子2索引")
    distance: float = Field(..., description="键长")
    symbols: List[str] = Field(..., description="原子符号")
    offset: List[int] = Field(..., description="偏移向量")


class SessionMetadata(BaseModel):
    """会话元数据模型"""
    name: Optional[str] = Field(None, description="会话名称")
    description: Optional[str] = Field(None, description="会话描述")
    tags: List[str] = Field(default_factory=list, description="标签")
    user_id: Optional[str] = Field(None, description="用户ID")
    project_id: Optional[str] = Field(None, description="项目ID")


class HistoryEntry(BaseModel):
    """历史记录条目"""
    index: int = Field(..., description="历史索引")
    timestamp: datetime = Field(..., description="时间戳")
    operation: str = Field(..., description="操作类型")
    parameters: Optional[Dict[str, Any]] = Field(None, description="操作参数")
    structure_data: StructureData = Field(..., description="结构数据")
    is_current: bool = Field(False, description="是否为当前状态")


class CreateStructureRequest(BaseModel):
    """创建结构请求模型"""
    type: str = Field(..., description="结构类型: bulk, molecule, surface, nanoparticle")
    formula: str = Field(..., description="化学式")
    crystal_structure: Optional[str] = Field(None, description="晶体结构")
    size: Optional[List[int]] = Field(None, description="超胞大小")
    lattice_constant: Optional[float] = Field(None, description="晶格常数")
    session_id: Optional[str] = Field(None, description="会话ID")


class ModifyStructureRequest(BaseModel):
    """修改结构请求模型"""
    session_id: str = Field(..., description="会话ID")
    operation: str = Field(..., description="操作类型")
    parameters: Dict[str, Any] = Field(..., description="操作参数")


class CalculatePropertiesRequest(BaseModel):
    """计算属性请求模型"""
    session_id: str = Field(..., description="会话ID")
    calculator: str = Field("emt", description="计算器类型")
    properties: List[str] = Field(["energy"], description="要计算的属性")


class OptimizeStructureRequest(BaseModel):
    """优化结构请求模型"""
    session_id: str = Field(..., description="会话ID")
    calculator: str = Field("emt", description="计算器类型")
    fmax: float = Field(0.01, description="收敛阈值")
    steps: int = Field(100, description="最大优化步数")


class SaveStructureRequest(BaseModel):
    """保存结构请求模型"""
    session_id: str = Field(..., description="会话ID")
    filename: str = Field(..., description="文件名")
    format: Optional[str] = Field(None, description="文件格式")


class PreviewStructureRequest(BaseModel):
    """预览结构请求模型"""
    session_id: str = Field(..., description="会话ID")
    format: str = Field("json", description="预览格式: json, cif, xyz")


class SessionResponse(BaseModel):
    """会话响应模型"""
    id: str = Field(..., description="会话ID")
    created_at: datetime = Field(..., description="创建时间")
    modified_at: datetime = Field(..., description="修改时间")
    status: str = Field(..., description="会话状态")
    has_structure: bool = Field(..., description="是否有结构")
    metadata: SessionMetadata = Field(..., description="元数据")
    structure_summary: Optional[Dict[str, Any]] = Field(None, description="结构摘要")


class StructureResponse(BaseModel):
    """结构响应模型"""
    success: bool = Field(..., description="操作是否成功")
    message: str = Field(..., description="响应消息")
    session_id: str = Field(..., description="会话ID")
    structure_data: Optional[StructureData] = Field(None, description="结构数据")
    properties: Optional[PropertyData] = Field(None, description="属性数据")
    structure_info: Optional[StructureInfo] = Field(None, description="结构信息")


class WebSocketMessage(BaseModel):
    """WebSocket消息模型"""
    type: str = Field(..., description="消息类型")
    session_id: str = Field(..., description="会话ID")
    data: Dict[str, Any] = Field(..., description="消息数据")
    timestamp: datetime = Field(default_factory=datetime.now, description="时间戳")


class ErrorResponse(BaseModel):
    """错误响应模型"""
    success: bool = Field(False, description="操作失败")
    error: str = Field(..., description="错误类型")
    message: str = Field(..., description="错误消息")
    details: Optional[Dict[str, Any]] = Field(None, description="错误详情")
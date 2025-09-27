from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
from datetime import datetime
from .structure import StructureData, PropertyData, SessionMetadata, HistoryEntry


class Session(BaseModel):
    """会话数据模型"""
    id: str = Field(..., description="会话唯一标识符")
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    modified_at: datetime = Field(default_factory=datetime.now, description="最后修改时间")
    status: str = Field("active", description="会话状态: active, inactive, completed, error")

    # 结构数据
    atoms_data: Optional[StructureData] = Field(None, description="当前原子结构数据")

    # 历史记录
    history: List[Dict[str, Any]] = Field(default_factory=list, description="操作历史记录")
    history_index: int = Field(-1, description="当前历史位置索引")

    # 属性和计算结果
    properties: Dict[str, Any] = Field(default_factory=dict, description="计算属性和结果")

    # 元数据
    metadata: SessionMetadata = Field(default_factory=SessionMetadata, description="会话元数据")

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

    def update_modified_time(self):
        """更新修改时间"""
        self.modified_at = datetime.now()

    def has_structure(self) -> bool:
        """检查是否有结构数据"""
        return self.atoms_data is not None

    def can_undo(self) -> bool:
        """检查是否可以撤销"""
        return self.history_index >= 0

    def can_redo(self) -> bool:
        """检查是否可以重做"""
        return self.history_index + 1 < len(self.history)

    def get_current_operation(self) -> Optional[str]:
        """获取当前操作类型"""
        if self.metadata and hasattr(self.metadata, 'last_operation'):
            return self.metadata.last_operation.get('type')
        return None

    def add_to_history(self, atoms_data: StructureData, operation: str, parameters: Optional[Dict[str, Any]] = None):
        """添加到历史记录"""
        # 如果不在历史末尾，清除后续历史
        if self.history_index + 1 < len(self.history):
            self.history = self.history[:self.history_index + 1]

        # 创建历史条目
        history_entry = {
            'timestamp': datetime.now().isoformat(),
            'operation': operation,
            'parameters': parameters or {},
            'atoms_data': atoms_data.dict()
        }

        self.history.append(history_entry)
        self.history_index = len(self.history) - 1

        # 限制历史记录数量
        max_history = 50
        if len(self.history) > max_history:
            self.history = self.history[-max_history:]
            self.history_index = len(self.history) - 1

        self.update_modified_time()

    def get_history_summary(self) -> List[Dict[str, Any]]:
        """获取历史记录摘要"""
        summary = []
        for i, entry in enumerate(self.history):
            summary.append({
                'index': i,
                'timestamp': entry['timestamp'],
                'operation': entry['operation'],
                'is_current': i == self.history_index,
                'can_restore': True
            })
        return summary


class SessionCreate(BaseModel):
    """创建会话请求模型"""
    session_id: Optional[str] = Field(None, description="可选的会话ID")
    metadata: Optional[SessionMetadata] = Field(None, description="会话元数据")


class SessionUpdate(BaseModel):
    """更新会话请求模型"""
    metadata: Optional[SessionMetadata] = Field(None, description="更新的元数据")
    status: Optional[str] = Field(None, description="更新的状态")


class SessionList(BaseModel):
    """会话列表请求模型"""
    limit: int = Field(100, description="返回数量限制", ge=1, le=1000)
    offset: int = Field(0, description="偏移量", ge=0)
    status_filter: Optional[str] = Field(None, description="状态过滤器")
    search: Optional[str] = Field(None, description="搜索关键词")


class SessionSummary(BaseModel):
    """会话摘要模型"""
    id: str = Field(..., description="会话ID")
    created_at: datetime = Field(..., description="创建时间")
    modified_at: datetime = Field(..., description="修改时间")
    status: str = Field(..., description="会话状态")
    has_structure: bool = Field(..., description="是否有结构")
    metadata: SessionMetadata = Field(..., description="元数据")
    structure_summary: Optional[Dict[str, Any]] = Field(None, description="结构摘要")
    operation_count: int = Field(0, description="操作次数")
    last_operation: Optional[str] = Field(None, description="最后操作")

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class SessionHistory(BaseModel):
    """会话历史模型"""
    session_id: str = Field(..., description="会话ID")
    history: List[HistoryEntry] = Field(..., description="历史记录")
    current_index: int = Field(-1, description="当前索引")
    can_undo: bool = Field(False, description="是否可以撤销")
    can_redo: bool = Field(False, description="是否可以重做")


class SessionOperationResult(BaseModel):
    """会话操作结果模型"""
    success: bool = Field(..., description="操作是否成功")
    message: str = Field(..., description="结果消息")
    session_id: str = Field(..., description="会话ID")
    operation: str = Field(..., description="操作类型")
    timestamp: datetime = Field(default_factory=datetime.now, description="操作时间")
    data: Optional[Dict[str, Any]] = Field(None, description="返回数据")

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class SessionStats(BaseModel):
    """会话统计模型"""
    total_sessions: int = Field(..., description="总会话数")
    active_sessions: int = Field(..., description="活跃会话数")
    sessions_with_structure: int = Field(..., description="有结构的会话数")
    total_operations: int = Field(..., description="总操作数")
    avg_operations_per_session: float = Field(..., description="平均每会话操作数")
    most_common_operations: List[Dict[str, Any]] = Field(..., description="最常见操作")

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
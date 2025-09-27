import asyncio
import json
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from ase import Atoms
import numpy as np
from .ase_engine import ASEEngine
from .structure_ops import StructureOperations
from utils.redis_client import get_redis_client


class SessionManager:
    """
    会话管理器，管理多个结构编辑会话
    """

    def __init__(self, redis_url: str = "redis://localhost:6379"):
        self.redis_url = redis_url
        self.redis = None
        self.ase_engine = ASEEngine()
        self.structure_ops = StructureOperations()
        self.sessions = {}  # 内存缓存
        self.session_timeout = 3600  # 1小时超时

    async def initialize(self):
        """初始化Redis连接"""
        try:
            self.redis = await get_redis_client(self.redis_url)
            print(f"Redis连接成功: {self.redis_url}")
        except Exception as e:
            print(f"Redis连接失败: {e}")
            raise

    async def close(self):
        """关闭连接"""
        if self.redis:
            await self.redis.close()

    def _generate_session_id(self) -> str:
        """生成唯一的会话ID"""
        return str(uuid.uuid4())

    async def create_session(
        self,
        session_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        创建新的会话

        Args:
            session_id: 可选的会话ID
            metadata: 会话元数据

        Returns:
            会话ID
        """
        if not session_id:
            session_id = self._generate_session_id()

        if await self.session_exists(session_id):
            raise ValueError(f"会话ID已存在: {session_id}")

        session_data = {
            'id': session_id,
            'created_at': datetime.now().isoformat(),
            'modified_at': datetime.now().isoformat(),
            'atoms_data': None,
            'history': [],
            'history_index': -1,
            'properties': {},
            'metadata': metadata or {},
            'status': 'active'
        }

        # 保存到Redis
        await self._save_session(session_id, session_data)

        # 更新内存缓存
        self.sessions[session_id] = session_data

        return session_id

    async def session_exists(self, session_id: str) -> bool:
        """检查会话是否存在"""
        try:
            result = await self.redis.exists(f"session:{session_id}")
            return bool(result)
        except Exception:
            return session_id in self.sessions

    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        获取会话数据

        Args:
            session_id: 会话ID

        Returns:
            会话数据或None
        """
        # 先检查内存缓存
        if session_id in self.sessions:
            return self.sessions[session_id]

        # 从Redis获取
        try:
            session_data = await self.redis.get(f"session:{session_id}")
            if session_data:
                data = json.loads(session_data)
                # 更新内存缓存
                self.sessions[session_id] = data
                return data
        except Exception as e:
            print(f"获取会话失败: {e}")

        return None

    async def update_session(
        self,
        session_id: str,
        atoms: Optional[Atoms] = None,
        properties: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        add_to_history: bool = True
    ) -> bool:
        """
        更新会话数据

        Args:
            session_id: 会话ID
            atoms: 原子结构
            properties: 属性数据
            metadata: 元数据
            add_to_history: 是否添加到历史记录

        Returns:
            更新是否成功
        """
        session_data = await self.get_session(session_id)
        if not session_data:
            return False

        try:
            # 更新修改时间
            session_data['modified_at'] = datetime.now().isoformat()

            # 更新原子结构
            if atoms is not None:
                old_atoms_data = session_data.get('atoms_data')
                new_atoms_data = self.ase_engine.convert_to_dict(atoms)
                session_data['atoms_data'] = new_atoms_data

                # 添加到历史记录
                if add_to_history and old_atoms_data:
                    await self._add_to_history(session_data, old_atoms_data)

            # 更新属性
            if properties is not None:
                session_data['properties'].update(properties)

            # 更新元数据
            if metadata is not None:
                session_data['metadata'].update(metadata)

            # 保存更新
            await self._save_session(session_id, session_data)
            self.sessions[session_id] = session_data

            return True

        except Exception as e:
            print(f"更新会话失败: {e}")
            return False

    async def set_structure(
        self,
        session_id: str,
        atoms: Atoms,
        operation_info: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        设置会话的原子结构

        Args:
            session_id: 会话ID
            atoms: 原子结构
            operation_info: 操作信息

        Returns:
            设置是否成功
        """
        metadata = {}
        if operation_info:
            metadata['last_operation'] = operation_info

        # 计算基本属性
        try:
            structure_info = self.ase_engine.get_structure_info(atoms)
            properties = {'structure_info': structure_info}
        except Exception:
            properties = {}

        return await self.update_session(
            session_id,
            atoms=atoms,
            properties=properties,
            metadata=metadata
        )

    async def get_structure(self, session_id: str) -> Optional[Atoms]:
        """
        获取会话的原子结构

        Args:
            session_id: 会话ID

        Returns:
            原子结构或None
        """
        session_data = await self.get_session(session_id)
        if not session_data or not session_data.get('atoms_data'):
            return None

        try:
            atoms = self.ase_engine.convert_from_dict(session_data['atoms_data'])
            return atoms
        except Exception as e:
            print(f"获取结构失败: {e}")
            return None

    async def delete_session(self, session_id: str) -> bool:
        """
        删除会话

        Args:
            session_id: 会话ID

        Returns:
            删除是否成功
        """
        try:
            # 从Redis删除
            await self.redis.delete(f"session:{session_id}")

            # 从内存缓存删除
            if session_id in self.sessions:
                del self.sessions[session_id]

            return True

        except Exception as e:
            print(f"删除会话失败: {e}")
            return False

    async def list_sessions(
        self,
        limit: int = 100,
        offset: int = 0,
        status_filter: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        列出所有会话

        Args:
            limit: 限制数量
            offset: 偏移量
            status_filter: 状态过滤

        Returns:
            会话列表
        """
        try:
            # 从Redis获取所有会话键
            keys = await self.redis.keys("session:*")

            sessions = []
            for key in keys[offset:offset + limit]:
                session_data = await self.redis.get(key)
                if session_data:
                    data = json.loads(session_data)

                    # 状态过滤
                    if status_filter and data.get('status') != status_filter:
                        continue

                    # 简化数据，只返回摘要信息
                    summary = {
                        'id': data['id'],
                        'created_at': data['created_at'],
                        'modified_at': data['modified_at'],
                        'status': data.get('status', 'active'),
                        'has_structure': bool(data.get('atoms_data')),
                        'metadata': data.get('metadata', {})
                    }

                    if data.get('atoms_data'):
                        structure_info = data.get('properties', {}).get('structure_info', {})
                        summary['structure_summary'] = {
                            'formula': structure_info.get('formula'),
                            'total_atoms': structure_info.get('total_atoms'),
                            'unique_elements': structure_info.get('unique_elements')
                        }

                    sessions.append(summary)

            # 按修改时间排序
            sessions.sort(key=lambda x: x['modified_at'], reverse=True)

            return sessions

        except Exception as e:
            print(f"列出会话失败: {e}")
            return []

    async def undo(self, session_id: str) -> bool:
        """
        撤销操作

        Args:
            session_id: 会话ID

        Returns:
            撤销是否成功
        """
        session_data = await self.get_session(session_id)
        if not session_data:
            return False

        history = session_data.get('history', [])
        history_index = session_data.get('history_index', -1)

        if history_index >= 0 and history_index < len(history):
            # 恢复到历史状态
            historical_data = history[history_index]
            session_data['atoms_data'] = historical_data
            session_data['history_index'] = history_index - 1
            session_data['modified_at'] = datetime.now().isoformat()

            await self._save_session(session_id, session_data)
            self.sessions[session_id] = session_data

            return True

        return False

    async def redo(self, session_id: str) -> bool:
        """
        重做操作

        Args:
            session_id: 会话ID

        Returns:
            重做是否成功
        """
        session_data = await self.get_session(session_id)
        if not session_data:
            return False

        history = session_data.get('history', [])
        history_index = session_data.get('history_index', -1)

        if history_index + 2 < len(history):
            # 前进到下一个状态
            next_data = history[history_index + 2]
            session_data['atoms_data'] = next_data
            session_data['history_index'] = history_index + 1
            session_data['modified_at'] = datetime.now().isoformat()

            await self._save_session(session_id, session_data)
            self.sessions[session_id] = session_data

            return True

        return False

    async def get_history(self, session_id: str) -> List[Dict[str, Any]]:
        """
        获取会话历史

        Args:
            session_id: 会话ID

        Returns:
            历史记录列表
        """
        session_data = await self.get_session(session_id)
        if not session_data:
            return []

        history = session_data.get('history', [])
        history_index = session_data.get('history_index', -1)

        result = []
        for i, historical_data in enumerate(history):
            result.append({
                'index': i,
                'is_current': i == history_index + 1,
                'timestamp': historical_data.get('timestamp'),
                'operation': historical_data.get('operation', 'unknown'),
                'summary': {
                    'formula': historical_data.get('formula'),
                    'total_atoms': historical_data.get('total_atoms')
                }
            })

        return result

    async def cleanup_expired_sessions(self) -> int:
        """
        清理过期会话

        Returns:
            清理的会话数量
        """
        try:
            keys = await self.redis.keys("session:*")
            expired_count = 0
            cutoff_time = datetime.now() - timedelta(seconds=self.session_timeout)

            for key in keys:
                session_data = await self.redis.get(key)
                if session_data:
                    data = json.loads(session_data)
                    modified_time = datetime.fromisoformat(data['modified_at'])

                    if modified_time < cutoff_time:
                        await self.redis.delete(key)
                        session_id = key.replace("session:", "")
                        if session_id in self.sessions:
                            del self.sessions[session_id]
                        expired_count += 1

            return expired_count

        except Exception as e:
            print(f"清理过期会话失败: {e}")
            return 0

    async def _save_session(self, session_id: str, session_data: Dict[str, Any]):
        """保存会话到Redis"""
        try:
            await self.redis.setex(
                f"session:{session_id}",
                self.session_timeout,
                json.dumps(session_data, default=self._json_serializer)
            )
        except Exception as e:
            print(f"保存会话失败: {e}")
            raise

    async def _add_to_history(self, session_data: Dict[str, Any], atoms_data: Dict[str, Any]):
        """添加到历史记录"""
        try:
            history = session_data.setdefault('history', [])
            history_index = session_data.get('history_index', -1)

            # 添加时间戳和操作信息
            historical_entry = atoms_data.copy()
            historical_entry.update({
                'timestamp': datetime.now().isoformat(),
                'operation': session_data.get('metadata', {}).get('last_operation', {}).get('type', 'unknown')
            })

            # 如果不在历史末尾，清除后续历史
            if history_index + 1 < len(history):
                history = history[:history_index + 1]

            history.append(historical_entry)

            # 限制历史记录数量
            max_history = 50
            if len(history) > max_history:
                history = history[-max_history:]

            session_data['history'] = history
            session_data['history_index'] = len(history) - 1

        except Exception as e:
            print(f"添加历史记录失败: {e}")

    def _json_serializer(self, obj):
        """JSON序列化器，处理特殊对象类型"""
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        elif isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.floating):
            return float(obj)
        elif isinstance(obj, datetime):
            return obj.isoformat()
        raise TypeError(f"Object of type {type(obj)} is not JSON serializable")
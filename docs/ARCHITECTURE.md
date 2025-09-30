# ASE MCP System Architecture Documentation

## System Overview

ASE MCP is a multi-protocol server based on the Atomic Simulation Environment (ASE), supporting MCP protocol, HTTP API, and WebSocket real-time communication.

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   LLM Clients   │    │  Web Frontend   │    │   API Clients   │
│  (Claude etc.)  │    │    (React)      │    │   (curl/SDK)    │
└─────────┬───────┘    └─────────┬───────┘    └─────────┬───────┘
          │                      │                      │
          │ MCP Protocol         │ HTTP + WebSocket     │ HTTP API
          │                      │                      │
┌─────────▼──────────────────────▼──────────────────────▼───────┐
│                     ASE MCP Server                            │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐│
│  │ MCP Handler │  │ Web Server  │  │    WebSocket Server     ││
│  └──────┬──────┘  └──────┬──────┘  └───────────┬─────────────┘│
│         │                │                     │              │
│  ┌──────▼────────────────▼─────────────────────▼──────────────┐│
│  │                Session Manager                             ││
│  └───────────────────────┬───────────────────────────────────┘│
│                          │                                    │
│  ┌───────────────────────▼───────────────────────────────────┐│
│  │                   ASE Engine                              ││
│  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────────────┐ ││
│  │  │  Structure  │ │ Calculator  │ │     File I/O        │ ││
│  │  │  Creation   │ │  Manager    │ │    Management       │ ││
│  │  └─────────────┘ └─────────────┘ └─────────────────────┘ ││
│  └───────────────────────────────────────────────────────────┘│
└───────────────────────────┬───────────────────────────────────┘
                            │
┌───────────────────────────▼───────────────────────────────────┐
│                  Storage Layer                                │
│  ┌─────────────┐           ┌─────────────────────────────────┐ │
│  │    Redis    │           │        File System              │ │
│  │  (Sessions) │           │     (Structure Files)           │ │
│  └─────────────┘           └─────────────────────────────────┘ │
└───────────────────────────────────────────────────────────────┘
```

## Core Components

### 1. ASE Engine (`server/core/ase_engine.py`)

**Responsibility**: Core engine for atomic structure operations

**Main Functions**:
- Structure creation: `create_bulk_structure()`, `create_molecule_structure()`, `create_surface_structure()`
- Structure modification: `modify_structure()` (12 operation types)
- Property calculation: `calculate_properties()`, `optimize_structure()`
- Data conversion: `convert_to_dict()`, `convert_from_dict()`
- File operations: `save_structure()`, `load_structure()`

**Key Features**:
- Support for all ASE structure types
- Thread-safe operations
- Error handling and validation
- Extensible calculator interface

### 2. Session Manager (`server/core/session_manager.py`)

**Responsibility**: Session and state management

**Main Functions**:
- Session lifecycle management
- Structure state persistence
- Operation history tracking
- Undo/redo functionality

**数据结构**:
```python
Session = {
    "id": str,
    "created_at": datetime,
    "modified_at": datetime,
    "status": "active|archived",
    "structure": Atoms,
    "metadata": dict,
    "history": List[Operation]
}
```

### 3. MCP Handler (`server/handlers/mcp_handler.py`)

**Responsibility**: MCP protocol implementation

**Supported Tools**:
- `create_structure`: Create new structures
- `modify_structure`: Modify existing structures
- `preview_structure`: Preview structures
- `calculate_properties`: Calculate properties
- `list_sessions`: List sessions
- `get_structure_info`: Get structure information
- More...

**Communication Mechanism**:
- Standard input/output communication
- JSON-RPC 2.0 protocol
- Tool discovery and validation

### 4. Web Server (`server/web_server.py`)

**职责**: HTTP API和静态文件服务

**API端点**:
```
POST   /api/structures              # 创建结构
GET    /api/structures/{id}         # 获取结构
POST   /api/structures/{id}/modify  # 修改结构
GET    /api/sessions                # 列出会话
DELETE /api/sessions/{id}           # 删除会话
```

**特性**:
- FastAPI框架
- 自动API文档生成
- CORS支持
- 错误处理中间件

### 5. WebSocket Server (`server/handlers/websocket_handler.py`)

**职责**: 实时通信

**消息类型**:
- `structure_created`: 结构创建通知
- `structure_modified`: 结构修改通知
- `session_updated`: 会话状态更新
- `error`: 错误消息

**连接管理**:
- 多客户端支持
- 自动重连机制
- 消息广播

### 6. Web Frontend (`client/`)

**技术栈**:
- React 18
- 3Dmol.js (分子可视化)
- WebSocket客户端

**主要组件**:
- `SimpleApp.js`: 主应用界面
- 3D可视化渲染器
- 实时数据更新

## 数据流

### 1. 结构创建流程

```
User Request → MCP/HTTP Handler → Session Manager → ASE Engine
                     ↓
Structure Created ← Session Storage ← Atoms Object ← ASE
                     ↓
WebSocket Broadcast ← Session Manager ← Result
                     ↓
Frontend Update ← WebSocket Client ← Notification
```

### 2. 结构修改流程

```
Modify Request → Handler → Session Manager → ASE Engine
                    ↓            ↓              ↓
                 Validate →  Get Current → Apply Operation
                    ↓         Structure        ↓
               Error Handle ←    ↓        → New Structure
                    ↓            ↓              ↓
                Response ← Update Session ← Save Result
                    ↓            ↓
                Frontend ← WebSocket Notification
```

## 存储层

### 1. Redis存储 (可选)

**数据结构**:
```
sessions:{session_id} → JSON(Session)
structures:{session_id} → Pickle(Atoms)
history:{session_id} → JSON(Operations[])
```

**特性**:
- 持久化会话
- 快速读写
- 支持过期策略

### 2. MockRedis Fallback

**场景**: Redis不可用时
**实现**: 内存字典模拟
**限制**: 进程重启后数据丢失

### 3. 文件系统

**用途**:
- 结构文件导出
- 临时文件存储
- 日志文件

## 安全性

### 1. 输入验证
- 参数类型检查
- 数值范围验证
- 化学式有效性验证

### 2. 资源限制
- 最大原子数限制
- 会话数量限制
- 计算时间限制

### 3. 错误处理
- 异常捕获和记录
- 用户友好的错误消息
- 系统状态恢复

## 性能优化

### 1. 缓存策略
- 结构计算结果缓存
- 会话状态缓存
- 静态文件缓存

### 2. 异步处理
- 非阻塞I/O操作
- 后台任务队列
- WebSocket异步广播

### 3. 内存管理
- 对象池复用
- 及时清理无用会话
- 大结构的流式处理

## 扩展点

### 1. 新计算器集成

```python
# 在ASE Engine中注册
self.calculators['new_calc'] = NewCalculator

# 实现计算器接口
class NewCalculator:
    def get_potential_energy(self): ...
    def get_forces(self): ...
```

### 2. 新结构类型

```python
# 扩展create_structure_by_type
def create_custom_structure(self, params):
    # 自定义结构创建逻辑
    return atoms
```

### 3. 新修改操作

```python
# 在modify_structure中添加
elif operation == "custom_operation":
    # 自定义修改逻辑
    pass
```

### 4. 新通信协议

```python
# 实现新的Handler
class NewProtocolHandler:
    def handle_request(self, request): ...
```

## 部署架构

### 1. 开发环境
```
Frontend Dev Server (3000) ← → Backend API (8000)
                              ↗ WebSocket (8001)
```

### 2. 生产环境
```
Load Balancer → Frontend (Nginx) → Backend Cluster
                     ↓                   ↓
               Static Files         API Services
                                        ↓
                                   Redis Cluster
```

### 3. 容器化部署
```
Docker Compose:
├── frontend (Nginx + React)
├── backend (Python + FastAPI)
├── redis (Cache)
└── websocket (Dedicated WS)
```

## 监控和日志

### 1. 应用监控
- 会话数量统计
- API响应时间
- 错误率监控

### 2. 日志级别
- ERROR: 系统错误
- WARNING: 用户操作警告
- INFO: 正常操作记录
- DEBUG: 详细调试信息

### 3. 性能指标
- 内存使用量
- CPU使用率
- 结构处理速度

通过这个架构，ASE MCP实现了高性能、可扩展、易维护的原子模拟服务。
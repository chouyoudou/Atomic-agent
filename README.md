# ASE MCP Server

一个基于原子模拟环境(ASE)的MCP服务器，支持实时晶体结构生成、修改和监控。

## 功能特性

- 🔬 **ASE集成**: 完整的原子模拟环境支持
- 🤖 **MCP协议**: 支持AI Agent通过MCP协议操作
- 🌐 **实时监控**: WebSocket实时推送结构更新
- 🎨 **3D可视化**: 基于3Dmol.js的专业分子可视化，支持晶胞边界和坐标轴显示
- 🔄 **会话管理**: 支持多会话并行操作
- 📚 **操作历史**: 支持撤销/重做功能

## 架构设计

```
Frontend (React + 3Dmol.js) ←→ WebSocket ←→ MCP Server (FastAPI)
          ↑                                          ↓
    HTTP API (CORS)                        ASE Core Engine
                                                  ↓
                                        Redis (Session Storage)
```

## 部署模式

### 模式 1: 一体化部署（默认）
前后端打包在一起，适合简单部署场景：
```bash
python server/main.py
# 访问: http://localhost:8000
```

### 模式 2: 前后端分离（推荐）
后端纯API服务，前端独立部署，适合开发和生产环境：
```bash
# 后端纯API服务
python server/main.py --api-only

# 前端开发服务器
cd client && npm start
# 访问: http://localhost:3000
```

## 快速开始

### 使用Docker Compose

```bash
# 克隆项目
git clone <repo-url>
cd ASE_MCP

# 启动所有服务
docker-compose up -d

# 访问前端界面
open http://localhost:3000
```

### 快速启动脚本

```bash
# 启动后端API服务器（推荐）
./start_api_only.sh

# 启动前端开发服务器（另一个终端）
./start_frontend.sh
```

### 本地开发

#### 1. 前后端分离模式（推荐）

**后端API服务：**
```bash
# 安装Python依赖
pip install -r requirements.txt

# 启动Redis（可选，有fallback）
redis-server

# 启动纯API后端
python server/main.py --api-only
# 监听: http://localhost:8000/api/*
```

**前端服务：**
```bash
# 安装前端依赖
cd client && npm install

# 启动前端开发服务器
npm start
# 访问: http://localhost:3000
```

#### 2. 一体化模式

```bash
# 安装依赖
pip install -r requirements.txt
cd client && npm install && npm run build && cd ..

# 启动一体化服务器
python server/main.py
# 访问: http://localhost:8000
```

## 命令行选项

```bash
python server/main.py --help
```

**主要选项：**
- `--api-only`: 仅运行API服务器，不提供前端静态文件（推荐）
- `--mcp-only`: 仅运行MCP服务器，用于CLI模式
- `--allowed-origins`: 设置CORS允许的源（多个用空格分隔）
- `--host`: Web服务器监听地址（默认：0.0.0.0）
- `--port`: Web服务器端口（默认：8000）
- `--websocket-port`: WebSocket服务器端口（默认：8001）

**环境变量：**
- `SERVE_STATIC=false`: 禁用静态文件服务
- `REDIS_URL`: Redis连接URL
- `WEB_HOST`: Web服务器地址
- `WEB_PORT`: Web服务器端口
```

#### 前端服务

```bash
# 安装Node.js依赖
cd client
npm install

# 启动开发服务器
npm start
```

## MCP工具说明

### create_structure
创建新的晶体结构

```json
{
  "type": "bulk|molecule|nanoparticle",
  "formula": "Si",
  "structure": "diamond",
  "session_id": "optional-uuid"
}
```

### modify_structure
修改现有结构

```json
{
  "session_id": "uuid",
  "operation": "rotate|translate|scale|supercell",
  "parameters": {"angle": 45, "axis": [0, 0, 1]}
}
```

### preview_structure
预览当前结构

```json
{
  "session_id": "uuid",
  "format": "json|cif|xyz"
}
```

## 开发指南

### 项目结构

```
ASE_MCP/
├── server/                 # Python后端
│   ├── core/              # 核心功能模块
│   ├── handlers/          # 请求处理器
│   ├── models/            # 数据模型
│   └── utils/             # 工具函数
├── client/                # React前端
│   └── src/
│       ├── components/    # React组件
│       └── services/      # 服务层
└── tests/                 # 测试文件
```

### 添加新功能

1. 在`server/core/`中添加核心逻辑
2. 在`server/handlers/`中添加MCP工具处理器
3. 在`client/src/components/`中添加前端组件
4. 编写相应测试

## API文档

启动服务后访问 http://localhost:8000/docs 查看完整的API文档。

## 许可证

MIT License
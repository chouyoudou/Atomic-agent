# ASE MCP Server

一个基于原子模拟环境(ASE)的MCP服务器，支持实时晶体结构生成、修改和监控。

## 功能特性

- 🔬 **ASE集成**: 完整的原子模拟环境支持
- 🤖 **MCP协议**: 支持AI Agent通过MCP协议操作
- 🌐 **实时监控**: WebSocket实时推送结构更新
- 🎨 **3D可视化**: 基于Three.js的交互式3D查看器
- 🔄 **会话管理**: 支持多会话并行操作
- 📚 **操作历史**: 支持撤销/重做功能

## 架构设计

```
Frontend (React + Three.js) ←→ WebSocket ←→ MCP Server (FastAPI)
                                                      ↓
                                              ASE Core Engine
                                                      ↓
                                            Redis (Session Storage)
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

### 本地开发

#### 后端服务

```bash
# 安装Python依赖
pip install -r requirements.txt

# 启动Redis
redis-server

# 启动MCP服务器
cd server
python main.py
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
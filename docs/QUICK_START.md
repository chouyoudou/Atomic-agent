# Quick Start Guide

## One-Minute Startup

### 1. Install Dependencies
```bash
# Python dependencies
pip install -r requirements.txt

# Frontend dependencies (if using separate mode)
cd client && npm install && cd ..
```

### 2. Start Services
```bash
# Method 1: One-click startup (recommended)
./scripts/start.sh

# Method 2: Separate mode
python server/main.py --api-only    # Backend
cd client && npm start               # Frontend

# Method 3: Integrated mode
python server/main.py
```

### 3. Access Interface
- **Frontend Interface**: http://localhost:3000 (separate mode)
- **API Documentation**: http://localhost:8000/docs
- **Integrated Interface**: http://localhost:8000 (integrated mode)

## Creating Your First Structure

### 使用Web界面
1. 打开浏览器访问前端界面
2. 点击"创建结构"
3. 选择"铜(Cu)" + "FCC" + "2x2x2"
4. 查看3D可视化结果

### 使用API
```bash
curl -X POST http://localhost:8000/api/structures \
-H "Content-Type: application/json" \
-d '{
  "type": "bulk",
  "formula": "Cu",
  "structure": "fcc",
  "size": [2, 2, 2]
}'
```

### 使用MCP（Claude等）
```json
{
  "tool": "create_structure",
  "parameters": {
    "type": "bulk",
    "formula": "Cu",
    "structure": "fcc",
    "size": [2, 2, 2]
  }
}
```

## 常用操作示例

### 1. 钻石到石墨转换

**步骤1**: 创建钻石
```bash
curl -X POST http://localhost:8000/api/structures \
-H "Content-Type: application/json" \
-d '{
  "type": "bulk",
  "formula": "C",
  "structure": "diamond",
  "size": [2, 2, 1]
}'
```

**步骤2**: 获取会话ID（从响应中）
```json
{
  "session_id": "abc-123-def",
  "structure_info": {...}
}
```

**步骤3**: 转换为石墨
```bash
curl -X POST http://localhost:8000/api/structures/abc-123-def/modify \
-H "Content-Type: application/json" \
-d '{
  "operation": "replace_atoms",
  "parameters": {
    "symbols": ["C", "C", "C", "C"],
    "positions": [
      [0.0, 0.0, 0.0],
      [1.42, 0.0, 0.0],
      [0.71, 1.23, 0.0],
      [2.13, 1.23, 0.0]
    ],
    "cell": [
      [2.84, 0.0, 0.0],
      [0.0, 2.46, 0.0],
      [0.0, 0.0, 3.35]
    ]
  }
}'
```

### 2. 结构旋转
```bash
curl -X POST http://localhost:8000/api/structures/{session_id}/modify \
-H "Content-Type: application/json" \
-d '{
  "operation": "rotate",
  "parameters": {
    "angle": 45,
    "axis": [0, 0, 1]
  }
}'
```

### 3. 创建超胞
```bash
curl -X POST http://localhost:8000/api/structures/{session_id}/modify \
-H "Content-Type: application/json" \
-d '{
  "operation": "supercell",
  "parameters": {
    "size": [3, 3, 1]
  }
}'
```

## 支持的结构类型

### 金属
- **铜(Cu)**: FCC结构
- **铁(Fe)**: BCC结构
- **锌(Zn)**: HCP结构
- **铝(Al)**: FCC结构

### 半导体
- **硅(Si)**: 钻石结构
- **锗(Ge)**: 钻石结构
- **砷化镓(GaAs)**: 闪锌矿结构

### 分子
- **水(H2O)**: 分子结构
- **甲烷(CH4)**: 分子结构
- **苯(C6H6)**: 分子结构

### 表面
- **Cu(111)**: FCC(111)表面
- **Si(100)**: 钻石(100)表面
- **Fe(110)**: BCC(110)表面

## 修改操作类型

| 操作 | 说明 | 参数示例 |
|------|------|----------|
| `rotate` | 旋转结构 | `{"angle": 45, "axis": [0,0,1]}` |
| `translate` | 平移结构 | `{"vector": [1,0,0]}` |
| `scale` | 缩放结构 | `{"factor": 1.1}` |
| `supercell` | 创建超胞 | `{"size": [2,2,2]}` |
| `modify_cell` | 修改晶胞 | `{"cell": [[a,0,0],[0,b,0],[0,0,c]]}` |
| `modify_positions` | 修改原子位置 | `{"positions": [[x,y,z],...]}` |
| `replace_atoms` | 完全替换原子 | `{"symbols": [...], "positions": [...]}` |
| `add_atom` | 添加原子 | `{"symbol": "H", "position": [0,0,0]}` |
| `remove_atoms` | 删除原子 | `{"indices": [0,1,2]}` |
| `change_species` | 改变原子种类 | `{"indices": [0], "symbols": ["Fe"]}` |

## 常见问题

### Q: 端口被占用怎么办？
```bash
# 查看占用进程
lsof -ti:8000,8001

# 杀死进程
kill $(lsof -ti:8000,8001)

# 或使用不同端口
python server/main.py --port 8002 --websocket-port 8003
```

### Q: Redis连接失败？
```bash
# 系统自动使用内存模拟，无需担心
# 如需真实Redis:
redis-server

# 或使用Docker
docker run -d -p 6379:6379 redis:alpine
```

### Q: 前端连接不上后端？
检查前端配置文件 `client/.env`:
```
REACT_APP_API_BASE_URL=http://localhost:8000
REACT_APP_WEBSOCKET_URL=ws://localhost:8001
```

### Q: 3D结构不显示？
1. 确保使用现代浏览器（Chrome/Firefox/Safari）
2. 检查浏览器控制台错误信息
3. 尝试刷新页面

## 进阶使用

### 批量操作脚本
```python
import requests

base_url = "http://localhost:8000/api"

# 创建多个结构
structures = []
for element in ["Cu", "Al", "Fe"]:
    response = requests.post(f"{base_url}/structures", json={
        "type": "bulk",
        "formula": element,
        "structure": "fcc",
        "size": [2, 2, 2]
    })
    structures.append(response.json()["session_id"])

# 批量修改
for session_id in structures:
    requests.post(f"{base_url}/structures/{session_id}/modify", json={
        "operation": "rotate",
        "parameters": {"angle": 30, "axis": [1, 1, 1]}
    })
```

### 自定义计算器
```python
# 在server/core/ase_engine.py中添加新计算器
self.calculators['custom'] = YourCustomCalculator
```

### WebSocket实时监控
```javascript
const ws = new WebSocket('ws://localhost:8001');
ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    console.log('结构更新:', data);
};
```

## 下一步

- 查看 [API参考文档](API_REFERENCE.md) 了解完整API
- 查看 [LLM训练指南](LLM_TRAINING_GUIDE.md) 进行模型微调
- 查看 [架构文档](ARCHITECTURE.md) 了解系统设计
- 查看 `examples/` 目录获取更多示例代码
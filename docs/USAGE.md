# ASE MCP Server 使用指南

## 🚀 快速开始

### 1. 环境准备

```bash
# 克隆项目
git clone <repo-url>
cd ASE_MCP

# 安装依赖
./scripts/start.sh install

# 启动Redis（如果未运行）
redis-server
```

### 2. 启动服务

#### 方式一：完整启动（推荐）
```bash
./scripts/start.sh start
```

访问：
- Web界面: http://localhost:3000
- API文档: http://localhost:8000/docs
- WebSocket: ws://localhost:8001

#### 方式二：Docker启动
```bash
./scripts/start.sh docker-build
./scripts/start.sh docker-start
```

#### 方式三：仅MCP服务器
```bash
./scripts/start.sh mcp-only
```

## 🛠 MCP工具使用

### 创建结构

```python
# 创建铜的FCC结构
create_structure(
    type="bulk",
    formula="Cu",
    crystal_structure="fcc",
    size=[2, 2, 2]
)

# 创建水分子
create_structure(
    type="molecule",
    formula="H2O"
)

# 创建表面
create_structure(
    type="surface",
    formula="Cu",
    crystal_structure="fcc",
    size=[3, 3]
)
```

### 修改结构

```python
# 旋转结构
modify_structure(
    session_id="your-session-id",
    operation="rotate",
    parameters={
        "axis": [0, 0, 1],
        "angle": 45
    }
)

# 平移结构
modify_structure(
    session_id="your-session-id",
    operation="translate",
    parameters={
        "vector": [1, 2, 3]
    }
)

# 创建超胞
modify_structure(
    session_id="your-session-id",
    operation="supercell",
    parameters={
        "size": [2, 2, 2]
    }
)
```

### 计算属性

```python
# 计算能量
calculate_properties(
    session_id="your-session-id",
    properties=["energy"]
)

# 计算能量和力
calculate_properties(
    session_id="your-session-id",
    properties=["energy", "forces"]
)
```

### 优化结构

```python
optimize_structure(
    session_id="your-session-id",
    calculator="emt",
    fmax=0.01,
    steps=100
)
```

### 预览和保存

```python
# 预览结构
preview_structure(
    session_id="your-session-id",
    format="json"  # 或 "cif", "xyz"
)

# 保存结构
save_structure(
    session_id="your-session-id",
    filename="my_structure.cif",
    format="cif"
)
```

### 会话管理

```python
# 列出会话
list_sessions(limit=20, offset=0)

# 获取会话信息
get_session_info(session_id="your-session-id")

# 撤销操作
undo_operation(session_id="your-session-id")

# 重做操作
redo_operation(session_id="your-session-id")

# 删除会话
delete_session(session_id="your-session-id")
```

## 🌐 Web界面使用

### 会话管理
1. **创建会话**: 点击"新建"按钮，填写会话信息
2. **选择会话**: 点击会话列表中的会话进行切换
3. **删除会话**: 点击会话右侧的删除按钮

### 结构创建
1. 在控制面板中选择"创建结构"
2. 选择结构类型（块体/分子/表面/纳米粒子）
3. 填写化学式和参数
4. 点击"创建结构"

### 结构修改
1. 选择包含结构的会话
2. 在"修改结构"面板中选择操作类型
3. 设置操作参数
4. 点击"应用修改"

### 3D可视化
- **旋转**: 鼠标左键拖拽
- **缩放**: 鼠标滚轮
- **平移**: 鼠标右键拖拽
- **选择原子**: 点击原子球体
- **显示设置**: 调整右侧面板的显示选项

### 计算和分析
1. 选择要计算的属性类型
2. 点击相应的计算按钮
3. 查看计算结果

## 📡 WebSocket实时通信

### 连接WebSocket
```javascript
const ws = new WebSocket('ws://localhost:8001');

ws.onopen = () => {
    console.log('WebSocket连接成功');
};

ws.onmessage = (event) => {
    const message = JSON.parse(event.data);
    console.log('收到消息:', message);
};
```

### 订阅会话更新
```javascript
// 订阅会话
ws.send(JSON.stringify({
    type: 'subscribe',
    session_id: 'your-session-id'
}));

// 取消订阅
ws.send(JSON.stringify({
    type: 'unsubscribe',
    session_id: 'your-session-id'
}));
```

### 消息类型

#### 结构更新通知
```javascript
{
    type: 'structure_update',
    session_id: 'uuid',
    data: {
        structure: {...},        // 结构数据
        structure_info: {...},   // 结构信息
        operation: {...},        // 操作信息
        timestamp: 'ISO-8601'
    }
}
```

#### 属性更新通知
```javascript
{
    type: 'property_update',
    session_id: 'uuid',
    data: {
        properties: {...},       // 计算的属性
        timestamp: 'ISO-8601'
    }
}
```

## 🐳 Docker部署

### 构建和启动
```bash
# 构建镜像
docker-compose build

# 启动服务
docker-compose up -d

# 查看日志
docker-compose logs -f

# 停止服务
docker-compose down
```

### 环境变量配置
```bash
# .env文件
REDIS_URL=redis://redis:6379
WEB_HOST=0.0.0.0
WEB_PORT=8000
WEBSOCKET_PORT=8001
REACT_APP_API_URL=http://localhost:8000
REACT_APP_WS_URL=ws://localhost:8001
```

## 🔧 配置选项

### 服务器配置
- `REDIS_URL`: Redis连接URL
- `WEB_HOST`: Web服务器绑定地址
- `WEB_PORT`: Web服务器端口
- `WEBSOCKET_PORT`: WebSocket服务器端口
- `ENABLE_MCP`: 是否启用MCP服务器
- `ENABLE_WEB`: 是否启用Web服务器

### 会话配置
- 会话超时时间: 3600秒（1小时）
- 历史记录限制: 50条
- 最大重连尝试: 5次

## 🧪 测试

```bash
# 运行所有测试
./scripts/start.sh test

# 运行特定测试
pytest tests/test_ase_engine.py -v

# 运行覆盖率测试
pytest tests/ --cov=server --cov-report=html
```

## ❓ 常见问题

### Q: Redis连接失败
A: 确保Redis服务已启动，检查连接URL是否正确

### Q: WebSocket连接断开
A: 检查网络连接，服务器会自动尝试重连

### Q: 结构创建失败
A: 检查化学式是否正确，参数是否在有效范围内

### Q: 计算器错误
A: 目前仅支持EMT计算器，后续会添加更多计算器

### Q: 内存使用过多
A: 定期清理过期会话，限制结构大小

## 📞 技术支持

如有问题，请：
1. 查看日志文件: `ase_mcp.log`
2. 检查服务器状态: http://localhost:8000/health
3. 提交Issue到GitHub仓库
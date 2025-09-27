# ASE MCP Server 安装和部署指南

## 📋 系统要求

### 基础要求
- **Python**: 3.9+ (推荐 3.11)
- **Node.js**: 16+ (推荐 18)
- **Redis**: 6+ (推荐 7)
- **操作系统**: Linux/macOS/Windows

### 硬件要求
- **内存**: 最小 4GB, 推荐 8GB+
- **存储**: 最小 5GB 可用空间
- **CPU**: 最小 2核心, 推荐 4核心+

## 🚀 快速安装

### 方式一：自动安装脚本
```bash
# 下载并运行安装脚本
curl -sSL https://raw.githubusercontent.com/your-repo/ASE_MCP/main/scripts/install.sh | bash

# 或者克隆仓库
git clone https://github.com/your-repo/ASE_MCP.git
cd ASE_MCP
./scripts/start.sh install
```

### 方式二：手动安装

#### 1. 克隆项目
```bash
git clone https://github.com/your-repo/ASE_MCP.git
cd ASE_MCP
```

#### 2. 创建Python虚拟环境
```bash
python3 -m venv venv
source venv/bin/activate  # Linux/macOS
# 或
venv\Scripts\activate     # Windows
```

#### 3. 安装Python依赖
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

#### 4. 安装前端依赖
```bash
cd client
npm install
cd ..
```

#### 5. 启动Redis
```bash
# Linux (使用包管理器)
sudo systemctl start redis

# macOS (使用Homebrew)
brew services start redis

# Windows (使用WSL或直接下载)
redis-server

# Docker
docker run -d -p 6379:6379 redis:7-alpine
```

## 🐳 Docker 部署（推荐）

### 使用 Docker Compose
```bash
# 克隆项目
git clone https://github.com/your-repo/ASE_MCP.git
cd ASE_MCP

# 构建并启动
docker-compose up -d

# 查看日志
docker-compose logs -f

# 停止服务
docker-compose down
```

### 手动 Docker 部署
```bash
# 构建镜像
docker build -f Dockerfile.server -t ase-mcp-server .
docker build -f Dockerfile.client -t ase-mcp-client .

# 启动Redis
docker run -d --name redis -p 6379:6379 redis:7-alpine

# 启动服务器
docker run -d --name ase-server --link redis -p 8000:8000 -p 8001:8001 ase-mcp-server

# 启动客户端
docker run -d --name ase-client -p 3000:3000 ase-mcp-client
```

## ⚙️ 配置

### 环境变量配置
```bash
# 复制配置文件模板
cp .env.example .env

# 编辑配置文件
vim .env
```

### 关键配置项
```bash
# Redis配置
REDIS_URL=redis://localhost:6379

# 服务器配置
WEB_HOST=0.0.0.0
WEB_PORT=8000
WEBSOCKET_PORT=8001

# 日志配置
LOG_LEVEL=INFO
LOG_FILE=ase_mcp.log

# 安全配置
SECRET_KEY=your-secret-key-here
```

### MCP客户端配置
```json
// 添加到你的MCP客户端配置中
{
  "mcpServers": {
    "ase-mcp": {
      "command": "python",
      "args": ["server/main.py", "--mcp-only"],
      "cwd": "/path/to/ASE_MCP",
      "env": {
        "PYTHONPATH": ".",
        "REDIS_URL": "redis://localhost:6379"
      }
    }
  }
}
```

## 🔧 启动服务

### 开发模式
```bash
# 完整服务启动（推荐）
./scripts/start.sh start

# 仅MCP服务器
./scripts/start.sh mcp-only

# 仅Web服务器
./scripts/start.sh web-only
```

### 生产模式
```bash
# 使用Docker Compose
docker-compose up -d

# 或使用systemd服务
sudo systemctl enable ase-mcp
sudo systemctl start ase-mcp
```

## 🧪 验证安装

### 1. 检查服务状态
```bash
# 健康检查
curl http://localhost:8000/health

# WebSocket连接测试
curl -i -N -H "Connection: Upgrade" -H "Upgrade: websocket" \
     -H "Sec-WebSocket-Key: SGVsbG8sIHdvcmxkIQ==" \
     -H "Sec-WebSocket-Version: 13" \
     http://localhost:8001/
```

### 2. 运行示例
```bash
# Python API示例
python examples/basic_usage.py

# 运行测试
./scripts/start.sh test
```

### 3. 访问Web界面
- **前端界面**: http://localhost:3000
- **API文档**: http://localhost:8000/docs
- **WebSocket**: ws://localhost:8001

## 🔍 故障排除

### 常见问题

#### Redis连接失败
```bash
# 检查Redis是否运行
redis-cli ping

# 检查端口是否被占用
netstat -tulpn | grep 6379

# 重启Redis
sudo systemctl restart redis
```

#### 端口冲突
```bash
# 检查端口占用
netstat -tulpn | grep 8000
netstat -tulpn | grep 8001

# 修改配置文件中的端口
export WEB_PORT=8080
export WEBSOCKET_PORT=8081
```

#### Python依赖问题
```bash
# 升级pip
pip install --upgrade pip

# 清理pip缓存
pip cache purge

# 重新安装依赖
pip install -r requirements.txt --force-reinstall
```

#### 前端构建失败
```bash
# 清理node_modules
cd client
rm -rf node_modules package-lock.json
npm install

# 检查Node.js版本
node --version
npm --version
```

### 日志分析
```bash
# 查看应用日志
tail -f ase_mcp.log

# 查看Docker日志
docker-compose logs -f ase-server

# 查看系统日志
journalctl -u ase-mcp -f
```

## 🔧 性能优化

### 生产环境优化
```bash
# 设置生产环境变量
export DEBUG=false
export LOG_LEVEL=WARNING
export ENABLE_PROFILING=false

# 使用生产级别的WSGI服务器
pip install gunicorn
gunicorn -w 4 -k uvicorn.workers.UvicornWorker server.main:app
```

### Redis优化
```bash
# 增加Redis内存限制
redis-cli CONFIG SET maxmemory 1gb
redis-cli CONFIG SET maxmemory-policy allkeys-lru

# 启用RDB持久化
redis-cli CONFIG SET save "900 1 300 10 60 10000"
```

### 系统资源监控
```bash
# 安装监控工具
pip install psutil htop

# 查看系统资源
htop
iostat -x 1
```

## 🔄 更新和维护

### 更新应用
```bash
# 拉取最新代码
git pull origin main

# 更新依赖
pip install -r requirements.txt --upgrade
cd client && npm update && cd ..

# 重启服务
./scripts/start.sh stop
./scripts/start.sh start
```

### 数据备份
```bash
# 备份Redis数据
redis-cli BGSAVE

# 备份应用数据
tar -czf backup-$(date +%Y%m%d).tar.gz data/ ase_mcp.log

# 自动备份脚本
crontab -e
# 添加: 0 2 * * * /path/to/backup.sh
```

### 日志轮转
```bash
# 配置logrotate
sudo vim /etc/logrotate.d/ase-mcp

# 添加配置
/path/to/ASE_MCP/ase_mcp.log {
    daily
    rotate 30
    compress
    delaycompress
    missingok
    notifempty
    create 644 user group
}
```

## 📞 技术支持

### 获取帮助
- **文档**: 查看 `USAGE.md` 了解详细用法
- **示例**: 运行 `examples/` 目录下的示例代码
- **Issue**: 在GitHub仓库提交问题
- **讨论**: 参与GitHub Discussions

### 贡献代码
1. Fork项目仓库
2. 创建功能分支: `git checkout -b feature/new-feature`
3. 提交更改: `git commit -am 'Add new feature'`
4. 推送分支: `git push origin feature/new-feature`
5. 提交Pull Request

### 联系方式
- **Email**: support@ase-mcp.org
- **Discord**: https://discord.gg/ase-mcp
- **文档站**: https://docs.ase-mcp.org
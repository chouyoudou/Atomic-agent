#!/bin/bash
# ASE MCP 前端启动脚本

echo "启动ASE MCP前端开发服务器..."
echo "确保后端API服务器正在运行: ./start_api_only.sh"
echo "==============================================="

cd "$(dirname "$0")/client"

# 检查是否安装了依赖
if [ ! -d "node_modules" ]; then
    echo "安装前端依赖..."
    npm install
fi

# 启动开发服务器
npm start
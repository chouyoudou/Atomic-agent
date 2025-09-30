#!/bin/bash
# ASE MCP API-Only 启动脚本

echo "启动ASE MCP API服务器（纯后端模式）..."
echo "前端请单独启动: cd client && npm start"
echo "=========================================="

cd "$(dirname "$0")"
python server/main.py --api-only "$@"
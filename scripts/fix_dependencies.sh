#!/bin/bash

# 修复依赖问题脚本

set -e

echo "🔧 修复Python依赖..."

# 卸载可能有问题的aioredis版本
pip uninstall aioredis -y || true

# 安装兼容版本
pip install "aioredis>=2.0.1,<2.1.0"

echo "✅ Python依赖修复完成"

echo "🔧 修复前端依赖..."

cd client

# 修复npm安全漏洞
npm audit fix || true

# 更新过时的依赖
npm update

echo "✅ 前端依赖修复完成"

cd ..

echo "🎉 所有依赖修复完成！"
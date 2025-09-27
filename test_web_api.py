#!/usr/bin/env python3
"""
直接通过Web API测试实时监控
"""

import asyncio
import websockets
import json
import requests
import time

async def test_websocket_and_api():
    print("🚀 测试Web API和WebSocket实时监控")
    print("📱 正在连接WebSocket...")

    try:
        # 连接WebSocket
        uri = "ws://localhost:8001"
        async with websockets.connect(uri) as websocket:
            print("✅ WebSocket连接成功!")

            # 监听WebSocket消息
            async def listen_websocket():
                try:
                    while True:
                        message = await websocket.recv()
                        data = json.loads(message)
                        print(f"📨 WebSocket消息: {data}")
                except Exception as e:
                    print(f"WebSocket监听错误: {e}")

            # 启动WebSocket监听任务
            listen_task = asyncio.create_task(listen_websocket())

            # 模拟通过API创建会话和结构
            print("\n🔬 通过REST API创建结构...")

            # 这里我们通过HTTP请求直接测试
            base_url = "http://localhost:8000"

            # 检查API健康状态
            response = requests.get(f"{base_url}/health")
            print(f"📊 健康检查: {response.json()}")

            # 获取会话列表
            response = requests.get(f"{base_url}/api/sessions")
            sessions_data = response.json()
            print(f"📋 当前会话: {len(sessions_data.get('sessions', []))} 个")

            print("\n💡 现在你需要在另一个终端运行 MCP 客户端来生成结构:")
            print("   python simple_test.py")
            print("\n🔄 监听WebSocket消息中...")

            # 持续监听10秒
            try:
                await asyncio.wait_for(listen_task, timeout=60)
            except asyncio.TimeoutError:
                print("⏰ 监听超时")

    except Exception as e:
        print(f"❌ 连接失败: {e}")

if __name__ == "__main__":
    asyncio.run(test_websocket_and_api())
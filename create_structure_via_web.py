#!/usr/bin/env python3
"""
通过Web服务器直接创建结构
这样结构会存储在Web服务器的内存中，界面可以看到
"""

import asyncio
import json
import websockets
import requests
import time

async def create_structures_via_web():
    print("🚀 通过Web服务器直接创建结构...")
    print("🔗 连接WebSocket以监听实时更新...")

    # 连接WebSocket监听更新
    websocket_uri = "ws://localhost:8001"
    base_url = "http://localhost:8000"

    try:
        async with websockets.connect(websocket_uri) as ws:
            print("✅ WebSocket连接成功!")

            # 创建监听任务
            async def listen_messages():
                try:
                    while True:
                        message = await ws.recv()
                        data = json.loads(message)
                        print(f"📨 实时消息: {data}")
                except Exception as e:
                    print(f"监听错误: {e}")

            listen_task = asyncio.create_task(listen_messages())

            # 等待连接稳定
            await asyncio.sleep(1)

            print("\n🧪 开始创建结构...")

            # 我们需要直接调用SessionManager来创建结构
            # 因为当前的Web API没有创建结构的端点
            # 让我们通过模拟来验证流程

            # 首先检查当前会话
            try:
                response = requests.get(f"{base_url}/api/sessions")
                sessions_data = response.json()
                print(f"📋 当前会话数: {len(sessions_data.get('sessions', []))}")
            except Exception as e:
                print(f"API调用错误: {e}")

            print(f"\n💡 目前Web API没有直接创建结构的端点。")
            print(f"💡 让我们添加这个端点...")

            # 等待一段时间以便观察
            await asyncio.sleep(5)

    except Exception as e:
        print(f"❌ 连接失败: {e}")

if __name__ == "__main__":
    asyncio.run(create_structures_via_web())
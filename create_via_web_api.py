#!/usr/bin/env python3
"""
通过Web API直接创建结构
这样结构会在Web服务器内存中，界面能立即看到
"""

import asyncio
import json
import requests
import websockets
import time

async def create_structures_via_api():
    print("🚀 通过Web API直接创建结构...")
    print("🌐 确保你已经打开了 http://localhost:8000")
    print("=" * 50)

    base_url = "http://localhost:8000"
    websocket_uri = "ws://localhost:8001"

    # 先检查服务器状态
    try:
        response = requests.get(f"{base_url}/health", timeout=5)
        print(f"✅ 服务器健康状态: {response.json()}")
    except Exception as e:
        print(f"❌ 无法连接到Web服务器: {e}")
        print("请先运行: python server/main.py")
        return

    # 连接WebSocket监听实时更新
    try:
        async with websockets.connect(websocket_uri) as ws:
            print("✅ WebSocket连接成功!")

            # 启动WebSocket监听任务
            async def listen_messages():
                try:
                    while True:
                        message = await ws.recv()
                        data = json.loads(message)
                        print(f"📨 实时消息: {data.get('type')} - {data.get('data', {}).get('message', '')}")

                        # 如果是结构更新，显示详细信息
                        if data.get('type') == 'structure_update':
                            structure_info = data.get('data', {}).get('structure_info', {})
                            print(f"   📊 结构信息: {structure_info.get('total_atoms', 0)} 原子")

                except Exception as e:
                    print(f"WebSocket监听错误: {e}")

            listen_task = asyncio.create_task(listen_messages())
            await asyncio.sleep(1)  # 等待连接稳定

            print("\n🧪 开始创建结构...")

            # 定义要创建的结构
            structures = [
                {
                    "type": "bulk",
                    "formula": "Cu",
                    "crystal_structure": "fcc",
                    "size": [2, 2, 2]
                },
                {
                    "type": "bulk",
                    "formula": "Al",
                    "crystal_structure": "fcc",
                    "size": [3, 3, 3]
                },
                {
                    "type": "molecule",
                    "formula": "H2O"
                }
            ]

            session_ids = []

            for i, struct in enumerate(structures):
                print(f"\n🔬 [{i+1}/3] 创建 {struct['formula']} 结构...")

                try:
                    # 通过Web API创建结构
                    response = requests.post(
                        f"{base_url}/api/structures",
                        json=struct,
                        headers={"Content-Type": "application/json"},
                        timeout=10
                    )

                    if response.status_code == 200:
                        data = response.json()
                        session_id = data['session_id']
                        session_ids.append(session_id)

                        print(f"   ✅ 创建成功! 会话ID: {session_id[:8]}...")
                        print(f"   📊 原子数: {data['structure_info']['total_atoms']}")
                        print(f"   💡 现在检查浏览器，应该能看到这个结构!")

                        # 等待WebSocket消息传播
                        await asyncio.sleep(3)

                    else:
                        print(f"   ❌ 创建失败: {response.status_code} {response.text}")

                except Exception as e:
                    print(f"   ❌ 请求失败: {e}")

            # 修改第一个结构
            if session_ids:
                print(f"\n🔄 旋转第一个结构...")
                try:
                    modify_data = {
                        "operation": "rotate",
                        "parameters": {
                            "angle": 45,
                            "axis": [0, 0, 1]
                        }
                    }

                    response = requests.post(
                        f"{base_url}/api/structures/{session_ids[0]}/modify",
                        json=modify_data,
                        headers={"Content-Type": "application/json"},
                        timeout=10
                    )

                    if response.status_code == 200:
                        print("   ✅ 旋转成功!")
                    else:
                        print(f"   ❌ 旋转失败: {response.status_code} {response.text}")

                except Exception as e:
                    print(f"   ❌ 旋转请求失败: {e}")

            print(f"\n🎉 完成! 创建了 {len(session_ids)} 个结构")
            print("💡 现在检查 http://localhost:8000 应该看到:")
            print("   - 左侧会话列表显示所有结构")
            print("   - 右侧实时消息显示所有操作")
            print("   - WebSocket状态显示'已连接'")

            # 验证会话列表
            try:
                response = requests.get(f"{base_url}/api/sessions")
                sessions_data = response.json()
                total_sessions = len(sessions_data.get('sessions', []))
                print(f"📋 服务器确认: {total_sessions} 个活跃会话")
            except Exception as e:
                print(f"❌ 验证会话列表失败: {e}")

            print("\n🔄 保持连接5秒观察实时更新...")
            try:
                await asyncio.wait_for(listen_task, timeout=5)
            except asyncio.TimeoutError:
                print("⏰ 监听完成")

    except Exception as e:
        print(f"❌ WebSocket连接失败: {e}")
        print("💡 提示: WebSocket失败不影响结构创建，请直接检查浏览器")

        # 即使WebSocket失败，也可以通过API创建结构
        print("\n🧪 继续通过API创建结构...")

        structures = [
            {
                "type": "bulk",
                "formula": "Cu",
                "crystal_structure": "fcc",
                "size": [2, 2, 2]
            }
        ]

        for struct in structures:
            try:
                response = requests.post(
                    f"{base_url}/api/structures",
                    json=struct,
                    headers={"Content-Type": "application/json"},
                    timeout=10
                )

                if response.status_code == 200:
                    data = response.json()
                    print(f"✅ 创建成功! 会话ID: {data['session_id'][:8]}...")
                    print("💡 现在检查浏览器应该能看到结构!")
                else:
                    print(f"❌ 创建失败: {response.status_code}")

            except Exception as e:
                print(f"❌ API请求失败: {e}")

if __name__ == "__main__":
    asyncio.run(create_structures_via_api())
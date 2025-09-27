#!/usr/bin/env python3
"""
快速演示 - 生成几个简单结构供监控
"""

import asyncio
import json
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def quick_demo():
    print("🚀 快速生成演示结构...")
    print("🌐 请立即打开 http://localhost:8000 监控!")
    print("=" * 50)

    server_params = StdioServerParameters(
        command="python",
        args=["server/main.py", "--mcp-only"],
        env=None
    )

    try:
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                print("✅ MCP连接成功")

                # 生成3个简单的结构
                structures = [
                    {"type": "bulk", "formula": "Cu", "crystal_structure": "fcc", "size": [2,2,2]},
                    {"type": "bulk", "formula": "Al", "crystal_structure": "fcc", "size": [3,3,3]},
                    {"type": "molecule", "formula": "H2O"}
                ]

                session_ids = []

                for i, struct in enumerate(structures):
                    print(f"\n🔬 [{i+1}/3] 创建 {struct['formula']} 结构...")

                    result = await session.call_tool("create_structure", struct)

                    if result.isError:
                        print(f"   ❌ 失败: {result.error}")
                        continue

                    data = json.loads(result.content[0].text)
                    session_id = data['session_id']
                    session_ids.append(session_id)

                    print(f"   ✅ 成功! ID: {session_id[:8]}")
                    print(f"   📊 原子数: {data['structure_info']['total_atoms']}")

                    # 给时间让WebSocket传播消息
                    print("   ⏳ 等待WebSocket传播...")
                    await asyncio.sleep(3)

                # 修改第一个结构
                if session_ids:
                    print(f"\n🔄 旋转第一个结构...")
                    result = await session.call_tool("modify_structure", {
                        "session_id": session_ids[0],
                        "operation": "rotate",
                        "parameters": {"angle": 45, "axis": [0, 0, 1]}
                    })

                    if result.isError:
                        print(f"   ❌ 旋转失败: {result.error}")
                    else:
                        print("   ✅ 旋转成功!")

                print(f"\n🎉 演示完成!")
                print("💡 现在检查 http://localhost:8000 应该看到:")
                print("   - 左侧: 3个会话")
                print("   - 右侧: 实时消息显示所有操作")
                print("   - WebSocket状态: 已连接")

                print("\n🔄 保持连接10秒钟...")
                await asyncio.sleep(10)

    except Exception as e:
        print(f"❌ 演示失败: {e}")

if __name__ == "__main__":
    asyncio.run(quick_demo())
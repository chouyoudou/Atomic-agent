#!/usr/bin/env python3
"""
简单的MCP客户端测试
"""

import asyncio
import json
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def simple_test():
    print("🧪 快速MCP测试...")

    server_params = StdioServerParameters(
        command="python",
        args=["server/main.py", "--mcp-only"],
        env=None
    )

    try:
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                print("✅ MCP连接成功")
                await session.initialize()

                # 创建结构
                print("🔬 创建铜晶体...")
                result = await session.call_tool("create_structure", {
                    "type": "bulk",
                    "formula": "Cu",
                    "crystal_structure": "fcc",
                    "size": [2, 2, 2]
                })

                if result.isError:
                    print(f"❌ 失败: {result.error}")
                else:
                    data = json.loads(result.content[0].text)
                    session_id = data['session_id']
                    print(f"✅ 成功创建! 会话: {session_id}")
                    print(f"   原子数: {data['structure_info']['total_atoms']}")

                    print("\n🔄 旋转结构...")
                    result2 = await session.call_tool("modify_structure", {
                        "session_id": session_id,
                        "operation": "rotate",
                        "parameters": {"angle": 45, "axis": [0, 0, 1]}
                    })

                    if result2.isError:
                        print(f"❌ 旋转失败: {result2.error}")
                    else:
                        print("✅ 旋转成功!")

                print("\n🎉 测试完成! 现在请检查:")
                print("  Web界面: http://localhost:8000")
                print("  应该能看到结构和WebSocket消息!")

    except Exception as e:
        print(f"❌ 测试失败: {e}")

if __name__ == "__main__":
    asyncio.run(simple_test())
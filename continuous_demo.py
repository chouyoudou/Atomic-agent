#!/usr/bin/env python3
"""
持续的MCP结构生成演示
模拟AI代理持续生成和修改结构的过程
"""

import asyncio
import json
import random
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

class StructureGenerator:
    def __init__(self):
        self.materials = ["Cu", "Al", "Fe", "Ni", "Au", "Ag"]
        self.crystal_structures = ["fcc", "bcc", "hcp"]
        self.sizes = [[2,2,2], [3,3,3], [2,3,2], [4,2,3]]
        self.operations = ["rotate", "translate", "scale"]

    async def continuous_generation(self):
        """持续生成结构的演示"""

        print("🚀 启动持续结构生成演示...")
        print("🌐 请在浏览器中打开 http://localhost:8000 监控")
        print("=" * 60)

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

                    session_ids = []

                    for i in range(5):  # 生成5个不同的结构
                        print(f"\n🔬 [{i+1}/5] 生成新结构...")

                        # 随机选择材料和参数
                        material = random.choice(self.materials)
                        crystal = random.choice(self.crystal_structures)
                        size = random.choice(self.sizes)

                        print(f"   材料: {material}, 结构: {crystal}, 尺寸: {size}")

                        # 创建结构
                        result = await session.call_tool("create_structure", {
                            "type": "bulk",
                            "formula": material,
                            "crystal_structure": crystal,
                            "size": size
                        })

                        if result.isError:
                            print(f"   ❌ 创建失败: {result.error}")
                            continue

                        data = json.loads(result.content[0].text)
                        session_id = data['session_id']
                        session_ids.append(session_id)

                        print(f"   ✅ 创建成功! 会话: {session_id[:8]}...")
                        print(f"   📊 原子数: {data['structure_info']['total_atoms']}")

                        # 等待WebSocket传播
                        await asyncio.sleep(3)

                        # 随机修改结构
                        if random.random() > 0.3:  # 70%概率修改
                            operation = random.choice(self.operations)
                            print(f"   🔄 执行操作: {operation}")

                            if operation == "rotate":
                                params = {
                                    "angle": random.randint(15, 90),
                                    "axis": [random.random(), random.random(), random.random()]
                                }
                            elif operation == "translate":
                                params = {
                                    "vector": [random.uniform(-2, 2) for _ in range(3)]
                                }
                            else:  # scale
                                params = {
                                    "factor": random.uniform(0.8, 1.5)
                                }

                            mod_result = await session.call_tool("modify_structure", {
                                "session_id": session_id,
                                "operation": operation,
                                "parameters": params
                            })

                            if mod_result.isError:
                                print(f"   ❌ 修改失败: {mod_result.error}")
                            else:
                                print(f"   ✅ {operation} 操作完成!")

                        await asyncio.sleep(4)  # 间隔4秒

                    print(f"\n🎉 演示完成! 总共创建了 {len(session_ids)} 个结构")
                    print("💡 在Web界面中你应该能看到:")
                    print("   - 会话列表中的所有结构")
                    print("   - 实时WebSocket消息")
                    print("   - 结构详细信息")

                    # 获取会话列表验证
                    print("\n📋 验证会话列表...")
                    list_result = await session.call_tool("list_sessions", {})
                    if not list_result.isError:
                        sessions_data = json.loads(list_result.content[0].text)
                        print(f"   服务器确认: {len(sessions_data.get('sessions', []))} 个活跃会话")

                    print("\n🔄 保持连接状态，按Ctrl+C停止...")
                    try:
                        while True:
                            await asyncio.sleep(10)
                    except KeyboardInterrupt:
                        print("\n👋 演示停止")

        except Exception as e:
            print(f"❌ 演示失败: {e}")
            import traceback
            traceback.print_exc()

async def main():
    generator = StructureGenerator()
    await generator.continuous_generation()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 用户中断演示")
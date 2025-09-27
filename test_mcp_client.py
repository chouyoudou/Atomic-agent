#!/usr/bin/env python3
"""
MCP客户端测试脚本
用于测试ASE MCP服务器功能并监控WebSocket实时更新
"""

import asyncio
import json
import sys
import time
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def test_mcp_structure_generation():
    """测试MCP结构生成功能"""

    print("🚀 启动MCP客户端测试...")
    print("=" * 60)

    # MCP服务器参数
    server_params = StdioServerParameters(
        command="python",
        args=["server/main.py", "--mcp-only"],
        env=None
    )

    try:
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                print("✅ MCP连接成功")

                # 初始化MCP会话
                await session.initialize()
                print("✅ MCP会话初始化完成")

                # 获取可用工具
                tools = await session.list_tools()
                print(f"📋 可用工具数量: {len(tools.tools)}")
                for tool in tools.tools:
                    print(f"  - {tool.name}: {tool.description}")

                print("\n" + "=" * 60)
                print("🧪 开始测试结构生成...")

                # 测试1: 创建晶体结构（会自动创建会话）
                print("\n🔬 1. 创建铜晶体结构...")
                create_structure_result = await session.call_tool(
                    "create_structure",
                    arguments={
                        "type": "bulk",
                        "formula": "Cu",
                        "crystal_structure": "fcc",
                        "size": [2, 2, 2]
                    }
                )

                if create_structure_result.isError:
                    print(f"❌ 创建结构失败: {create_structure_result.error}")
                    return
                else:
                    structure_data = json.loads(create_structure_result.content[0].text)
                    session_id = structure_data['session_id']
                    print(f"✅ 铜晶体结构创建成功!")
                    print(f"   - 会话ID: {session_id}")
                    print(f"   - 原子数量: {structure_data['structure_info']['total_atoms']}")
                    print(f"   - 化学式: {structure_data['structure_info']['formula']}")
                    if 'volume' in structure_data['structure_info']:
                        print(f"   - 体积: {structure_data['structure_info']['volume']:.2f} Ų")
                    print(f"   - 元素: {structure_data['structure_info'].get('unique_elements', [])}")

                # 等待一下让WebSocket传播消息
                print("\n⏳ 等待WebSocket消息传播...")
                await asyncio.sleep(2)

                # 测试2: 修改结构 - 旋转
                print("\n🔄 2. 旋转结构...")
                modify_result = await session.call_tool(
                    "modify_structure",
                    arguments={
                        "session_id": session_id,
                        "operation": "rotate",
                        "parameters": {
                            "angle": 45,
                            "axis": [0, 0, 1]
                        }
                    }
                )

                if modify_result.isError:
                    print(f"❌ 旋转结构失败: {modify_result.error}")
                else:
                    print("✅ 结构旋转成功!")

                await asyncio.sleep(2)

                # 测试3: 创建分子结构（新会话）
                print("\n🧬 3. 创建水分子...")
                water_result = await session.call_tool(
                    "create_structure",
                    arguments={
                        "type": "molecule",
                        "formula": "H2O"
                    }
                )

                if water_result.isError:
                    print(f"❌ 创建水分子失败: {water_result.error}")
                else:
                    water_data = json.loads(water_result.content[0].text)
                    print(f"✅ 水分子创建成功!")
                    print(f"   - 原子数量: {water_data['structure_info']['total_atoms']}")
                    print(f"   - 化学式: {water_data['structure_info']['formula']}")

                await asyncio.sleep(2)

                # 测试4: 创建表面结构（新会话）
                print("\n🏔️ 4. 创建铝表面...")
                surface_result = await session.call_tool(
                    "create_structure",
                    arguments={
                        "type": "surface",
                        "formula": "Al",
                        "miller_indices": [1, 1, 1],
                        "layers": 4
                    }
                )

                if surface_result.isError:
                    print(f"❌ 创建表面失败: {surface_result.error}")
                else:
                    surface_data = json.loads(surface_result.content[0].text)
                    print(f"✅ 铝表面创建成功!")
                    print(f"   - 原子数量: {surface_data['structure_info']['total_atoms']}")
                    print(f"   - 表面: Al({surface_data.get('surface_info', {}).get('miller_indices', '[1,1,1]')})")

                await asyncio.sleep(2)

                # 测试5: 计算属性（使用第一个session_id）
                print("\n🔍 5. 计算结构属性...")
                calc_result = await session.call_tool(
                    "calculate_properties",
                    arguments={
                        "session_id": session_id,
                        "properties": ["energy", "forces", "stress"]
                    }
                )

                if calc_result.isError:
                    print(f"❌ 计算属性失败: {calc_result.error}")
                else:
                    calc_data = json.loads(calc_result.content[0].text)
                    print(f"✅ 属性计算完成!")
                    if "properties" in calc_data:
                        props = calc_data["properties"]
                        print(f"   - 能量: {props.get('energy', 'N/A')} eV")
                        print(f"   - 受力: {len(props.get('forces', []))} 个原子")

                await asyncio.sleep(2)

                # 测试6: 获取会话信息
                print("\n📊 6. 获取会话信息...")
                session_info_result = await session.call_tool(
                    "get_session_info",
                    arguments={"session_id": session_id}
                )

                if session_info_result.isError:
                    print(f"❌ 获取会话信息失败: {session_info_result.error}")
                else:
                    session_info = json.loads(session_info_result.content[0].text)
                    print(f"✅ 会话信息获取成功!")
                    print(f"   - 会话ID: {session_info['session']['id']}")
                    print(f"   - 创建时间: {session_info['session']['created_at']}")
                    print(f"   - 修改时间: {session_info['session']['modified_at']}")
                    print(f"   - 历史记录: {len(session_info['session'].get('history', []))} 条")

                print("\n" + "=" * 60)
                print("🎉 MCP测试完成!")
                print("💡 现在请检查Web界面 http://localhost:8000 查看实时更新")
                print("🔄 WebSocket应该显示所有结构变化的实时消息")
                print("=" * 60)

    except Exception as e:
        print(f"❌ MCP测试失败: {e}")
        import traceback
        traceback.print_exc()

async def main():
    """主函数"""
    print("🧪 ASE MCP结构生成和实时监控测试")
    print("=" * 60)
    print("📌 确保ASE MCP服务器正在运行:")
    print("   ./scripts/start.sh start")
    print("📌 然后在浏览器中打开:")
    print("   http://localhost:8000")
    print("=" * 60)

    print("🚀 自动开始测试...")

    await test_mcp_structure_generation()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 测试被用户中断")
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        sys.exit(1)
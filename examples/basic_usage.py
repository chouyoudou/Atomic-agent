#!/usr/bin/env python3
"""
ASE MCP Server 基本用法示例
演示如何通过Python API使用MCP工具
"""

import asyncio
import json
from mcp.client.session import ClientSession
from mcp.client.stdio import stdio_client


async def basic_usage_example():
    """基本用法示例"""

    # 连接到MCP服务器
    async with stdio_client() as streams:
        async with ClientSession(streams[0], streams[1]) as session:

            # 获取可用工具
            tools = await session.list_tools()
            print("可用工具:")
            for tool in tools.tools:
                print(f"  - {tool.name}: {tool.description}")

            print("\n" + "="*50)

            # 1. 创建铜的FCC结构
            print("1. 创建铜的FCC结构...")
            result = await session.call_tool(
                "create_structure",
                {
                    "type": "bulk",
                    "formula": "Cu",
                    "crystal_structure": "fcc",
                    "size": [2, 2, 2]
                }
            )

            response = json.loads(result.content[0].text)
            if response["success"]:
                session_id = response["session_id"]
                print(f"✓ 结构创建成功，会话ID: {session_id}")
                print(f"  原子数: {response['structure_data']['total_atoms']}")
                print(f"  化学式: {response['structure_data']['formula']}")
            else:
                print(f"✗ 创建失败: {response['message']}")
                return

            # 2. 旋转结构
            print("\n2. 旋转结构45度...")
            result = await session.call_tool(
                "modify_structure",
                {
                    "session_id": session_id,
                    "operation": "rotate",
                    "parameters": {
                        "axis": [0, 0, 1],
                        "angle": 45
                    }
                }
            )

            response = json.loads(result.content[0].text)
            if response["success"]:
                print("✓ 结构旋转成功")
            else:
                print(f"✗ 旋转失败: {response['message']}")

            # 3. 计算能量
            print("\n3. 计算能量...")
            result = await session.call_tool(
                "calculate_properties",
                {
                    "session_id": session_id,
                    "properties": ["energy"]
                }
            )

            response = json.loads(result.content[0].text)
            if response["success"]:
                energy = response["properties"]["energy"]
                print(f"✓ 能量计算完成: {energy:.4f} eV")
            else:
                print(f"✗ 计算失败: {response['message']}")

            # 4. 预览结构
            print("\n4. 预览结构...")
            result = await session.call_tool(
                "preview_structure",
                {
                    "session_id": session_id,
                    "format": "json"
                }
            )

            response = json.loads(result.content[0].text)
            if response["success"]:
                structure_info = response["structure_data"]["structure_info"]
                print("✓ 结构信息:")
                print(f"  体积: {structure_info.get('cell_volume', 'N/A')} Ų")
                print(f"  质心: {structure_info.get('center_of_mass', 'N/A')}")
                print(f"  唯一元素: {structure_info.get('unique_elements', 'N/A')}")

            # 5. 保存结构
            print("\n5. 保存结构...")
            result = await session.call_tool(
                "save_structure",
                {
                    "session_id": session_id,
                    "filename": "data/structures/cu_fcc_example.cif",
                    "format": "cif"
                }
            )

            response = json.loads(result.content[0].text)
            if response["success"]:
                print(f"✓ 结构已保存到: {response['properties']['saved_path']}")
            else:
                print(f"✗ 保存失败: {response['message']}")

            # 6. 列出会话
            print("\n6. 列出所有会话...")
            result = await session.call_tool(
                "list_sessions",
                {"limit": 5}
            )

            response = json.loads(result.content[0].text)
            if response["success"]:
                print(f"✓ 找到 {len(response['sessions'])} 个会话")
                for sess in response["sessions"][:3]:
                    print(f"  - {sess['id'][:8]}... : {sess.get('metadata', {}).get('name', '未命名')}")


async def molecule_example():
    """分子结构示例"""

    async with stdio_client() as streams:
        async with ClientSession(streams[0], streams[1]) as session:

            print("\n" + "="*50)
            print("分子结构示例")
            print("="*50)

            # 创建水分子
            print("创建水分子...")
            result = await session.call_tool(
                "create_structure",
                {
                    "type": "molecule",
                    "formula": "H2O"
                }
            )

            response = json.loads(result.content[0].text)
            if response["success"]:
                session_id = response["session_id"]
                print(f"✓ 水分子创建成功")
                print(f"  原子数: {response['structure_data']['total_atoms']}")

                # 获取结构详细信息
                result = await session.call_tool(
                    "get_structure_info",
                    {"session_id": session_id}
                )

                response = json.loads(result.content[0].text)
                if response["success"]:
                    info = response["structure_info"]
                    print(f"  键连接数: {info.get('total_bonds', 0)}")
                    print(f"  最小距离: {info.get('min_distance', 'N/A')} Å")


async def surface_example():
    """表面结构示例"""

    async with stdio_client() as streams:
        async with ClientSession(streams[0], streams[1]) as session:

            print("\n" + "="*50)
            print("表面结构示例")
            print("="*50)

            # 创建Cu(111)表面
            print("创建Cu(111)表面...")
            result = await session.call_tool(
                "create_structure",
                {
                    "type": "surface",
                    "formula": "Cu",
                    "crystal_structure": "fcc",
                    "size": [3, 3]
                }
            )

            response = json.loads(result.content[0].text)
            if response["success"]:
                session_id = response["session_id"]
                print(f"✓ 表面创建成功")
                print(f"  原子数: {response['structure_data']['total_atoms']}")

                # 创建超胞
                print("创建2x2超胞...")
                result = await session.call_tool(
                    "modify_structure",
                    {
                        "session_id": session_id,
                        "operation": "supercell",
                        "parameters": {"size": [2, 2, 1]}
                    }
                )

                response = json.loads(result.content[0].text)
                if response["success"]:
                    print(f"✓ 超胞创建成功")
                    print(f"  新原子数: {response['structure_data']['total_atoms']}")


if __name__ == "__main__":
    print("ASE MCP Server 使用示例")
    print("请确保MCP服务器正在运行...")
    print("启动命令: python server/main.py --mcp-only")
    print()

    # 运行示例
    asyncio.run(basic_usage_example())
    asyncio.run(molecule_example())
    asyncio.run(surface_example())

    print("\n示例完成！")
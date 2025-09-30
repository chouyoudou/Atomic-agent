#!/usr/bin/env python3
"""
ASE MCP Server Basic Usage Examples
Demonstrates how to use MCP tools through Python API
"""

import asyncio
import json
from mcp.client.session import ClientSession
from mcp.client.stdio import stdio_client


async def basic_usage_example():
    """Basic usage examples"""

    # Connect to MCP server
    async with stdio_client() as streams:
        async with ClientSession(streams[0], streams[1]) as session:

            # Get available tools
            tools = await session.list_tools()
            print("Available tools:")
            for tool in tools.tools:
                print(f"  - {tool.name}: {tool.description}")

            print("\n" + "="*50)

            # 1. Create copper FCC structure
            print("1. Creating copper FCC structure...")
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
                print(f"✓ Structure created successfully, session ID: {session_id}")
                print(f"  Number of atoms: {response['structure_data']['total_atoms']}")
                print(f"  Chemical formula: {response['structure_data']['formula']}")
            else:
                print(f"✗ Creation failed: {response['message']}")
                return

            # 2. Rotate structure
            print("\n2. Rotating structure 45 degrees...")
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
                print("✓ Structure rotation successful")
            else:
                print(f"✗ Rotation failed: {response['message']}")

            # 3. Calculate energy
            print("\n3. Calculating energy...")
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
                print(f"✓ Energy calculation completed: {energy:.4f} eV")
            else:
                print(f"✗ Calculation failed: {response['message']}")

            # 4. Preview structure
            print("\n4. Previewing structure...")
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
                print("✓ Structure information:")
                print(f"  Volume: {structure_info.get('cell_volume', 'N/A')} Ų")
                print(f"  Center of mass: {structure_info.get('center_of_mass', 'N/A')}")
                print(f"  Unique elements: {structure_info.get('unique_elements', 'N/A')}")

            # 5. Save structure
            print("\n5. Saving structure...")
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
                print(f"✓ Structure saved to: {response['properties']['saved_path']}")
            else:
                print(f"✗ Save failed: {response['message']}")

            # 6. List sessions
            print("\n6. Listing all sessions...")
            result = await session.call_tool(
                "list_sessions",
                {"limit": 5}
            )

            response = json.loads(result.content[0].text)
            if response["success"]:
                print(f"✓ Found {len(response['sessions'])} sessions")
                for sess in response["sessions"][:3]:
                    print(f"  - {sess['id'][:8]}... : {sess.get('metadata', {}).get('name', 'Unnamed')}")


async def molecule_example():
    """Molecular structure examples"""

    async with stdio_client() as streams:
        async with ClientSession(streams[0], streams[1]) as session:

            print("\n" + "="*50)
            print("Molecular Structure Examples")
            print("="*50)

            # Create water molecule
            print("Creating water molecule...")
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
                print(f"✓ Water molecule created successfully")
                print(f"  Number of atoms: {response['structure_data']['total_atoms']}")

                # Get detailed structure information
                result = await session.call_tool(
                    "get_structure_info",
                    {"session_id": session_id}
                )

                response = json.loads(result.content[0].text)
                if response["success"]:
                    info = response["structure_info"]
                    print(f"  Number of bonds: {info.get('total_bonds', 0)}")
                    print(f"  Minimum distance: {info.get('min_distance', 'N/A')} Å")


async def surface_example():
    """Surface structure examples"""

    async with stdio_client() as streams:
        async with ClientSession(streams[0], streams[1]) as session:

            print("\n" + "="*50)
            print("Surface Structure Examples")
            print("="*50)

            # Create Cu(111) surface
            print("Creating Cu(111) surface...")
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
                print(f"✓ Surface created successfully")
                print(f"  Number of atoms: {response['structure_data']['total_atoms']}")

                # Create supercell
                print("Creating 2x2 supercell...")
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
                    print(f"✓ Supercell created successfully")
                    print(f"  New number of atoms: {response['structure_data']['total_atoms']}")


if __name__ == "__main__":
    print("ASE MCP Server Usage Examples")
    print("Please ensure the MCP server is running...")
    print("Startup command: python server/main.py --mcp-only")
    print()

    # Run examples
    asyncio.run(basic_usage_example())
    asyncio.run(molecule_example())
    asyncio.run(surface_example())

    print("\nExamples completed!")
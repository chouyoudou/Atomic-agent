#!/usr/bin/env python3
"""
ASE MCP API Structure Creation Examples

Demonstrates how to use the HTTP API to create various types of atomic structures.
"""

import requests
import json
import time

# Server configuration
BASE_URL = "http://localhost:8000/api"

def create_structure(structure_data):
    """Generic function for creating structures"""
    response = requests.post(f"{BASE_URL}/structures", json=structure_data)
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Created successfully: {data['structure_info']['formula']} "
              f"({data['structure_info']['total_atoms']} atoms)")
        print(f"   Session ID: {data['session_id']}")
        return data['session_id']
    else:
        print(f"❌ Creation failed: {response.text}")
        return None

def main():
    print("🔬 ASE MCP Structure Creation Examples")
    print("=" * 50)

    # Example 1: Metal structures
    print("\n1. Metal Structures")

    # Copper FCC structure
    cu_session = create_structure({
        "type": "bulk",
        "formula": "Cu",
        "structure": "fcc",
        "size": [2, 2, 2]
    })

    # Iron BCC structure
    fe_session = create_structure({
        "type": "bulk",
        "formula": "Fe",
        "structure": "bcc",
        "size": [2, 2, 2]
    })

    # Zinc HCP structure
    zn_session = create_structure({
        "type": "bulk",
        "formula": "Zn",
        "structure": "hcp",
        "size": [2, 2, 1]
    })

    # Example 2: Semiconductor structures
    print("\n2. Semiconductor Structures")

    # Silicon diamond structure
    si_session = create_structure({
        "type": "bulk",
        "formula": "Si",
        "structure": "diamond",
        "size": [2, 2, 2]
    })

    # Carbon diamond structure (for later conversion to graphite)
    c_diamond_session = create_structure({
        "type": "bulk",
        "formula": "C",
        "structure": "diamond",
        "size": [2, 2, 1]
    })

    # Example 3: Molecular structures
    print("\n3. Molecular Structures")

    # Water molecule
    h2o_session = create_structure({
        "type": "molecule",
        "formula": "H2O"
    })

    # Methane molecule
    ch4_session = create_structure({
        "type": "molecule",
        "formula": "CH4"
    })

    # Benzene molecule
    c6h6_session = create_structure({
        "type": "molecule",
        "formula": "C6H6"
    })

    # Example 4: Surface structures
    print("\n4. Surface Structures")

    # Cu(111) surface
    cu111_session = create_structure({
        "type": "surface",
        "formula": "Cu",
        "structure": "fcc",
        "miller": [1, 1, 1],
        "layers": 4,
        "size": [3, 3],
        "vacuum": 10.0
    })

    # Si(100) surface
    si100_session = create_structure({
        "type": "surface",
        "formula": "Si",
        "structure": "diamond",
        "miller": [1, 0, 0],
        "layers": 6,
        "size": [2, 2],
        "vacuum": 15.0
    })

    # List all created sessions
    print("\n5. View All Sessions")
    response = requests.get(f"{BASE_URL}/sessions")
    if response.status_code == 200:
        sessions = response.json()["sessions"]
        print(f"Total of {len(sessions)} structures created:")
        for session in sessions:
            summary = session.get("structure_summary", {})
            print(f"  - {session['id'][:8]}... : {summary.get('formula', 'Unknown')} "
                  f"({summary.get('total_atoms', 0)} atoms)")

    print(f"\n🎉 Examples completed! Visit http://localhost:3000 to view 3D visualization")

if __name__ == "__main__":
    main()
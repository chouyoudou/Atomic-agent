#!/usr/bin/env python3
"""
ASE MCP API Crystal Transformation Examples

Demonstrates how to perform complex crystal structure transformations, such as diamond↔graphite, different metal phase transitions, etc.
"""

import requests
import json
import time

# Server configuration
BASE_URL = "http://localhost:8000/api"

def create_structure(structure_data):
    """Create structure"""
    response = requests.post(f"{BASE_URL}/structures", json=structure_data)
    if response.status_code == 200:
        data = response.json()
        session_id = data["session_id"]
        info = data["structure_info"]
        print(f"✅ Created: {info['formula']} ({info['total_atoms']} atoms) - {session_id[:8]}...")
        return session_id, info
    else:
        print(f"❌ Creation failed: {response.text}")
        return None, None

def transform_structure(session_id, operation, parameters, description):
    """Transform structure"""
    print(f"🔄 {description}...")
    response = requests.post(f"{BASE_URL}/structures/{session_id}/modify", json={
        "operation": operation,
        "parameters": parameters
    })
    if response.status_code == 200:
        data = response.json()
        info = data["structure_info"]
        print(f"✅ Completed: {info['formula']} ({info['total_atoms']} atoms)")
        print(f"   Volume: {info.get('cell_volume', 0):.2f} Ų")
        if 'min_distance' in info:
            print(f"   Shortest bond length: {info['min_distance']:.3f} Å")
        return info
    else:
        print(f"❌ Transformation failed: {response.text}")
        return None

def main():
    print("💎 ASE MCP Crystal Transformation Examples")
    print("=" * 50)

    # Example 1: Diamond ↔ Graphite transformation
    print("\n1. Carbon Allotrope Transformation: Diamond ↔ Graphite")

    # Create diamond structure
    diamond_session, diamond_info = create_structure({
        "type": "bulk",
        "formula": "C",
        "structure": "diamond",
        "size": [2, 2, 1]
    })

    if diamond_session:
        print(f"Diamond density-related volume: {diamond_info.get('cell_volume', 0):.2f} Ų")

        # Convert to graphite
        graphite_info = transform_structure(diamond_session, "replace_atoms", {
            "symbols": ["C"] * 8,
            "positions": [
                # First layer
                [0.0, 0.0, 0.0],
                [1.42, 0.0, 0.0],
                [0.71, 1.23, 0.0],
                [2.13, 1.23, 0.0],
                # Second layer (AB stacking)
                [0.71, 0.41, 3.35],
                [2.13, 0.41, 3.35],
                [1.42, 1.64, 3.35],
                [2.84, 1.64, 3.35]
            ],
            "cell": [
                [2.84, 0.0, 0.0],
                [0.0, 2.46, 0.0],
                [0.0, 0.0, 6.7]
            ]
        }, "Converting diamond to graphite")

        if graphite_info:
            print(f"Graphite density-related volume: {graphite_info.get('cell_volume', 0):.2f} Ų")
            volume_change = ((graphite_info.get('cell_volume', 0) -
                            diamond_info.get('cell_volume', 0)) /
                           diamond_info.get('cell_volume', 1)) * 100
            print(f"Volume change: {volume_change:+.1f}%")

            # Convert back to diamond
            time.sleep(1)
            diamond_back_info = transform_structure(diamond_session, "replace_atoms", {
                "symbols": ["C"] * 8,
                "positions": [
                    [0.0, 0.0, 0.0],
                    [1.783, 1.783, 0.0],
                    [1.783, 0.0, 1.783],
                    [0.0, 1.783, 1.783],
                    [0.892, 0.892, 0.892],
                    [2.675, 2.675, 0.892],
                    [2.675, 0.892, 2.675],
                    [0.892, 2.675, 2.675]
                ],
                "cell": [
                    [3.567, 0.0, 0.0],
                    [0.0, 3.567, 0.0],
                    [0.0, 0.0, 3.567]
                ]
            }, "Converting graphite back to diamond")

    # Example 2: Iron phase transition (FCC ↔ BCC)
    print("\n2. Iron Crystal Phase Transition: FCC ↔ BCC")

    # Create FCC iron
    fcc_fe_session, fcc_info = create_structure({
        "type": "bulk",
        "formula": "Fe",
        "structure": "fcc",
        "size": [2, 2, 2]
    })

    if fcc_fe_session:
        # Convert to BCC structure
        bcc_info = transform_structure(fcc_fe_session, "replace_atoms", {
            "symbols": ["Fe"] * 16,  # BCC 2x2x2 supercell
            "positions": [
                # Atomic positions for BCC crystal
                [0.0, 0.0, 0.0], [1.435, 1.435, 1.435],
                [2.87, 0.0, 0.0], [4.305, 1.435, 1.435],
                [0.0, 2.87, 0.0], [1.435, 4.305, 1.435],
                [2.87, 2.87, 0.0], [4.305, 4.305, 1.435],
                [0.0, 0.0, 2.87], [1.435, 1.435, 4.305],
                [2.87, 0.0, 2.87], [4.305, 1.435, 4.305],
                [0.0, 2.87, 2.87], [1.435, 4.305, 4.305],
                [2.87, 2.87, 2.87], [4.305, 4.305, 4.305]
            ],
            "cell": [
                [5.74, 0.0, 0.0],
                [0.0, 5.74, 0.0],
                [0.0, 0.0, 5.74]
            ]
        }, "Converting FCC iron to BCC iron")

    # Example 3: Silicon pressure phase transition simulation
    print("\n3. Silicon Pressure Phase Transition Simulation")

    # Create ambient pressure silicon (diamond structure)
    si_session, si_info = create_structure({
        "type": "bulk",
        "formula": "Si",
        "structure": "diamond",
        "size": [2, 2, 2]
    })

    if si_session:
        original_volume = si_info.get('cell_volume', 0)
        print(f"Ambient pressure silicon volume: {original_volume:.2f} Ų")

        # Simulate compression - shrink unit cell
        compressed_info = transform_structure(si_session, "modify_cell", {
            "cell": [
                [6.5, 0.0, 0.0],   # Originally ~7.14
                [0.0, 6.5, 0.0],
                [0.0, 0.0, 6.5]
            ],
            "scale_atoms": True
        }, "Applying pressure to compress silicon structure")

        if compressed_info:
            compressed_volume = compressed_info.get('cell_volume', 0)
            compression_ratio = (original_volume - compressed_volume) / original_volume * 100
            print(f"Compressed volume: {compressed_volume:.2f} Ų")
            print(f"Compression ratio: {compression_ratio:.1f}%")

    # Example 4: Layered material construction
    print("\n4. Layered Material Construction Example")

    # Create single-layer graphene
    graphene_session, graphene_info = create_structure({
        "type": "molecule",
        "formula": "C6H6"  # First use benzene ring as base
    })

    if graphene_session:
        # Convert to larger graphene sheet
        graphene_sheet_info = transform_structure(graphene_session, "replace_atoms", {
            "symbols": ["C"] * 24,
            "positions": [
                # 4x6 graphene fragment
                [0.0, 0.0, 0.0], [1.42, 0.0, 0.0], [2.13, 1.23, 0.0], [3.55, 1.23, 0.0],
                [0.71, 1.23, 0.0], [2.84, 1.23, 0.0], [3.55, 2.46, 0.0], [4.97, 2.46, 0.0],
                [1.42, 2.46, 0.0], [3.55, 2.46, 0.0], [4.26, 3.69, 0.0], [5.68, 3.69, 0.0],
                [0.0, 3.69, 0.0], [1.42, 3.69, 0.0], [2.13, 4.92, 0.0], [3.55, 4.92, 0.0],
                [0.71, 4.92, 0.0], [2.84, 4.92, 0.0], [3.55, 6.15, 0.0], [4.97, 6.15, 0.0],
                [1.42, 6.15, 0.0], [3.55, 6.15, 0.0], [4.26, 7.38, 0.0], [5.68, 7.38, 0.0]
            ],
            "cell": [
                [7.1, 0.0, 0.0],
                [0.0, 8.61, 0.0],
                [0.0, 0.0, 20.0]  # Large z-direction to prevent periodicity
            ]
        }, "Building graphene nanosheet")

    # Example 5: Nanotube construction
    print("\n5. One-Dimensional Nanostructure Example")

    # Create simplified version of carbon nanotube
    nanotube_session, nanotube_info = create_structure({
        "type": "molecule",
        "formula": "C6H6"
    })

    if nanotube_session:
        # Convert to simple carbon nanotube segment
        transform_structure(nanotube_session, "replace_atoms", {
            "symbols": ["C"] * 20,
            "positions": [
                # Simplified (5,5) nanotube segment atomic positions
                [0.0, 1.42, 0.0], [1.23, 0.71, 0.0], [1.23, -0.71, 0.0], [0.0, -1.42, 0.0],
                [-1.23, -0.71, 0.0], [-1.23, 0.71, 0.0], [0.0, 1.42, 1.25], [1.23, 0.71, 1.25],
                [1.23, -0.71, 1.25], [0.0, -1.42, 1.25], [-1.23, -0.71, 1.25], [-1.23, 0.71, 1.25],
                [0.0, 1.42, 2.5], [1.23, 0.71, 2.5], [1.23, -0.71, 2.5], [0.0, -1.42, 2.5],
                [-1.23, -0.71, 2.5], [-1.23, 0.71, 2.5], [0.0, 1.42, 3.75], [1.23, 0.71, 3.75]
            ],
            "cell": [
                [5.0, 0.0, 0.0],
                [0.0, 5.0, 0.0],
                [0.0, 0.0, 5.0]
            ]
        }, "Building carbon nanotube segment")

    # Summary
    print("\n📊 Transformation Examples Summary")
    response = requests.get(f"{BASE_URL}/sessions")
    if response.status_code == 200:
        sessions = response.json()["sessions"]
        print(f"Total of {len(sessions)} structures created:")
        for session in sessions:
            summary = session.get("structure_summary", {})
            print(f"  - {session['id'][:8]}... : {summary.get('formula', 'Unknown')} "
                  f"({summary.get('total_atoms', 0)} atoms)")

    print(f"\n🎉 Crystal transformation examples completed!")
    print("💡 These examples demonstrated:")
    print("   - Allotrope transformations (C: diamond↔graphite)")
    print("   - Metal phase transitions (Fe: FCC↔BCC)")
    print("   - Pressure phase transition simulation (Si compression)")
    print("   - Layered material construction (graphene)")
    print("   - One-dimensional nanostructures (carbon nanotubes)")
    print(f"\nVisit http://localhost:3000 to view 3D visualization of all structures!")

if __name__ == "__main__":
    main()
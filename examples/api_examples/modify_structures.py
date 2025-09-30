#!/usr/bin/env python3
"""
ASE MCP API Structure Modification Examples

Demonstrates how to use the HTTP API to modify existing atomic structures.
"""

import requests
import json
import time

# Server configuration
BASE_URL = "http://localhost:8000/api"

def create_test_structure():
    """Create a test copper structure"""
    response = requests.post(f"{BASE_URL}/structures", json={
        "type": "bulk",
        "formula": "Cu",
        "structure": "fcc",
        "size": [2, 2, 2]
    })
    if response.status_code == 200:
        session_id = response.json()["session_id"]
        print(f"✅ Created test structure: {session_id}")
        return session_id
    else:
        print(f"❌ Creation failed: {response.text}")
        return None

def modify_structure(session_id, operation, parameters):
    """Generic function for modifying structures"""
    response = requests.post(f"{BASE_URL}/structures/{session_id}/modify", json={
        "operation": operation,
        "parameters": parameters
    })
    if response.status_code == 200:
        data = response.json()
        info = data["structure_info"]
        print(f"✅ {operation} successful: {info['formula']} ({info['total_atoms']} atoms)")
        print(f"   Cell volume: {info.get('cell_volume', 0):.2f} Ų")
        return True
    else:
        print(f"❌ {operation} failed: {response.text}")
        return False

def main():
    print("🔧 ASE MCP Structure Modification Examples")
    print("=" * 50)

    # Create test structure
    session_id = create_test_structure()
    if not session_id:
        return

    # Example 1: Geometric transformations
    print("\n1. Geometric Transformation Operations")

    # Rotate structure
    print("Rotating 45 degrees...")
    modify_structure(session_id, "rotate", {
        "angle": 45,
        "axis": [0, 0, 1]
    })

    # Translate structure
    print("Translating...")
    modify_structure(session_id, "translate", {
        "vector": [1.0, 1.0, 0.0]
    })

    # Scale structure
    print("Scaling to 110%...")
    modify_structure(session_id, "scale", {
        "factor": 1.1
    })

    # Example 2: Cell operations
    print("\n2. Cell Operations")

    # Create supercell
    print("Creating 3x3x1 supercell...")
    modify_structure(session_id, "supercell", {
        "size": [3, 3, 1]
    })

    # Modify cell parameters
    print("Modifying cell size...")
    modify_structure(session_id, "modify_cell", {
        "cell": [
            [15.0, 0.0, 0.0],
            [0.0, 15.0, 0.0],
            [0.0, 0.0, 10.0]
        ],
        "scale_atoms": False
    })

    # Example 3: Atomic operations
    print("\n3. Atomic Operations")

    # Add atoms
    print("Adding hydrogen atom...")
    modify_structure(session_id, "add_atom", {
        "symbol": "H",
        "position": [7.5, 7.5, 5.0]
    })

    # Change atomic species
    print("Changing first two atoms to gold atoms...")
    modify_structure(session_id, "change_species", {
        "indices": [0, 1],
        "symbols": ["Au", "Au"]
    })

    # Duplicate atoms
    print("Duplicating first atom...")
    modify_structure(session_id, "duplicate_atoms", {
        "indices": [0],
        "offset": [0, 0, 2.0]
    })

    # Example 4: Structure reconstruction
    print("\n4. Structure Reconstruction Example - Diamond to Graphite")

    # First create diamond structure
    print("Creating diamond structure...")
    diamond_response = requests.post(f"{BASE_URL}/structures", json={
        "type": "bulk",
        "formula": "C",
        "structure": "diamond",
        "size": [2, 2, 1]
    })

    if diamond_response.status_code == 200:
        diamond_session = diamond_response.json()["session_id"]
        print(f"Diamond structure created successfully: {diamond_session}")

        # Convert to graphite structure
        print("Converting to graphite structure...")
        graphite_success = modify_structure(diamond_session, "replace_atoms", {
            "symbols": ["C", "C", "C", "C"],
            "positions": [
                [0.0, 0.0, 0.0],
                [1.42, 0.0, 0.0],
                [0.71, 1.23, 0.0],
                [2.13, 1.23, 0.0]
            ],
            "cell": [
                [2.84, 0.0, 0.0],
                [0.0, 2.46, 0.0],
                [0.0, 0.0, 3.35]
            ]
        })

        if graphite_success:
            print("🎉 Diamond successfully converted to graphite!")

    # Example 5: Defect creation
    print("\n5. Defect Creation")

    # Create vacancies
    print("Removing some atoms to create vacancies...")
    modify_structure(session_id, "remove_atoms", {
        "indices": [0, 5, 10]  # Remove three atoms
    })

    # Get final structure information
    print("\n6. Final Structure Information")
    response = requests.get(f"{BASE_URL}/structures/{session_id}")
    if response.status_code == 200:
        info = response.json()["structure_info"]
        print(f"Final structure: {info['formula']}")
        print(f"Total atoms: {info['total_atoms']}")
        print(f"Unique elements: {', '.join(info['unique_elements'])}")
        print(f"Cell volume: {info.get('cell_volume', 0):.2f} Ų")
        if 'min_distance' in info:
            print(f"Shortest bond length: {info['min_distance']:.3f} Å")
            print(f"Average bond length: {info['avg_distance']:.3f} Å")

    print(f"\n🎉 Modification examples completed! Visit http://localhost:3000 to view the final structure")

if __name__ == "__main__":
    main()
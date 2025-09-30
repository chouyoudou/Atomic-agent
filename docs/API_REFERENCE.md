# ASE MCP API Usage Tutorial

## Overview

The ASE MCP server provides comprehensive APIs for crystal structure creation, modification, and analysis. This tutorial demonstrates how to use these APIs for atomic structure operations.

## Basic Configuration

### Starting the Server

```bash
# Separate frontend/backend mode (recommended)
python server/main.py --api-only  # Backend API (port 8000)
cd client && npm start             # Frontend interface (port 3000)

# Integrated mode
python server/main.py              # Frontend and backend together (port 8000)
```

### API Base URLs

- **API Endpoint**: `http://localhost:8000/api`
- **WebSocket**: `ws://localhost:8001`
- **Frontend Interface**: `http://localhost:3000` (separate mode) or `http://localhost:8000` (integrated mode)

## 1. Structure Creation API

### Creating Crystal Structures

**Endpoint**: `POST /api/structures`

```python
import requests

# Create diamond structure
data = {
    "type": "bulk",
    "formula": "C",
    "crystal_structure": "diamond",
    "lattice_parameter": 3.567,
    "size": [2, 2, 2],
    "metadata": {
        "name": "Diamond Structure",
        "description": "2x2x2 diamond supercell"
    }
}

response = requests.post("http://localhost:8000/api/structures", json=data)
result = response.json()
session_id = result["session_id"]
```

### Supported Crystal Structure Types

- `diamond` - Diamond structure
- `fcc` - Face-centered cubic
- `bcc` - Body-centered cubic
- `sc` - Simple cubic
- `hcp` - Hexagonal close-packed
- `rocksalt` - Rock salt structure
- `cesiumchloride` - Cesium chloride structure
- `fluorite` - Fluorite structure
- `zinc_blende` - Zinc blende structure

### Creating Molecular Structures

```python
# Create water molecule
data = {
    "type": "molecule",
    "formula": "H2O",
    "metadata": {
        "name": "Water Molecule",
        "description": "H2O molecular structure"
    }
}

response = requests.post("http://localhost:8000/api/structures", json=data)
```

### Creating Surface Structures

```python
# Create Cu(111) surface
data = {
    "type": "surface",
    "formula": "Cu",
    "miller_indices": [1, 1, 1],
    "layers": 4,
    "vacuum": 10.0,
    "size": [3, 3],
    "metadata": {
        "name": "Cu(111) Surface",
        "description": "4-layer Cu(111) surface with 10Å vacuum"
    }
}

response = requests.post("http://localhost:8000/api/structures", json=data)
```

## 2. Structure Modification API

### Modifying Cell Parameters

**Endpoint**: `POST /api/structures/{session_id}/modify`

```python
# Modify cell size
modify_data = {
    "operation": "modify_cell",
    "parameters": {
        "cell": [
            [4.0, 0.0, 0.0],  # a vector
            [0.0, 4.0, 0.0],  # b vector
            [0.0, 0.0, 4.0]   # c vector
        ],
        "scale_atoms": True  # Whether to scale atomic positions proportionally
    }
}

response = requests.post(f"http://localhost:8000/api/structures/{session_id}/modify",
                        json=modify_data)
```

### Modifying Atomic Positions

```python
# Modify positions of specific atoms
modify_data = {
    "operation": "modify_positions",
    "parameters": {
        "indices": [0, 1],  # Atomic indices
        "positions": [
            [1.0, 1.0, 1.0],  # New position of atom 0
            [2.0, 2.0, 2.0]   # New position of atom 1
        ]
    }
}

response = requests.post(f"http://localhost:8000/api/structures/{session_id}/modify",
                        json=modify_data)
```

### Adding Atoms

```python
# Add a single atom
modify_data = {
    "operation": "add_atom",
    "parameters": {
        "symbol": "O",  # Oxygen atom
        "position": [0.0, 0.0, 5.0]  # Position coordinates
    }
}

response = requests.post(f"http://localhost:8000/api/structures/{session_id}/modify",
                        json=modify_data)
```

### Removing Atoms

```python
# Remove specific atoms
modify_data = {
    "operation": "remove_atoms",
    "parameters": {
        "indices": [2, 5, 8]  # Indices of atoms to remove
    }
}

response = requests.post(f"http://localhost:8000/api/structures/{session_id}/modify",
                        json=modify_data)
```

### Changing Atomic Species

```python
# Change specified atoms to other elements
modify_data = {
    "operation": "change_species",
    "parameters": {
        "indices": [0, 1, 2],        # Atomic indices
        "symbols": ["N", "N", "N"]   # New element symbols
    }
}

response = requests.post(f"http://localhost:8000/api/structures/{session_id}/modify",
                        json=modify_data)
```

### Complete Atomic Structure Replacement

```python
# Completely replace with new atomic structure (preserve cell)
modify_data = {
    "operation": "replace_atoms",
    "parameters": {
        "symbols": ["C", "C", "O", "O"],  # New atomic symbols
        "positions": [                     # New atomic positions
            [0.0, 0.0, 0.0],
            [1.0, 1.0, 1.0],
            [2.0, 0.0, 0.0],
            [0.0, 2.0, 0.0]
        ],
        "cell": [  # Optional: modify cell simultaneously
            [5.0, 0.0, 0.0],
            [0.0, 5.0, 0.0],
            [0.0, 0.0, 5.0]
        ]
    }
}

response = requests.post(f"http://localhost:8000/api/structures/{session_id}/modify",
                        json=modify_data)
```

### Geometric Transformation Operations

```python
# Rotate structure
modify_data = {
    "operation": "rotate",
    "parameters": {
        "axis": [0, 0, 1],    # Rotate around z-axis
        "angle": 45,          # Rotation angle (degrees)
        "center": [2.5, 2.5, 2.5]  # Rotation center
    }
}

# Translate structure
modify_data = {
    "operation": "translate",
    "parameters": {
        "vector": [1.0, 0.0, 0.0]  # Translation vector
    }
}

# Scale structure
modify_data = {
    "operation": "scale",
    "parameters": {
        "factor": 1.1  # Scaling factor
    }
}

# Create supercell
modify_data = {
    "operation": "supercell",
    "parameters": {
        "size": [3, 3, 1]  # 3x3x1 supercell
    }
}
```

### Creating Defects

```python
# Create vacancy defects
modify_data = {
    "operation": "create_vacancy",
    "parameters": {
        "indices": [5, 10]  # Remove atoms at these positions to create vacancies
    }
}

# Duplicate atoms (create interstitial atoms)
modify_data = {
    "operation": "duplicate_atoms",
    "parameters": {
        "indices": [0],           # Indices of atoms to duplicate
        "offset": [0.5, 0.5, 0.5] # Duplication offset
    }
}
```

## 3. Query API

### Getting Session List

**Endpoint**: `GET /api/sessions`

```python
response = requests.get("http://localhost:8000/api/sessions")
sessions = response.json()["sessions"]

for session in sessions:
    print(f"Session ID: {session['id']}")
    print(f"Name: {session['metadata']['name']}")
    print(f"Atom count: {session['atom_count']}")
```

### Getting Structure Details

**Endpoint**: `GET /api/sessions/{session_id}`

```python
response = requests.get(f"http://localhost:8000/api/sessions/{session_id}")
session_data = response.json()["session"]

# Get structure information
structure = session_data["current_structure"]
print(f"Chemical formula: {structure['chemical_formula']}")
print(f"Number of atoms: {structure['num_atoms']}")
print(f"Cell: {structure['cell']}")
print(f"Atomic positions: {structure['positions']}")
```

### Getting Structure in XYZ Format

**Endpoint**: `GET /api/sessions/{session_id}/xyz`

```python
response = requests.get(f"http://localhost:8000/api/sessions/{session_id}/xyz")
xyz_data = response.text

# Save as XYZ file
with open("structure.xyz", "w") as f:
    f.write(xyz_data)
```

## 4. Structure Analysis API

### Calculating Structure Properties

**Endpoint**: `POST /api/sessions/{session_id}/calculate`

```python
calc_data = {
    "calculator": "emt",  # EMT calculator
    "properties": ["energy", "forces", "stress"]
}

response = requests.post(f"http://localhost:8000/api/sessions/{session_id}/calculate",
                        json=calc_data)
properties = response.json()["properties"]

print(f"Energy: {properties['energy']} eV")
print(f"Forces: {properties['forces']}")
```

## 5. Practical Application Examples

### Example 1: Converting Diamond Structure to Graphite

```python
import requests

# 1. Create diamond structure
diamond_data = {
    "type": "bulk",
    "formula": "C",
    "crystal_structure": "diamond",
    "lattice_parameter": 3.567,
    "size": [2, 2, 2]
}

response = requests.post("http://localhost:8000/api/structures", json=diamond_data)
session_id = response.json()["session_id"]

# 2. Get current structure
response = requests.get(f"http://localhost:8000/api/sessions/{session_id}")
structure = response.json()["session"]["current_structure"]

# 3. Convert to graphite layered structure
# Create atomic positions for graphite monolayer (hexagonal ring structure)
graphite_positions = [
    [0.0, 0.0, 0.0],      # First carbon atom
    [1.42, 0.0, 0.0],     # Second carbon atom
    [2.13, 1.23, 0.0],    # Third carbon atom
    [1.42, 2.46, 0.0],    # Fourth carbon atom
    [0.0, 2.46, 0.0],     # Fifth carbon atom
    [-0.71, 1.23, 0.0],   # Sixth carbon atom
]

graphite_symbols = ["C"] * len(graphite_positions)

# Set graphite cell
graphite_cell = [
    [2.46, 0.0, 0.0],     # a vector
    [1.23, 2.13, 0.0],    # b vector
    [0.0, 0.0, 6.71]      # c vector (interlayer distance)
]

# 4. Replace with graphite structure
modify_data = {
    "operation": "replace_atoms",
    "parameters": {
        "symbols": graphite_symbols,
        "positions": graphite_positions,
        "cell": graphite_cell
    }
}

response = requests.post(f"http://localhost:8000/api/structures/{session_id}/modify",
                        json=modify_data)

print("✅ Successfully converted diamond structure to graphite structure!")
print(f"🌐 View results: http://localhost:3000")
```

### Example 2: Creating Surface Adsorption Structure

```python
# 1. Create Cu(111) surface
surface_data = {
    "type": "surface",
    "formula": "Cu",
    "miller_indices": [1, 1, 1],
    "layers": 4,
    "vacuum": 10.0,
    "size": [3, 3]
}

response = requests.post("http://localhost:8000/api/structures", json=surface_data)
session_id = response.json()["session_id"]

# 2. Add CO molecule to surface
# First add C atom
co_c_data = {
    "operation": "add_atom",
    "parameters": {
        "symbol": "C",
        "position": [5.0, 5.0, 12.0]  # Above surface
    }
}

response = requests.post(f"http://localhost:8000/api/structures/{session_id}/modify",
                        json=co_c_data)

# 3. Add O atom
co_o_data = {
    "operation": "add_atom",
    "parameters": {
        "symbol": "O",
        "position": [5.0, 5.0, 13.15]  # 1.15Å above C atom
    }
}

response = requests.post(f"http://localhost:8000/api/structures/{session_id}/modify",
                        json=co_o_data)

print("✅ Successfully created CO adsorbed on Cu(111) surface structure!")
```

### Example 3: Batch Processing and Analysis

```python
# Create series of structures with different lattice parameters
lattice_params = [3.5, 3.6, 3.7, 3.8]
session_ids = []

for a in lattice_params:
    data = {
        "type": "bulk",
        "formula": "Cu",
        "crystal_structure": "fcc",
        "lattice_parameter": a,
        "size": [2, 2, 2],
        "metadata": {"name": f"Cu_a{a}"}
    }

    response = requests.post("http://localhost:8000/api/structures", json=data)
    session_ids.append(response.json()["session_id"])

# Calculate energy for each structure
energies = []
for sid in session_ids:
    calc_data = {"calculator": "emt", "properties": ["energy"]}
    response = requests.post(f"http://localhost:8000/api/sessions/{sid}/calculate",
                            json=calc_data)
    energy = response.json()["properties"]["energy"]
    energies.append(energy)

# Find structure with lowest energy
min_idx = energies.index(min(energies))
print(f"Lowest energy structure: a={lattice_params[min_idx]}, E={energies[min_idx]} eV")
```

## 6. WebSocket Real-time Communication

```python
import websocket
import json

def on_message(ws, message):
    data = json.loads(message)
    print(f"Received update: {data['type']}")
    if data['type'] == 'structure_updated':
        print(f"Structure updated: {data['session_id']}")

def on_open(ws):
    print("WebSocket connection established")

# Connect WebSocket
ws = websocket.WebSocketApp("ws://localhost:8001",
                           on_message=on_message,
                           on_open=on_open)
ws.run_forever()
```

## 7. Error Handling

```python
import requests

try:
    response = requests.post("http://localhost:8000/api/structures", json=data)
    response.raise_for_status()  # 检查HTTP错误

    result = response.json()
    if not result.get("success", False):
        print(f"API error: {result.get('error', 'Unknown error')}")

except requests.exceptions.RequestException as e:
    print(f"Request error: {e}")
except ValueError as e:
    print(f"JSON parsing error: {e}")
```

## 8. Best Practices

1. **Session Management**: Save important session_ids, they are unique identifiers for accessing structures
2. **Error Handling**: Always check the success status of API responses
3. **Performance**: Large structure operations may require more time, consider asynchronous processing
4. **Visualization**: Use the frontend interface to view structure changes in real-time
5. **Backup**: Important structures can be exported to XYZ or other formats

## 9. Common Questions

**Q: How to view all supported operations?**
A: Check the modification API section of this document, or query the `/api/docs` endpoint

**Q: How to save modified structures?**
A: Structures are automatically saved in sessions and can be accessed via session_id

**Q: How to export structures?**
A: Use `/api/sessions/{session_id}/xyz` to export in XYZ format

**Q: What to do if WebSocket disconnects?**
A: The frontend will automatically reconnect, or manually re-establish the connection

**Q: Can multiple sessions be modified simultaneously?**
A: Yes, each session is independent

## Summary

The ASE MCP API provides comprehensive atomic structure manipulation capabilities, from basic creation and modification to advanced analysis functions. Combined with the frontend 3D visualization interface, it allows real-time viewing of structure changes, making it a powerful tool for atomic simulation and materials design.

🌐 **Frontend Interface**: http://localhost:3000
📡 **API Documentation**: http://localhost:8000/docs
🔗 **WebSocket**: ws://localhost:8001
# ASE MCP LLM Fine-tuning Training Guide

## Overview

This guide is specifically designed for training Large Language Models (LLMs) to use the ASE MCP server. It includes system prompts, API call templates, training data formats, and best practices.

## System Prompt Recommendations

### Basic System Prompt

```
You are a professional atomic simulation expert assistant capable of creating, modifying, and analyzing crystal structures using ASE MCP tools.

Available tools:
- create_structure: Create new atomic structures
- modify_structure: Modify existing structures
- preview_structure: Preview structures
- calculate_properties: Calculate physical properties
- list_sessions: List sessions
- get_structure_info: Get structure information

When users request atomic structure operations, use the appropriate MCP tools to complete the tasks.
```

### Enhanced System Prompt

```
You are an Atomic Simulation Environment (ASE) expert capable of:

1. Creating various crystal structures:
   - Metals: Cu, Al, Fe (FCC, BCC, HCP)
   - Semiconductors: Si, GaAs (diamond, zinc blende)
   - Molecules: H2O, CH4, C6H6

2. Modifying structures:
   - Geometric transformations: rotation, translation, scaling
   - Cell operations: modify lattice parameters
   - Atomic operations: add, delete, replace atoms
   - Structure conversion: diamond ↔ graphite

3. Computational analysis:
   - Energy calculations
   - Structural optimization
   - Structure parameter analysis

Use JSON format MCP tool calls, ensuring correct parameters.
```

## MCP Tool Specifications

### 1. create_structure

**Function**: Create new atomic structures

**Parameter Format**:
```json
{
  "type": "bulk|molecule|surface",
  "formula": "element chemical formula",
  "structure": "crystal structure type",
  "size": [nx, ny, nz],
  "session_id": "optional session ID"
}
```

**Example Calls**:
```json
// Create 2x2x2 copper FCC structure
{
  "type": "bulk",
  "formula": "Cu",
  "structure": "fcc",
  "size": [2, 2, 2]
}

// Create water molecule
{
  "type": "molecule",
  "formula": "H2O"
}

// Create silicon surface
{
  "type": "surface",
  "formula": "Si",
  "structure": "diamond",
  "miller": [1, 1, 1],
  "layers": 4
}
```

### 2. modify_structure

**Function**: Modify existing structures

**Supported Operations**:
- `rotate`: Rotation
- `translate`: Translation
- `scale`: Scaling
- `supercell`: Create supercell
- `modify_cell`: Modify cell
- `modify_positions`: Modify atomic positions
- `replace_atoms`: Complete atomic replacement
- `add_atom`: Add atom
- `remove_atoms`: Remove atoms
- `change_species`: Change atomic species

**Parameter Format**:
```json
{
  "session_id": "session ID",
  "operation": "operation type",
  "parameters": {
    // specific parameters
  }
}
```

**Example Calls**:
```json
// Rotate structure
{
  "session_id": "uuid",
  "operation": "rotate",
  "parameters": {
    "angle": 45,
    "axis": [0, 0, 1]
  }
}

// Diamond to graphite conversion (complete replacement)
{
  "session_id": "uuid",
  "operation": "replace_atoms",
  "parameters": {
    "symbols": ["C", "C", "C", "C"],
    "positions": [[0,0,0], [1.42,0,0], [0.71,1.23,0], [2.13,1.23,0]],
    "cell": [[2.84,0,0], [0,2.46,0], [0,0,3.35]]
  }
}
```

### 3. Other Tools

```json
// Preview structure
{
  "session_id": "uuid",
  "format": "json|xyz|cif"
}

// Calculate properties
{
  "session_id": "uuid",
  "calculator": "emt",
  "properties": ["energy", "forces"]
}

// List sessions
{}

// Get structure information
{
  "session_id": "uuid"
}
```

## Training Data Format

### Conversational Training Data

```json
{
  "conversations": [
    {
      "human": "Create a face-centered cubic structure of copper",
      "assistant": "I'll create a face-centered cubic structure of copper for you.",
      "tool_calls": [
        {
          "name": "create_structure",
          "parameters": {
            "type": "bulk",
            "formula": "Cu",
            "structure": "fcc",
            "size": [2, 2, 2]
          }
        }
      ],
      "tool_results": [
        {
          "success": true,
          "session_id": "abc-123",
          "structure_info": {
            "formula": "Cu32",
            "total_atoms": 32
          }
        }
      ],
      "final_response": "Successfully created a face-centered cubic structure of copper containing 32 atoms. Session ID: abc-123"
    }
  ]
}
```

### Common Operation Templates

#### 1. Structure Creation Template

```python
# User: Create {element} {structure type}
# Assistant template:
tools = {
  "create_structure": {
    "type": "bulk",
    "formula": "{element}",
    "structure": "{structure type}",
    "size": [2, 2, 2]
  }
}
```

#### 2. Structure Modification Template

```python
# User: Rotate the structure by {angle} degrees
# Assistant template:
tools = {
  "modify_structure": {
    "session_id": "{current session ID}",
    "operation": "rotate",
    "parameters": {
      "angle": "{angle}",
      "axis": [0, 0, 1]
    }
  }
}
```

#### 3. Structure Conversion Template

```python
# User: Convert diamond to graphite
# Assistant template:
tools = {
  "modify_structure": {
    "session_id": "{current session ID}",
    "operation": "replace_atoms",
    "parameters": {
      "symbols": ["C"] * graphite_atom_count,
      "positions": graphite_atomic_coordinates,
      "cell": graphite_cell_parameters
    }
  }
}
```

## Typical Usage Scenarios

### 1. Materials Design Workflow

```
User: I want to study the surface properties of silicon
Assistant:
1. First create Si(111) surface structure
2. Analyze surface atomic coordination
3. Calculate surface energy
4. Optimize surface structure
```

### 2. Structure Comparison Analysis

```
User: Compare the structural differences between diamond and graphite
Assistant:
1. Create diamond structure
2. Convert to graphite structure
3. Compare cell parameters
4. Analyze density differences
```

### 3. Defect Studies

```
User: Create vacancy defects in silicon
Assistant:
1. Create perfect silicon structure
2. Remove atoms at specific positions
3. Analyze defect environment
4. Calculate defect formation energy
```

## Error Handling Patterns

### 1. Parameter Errors

```python
if "error" in result:
    # Check parameter format
    # Provide correct parameter examples
    # Retry tool call
```

### 2. Session Management

```python
# Always check if session exists
sessions = list_sessions()
if session_id not in sessions:
    # Create new session or use existing session
```

### 3. Structure Validation

```python
# Validate structure reasonableness after modification
structure_info = get_structure_info(session_id)
if structure_info["total_atoms"] == 0:
    # Handle empty structure issues
```

## Best Practices

### 1. Session Management
- Create dedicated sessions for each user task
- Check session status before operations
- Clean up unused sessions promptly

### 2. Parameter Validation
- Validate chemical formula validity
- Check numerical parameter ranges
- Ensure coordinates and cell parameters are reasonable

### 3. Error Recovery
- Save structure state before operations
- Provide undo/redo functionality
- Give clear error explanations

### 4. User Experience
- Provide structure visualization links
- Explain the physical meaning of operation results
- Suggest possible follow-up operations

## Fine-tuning Recommendations

### 1. Data Collection
- Collect real atomic simulation conversations
- Include various structure types and operations
- Cover error handling scenarios

### 2. Training Strategy
- Use reinforcement learning to optimize tool calls
- Focus on parameter accuracy training
- Strengthen physics and chemistry knowledge understanding

### 3. Evaluation Metrics
- Tool call success rate
- Parameter accuracy
- Physical reasonableness
- User satisfaction

By following this guide, you can train professional and reliable ASE MCP assistants.
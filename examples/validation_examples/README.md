# GeometryAnalyzer Validation Examples

This directory contains examples and debugging tools for the GeometryAnalyzer validation system.

## Files

### `basic_validation.py`
Demonstrates basic usage of GeometryAnalyzer with common structures.

**Examples included:**
1. Water molecule (0D structure)
2. FCC copper crystal (3D structure)
3. Constraint checking
4. Structure comparison

**Usage:**
```bash
python examples/validation_examples/basic_validation.py
```

**Expected output:**
- Dimensionality detection
- Coordination numbers
- Geometry types
- Bond length statistics
- Constraint validation results

### `debug_data_structure.py`
Debug tool for inspecting robocrystallographer's condensed data format.

**Usage:**
```bash
python examples/validation_examples/debug_data_structure.py
```

**Shows:**
- Top-level keys in condensed dict
- Sites dict structure (not list!)
- NN as list of indices
- Distances dict format
- Full JSON of first site

## Key Learnings

### Robocrystallographer Data Format

```python
condensed = {
    "sites": {
        0: {  # Site index as key (dict, not list!)
            "element": "Cu0+",  # With oxidation state
            "nn": [0, 0, 0, ...],  # List of neighbor indices
            "nnn": {"edge": [...], "face": [...]},  # Next-nearest neighbors
            "geometry": {"type": "cuboctahedral", "likeness": 1.0}
        }
    },
    "distances": {
        0: {  # Site index
            0: [2.54, 2.54, ...]  # Neighbor index: [distances]
        }
    },
    "dimensionality": 3,
    "formula": "Cu",
    ...
}
```

### Common Pitfalls

1. **Sites is dict, not list**: Use `sites.items()` not `enumerate(sites)`
2. **NN is list of indices**: Length gives coordination, not `nnn` value
3. **Element includes oxidation**: Strip with regex `r'[\d\+\-]+$'`
4. **Distances at top level**: Not inside site data

## Performance Notes

- Typical runtime: 10-30 seconds per structure
- robocrystallographer is computation-intensive
- This is expected behavior, not a bug
- Do not skip tests or simplify for performance

## Testing

Run unit tests:
```bash
pytest server/tests/test_validators/test_geometry_analyzer.py -v
```

Expected: 13 passed, ~105 seconds runtime
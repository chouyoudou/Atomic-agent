# GeometryAnalyzer Validation Examples

This directory contains examples and debugging tools for the GeometryAnalyzer validation system.

## Phase 0: Foundation Examples

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
- Runtime: ~2 minutes

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

---

## Phase 1: Tolerance-Based Validation Examples

### `phase1_tolerance_demo.py` ⭐ **PRIMARY DEMO**
Comprehensive demonstration of the three-level feedback system (passed/warning/violation).

**6 Examples included:**
1. **Perfect FCC Cu** - All constraints pass
2. **Bond Length Warning** - Slight deviation triggers warning
3. **Severe Violation** - Dimensionality mismatch
4. **Geometry Likeness** - Order Parameter quantification
5. **Tolerance Boundaries** - Testing thresholds (5%/15%)
6. **Multiple Constraints** - Simultaneous validation

**Usage:**
```bash
python examples/validation_examples/phase1_tolerance_demo.py
```

**Expected output:**
- Three-level feedback examples
- Order Parameter quantification
- Tolerance threshold behavior
- Multi-constraint validation
- Runtime: ~2 minutes

**Key demonstrations:**
- Silent pass for <5% deviations
- Warnings for 5-15% deviations
- Violations for >15% deviations
- Element-specific thresholds (O: 0.5, Ti/Al: 0.7)

### `download_mp_structures.py`
Downloads real complex structures from Materials Project database for testing.

**Structures downloaded:**
- BaTiO3 (mp-19990) - Perovskite, Ti octahedral coordination
- Al2O3 (mp-1244874) - Corundum, Al octahedral coordination
- ZnS (mp-1244890) - Zinc Blende, tetrahedral coordination

**Usage:**
```bash
python examples/validation_examples/download_mp_structures.py
```

**Output:** Saves structures to `mp_structures/` directory
**Requirements:** Materials Project API key in `mp_api` file
**Runtime:** ~10 seconds

### Experimental/Advanced Examples

⚠️ **Note**: The following examples are experimental and may require longer runtime or manual configuration.

#### `test_mp_structures.py` (Experimental)
Simplified perturbation tests on MP structures.

**Tests:**
- Bond stretching sensitivity (0.95x - 1.20x)
- Random displacement robustness (0.0 - 0.3 Å)
- Constraint validation at different thresholds

**Runtime:** ~5-10 minutes (slow due to multiple robocrys analyses)

#### `complex_structures_validation.py` (Incomplete)
Comprehensive validation suite for complex structures.

**Status:** Concept demonstration, not fully functional
**Note:** Preserved for reference, requires supercell analysis (very slow)

#### `final_validation_tests.py` (Incomplete)
Final integrated testing script.

**Status:** Concept demonstration
**Note:** Designed for single structure, can be adapted

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

## Recommended Usage Flow

### For Learning
1. Start with `basic_validation.py` to understand Phase 0 foundations
2. Run `phase1_tolerance_demo.py` to see three-level feedback in action
3. (Optional) Download MP structures with `download_mp_structures.py`

### For Development
1. Use Phase 0/1 examples as templates for your own structures
2. Refer to `debug_data_structure.py` when debugging robocrys output
3. Check unit tests for comprehensive usage patterns

### For Testing Complex Structures
1. Download reference structures with `download_mp_structures.py`
2. Adapt `test_mp_structures.py` for your specific perturbation needs
3. Note: Performance testing best done on primitive cells (<10 atoms)

##  Testing

Run all validation tests:
```bash
# Phase 0 tests (13 tests)
pytest server/tests/test_validators/test_geometry_analyzer.py -v

# Phase 1 tests (16 tests)
pytest server/tests/test_validators/test_constraints.py -v

# All validation tests (29 tests)
pytest server/tests/test_validators/ -v
```

**Expected:**
- Phase 0: 13/13 passed, ~107 seconds
- Phase 1: 16/16 passed, ~67 seconds
- Total: 29/29 passed, ~3 minutes
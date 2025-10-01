# Crystal Geometry Analysis System - Implementation Checklist

## Overview

This checklist tracks the implementation of a **geometric analysis tool** that provides LLM agents with accurate measurements and interpretive hints for iterative crystal structure refinement.

**Core Principle**: Measure accurately, suggest carefully, never prescribe specific coordinates.

---

## Implementation Standards

### 1. Code Reuse Strategy
**Priority**: Maximize use of existing robocrystallographer functionality

Based on robocrystallographer.pdf analysis, the following components are available:

| Feature Category | Robocrys Component | Our Usage Strategy |
|-----------------|-------------------|-------------------|
| **Dimensionality (0D/1D/2D/3D)** | `get_structure_components()` | Direct use via inheritance |
| **Coordination numbers** | `SiteAnalyzer` + `CrystalNN` | Inherit and extend |
| **Local geometry** | `SiteAnalyzer.get_geometry()` | Use directly, add RMSD calculations |
| **Polyhedra connectivity** | Next-neighbor analysis | Inherit logic, add quantification |
| **Bond lengths/angles** | Built-in bond analysis | Use directly |
| **Oxidation states** | `add_oxidation_state_by_guess()` | Use when available |
| **Space group/symmetry** | `SpacegroupAnalyzer` | Direct use |
| **Mineral prototype** | `MineralMatcher` | Optional enhancement |

**Implementation approach:**
- Inherit from robocrys classes where possible
- Extend (don't modify) robocrystallographer source code
- Add quantification layer (RMSD, deviation %) on top of robocrys analysis
- Create thin wrapper classes in `server/core/validators/`

### 2. Code Style Standards
**Style**: Production-ready release quality

- **Language**: English only (code, comments, docstrings)
- **Comments**: Minimal - code should be self-documenting
- **Naming**: Clear, concise variable/function names
- **Docstrings**: Brief, essential information only
- **Format**: Follow PEP 8, use type hints
- **Structure**: Clean separation of concerns

**Good example:**
```python
def calculate_rmsd_from_ideal(positions: np.ndarray, ideal_geometry: str) -> float:
    ideal_positions = IDEAL_GEOMETRIES[ideal_geometry]
    aligned = kabsch_align(positions, ideal_positions)
    return np.sqrt(np.mean((aligned - ideal_positions)**2))
```

**Bad example:**
```python
def calculate_rmsd_from_ideal(positions: np.ndarray, ideal_geometry: str) -> float:
    # First we need to get the ideal positions for this geometry type
    # This is stored in our IDEAL_GEOMETRIES constant dictionary
    ideal_positions = IDEAL_GEOMETRIES[ideal_geometry]

    # Now we align the actual positions to the ideal using Kabsch algorithm
    # This removes rotation/translation differences
    aligned = kabsch_align(positions, ideal_positions)

    # Finally calculate root mean square deviation
    # Lower RMSD means closer to ideal geometry
    return np.sqrt(np.mean((aligned - ideal_positions)**2))
```

### 3. Test-Driven Requirements
**Acceptance criteria**: Tests must pass before marking task complete

- Write tests before or during implementation
- Each component needs unit tests with expected inputs/outputs
- Include corner cases explicitly
- Test coverage target: >90%
- Tests must be deterministic and reproducible

**CRITICAL RULES**:
- ❌ **NO simplification** - Even if slow, implement full functionality
- ❌ **NO skipping tests** - All tests must pass, no pytest.mark.skip
- ❌ **NO workarounds** - Don't bypass issues with temporary solutions
- ✅ **Report blockers immediately** - If truly stuck, stop and report to user

### 4. Robocrystallographer Integration Points

Key classes to inherit/use:

```python
from robocrys import StructureCondenser, StructureDescriber
from robocrys.condense.site import SiteAnalyzer
from robocrys.condense.mineral import MineralMatcher
from pymatgen.analysis.local_env import CrystalNN

class GeometryAnalyzer(StructureCondenser):
    """Extends robocrys with quantitative deviation metrics"""

    def analyze_with_hints(self, structure):
        # Use parent class for basic analysis
        condensed = self.condense_structure(structure)

        # Add our quantification layer
        hints = self._generate_geometric_hints(condensed)
        return {"observations": condensed, "hints": hints}
```

---

## Implementation Phases

### Phase 0: Foundation ✅ COMPLETED

**Status**: All functionality implemented and tested
**Completion date**: 2025-09-30
**Test results**: 13/13 passed
**Git commit**: `ff54786`

#### 0.1 Core Geometric Measurement Engine ✅
**Objective**: Build accurate, universal measurement algorithms

**Files created:**
- [x] `server/core/validators/__init__.py`
- [x] `server/core/validators/geometry_analyzer.py` - Core measurement engine (285 lines)
- [x] `server/tests/test_validators/test_geometry_analyzer.py` - Unit tests (143 lines)
- [x] `server/api/structure_validation.py` - API endpoints
- [x] `examples/validation_examples/basic_validation.py` - Usage examples
- [x] `examples/validation_examples/debug_data_structure.py` - Debug tool
- [x] `examples/validation_examples/README.md` - Documentation

**Not created** (using robocrys instead):
- ~~`coordination_analyzer.py`~~ - Use robocrys SiteAnalyzer
- ~~`distance_calculator.py`~~ - Use robocrys distances dict
- ~~`angle_calculator.py`~~ - Use robocrys angles dict
- ~~`geometry_analysis.py`~~ - Direct dict output

**Key Implementations:**

**1. Robocrystallographer Integration** ✅
```python
class GeometryAnalyzer:
    def __init__(self):
        self.condenser = StructureCondenser()  # Use robocrys
        self.adaptor = AseAtomsAdaptor()
```

**Learned data structure:**
- `sites`: dict {site_index: site_data} (NOT list!)
- `nn`: list of neighbor indices (length = coordination)
- `distances`: {site_idx: {neighbor_idx: [distances]}}
- `geometry`: {"type": str, "likeness": float}

**2. Oxidation State Handling** ✅
```python
@staticmethod
def _strip_oxidation_state(element_str: str) -> str:
    """Remove oxidation state from element string (e.g., 'Cu0+' -> 'Cu')"""
    import re
    return re.sub(r'[\d\+\-]+$', '', element_str)
```

**3. Observation Extraction** ✅
```python
def calculate_cutoff_distance(element1: str, element2: str, tolerance: float = 1.3) -> float:
    """
    Calculate bonding cutoff based on covalent radii

    Args:
        element1, element2: Element symbols
        tolerance: Multiplier (default 1.3 = 30% tolerance)

    Returns:
        Cutoff distance in Angstroms
    """
    r1 = COVALENT_RADII[element1]
    r2 = COVALENT_RADII[element2]
    return tolerance * (r1 + r2)
```

**2. PBC-Aware Distance Calculator**
```python
def calculate_distance_pbc(atom1: Atom, atom2: Atom, cell: Cell) -> dict:
    """
    Calculate minimum image distance with PBC

    Returns:
        {
            "distance": float,
            "vector": np.array,
            "crosses_boundary": bool,
            "pbc_applied": [bool, bool, bool]
        }
    """
```

**3. Coordination Number Analyzer**
```python
def analyze_coordination(atom: Atom, structure: Atoms) -> dict:
    """
    Count neighbors within adaptive cutoff

    Returns:
        {
            "total_neighbors": int,
            "by_element": dict,
            "distances": list[float],
            "neighbor_indices": list[int],
            "neighbor_vectors": list[np.array],
            "cutoff_used": float
        }
    """
```

**Test Results:** ✅ All Passing
```python
# server/tests/test_validators/test_geometry_analyzer.py - 13/13 passed

✓ test_analyzer_initialization
✓ test_analyze_fcc_structure
✓ test_coordination_in_fcc - Cu coordination = 12
✓ test_molecule_dimensionality - H2O dimensionality = 0
✓ test_bond_length_statistics - Bond length extraction
✓ test_incomplete_coordination_hint
✓ test_constraint_checking_dimensionality
✓ test_constraint_checking_coordination
✓ test_constraint_failure
✓ test_structure_comparison
✓ test_observations_extraction
✓ test_site_geometry_analysis
✓ test_hint_confidence_levels
```

**Runtime**: ~105 seconds (robocrys is computation-intensive)

**Example outputs validated:**
- Cu FCC: 3D, Fm-3m, coord=12, cuboctahedral ✓
- H2O: 0D, H+O sites, bond statistics ✓
- Constraints: Dimensionality + coordination checking ✓

---

### Phase 1: Tolerance-Based Validation ✅ COMPLETED (2025-09-30)

**实际完成内容** (与原计划的差异):
- ✅ **ConstraintValidator** with 3-level feedback (passed/warning/violation)
- ✅ **Geometry likeness** using robocrys Order Parameters (OP 0.0-1.0)
- ✅ **Bond length/angle tolerance** ranges with element-specific thresholds
- ❌ **未实现Kabsch/RMSD** (原计划有，实际用OP代替 - 技术决策)
- ✅ **Comprehensive testing** (30+ scenarios with MP real structures)
- ✅ **Performance optimization** (primitive cell: 1-5s, suitable for LLM feedback)

**关键技术决策**:
1. **使用robocrys OP代替RMSD**:
   - Robocrys Order Parameter已提供0.0-1.0几何质量量化
   - 无需实现Kabsch alignment
   - 更快且与RMSD高度相关

2. **容差阈值 (5%/15%)**:
   - <5% 偏差: Silent pass (避免信息过载)
   - 5-15% 偏差: Warning (提醒LLM)
   - >15% 偏差: Violation (必须修复)

3. **元素特异性阈值**:
   - O: min_likeness=0.5 (天然较低OP)
   - Ti/Al: min_likeness=0.7 (标准金属)
   - 严格模式: min_likeness=0.9 (高精度)

**实现文件**:
- ✅ `server/core/validators/constraint_validator.py` (285行)
- ✅ `server/core/validators/geometry_hints.py` (238行)
- ✅ `server/core/validators/geometry_analyzer.py` (扩展: +geometry_likeness字段)
- ✅ `server/tests/test_validators/test_constraints.py` (16 tests, all passing)
- ✅ `examples/validation_examples/phase1_tolerance_demo.py` (6 demos)

**测试结果**:
- Phase 0 tests: 13/13 passed ✓
- Phase 1 tests: 16/16 passed ✓
- MP structures tested: BaTiO3, Al2O3, ZnS
- Perturbation tests: Bond stretch (0.95-1.20x), Random displacement (0-0.3Å)

**性能特性**:
- Primitive cell (<10 atoms): 1-5 seconds ✅ (LLM反馈可用)
- Supercell (40+ atoms): 60-180 seconds ⚠️ (最终验证)

**Git提交**: d4c4ef1, 19c99a1
**详细文档**: `docs/validation/PHASE1_VALIDATION_FINDINGS.md`, `docs/validation/PHASE1_SUMMARY.md`

---

### Phase 1 (Original Plan - For Reference)

#### 1.1 Coordination Analysis with Quantification
    """Test coordination in Cu(111) surface"""
    # Expected: Bulk atoms=12, surface atoms=9

def test_coordination_defect():
    """Test coordination with vacancy"""
    # Expected: Atoms near vacancy have reduced coordination

def test_empty_structure():
    """Test with 0 atoms"""
    # Expected: Graceful handling, no crash

def test_single_atom():
    """Test with 1 atom"""
    # Expected: coordination=0, no errors
```

**Acceptance criteria:**
- [ ] All unit tests pass
- [ ] Works for any element pair (periodic table coverage)
- [ ] Correct PBC handling (verified with known structures)
- [ ] Performance: <10ms for <1000 atoms

---

#### 0.2 Geometric Hint System
**Objective**: Provide interpretive suggestions with quantified deviations

**Files to create:**
- [ ] `server/core/validators/geometry_hints.py` - Hint generation
- [ ] `server/core/validators/polyhedra_analyzer.py` - Polyhedra geometry recognition
- [ ] `server/core/validators/ideal_geometries.py` - Reference geometries database

**Implementation requirements:**

**1. Ideal Geometry Database**
```python
IDEAL_GEOMETRIES = {
    "linear": {
        "coordination": 2,
        "angles": [180.0],
        "reference_vectors": [[1,0,0], [-1,0,0]]
    },
    "octahedral": {
        "coordination": 6,
        "angles": [90.0, 180.0],  # cis, trans
        "reference_vectors": [
            [1,0,0], [-1,0,0], [0,1,0],
            [0,-1,0], [0,0,1], [0,0,-1]
        ]
    },
    # ... more geometries
}
```

**2. RMSD Calculator**
```python
def calculate_rmsd_from_ideal(
    neighbor_vectors: list[np.array],
    ideal_geometry: str
) -> float:
    """
    Calculate RMSD from ideal geometry after optimal alignment

    Returns: RMSD in Angstroms
    """
```

**3. Hint Generator**
```python
def generate_geometric_hint(
    coordination_data: dict,
    element: str
) -> dict:
    """
    Generate interpretive hint with quantified deviations

    Returns:
        {
            "interpretation": str,
            "confidence": "high" | "probable" | "ambiguous",
            "metrics": {
                "rmsd_from_ideal": float,
                "deviation_percentage": float,
                ...
            },
            "note": str  # Human-readable assessment
        }
    """
```

**Key principle**: **NO specific coordinate suggestions**
- ✅ Direction: "Missing in -z direction"
- ❌ Position: "Add atom at [2.0, 3.0, 5.1]"

**Test plan:**
```python
# tests/test_validators/test_geometry_hints.py

def test_hint_perfect_octahedron():
    """Test hint for perfect octahedral geometry"""
    # Input: 6 neighbors in perfect Oh symmetry
    # Expected:
    #   interpretation="octahedral"
    #   confidence="high"
    #   rmsd < 0.05 Å

def test_hint_distorted_octahedron():
    """Test hint for Jahn-Teller distorted octahedron"""
    # Input: 6 neighbors, 4 short + 2 long bonds
    # Expected:
    #   interpretation="distorted_octahedral"
    #   confidence="high"
    #   rmsd > 0.2 Å
    #   distortion_type="Jahn-Teller"

def test_hint_incomplete_octahedron():
    """Test hint for 5-coordinate"""
    # Input: 5 neighbors in square pyramidal arrangement
    # Expected:
    #   interpretation="incomplete_octahedral"
    #   confidence="probable"
    #   missing_direction="-z" (NO coordinates)

def test_hint_ambiguous_5_coord():
    """Test ambiguous 5-coordination"""
    # Input: 5 neighbors, unclear if square pyramid or trigonal bipyramid
    # Expected:
    #   interpretation="5_coordinate_ambiguous"
    #   confidence="ambiguous"
    #   possibilities=[...] with RMSD for each

def test_hint_no_coordinates_in_output():
    """Ensure hints never suggest specific atomic positions"""
    # Expected: No [x,y,z] coordinates in any hint output
```

**Acceptance criteria:**
- [ ] All geometry types (2-12 coordination) handled
- [ ] Quantified deviations always provided
- [ ] NO specific atomic coordinates suggested
- [ ] Ambiguous cases explicitly marked

---

#### 0.3 API Endpoint Structure
**Objective**: Design clean, consistent API

**Files to create:**
- [ ] `server/api/analysis_routes.py` - Analysis endpoints
- [ ] `server/api/constraint_routes.py` - Constraint validation endpoints
- [ ] `server/api/comparison_routes.py` - Structure comparison endpoints

**Endpoints to implement:**

1. **`POST /api/structures/{id}/analyze`**
   - Returns: observations + geometric hints
   - Performance: <50ms (fast mode)

2. **`POST /api/structures/{id}/validate`**
   - Input: constraints (optional)
   - Returns: constraint satisfaction results

3. **`POST /api/structures/compare`**
   - Input: two structure IDs
   - Returns: changes between iterations

**Test plan:**
```python
# tests/test_api/test_analysis_endpoints.py

def test_analyze_endpoint_basic():
    """Test basic analysis request"""
    response = client.post("/api/structures/abc123/analyze")
    # Expected: 200, observations + hints

def test_analyze_without_hints():
    """Test analysis with hints disabled"""
    response = client.post(
        "/api/structures/abc123/analyze",
        json={"include_hints": false}
    )
    # Expected: observations only, no geometric_hint fields

def test_validate_with_constraints():
    """Test constraint validation"""
    # Expected: satisfied_fraction format ("8/12")

def test_compare_iterations():
    """Test structure comparison"""
    # Expected: coordination_changes tracked
```

**Acceptance criteria:**
- [ ] All endpoints return consistent JSON schema
- [ ] Performance targets met (<50ms, <200ms, <1000ms)
- [ ] Error handling (404, 400, 500) works correctly

---

### Phase 1: Core Measurement Implementation (Weeks 3-4)

#### 1.1 Coordination Number Validation
**Objective**: Accurate coordination counting for all structure types

**Implementation tasks:**
- [ ] Implement adaptive cutoff for all element pairs
- [ ] Handle periodic boundary conditions correctly
- [ ] Handle surface structures (no false positives)
- [ ] Handle defects (vacancies, interstitials)
- [ ] Provide neighbor vector information (not just counts)

**Test structures:**
- [ ] Bulk FCC Cu (all atoms CN=12)
- [ ] NaCl rocksalt (Na=6, Cl=6)
- [ ] Al2O3 corundum (Al=6, O=4)
- [ ] Cu(111) surface (mixed CN: 12, 9, 7)
- [ ] FCC with vacancy (11 near vacancy)
- [ ] Molecule (H2O, no PBC)

**Test plan:**
```python
def test_bulk_fcc_coordination():
    atoms = bulk('Cu', 'fcc', a=3.61) * (3, 3, 3)
    # Expected: All 108 Cu atoms have CN=12

def test_nacl_mixed_coordination():
    atoms = bulk('NaCl', 'rocksalt', a=5.64) * (2, 2, 2)
    # Expected: All Na atoms CN=6, all Cl atoms CN=6

def test_surface_coordination():
    surface = fcc111('Cu', size=(4, 4, 4), vacuum=10.0)
    # Expected:
    #   Bulk atoms: CN=12
    #   Surface atoms: CN=9
    #   Edge atoms: CN=7

def test_molecule_no_pbc():
    atoms = molecule('H2O')
    # Expected: O has 2 neighbors, H have 1 neighbor each
    # No periodic images

def test_partial_occupancy():
    # Atom with occupancy=0.5
    # Expected: Note in output about uncertainty
```

**Acceptance criteria:**
- [ ] False positive rate <2%
- [ ] False negative rate <1%
- [ ] All test structures pass
- [ ] Performance <10ms for <1000 atoms

---

#### 1.2 Bond Length and Angle Analysis
**Objective**: Accurate geometric measurements

**Implementation tasks:**
- [ ] Calculate all bond lengths with PBC
- [ ] Calculate all bond angles for each atom
- [ ] Provide statistical summaries (mean, std dev)
- [ ] Handle edge cases (linear molecules, overlapping atoms)

**Test plan:**
```python
def test_bond_lengths_pbc():
    """Test bonds across periodic boundaries"""
    # Test case: Atoms at cell edges
    # Expected: Correct minimum image distances

def test_angle_calculation():
    """Test angle calculations"""
    # Test case: Perfect tetrahedral CH4
    # Expected: All H-C-H angles = 109.47°

def test_overlapping_atoms():
    """Test with atoms too close"""
    # Test case: Two atoms at same position
    # Expected: Distance ~0, flagged in output
```

**Acceptance criteria:**
- [ ] Angle accuracy: ±0.5°
- [ ] Distance accuracy: ±0.01 Å
- [ ] All edge cases handled gracefully

---

#### 1.3 Constraint System Foundation
**Objective**: Framework for checking user-defined constraints

**Constraint types to implement:**
- [ ] `coordination_number` - Check CN for specific elements
- [ ] `bond_distance` - Check bond length ranges
- [ ] `bond_angle` - Check angle ranges
- [ ] `stoichiometry` - Check chemical formula
- [ ] `cell_volume` - Check unit cell size

**Test plan:**
```python
def test_coordination_constraint():
    """Test coordination number constraint"""
    constraint = {
        "type": "coordination_number",
        "target_element": "Al",
        "ligand_element": "O",
        "expected_coordination": 6,
        "tolerance": 0
    }
    # Expected: satisfied_fraction format

def test_conflicting_constraints():
    """Test detection of impossible constraint combinations"""
    # Constraints: CN=6, bond_length=1.5Å, cell=4Å
    # Expected: Compatibility check fails
```

**Acceptance criteria:**
- [ ] All 5 constraint types working
- [ ] Fraction notation ("8/12") used
- [ ] Constraint conflict detection works

---

### Phase 2: Enhanced Analysis (Weeks 5-6)

#### 2.1 Polyhedra Geometry Recognition
**Objective**: Identify common coordination geometries

**Geometries to support:**
- [ ] Linear (CN=2)
- [ ] Trigonal planar (CN=3)
- [ ] Tetrahedral (CN=4)
- [ ] Square planar (CN=4)
- [ ] Square pyramidal (CN=5)
- [ ] Trigonal bipyramidal (CN=5)
- [ ] Octahedral (CN=6)
- [ ] Pentagonal bipyramidal (CN=7)
- [ ] Cubic (CN=8)
- [ ] Higher coordination (CN=9-12)

**Test plan:**
```python
def test_octahedral_recognition():
    """Test octahedral geometry identification"""
    # Test cases:
    # 1. Perfect octahedron → RMSD < 0.05
    # 2. Distorted octahedron → RMSD > 0.2, note distortion
    # 3. Jahn-Teller → identify distortion type

def test_ambiguous_5_coord():
    """Test ambiguous 5-coordination"""
    # Expected: Multiple possibilities with RMSD comparison

def test_incomplete_coordination():
    """Test incomplete geometry detection"""
    # 5-coord that looks like incomplete octahedron
    # Expected:
    #   "incomplete_octahedral"
    #   missing_direction (NO coordinates)
    #   existing bond statistics
```

**Acceptance criteria:**
- [ ] All geometries 2-8 supported
- [ ] RMSD calculations accurate
- [ ] Ambiguous cases handled
- [ ] NO coordinate suggestions in output

---

#### 2.2 Change Tracking Between Iterations
**Objective**: Show what improved/worsened

**Implementation tasks:**
- [ ] Track atom additions/removals/movements
- [ ] Track coordination changes
- [ ] Track constraint satisfaction changes
- [ ] Highlight improvements vs. regressions

**Test plan:**
```python
def test_track_coordination_improvement():
    """Test tracking coordination fixes"""
    # Iteration 1: Al#5 has CN=5
    # Iteration 2: Al#5 has CN=6
    # Expected:
    #   change_type="improvement"
    #   old_coordination=5, new_coordination=6

def test_track_regression():
    """Test detection of worsened structure"""
    # Iteration 1: 10/12 atoms satisfy constraint
    # Iteration 2: 9/12 atoms satisfy constraint
    # Expected: regression detected

def test_unchanged_issue():
    """Test detection of stuck state"""
    # Iterations 1-3: Same violation
    # Expected: unchanged_issues=1 (report, don't intervene)
```

**Acceptance criteria:**
- [ ] All change types tracked
- [ ] Improvements highlighted
- [ ] Regressions detected
- [ ] No agent management (just report)

---

#### 2.3 Robocrystallographer Integration (Optional)
**Objective**: Enhanced analysis when available

**Implementation tasks:**
- [ ] ASE → pymatgen conversion
- [ ] Call robocrystallographer API
- [ ] Parse results into hints format
- [ ] Graceful fallback on failure

**Test plan:**
```python
def test_robocrys_success():
    """Test successful robocrys integration"""
    # Input: Well-formed Al2O3
    # Expected: polyhedra connectivity detected

def test_robocrys_failure_fallback():
    """Test fallback when robocrys fails"""
    # Input: Structure without oxidation states
    # Expected: Geometric hints still provided

def test_robocrys_optional():
    """Test that robocrys is truly optional"""
    # analysis_level="fast" should work without robocrys
```

**Acceptance criteria:**
- [ ] Integration working when possible
- [ ] Fallback working on failure
- [ ] Performance acceptable (<1s)

---

### Phase 3: Corner Case Handling (Weeks 7-8)

#### 3.1 Corner Case Test Suite
**Objective**: Handle all edge cases without false feedback

**Corner cases to test:**

**Structural:**
- [ ] Empty structure (0 atoms)
- [ ] Single atom
- [ ] Atoms at periodic boundaries
- [ ] Overlapping atoms (distance < 0.1 Å)
- [ ] Very large distances (no bonds)
- [ ] Mixed periodicity (2D material in 3D cell)

**Geometric:**
- [ ] Atoms exactly at cutoff distance
- [ ] Angles exactly 0° or 180°
- [ ] Highly distorted geometries
- [ ] Unusual coordination (CN > 12)
- [ ] Linear molecules (no planar reference)

**Physical:**
- [ ] Partial occupancy
- [ ] Mixed oxidation states
- [ ] Disordered structures
- [ ] Van der Waals gaps
- [ ] Surface structures
- [ ] Defects (vacancies, interstitials)

**Test plan:**
```python
def test_atoms_at_boundary():
    """Test atoms exactly at periodic boundary"""
    # Expected: Correct neighbor detection via PBC

def test_overlapping_atoms():
    """Test atoms at same position"""
    # Expected: distance=0 reported, flagged as severe overlap

def test_partial_occupancy():
    """Test atom with occupancy < 1.0"""
    # Expected: Note about uncertainty in coordination

def test_surface_structure():
    """Test surface slab"""
    # Expected: Lower coordination reported, not flagged as error
    # Let LLM decide if it's surface or defect

def test_vdw_gap():
    """Test layered material with large gap"""
    # Expected: Large inter-layer distance reported as fact
    # Hint: "Possible layered structure" (not error)
```

**Acceptance criteria:**
- [ ] All corner cases handled without crashes
- [ ] No false positives (<2%)
- [ ] Ambiguous cases marked as such
- [ ] Documentation of all corner case behavior

---

#### 3.2 Ambiguity Handling
**Objective**: Explicit handling of uncertain cases

**Ambiguous scenarios:**
1. 5-coordinate: square pyramid vs trigonal bipyramid
2. Distant neighbor: bonded or not?
3. Surface vs. defect: under-coordination
4. Distortion: intentional (Jahn-Teller) vs. error

**Response strategy:**
```python
{
  "geometric_hint": {
    "interpretation": "ambiguous_5_coordinate",
    "confidence": "ambiguous",
    "possibilities": [
      {"type": "square_pyramidal", "rmsd": 0.12},
      {"type": "trigonal_bipyramidal", "rmsd": 0.18}
    ],
    "note": "Both geometries possible, square pyramidal more likely (lower RMSD)"
  }
}
```

**Test plan:**
```python
def test_ambiguous_marked_clearly():
    """Test that ambiguous cases are marked"""
    # Expected: confidence="ambiguous" in output

def test_multiple_interpretations():
    """Test multiple possibilities provided"""
    # Expected: possibilities list with RMSD for each

def test_no_guessing():
    """Ensure system doesn't guess when uncertain"""
    # Expected: Report ambiguity, don't pick one
```

**Acceptance criteria:**
- [ ] All ambiguous scenarios identified
- [ ] Multiple possibilities provided with evidence
- [ ] No hidden guessing

---

### Phase 4: Performance Optimization (Weeks 9-10)

#### 4.1 Caching and Incremental Analysis
**Objective**: Speed up repeated analyses

**Optimization strategies:**
- [ ] Cache coordination calculations by structure hash
- [ ] Incremental updates (only re-analyze changed atoms)
- [ ] Lazy evaluation of expensive analyses
- [ ] Batch processing for multiple structures

**Test plan:**
```python
def test_cache_hit():
    """Test that repeated analysis uses cache"""
    # Analyze same structure twice
    # Expected: Second call <5ms

def test_incremental_update():
    """Test incremental analysis after small change"""
    # Move one atom
    # Expected: Only analyze affected neighborhood

def test_cache_invalidation():
    """Test cache correctly invalidated on change"""
    # Modify structure
    # Expected: New analysis, not stale cache
```

**Performance targets:**
- [ ] Fast mode: <50ms for <1000 atoms (95th percentile)
- [ ] Standard mode: <200ms for <1000 atoms
- [ ] Thorough mode: <1000ms for <1000 atoms
- [ ] Cache hit: <5ms

---

#### 4.2 Parallel Processing
**Objective**: Speed up analysis of large structures

**Implementation tasks:**
- [ ] Parallelize per-atom coordination analysis
- [ ] Parallelize constraint checking
- [ ] Thread-safe caching

**Test plan:**
```python
def test_parallel_speedup():
    """Test parallel processing improves performance"""
    # Large structure (2000 atoms)
    # Expected: <2x time vs. 1000 atoms (not 4x)

def test_thread_safety():
    """Test concurrent analyses don't interfere"""
    # Analyze multiple structures simultaneously
    # Expected: Correct results for all
```

**Acceptance criteria:**
- [ ] Speedup >1.5x on 4+ cores
- [ ] Thread-safe
- [ ] No race conditions

---

### Phase 5: Documentation and Testing (Weeks 11-12)

#### 5.1 API Documentation
**Files to create:**
- [ ] `docs/ANALYSIS_API.md` - Complete API reference
- [ ] `docs/CONSTRAINT_REFERENCE.md` - All constraint types
- [ ] `docs/MEASUREMENT_ALGORITHMS.md` - Algorithm details
- [ ] `docs/CORNER_CASES.md` - Edge case catalog

**Documentation requirements:**
- [ ] Every endpoint documented with examples
- [ ] All constraint types explained
- [ ] Corner case behavior documented
- [ ] Performance characteristics documented

---

#### 5.2 Example Scripts
**Files to create:**
- [ ] `examples/validation_examples/basic_analysis.py`
- [ ] `examples/validation_examples/constraint_validation.py`
- [ ] `examples/validation_examples/iterative_refinement.py`
- [ ] `examples/validation_examples/corner_cases.py`

**Each example must include:**
- [ ] Setup code
- [ ] Analysis request
- [ ] Expected output (pass case)
- [ ] Expected output (fail case)
- [ ] Explanation of results

---

#### 5.3 Comprehensive Test Suite
**Test coverage requirements:**
- [ ] Unit tests: >90% line coverage
- [ ] Integration tests: All API endpoints
- [ ] Performance tests: All performance targets
- [ ] Corner case tests: All identified edge cases

**Test categories:**
```
tests/
├── unit/
│   ├── test_coordination_analyzer.py
│   ├── test_distance_calculator.py
│   ├── test_angle_calculator.py
│   ├── test_geometry_hints.py
│   └── test_polyhedra_analyzer.py
├── integration/
│   ├── test_api_endpoints.py
│   ├── test_constraint_validation.py
│   └── test_structure_comparison.py
├── performance/
│   ├── benchmark_coordination.py
│   ├── benchmark_api_latency.py
│   └── test_performance_targets.py
└── corner_cases/
    ├── test_boundary_conditions.py
    ├── test_ambiguous_geometries.py
    └── test_edge_cases.py
```

**Acceptance criteria:**
- [ ] All tests passing
- [ ] Coverage targets met
- [ ] Performance benchmarks passing
- [ ] CI/CD pipeline working

---

## Success Metrics

### Accuracy Metrics
- [ ] **False positive rate**: <2% (valid structures flagged as problematic)
- [ ] **False negative rate**: <1% (invalid structures pass)
- [ ] **Measurement precision**:
  - Bond lengths: ±0.01 Å
  - Bond angles: ±0.5°
  - Coordination: exact count

### Performance Metrics
- [ ] **Fast mode**: <50ms for <1000 atoms (95th percentile)
- [ ] **Standard mode**: <200ms for <1000 atoms
- [ ] **Thorough mode**: <1000ms for <1000 atoms
- [ ] **API uptime**: 99.9%

### Reliability Metrics
- [ ] **Reproducibility**: 100% (same input → same output)
- [ ] **Corner case handling**: 0 crashes on edge cases
- [ ] **Constraint conflict detection**: 100% accuracy

### Integration Metrics
- [ ] **LLM usability**: >90% of hints are actionable
- [ ] **Iteration convergence**: Structures improve in >80% of test cases
- [ ] **No misleading feedback**: 0 cases of incorrect coordinate suggestions

---

## What This Checklist EXCLUDES

**Explicitly NOT building:**
- ❌ Agent stuck detection (framework responsibility)
- ❌ Human intervention alerts (framework responsibility)
- ❌ Automated structure fixes (LLM decides)
- ❌ Specific atomic position suggestions (too error-prone)
- ❌ One-shot template application (LLM iterates)
- ❌ Real-time WebSocket validation (on-demand only)
- ❌ 3D visualization of violations (separate concern)
- ❌ Structure type auto-classification (LLM declares intent)

---

## Acceptance Criteria for Each Phase

### Phase 0: Foundation
- [ ] All measurement algorithms implemented and tested
- [ ] Geometric hint system working without coordinate suggestions
- [ ] API structure defined
- [ ] Performance targets met for core functions

### Phase 1: Core Implementation
- [ ] Coordination, bond length, angle analysis working
- [ ] Constraint framework operational
- [ ] All test structures passing
- [ ] API endpoints functional

### Phase 2: Enhanced Analysis
- [ ] Polyhedra recognition working for 2-12 coordination
- [ ] Change tracking between iterations functional
- [ ] Robocrystallographer integration (optional) working

### Phase 3: Corner Cases
- [ ] All identified corner cases handled
- [ ] Ambiguous scenarios marked explicitly
- [ ] No false feedback cases

### Phase 4: Optimization
- [ ] Performance targets achieved
- [ ] Caching working correctly
- [ ] Parallel processing functional

### Phase 5: Completion
- [ ] All documentation complete
- [ ] All examples working
- [ ] Test coverage >90%
- [ ] System ready for production use

---

## Document Status

**Version**: 3.0 (Aligned with Geometric Analysis Tool design)
**Last Updated**: 2025-01-15
**Next Review**: Weekly during implementation

---

## Notes
- Each checkbox requires **passing tests** before checking
- Performance benchmarks re-run after each phase
- No coordinate suggestions anywhere in output
- System measures and suggests; LLM decides and executes
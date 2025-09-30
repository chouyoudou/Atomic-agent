# Crystal Geometry Analysis System - Design Specification

## Executive Summary

This is a **geometric analysis tool** that provides accurate, factual measurements of crystal structures. It helps LLM agents iteratively refine structures by reporting **observations** (what is measured) rather than **interpretations** (what it means).

**Core Principle**: Be a microscope, not a diagnostician. Provide clear data; let the LLM interpret.

---

## Design Philosophy

### Core Assumptions

1. **LLMs need facts + context**: Report measurements (facts) AND interpretive hints (suggestions)
   - **Observation**: "5 neighbors within 2.0 Å"
   - **Hint**: "Likely incomplete octahedron (6-coordinate expected, 1 missing, ~17% deviation from ideal)"
2. **LLMs iterate to converge**: Support 10-50 refinement cycles with consistent feedback
3. **Accuracy > Speed > Intelligence**: Correct measurements matter most
4. **Separate facts from suggestions**: Facts are authoritative, hints are suggestive

### What This System IS

- ✅ Geometric measurement tool (distances, angles, coordination)
- ✅ Observation reporter (factual data about structure)
- ✅ Constraint checker (if constraints provided)
- ✅ Change tracker (what improved/worsened between iterations)

### What This System IS NOT

- ❌ Structure classifier ("this is perovskite")
- ❌ Intent interpreter ("you probably meant octahedral")
- ❌ Agent manager (stuck detection, intervention)
- ❌ Automated fixer (one-shot template applications)

---

## 1. System Architecture

### 1.1 Three-Layer Analysis

```
┌──────────────────────────────────────────────────────┐
│         Layer 1: Observations (Always)               │
│  Pure geometric measurements - no interpretation     │
│  ├─ Distances between atoms                          │
│  ├─ Coordination numbers (neighbor counts)           │
│  ├─ Bond angles                                      │
│  └─ Cell parameters                                  │
└──────────────────────────────────────────────────────┘
                        │
                        ▼
┌──────────────────────────────────────────────────────┐
│    Layer 2: Constraint Checking (Optional)           │
│  If LLM provides constraints, check satisfaction     │
│  ├─ "All Al atoms should have 6 O neighbors"        │
│  └─ "Al-O distance should be 1.8-2.0 Å"            │
└──────────────────────────────────────────────────────┘
                        │
                        ▼
┌──────────────────────────────────────────────────────┐
│      Layer 3: Geometric Hints (Always Included)      │
│  Interpretive suggestions with quantified deviations │
│  ├─ "Likely incomplete octahedron (1/6 missing)"    │
│  ├─ "Deviation from ideal: RMSD=0.23 Å (~12%)"     │
│  └─ "Suggestion: +z direction gap (~2.1 Å)"        │
└──────────────────────────────────────────────────────┘
```

### 1.2 Analysis Modes

**Fast Mode (default):** <50ms for <1000 atoms
- Coordination counting
- Distance measurements
- Basic angle checks

**Standard Mode:** <200ms
- Above + symmetry detection
- Polyhedra geometry analysis

**Thorough Mode:** <1000ms
- Above + robocrystallographer integration
- Detailed connectivity analysis

---

## 2. API Design

### 2.1 Basic Geometric Analysis

**Endpoint:** `POST /api/structures/{id}/analyze`

**Request:**
```json
{
  "structure_id": "abc123",
  "analysis_level": "fast",
  "include_hints": true
}
```

**Note**: `include_hints` defaults to `true`. Hints provide interpretive context with quantified deviations.

**Response (observations + hints):**
```json
{
  "structure_id": "abc123",
  "timestamp": "2025-01-15T14:32:15Z",
  "observations": {
    "atoms": [
      {
        "index": 0,
        "element": "Al",
        "position": [0.0, 0.0, 0.0],
        "coordination": {
          "total_neighbors": 6,
          "by_element": {"O": 6},
          "distances": [1.89, 1.91, 1.92, 1.95, 1.98, 2.01],
          "neighbor_indices": [12, 13, 14, 15, 16, 17]
        },
        "geometry": {
          "neighbor_vectors": [
            [2.0, 0.0, 0.0],
            [-2.0, 0.0, 0.0],
            [0.0, 2.0, 0.0],
            [0.0, -2.0, 0.0],
            [0.0, 0.0, 2.0],
            [0.0, 0.0, -2.0]
          ]
        },
        "geometric_hint": {
          "interpretation": "octahedral",
          "confidence": "high",
          "metrics": {
            "rmsd_from_ideal_octahedron": 0.05,
            "bond_length_uniformity": 0.94,
            "angle_deviations": {
              "mean": 1.2,
              "max": 2.5
            }
          },
          "assessment": "Well-formed octahedron with minor distortions (~3% deviation)"
        }
      },
      {
        "index": 5,
        "element": "Al",
        "position": [2.0, 3.0, 4.0],
        "coordination": {
          "total_neighbors": 5,
          "by_element": {"O": 5},
          "distances": [1.89, 1.91, 1.95, 2.00, 2.01],
          "neighbor_indices": [20, 21, 22, 23, 24]
        },
        "geometry": {
          "neighbor_vectors": [
            [1.9, 0.1, 0.0],
            [-1.8, 0.2, 0.0],
            [0.0, 1.9, 0.1],
            [0.0, -2.0, 0.0],
            [0.1, 0.0, 2.0]
          ]
        },
        "geometric_hint": {
          "interpretation": "incomplete_octahedral",
          "confidence": "probable",
          "evidence": {
            "current_geometry": "square_pyramidal_like",
            "expected_geometry": "octahedral",
            "completeness": "5/6 coordination",
            "missing_direction": {
              "direction": "-z",
              "explanation": "Gap detected opposite to existing neighbor in +z direction"
            }
          },
          "metrics": {
            "rmsd_from_ideal_square_pyramid": 0.12,
            "rmsd_from_partial_octahedron": 0.08,
            "existing_bond_lengths": {
              "mean": 1.95,
              "std_dev": 0.05,
              "range": [1.89, 2.01]
            }
          },
          "deviation_quantification": {
            "from_ideal_octahedron": "~17% (1 of 6 neighbors missing)",
            "bond_length_variation": "0.05 Å (~2.6% relative std dev)"
          },
          "note": "If 6-coordinate octahedral is intended, consider adding ligand in -z direction"
        }
      }
    ],
    "cell": {
      "lattice_vectors": [
        [4.76, 0.0, 0.0],
        [0.0, 4.76, 0.0],
        [0.0, 0.0, 13.0]
      ],
      "volume": 294.896,
      "angles": [90.0, 90.0, 120.0]
    },
    "global_stats": {
      "total_atoms": 30,
      "composition": {"Al": 12, "O": 18},
      "formula": "Al2O3",
      "coordination_distribution": {
        "Al": {"4": 0, "5": 4, "6": 8},
        "O": {"2": 0, "3": 6, "4": 12}
      }
    }
  }
}
```

**Key design decisions:**
- **Observations** are factual measurements (distances, angles, counts)
- **Hints** provide geometric interpretations with quantified deviations
- Hints include:
  - Geometry type suggestions ("octahedral", "incomplete_octahedral")
  - Deviation metrics (RMSD, % deviation from ideal)
  - Missing direction indicators (e.g., "-z direction") **without specific coordinates**
  - Existing bond length statistics (mean, std dev, range)
  - Confidence levels (high, probable, ambiguous)
- **Hints do NOT include**:
  - Specific atomic positions (e.g., "add atom at [x,y,z]") - too error-prone
  - Automated fixes or modifications
  - Prescriptive actions beyond directional guidance
- Complete information (all neighbor vectors, not just counts)
- Reproducible (same structure → same output)

### 2.2 Constraint-Guided Analysis

**Endpoint:** `POST /api/structures/{id}/validate`

When LLM provides design constraints, check satisfaction:

**Request:**
```json
{
  "structure_id": "abc123",
  "constraints": [
    {
      "type": "coordination_number",
      "target_element": "Al",
      "ligand_element": "O",
      "expected_coordination": 6,
      "tolerance": 0
    },
    {
      "type": "bond_distance",
      "element_pair": ["Al", "O"],
      "min_distance": 1.8,
      "max_distance": 2.0
    }
  ]
}
```

**Response:**
```json
{
  "structure_id": "abc123",
  "constraint_results": [
    {
      "constraint_index": 0,
      "constraint_type": "coordination_number",
      "satisfied": false,
      "details": {
        "atoms_satisfying": 8,
        "atoms_violating": 4,
        "violating_atom_indices": [5, 7, 9, 11],
        "violations": [
          {
            "atom_index": 5,
            "observed_coordination": 5,
            "expected_coordination": 6,
            "difference": -1
          },
          {
            "atom_index": 7,
            "observed_coordination": 5,
            "expected_coordination": 6,
            "difference": -1
          }
        ]
      }
    },
    {
      "constraint_index": 1,
      "constraint_type": "bond_distance",
      "satisfied": true,
      "details": {
        "total_bonds_checked": 48,
        "bonds_in_range": 48,
        "bonds_out_of_range": 0
      }
    }
  ],
  "summary": {
    "all_constraints_satisfied": false,
    "satisfied_count": 1,
    "violated_count": 1
  }
}
```

**Key design decisions:**
- Constraints are **optional** (LLM provides them)
- Results are **fractions** ("8 out of 12 atoms satisfy")
- Specific atom indices provided for targeted fixes

### 2.3 Change Tracking Between Iterations

**Endpoint:** `POST /api/structures/{id}/compare`

Compare current structure with previous iteration:

**Request:**
```json
{
  "current_structure_id": "abc124",
  "previous_structure_id": "abc123"
}
```

**Response:**
```json
{
  "comparison": {
    "atoms_added": 1,
    "atoms_removed": 0,
    "atoms_moved": 2,
    "changes": [
      {
        "type": "atom_added",
        "atom_index": 25,
        "element": "O",
        "position": [1.0, 2.0, 6.1]
      },
      {
        "type": "atom_moved",
        "atom_index": 5,
        "old_position": [2.0, 3.0, 4.0],
        "new_position": [2.0, 3.0, 4.2],
        "displacement": 0.2
      }
    ],
    "coordination_changes": [
      {
        "atom_index": 5,
        "old_coordination": 5,
        "new_coordination": 6,
        "change": "+1",
        "interpretation": "improvement"
      }
    ],
    "constraint_satisfaction_changes": {
      "constraint_0": {
        "previous_satisfied_fraction": "8/12",
        "current_satisfied_fraction": "9/12",
        "change": "+1 atom now satisfies constraint"
      }
    }
  }
}
```

**Key design decisions:**
- Shows exactly what changed
- Highlights improvements vs. regressions
- Helps LLM understand if modifications helped

---

## 3. Geometric Analysis Methods

### 3.1 Coordination Number Analysis

**Method: Adaptive cutoff based on covalent radii**

```python
def analyze_coordination(atom, structure):
    """
    Count neighbors within bonding distance
    """
    element1 = atom.element
    neighbors = []

    for other_atom in structure:
        if other_atom.index == atom.index:
            continue

        element2 = other_atom.element
        distance = calculate_distance(atom, other_atom, use_pbc=True)

        # Adaptive cutoff: 1.3 × (r1 + r2)
        cutoff = 1.3 * (covalent_radius[element1] + covalent_radius[element2])

        if distance <= cutoff:
            neighbors.append({
                "index": other_atom.index,
                "element": element2,
                "distance": distance,
                "vector": other_atom.position - atom.position
            })

    return {
        "total_neighbors": len(neighbors),
        "by_element": group_by_element(neighbors),
        "distances": [n["distance"] for n in neighbors],
        "neighbor_indices": [n["index"] for n in neighbors],
        "cutoff_used": cutoff
    }
```

**Why this works:**
- Universal (works for any element pair)
- Transparent (reports cutoff used)
- Handles corner cases (periodic boundaries)

### 3.2 Bond Angle Analysis

```python
def analyze_angles(atom, neighbors):
    """
    Calculate all angles around central atom
    """
    angles = []

    for i in range(len(neighbors)):
        for j in range(i+1, len(neighbors)):
            vector1 = neighbors[i]["vector"]
            vector2 = neighbors[j]["vector"]

            angle = calculate_angle(vector1, vector2)

            angles.append({
                "atom_indices": [neighbors[i]["index"], atom.index, neighbors[j]["index"]],
                "angle": angle,
                "vector1_length": np.linalg.norm(vector1),
                "vector2_length": np.linalg.norm(vector2)
            })

    return {
        "angles": angles,
        "min_angle": min(a["angle"] for a in angles),
        "max_angle": max(a["angle"] for a in angles),
        "mean_angle": np.mean([a["angle"] for a in angles])
    }
```

### 3.3 Polyhedra Geometry Recognition with Quantified Deviations

**For "hints" layer (always included):**

```python
def identify_geometry_hint(neighbor_vectors, distances, element_pair):
    """
    Suggest possible geometry with quantified deviation metrics

    Returns: hint with interpretation + deviation quantification
    """
    n = len(neighbor_vectors)

    if n == 2:
        angle = calculate_angle(neighbor_vectors[0], neighbor_vectors[1])
        if 170 < angle < 190:
            deviation = abs(180 - angle)
            return {
                "interpretation": "linear",
                "confidence": "high",
                "metrics": {
                    "angle": angle,
                    "deviation_from_ideal": f"{deviation:.1f}° (~{deviation/180*100:.1f}%)"
                }
            }
        else:
            return {
                "interpretation": "bent",
                "confidence": "high",
                "metrics": {
                    "angle": angle,
                    "deviation_from_linear": f"{abs(180-angle):.1f}° (~{abs(180-angle)/180*100:.1f}%)"
                }
            }

    elif n == 4:
        # Check if square planar vs tetrahedral
        planar_score = check_planarity(neighbor_vectors)
        tetra_rmsd = calculate_tetrahedral_rmsd(neighbor_vectors)
        square_rmsd = calculate_square_planar_rmsd(neighbor_vectors)

        if planar_score > 0.9:
            return {
                "interpretation": "square_planar",
                "confidence": "probable",
                "metrics": {
                    "rmsd_from_ideal": square_rmsd,
                    "planarity_score": planar_score,
                    "deviation_percentage": f"~{square_rmsd/np.mean(distances)*100:.1f}%"
                },
                "assessment": f"Square planar geometry with {square_rmsd:.2f} Å RMSD from ideal"
            }
        else:
            return {
                "interpretation": "tetrahedral",
                "confidence": "probable",
                "metrics": {
                    "rmsd_from_ideal": tetra_rmsd,
                    "angle_deviations": calculate_angle_deviations(neighbor_vectors, ideal_tetrahedral=109.47),
                    "deviation_percentage": f"~{tetra_rmsd/np.mean(distances)*100:.1f}%"
                },
                "assessment": f"Tetrahedral geometry with {tetra_rmsd:.2f} Å RMSD from ideal"
            }

    elif n == 5:
        # Ambiguous - provide both interpretations with metrics
        sq_pyr_rmsd = calculate_square_pyramidal_rmsd(neighbor_vectors)
        trig_bip_rmsd = calculate_trigonal_bipyramidal_rmsd(neighbor_vectors)

        return {
            "interpretation": "5_coordinate_ambiguous",
            "confidence": "ambiguous",
            "possibilities": [
                {
                    "type": "square_pyramidal",
                    "rmsd": sq_pyr_rmsd,
                    "likelihood": "higher" if sq_pyr_rmsd < trig_bip_rmsd else "lower"
                },
                {
                    "type": "trigonal_bipyramidal",
                    "rmsd": trig_bip_rmsd,
                    "likelihood": "higher" if trig_bip_rmsd < sq_pyr_rmsd else "lower"
                }
            ],
            "note": f"Both geometries possible. Square pyramidal RMSD={sq_pyr_rmsd:.2f}Å, Trigonal bipyramidal RMSD={trig_bip_rmsd:.2f}Å"
        }

    elif n == 6:
        # Check octahedral symmetry with detailed metrics
        oct_rmsd = calculate_octahedral_rmsd(neighbor_vectors)
        bond_lengths = distances
        bond_std = np.std(bond_lengths)
        angle_deviations = calculate_angle_deviations(neighbor_vectors, ideal_octahedral=90.0)

        if oct_rmsd < 0.2:
            return {
                "interpretation": "octahedral",
                "confidence": "high",
                "metrics": {
                    "rmsd_from_ideal": oct_rmsd,
                    "bond_length_std_dev": bond_std,
                    "angle_deviations": angle_deviations,
                    "deviation_percentage": f"~{oct_rmsd/np.mean(bond_lengths)*100:.1f}%"
                },
                "assessment": f"Well-formed octahedron (RMSD={oct_rmsd:.2f}Å, ~{oct_rmsd/np.mean(bond_lengths)*100:.1f}% deviation)"
            }
        else:
            return {
                "interpretation": "distorted_octahedral",
                "confidence": "high",
                "metrics": {
                    "rmsd_from_ideal": oct_rmsd,
                    "bond_length_std_dev": bond_std,
                    "angle_deviations": angle_deviations,
                    "deviation_percentage": f"~{oct_rmsd/np.mean(bond_lengths)*100:.1f}%"
                },
                "assessment": f"Distorted octahedron (RMSD={oct_rmsd:.2f}Å, ~{oct_rmsd/np.mean(bond_lengths)*100:.1f}% deviation)",
                "distortion_type": identify_distortion_type(angle_deviations)  # e.g., "Jahn-Teller"
            }

    else:
        return {
            "interpretation": f"{n}_coordinate",
            "confidence": "certain",
            "note": f"No standard geometry template for {n}-coordination"
        }
```

**Key design decisions:**
- **Always provide quantified deviations** (RMSD, %, specific angles)
- Three confidence levels: `high` | `probable` | `ambiguous`
- Ambiguous cases provide multiple interpretations with comparison metrics
- Include distortion identification (Jahn-Teller, compression, etc.)
- All hints are suggestions (not authoritative facts)

---

## 4. Constraint System

### 4.1 Constraint Types

**Available constraint templates:**

```yaml
coordination_number:
  description: "Check coordination number for specific atoms"
  parameters:
    target_element: string
    ligand_element: string  # optional, default: any
    expected_coordination: int
    tolerance: int  # ±N neighbors

bond_distance:
  description: "Check bond lengths between element pairs"
  parameters:
    element_pair: [string, string]
    min_distance: float  # Å
    max_distance: float  # Å

bond_angle:
  description: "Check angles in specific bonding patterns"
  parameters:
    atom_triplet: [element, element, element]  # e.g., [O, Al, O]
    min_angle: float  # degrees
    max_angle: float  # degrees

stoichiometry:
  description: "Check chemical formula"
  parameters:
    expected_formula: string  # e.g., "Al2O3"
    allow_supercell: bool  # true = Al4O6 is valid

cell_volume:
  description: "Check unit cell volume"
  parameters:
    min_volume: float  # Ų
    max_volume: float  # Ų

symmetry:
  description: "Check space group symmetry"
  parameters:
    expected_space_group: string  # e.g., "R-3c"
    tolerance: float  # Å for symmetry detection
```

### 4.2 Constraint Satisfaction Reporting

**Use fraction notation:**

```json
{
  "constraint": "Al_octahedral_coordination",
  "satisfied_fraction": "8/12",
  "details": {
    "total_atoms_checked": 12,
    "atoms_satisfying": 8,
    "atoms_violating": 4,
    "violation_details": [
      {"atom_index": 5, "observed": 5, "expected": 6},
      {"atom_index": 7, "observed": 5, "expected": 6},
      {"atom_index": 9, "observed": 5, "expected": 6},
      {"atom_index": 11, "observed": 7, "expected": 6}
    ]
  }
}
```

---

## 5. Corner Case Handling

### 5.1 Ambiguous Geometries

**Scenario**: Atom with 5 neighbors - square pyramidal or incomplete octahedral?

**Response:**
```json
{
  "atom_index": 5,
  "coordination": {
    "total_neighbors": 5,
    "distances": [1.9, 1.9, 1.95, 2.0, 2.8]
  },
  "geometry_hint": {
    "determination": "ambiguous",
    "note": "5th neighbor at 2.8 Å is 40% beyond typical Al-O distance (2.0 Å)",
    "interpretations": [
      "square_pyramidal (5-coordinate is complete)",
      "incomplete_octahedral (6th neighbor missing or too far)"
    ],
    "recommendation": "Check if 6th neighbor exists beyond 2.8 Å cutoff"
  }
}
```

### 5.2 Surface Atoms

**Do not auto-detect surfaces**. Report observations:

```json
{
  "atom_index": 15,
  "coordination": {
    "total_neighbors": 9,
    "note": "Lower than bulk coordination (12 for FCC)"
  },
  "position_context": {
    "z_position": 0.5,
    "cell_z_height": 20.0,
    "note": "Atom near cell boundary in z-direction"
  }
}
```

Let LLM decide if this is a surface or defect.

### 5.3 Periodic Boundary Conditions

**Always handle PBC correctly:**

```python
def calculate_distance_pbc(atom1, atom2, cell):
    """
    Calculate minimum image distance accounting for PBC
    """
    vector = atom2.position - atom1.position

    # Apply minimum image convention
    for i in range(3):
        if cell.pbc[i]:  # This direction has periodic boundary
            vector[i] -= cell.lengths[i] * round(vector[i] / cell.lengths[i])

    distance = np.linalg.norm(vector)

    return {
        "distance": distance,
        "vector": vector,
        "pbc_applied": cell.pbc.tolist()
    }
```

### 5.4 Partial Occupancy

**Report as uncertainty:**

```json
{
  "atom_index": 10,
  "occupancy": 0.5,
  "note": "Partial occupancy - atom present only 50% of the time",
  "coordination": {
    "total_neighbors": 4,
    "note": "Coordination count assumes full occupancy"
  },
  "interpretation_guidance": "For 50% occupancy, average coordination may be 2-4 depending on structure"
}
```

### 5.5 Distortions (Jahn-Teller, etc.)

**Report measurements without judgment:**

```json
{
  "atom_index": 8,
  "element": "Mn",
  "coordination": {
    "total_neighbors": 6,
    "distances": [1.9, 1.9, 2.0, 2.0, 2.3, 2.3],
    "distance_distribution": {
      "mean": 2.067,
      "std_dev": 0.166,
      "note": "Large standard deviation suggests distorted geometry"
    }
  },
  "geometry_hint": {
    "hint": "distorted_octahedral",
    "note": "4 short bonds (1.9-2.0 Å) + 2 long bonds (2.3 Å) - consistent with Jahn-Teller distortion"
  }
}
```

---

## 6. Validation Profiles

### 6.1 Three Strictness Levels

```yaml
strict:
  description: "For publication-quality structures"
  bond_distance_tolerance: 0.10  # ±10%
  angle_tolerance: 5.0  # ±5°
  coordination_tolerance: 0  # Exact match
  report_warnings: true

standard:
  description: "For general refinement"
  bond_distance_tolerance: 0.20  # ±20%
  angle_tolerance: 10.0  # ±10°
  coordination_tolerance: 0  # Exact match
  report_warnings: false

relaxed:
  description: "For initial exploration"
  bond_distance_tolerance: 0.30  # ±30%
  angle_tolerance: 15.0  # ±15°
  coordination_tolerance: 1  # ±1 neighbor
  report_warnings: false
```

**Usage:**
```json
{
  "analysis_profile": "standard",
  "constraints": [...]
}
```

---

## 7. Robocrystallographer Integration

### 7.1 Optional Enhancement

**Robocrystallographer provides:**
- Automatic polyhedra detection
- Connectivity analysis (face/edge/corner sharing)
- Structure type classification

**But it:**
- Requires oxidation states (often unknown)
- May fail on partial structures
- Is slow (>100ms)

### 7.2 Lazy Evaluation Design

```python
def analyze_structure(atoms, use_robocrys=False):
    """
    Always compute geometric analysis.
    Optionally add robocrys interpretation.
    """
    # Layer 1: Always computed (fast)
    geometric_analysis = compute_geometry(atoms)

    # Layer 2: Optional enrichment (slow)
    if use_robocrys:
        try:
            robo_analysis = robocrystallographer_analyze(atoms)
            geometric_analysis["robocrys_interpretation"] = robo_analysis
        except Exception as e:
            geometric_analysis["robocrys_interpretation"] = {
                "status": "failed",
                "reason": str(e)
            }

    return geometric_analysis
```

**API usage:**
```json
{
  "analysis_level": "thorough",  // Triggers robocrys
  "robocrys_options": {
    "oxidation_states": {"Al": 3, "O": -2}  // Optional hint
  }
}
```

---

## 8. Implementation Priorities

### Phase 1: Core Measurement Engine (Weeks 1-3)

**Must have:**
1. ✅ Coordination number analysis (adaptive cutoff)
2. ✅ Distance measurements (with PBC)
3. ✅ Bond angle calculations
4. ✅ Constraint checking framework
5. ✅ Change tracking between iterations

**Explicitly NOT included:**
- ❌ Robocrystallographer integration
- ❌ Symmetry detection
- ❌ Structure type classification
- ❌ Automated fixes

### Phase 2: Enhanced Analysis (Weeks 4-6)

**Add if Phase 1 successful:**
1. Geometry hint system (octahedral, tetrahedral, etc.)
2. Polyhedra connectivity analysis
3. Basic symmetry detection
4. Robocrystallographer integration (optional)

### Phase 3: Optimization (Weeks 7-8)

1. Performance optimizations (caching, incremental)
2. Batch analysis API
3. Validation profile templates
4. WebSocket streaming for large structures

---

## 9. API Response Examples

### 9.1 Simple Structure Analysis

**Input**: Al2O3 structure with one incomplete Al coordination

**Response:**
```json
{
  "structure_id": "abc123",
  "observations": {
    "global_stats": {
      "formula": "Al2O3",
      "total_atoms": 30,
      "composition": {"Al": 12, "O": 18},
      "coordination_distribution": {
        "Al": {"5": 1, "6": 11},
        "O": {"4": 18}
      }
    },
    "atoms": [
      {
        "index": 5,
        "element": "Al",
        "position": [2.38, 0.0, 3.25],
        "coordination": {
          "total_neighbors": 5,
          "by_element": {"O": 5},
          "distances": [1.89, 1.91, 1.95, 1.98, 2.01],
          "neighbor_indices": [15, 16, 17, 18, 19],
          "cutoff_used": 2.6
        }
      }
    ]
  }
}
```

### 9.2 Constraint Validation

**Input**: Check if all Al atoms have octahedral coordination

**Response:**
```json
{
  "constraint_results": [
    {
      "constraint_type": "coordination_number",
      "satisfied": false,
      "details": {
        "satisfied_fraction": "11/12",
        "atoms_satisfying": 11,
        "atoms_violating": 1,
        "violations": [
          {
            "atom_index": 5,
            "observed_coordination": 5,
            "expected_coordination": 6,
            "difference": -1,
            "neighbor_details": {
              "existing_neighbors": [15, 16, 17, 18, 19],
              "distances": [1.89, 1.91, 1.95, 1.98, 2.01]
            }
          }
        ]
      }
    }
  ]
}
```

### 9.3 Iteration Comparison

**Input**: Compare iteration N with iteration N-1

**Response:**
```json
{
  "comparison": {
    "changes_summary": {
      "atoms_added": 1,
      "atoms_moved": 0,
      "atoms_removed": 0
    },
    "coordination_changes": [
      {
        "atom_index": 5,
        "old_coordination": 5,
        "new_coordination": 6,
        "change_type": "improvement",
        "new_neighbor": {
          "index": 25,
          "element": "O",
          "distance": 1.95
        }
      }
    ],
    "constraint_satisfaction_changes": {
      "Al_octahedral": {
        "old_fraction": "11/12",
        "new_fraction": "12/12",
        "status": "now_satisfied"
      }
    }
  }
}
```

---

## 10. Success Metrics

### Accuracy Metrics
- **False positive rate**: <2% (valid structures flagged as invalid)
- **False negative rate**: <1% (invalid structures pass validation)
- **Measurement precision**: Bond lengths ±0.01 Å, angles ±0.5°

### Performance Metrics
- **Fast mode**: <50ms for <1000 atoms (95th percentile)
- **Standard mode**: <200ms for <1000 atoms
- **Thorough mode**: <1000ms for <1000 atoms

### Reliability Metrics
- **API uptime**: 99.9%
- **Reproducibility**: Same structure → identical output (100%)
- **Corner case handling**: No crashes on edge cases

---

## 11. What This Design Eliminates

**Removed from previous design:**
- ❌ "Validation" terminology (now "analysis")
- ❌ Agent stuck detection (not our responsibility)
- ❌ Human intervention alerts (agent framework handles this)
- ❌ Template-based automated fixes (LLM makes decisions)
- ❌ Structure type auto-detection (LLM declares intent)
- ❌ Confidence scores on observations (facts have no confidence)
- ❌ One-shot template application (LLM iterates)

**Added clarity:**
- ✅ Three-layer architecture (observations, constraints, hints)
- ✅ Separation of facts from interpretations
- ✅ Change tracking between iterations
- ✅ Explicit handling of ambiguous cases
- ✅ Adaptive cutoff methods (universal applicability)
- ✅ Fraction notation for partial satisfaction

---

## Document Status

**Version**: 3.0 (Geometric Analysis Tool - Final)
**Last Updated**: 2025-01-15
**Replaces**: Version 2.0 (LLM-first design)
**Next Review**: After Phase 1 implementation

---

## Appendices

### Appendix A: Measurement Algorithms
See `docs/MEASUREMENT_ALGORITHMS.md` (to be created)

### Appendix B: Constraint Specification Reference
See `docs/CONSTRAINT_REFERENCE.md` (to be created)

### Appendix C: API Complete Reference
See `docs/ANALYSIS_API.md` (to be created)

### Appendix D: Corner Case Catalog
See `docs/CORNER_CASES.md` (to be created)
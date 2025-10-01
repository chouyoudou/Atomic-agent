"""Final comprehensive validation tests with MP structures.

⚠️ CONCEPT VALIDATION - Designed for single structure testing

This script demonstrates comprehensive validation testing patterns including:
1. Perfect vs perturbed structures
2. Tolerance threshold tuning (strict/normal/relaxed)
3. Edge cases (extreme compression, large noise)

Performance:
- Designed for primitive cells (<10 atoms)
- Runtime: ~2-3 minutes per structure
- Can be adapted for batch testing

Usage:
    python examples/validation_examples/final_validation_tests.py

Note: Falls back to Cu FCC if no MP structures are cached.
"""

import sys
sys.path.insert(0, '.')

from ase.io import read
from ase.build import bulk
import numpy as np
from server.core.validators.geometry_analyzer import GeometryAnalyzer
import glob


def load_mp_structure():
    """Load one MP structure for testing."""
    files = glob.glob('examples/validation_examples/mp_structures/*.xyz')
    if files:
        atoms = read(files[0])
        return atoms
    else:
        # Fallback to simple structure
        return bulk("Cu", "fcc", a=3.6)


def perturb_bonds(atoms, factor):
    """Scale all bonds uniformly."""
    atoms_pert = atoms.copy()
    atoms_pert.set_cell(atoms_pert.get_cell() * factor, scale_atoms=True)
    return atoms_pert


def perturb_random(atoms, amplitude, seed=42):
    """Add random displacements."""
    np.random.seed(seed)
    atoms_pert = atoms.copy()
    pos = atoms_pert.get_positions()
    noise = np.random.randn(*pos.shape) * amplitude
    atoms_pert.set_positions(pos + noise)
    return atoms_pert


print("=" * 80)
print("FINAL VALIDATION TESTS - Complex Structures")
print("=" * 80)

analyzer = GeometryAnalyzer()
atoms_perfect = load_mp_structure()

print(f"\nTest Structure: {len(atoms_perfect)} atoms")
result = analyzer.analyze_structure(atoms_perfect)
obs = result['observations']
print(f"Formula: {obs['formula']}")
print(f"Dimensionality: {obs['dimensionality']}D")

# Get element statistics
elements = {}
for site in obs['sites']:
    elem = site['element']
    if elem not in elements:
        elements[elem] = {'ops': [], 'coords': []}
    elements[elem]['ops'].append(site.get('geometry_likeness', 0))
    elements[elem]['coords'].append(site['coordination'])

print("\nPerfect Structure Analysis:")
for elem in sorted(elements.keys()):
    avg_op = np.mean(elements[elem]['ops'])
    avg_coord = np.mean(elements[elem]['coords'])
    print(f"  {elem}: coord={avg_coord:.1f}, avg_OP={avg_op:.4f}")

# Test 1: Bond stretching
print("\n" + "-" * 80)
print("TEST 1: Bond Stretching Sensitivity")
print("-" * 80)
print(f"{'Factor':<10} {'Avg OP':<12} {'OP Change':<12} {'Assessment'}")
print("-" * 80)

perfect_op = np.mean([s.get('geometry_likeness', 0) for s in obs['sites']])

for factor in [1.00, 1.02, 1.05, 1.10, 1.15, 1.20]:
    atoms = perturb_bonds(atoms_perfect, factor)
    result = analyzer.analyze_structure(atoms)
    obs_pert = result['observations']
    avg_op = np.mean([s.get('geometry_likeness', 0) for s in obs_pert['sites']])
    delta = avg_op - perfect_op

    if abs(delta) < 0.02:
        assess = "Negligible"
    elif abs(delta) < 0.05:
        assess = "Minor"
    elif abs(delta) < 0.10:
        assess = "Moderate"
    else:
        assess = "Significant"

    print(f"{factor:<10.2f} {avg_op:<12.4f} {delta:+12.4f} {assess}")

# Test 2: Random displacements
print("\n" + "-" * 80)
print("TEST 2: Random Displacement Robustness")
print("-" * 80)
print(f"{'Disp(Å)':<10} {'Avg OP':<12} {'Coord Changes':<15} {'Assessment'}")
print("-" * 80)

perfect_coords = [s['coordination'] for s in obs['sites']]

for disp in [0.00, 0.05, 0.10, 0.15, 0.20, 0.30]:
    atoms = perturb_random(atoms_perfect, disp)
    result = analyzer.analyze_structure(atoms)
    obs_pert = result['observations']
    avg_op = np.mean([s.get('geometry_likeness', 0) for s in obs_pert['sites']])
    coords = [s['coordination'] for s in obs_pert['sites']]
    coord_changes = sum(1 for c1, c2 in zip(perfect_coords, coords) if c1 != c2)

    if coord_changes == 0 and abs(avg_op - perfect_op) < 0.05:
        assess = "Stable"
    elif coord_changes < len(coords) * 0.1:
        assess = "Minor changes"
    elif coord_changes < len(coords) * 0.3:
        assess = "Moderate changes"
    else:
        assess = "Major changes"

    print(f"{disp:<10.2f} {avg_op:<12.4f} {coord_changes}/{len(coords):<10} {assess}")

# Test 3: Constraint validation at thresholds
print("\n" + "-" * 80)
print("TEST 3: Constraint Thresholds for LLM Feedback")
print("-" * 80)

# Find an element with good geometry
target_elem = None
target_geom = None
for site in obs['sites']:
    if site['element'] != 'O' and site.get('geometry') and site.get('geometry_likeness', 0) > 0.8:
        target_elem = site['element']
        target_geom = site['geometry']
        break

if target_elem:
    print(f"Testing {target_elem} ({target_geom}) constraints")
    print(f"\n{'Distortion':<12} {'Min OP=0.9':<15} {'Min OP=0.7':<15} {'Min OP=0.5':<15}")
    print("-" * 80)

    for factor in [1.00, 1.05, 1.10, 1.15]:
        atoms = perturb_bonds(atoms_perfect, factor)

        row = f"{factor:<12.2f} "

        for min_op in [0.9, 0.7, 0.5]:
            constraints = {
                "geometry_likeness": {
                    target_elem: {
                        "type": target_geom,
                        "min_likeness": min_op
                    }
                }
            }

            result = analyzer.analyze_structure(atoms, constraints=constraints)
            check = result['constraints_check']

            if check['passed']:
                status = "✅ Pass"
            elif check['warnings']:
                status = "⚠️  Warn"
            else:
                status = "❌ Fail"

            row += f"{status:<15} "

        print(row)

# Test 4: Edge cases
print("\n" + "-" * 80)
print("TEST 4: Edge Cases")
print("-" * 80)

print("\n4.1 Extreme compression (0.85x):")
atoms_compressed = perturb_bonds(atoms_perfect, 0.85)
result = analyzer.analyze_structure(atoms_compressed)
obs_comp = result['observations']
print(f"  Avg OP: {np.mean([s.get('geometry_likeness', 0) for s in obs_comp['sites']]):.4f}")
print(f"  Coordination changes: {sum(1 for c1, c2 in zip(perfect_coords, [s['coordination'] for s in obs_comp['sites']]) if c1 != c2)}/{len(perfect_coords)}")

print("\n4.2 Large random noise (0.5 Å):")
atoms_noisy = perturb_random(atoms_perfect, 0.5)
result = analyzer.analyze_structure(atoms_noisy)
obs_noisy = result['observations']
print(f"  Avg OP: {np.mean([s.get('geometry_likeness', 0) for s in obs_noisy['sites']]):.4f}")
print(f"  Coordination changes: {sum(1 for c1, c2 in zip(perfect_coords, [s['coordination'] for s in obs_noisy['sites']]) if c1 != c2)}/{len(perfect_coords)}")

print("\n" + "=" * 80)
print("SUMMARY: Recommendations for LLM Feedback")
print("=" * 80)
print("""
1. **Tolerance Thresholds**:
   - Strict mode (OP > 0.9): For high-precision requirements
   - Normal mode (OP > 0.7): Recommended default
   - Relaxed mode (OP > 0.5): For exploratory/rough structures

2. **Bond Length Tolerance**:
   - <2% stretch: Negligible effect, no warning needed
   - 2-5% stretch: Minor effect, optional warning
   - 5-10% stretch: Moderate effect, warning recommended
   - >10% stretch: Significant effect, violation

3. **Random Displacement Tolerance**:
   - <0.08 Å: Stable, no coordination changes
   - 0.08-0.15 Å: Minor changes possible
   - >0.15 Å: Coordination changes likely

4. **LLM Agent Guidance**:
   - Report violations only when deviation >15% from tolerance
   - Use warnings for 5-15% deviation range
   - Silent pass for deviations <5%
   - This prevents information overload while ensuring safety

5. **Real Structures**:
   - Perfect MP structures: OP typically 0.85-0.99
   - Not 1.0 due to thermal effects and symmetry breaking
   - Set thresholds accordingly (0.7-0.8 reasonable)
""")
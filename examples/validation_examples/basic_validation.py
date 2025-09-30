#!/usr/bin/env python3
"""
Basic validation example for GeometryAnalyzer.
Demonstrates analysis of simple structures (molecules and crystals).
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from ase.build import bulk, molecule
from server.core.validators import GeometryAnalyzer


def example_water_molecule():
    """Analyze water molecule (0D structure)"""
    print("\n" + "="*60)
    print("Example 1: Water Molecule (H2O)")
    print("="*60)

    analyzer = GeometryAnalyzer()
    water = molecule("H2O")

    result = analyzer.analyze_structure(water)
    obs = result["observations"]

    print(f"Dimensionality: {obs['dimensionality']}D")
    print(f"Formula: {obs['formula']}")
    print(f"Space group: {obs['spacegroup']}")
    print(f"\nSites ({len(obs['sites'])} unique):")

    for site in obs["sites"]:
        print(f"  {site['element']}: coord={site['coordination']}, geom={site['geometry']}")
        if site['bond_lengths']:
            bl = site['bond_lengths']
            print(f"    Bonds: {bl['mean']:.3f} ± {bl['std_dev']:.3f} Å ({bl['count']} total)")

    hints = result["hints"]
    print(f"\nHints: {len(hints)} issues detected")


def example_fcc_copper():
    """Analyze FCC copper crystal (3D structure)"""
    print("\n" + "="*60)
    print("Example 2: FCC Copper Crystal")
    print("="*60)

    analyzer = GeometryAnalyzer()
    cu = bulk("Cu", "fcc", a=3.6)

    result = analyzer.analyze_structure(cu)
    obs = result["observations"]

    print(f"Dimensionality: {obs['dimensionality']}D")
    print(f"Formula: {obs['formula']}")
    print(f"Space group: {obs['spacegroup']}")
    print(f"Crystal system: {obs['crystal_system']}")

    for site in obs["sites"]:
        print(f"\n{site['element']} site:")
        print(f"  Coordination: {site['coordination']}")
        print(f"  Geometry: {site['geometry']}")
        if site['bond_lengths']:
            bl = site['bond_lengths']
            print(f"  Bond lengths: {bl['mean']:.3f} ± {bl['std_dev']:.4f} Å")
            print(f"  Range: [{bl['min']:.3f}, {bl['max']:.3f}] Å")


def example_constraint_checking():
    """Demonstrate constraint validation"""
    print("\n" + "="*60)
    print("Example 3: Constraint Checking")
    print("="*60)

    analyzer = GeometryAnalyzer()
    cu = bulk("Cu", "fcc", a=3.6)

    constraints = {
        "dimensionality": 3,
        "coordination": {"Cu": 12}
    }

    result = analyzer.analyze_structure(cu, constraints=constraints)
    check = result["constraints_check"]

    print("Constraints defined:")
    print(f"  - Dimensionality: {constraints['dimensionality']}D")
    print(f"  - Cu coordination: {constraints['coordination']['Cu']}")

    print(f"\nResults:")
    print(f"  Passed: {len(check['passed'])}")
    for item in check['passed']:
        print(f"    ✓ {item['constraint']}: {item['actual']} == {item['expected']}")

    print(f"  Failed: {len(check['failed'])}")
    for item in check['failed']:
        print(f"    ✗ {item['constraint']}: {item['actual']} != {item['expected']}")


def example_structure_comparison():
    """Compare structures before and after modification"""
    print("\n" + "="*60)
    print("Example 4: Structure Comparison")
    print("="*60)

    analyzer = GeometryAnalyzer()

    cu_original = bulk("Cu", "fcc", a=3.6)
    cu_expanded = bulk("Cu", "fcc", a=3.7)

    comparison = analyzer.compare_structures(cu_original, cu_expanded)

    print("Original structure: a=3.6 Å")
    print("Modified structure: a=3.7 Å")
    print(f"\nObservation changes: {len(comparison['observations_delta'])}")

    hints_before = comparison['hints_delta']['before']
    hints_after = comparison['hints_delta']['after']
    resolved = comparison['hints_delta']['resolved_issues']

    print(f"Hints before: {len(hints_before)}")
    print(f"Hints after: {len(hints_after)}")
    print(f"Issues resolved: {resolved}")


if __name__ == "__main__":
    print("GeometryAnalyzer Basic Examples")
    print("=" * 60)

    example_water_molecule()
    example_fcc_copper()
    example_constraint_checking()
    example_structure_comparison()

    print("\n" + "="*60)
    print("All examples completed successfully ✓")
    print("="*60)
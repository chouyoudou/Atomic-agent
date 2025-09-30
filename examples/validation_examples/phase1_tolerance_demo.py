"""Phase 1: Tolerance-Based Constraint Validation Demo

Demonstrates the three-level feedback system:
- passed: within tolerance range
- warning: slightly outside (5-15%)
- violation: severely violating (>15%)
"""

from ase.build import bulk, molecule
from ase import Atoms
import numpy as np
from server.core.validators.geometry_analyzer import GeometryAnalyzer


def demo_perfect_structure():
    """Example 1: Perfect FCC Cu - all constraints pass"""
    print("=" * 60)
    print("Example 1: Perfect FCC Cu Structure")
    print("=" * 60)

    analyzer = GeometryAnalyzer()
    cu = bulk("Cu", "fcc", a=3.6)

    constraints = {
        "dimensionality": 3,
        "coordination": {"Cu": 12},
        "geometry_likeness": {
            "Cu": {
                "type": "cuboctahedral",
                "min_likeness": 0.9
            }
        }
    }

    result = analyzer.analyze_structure(cu, constraints=constraints)
    check = result["constraints_check"]

    print(f"\n✅ Passed: {len(check['passed'])}")
    for item in check["passed"]:
        print(f"  - {item['type']}: {item['detail']}")

    print(f"\n⚠️  Warnings: {len(check['warnings'])}")
    print(f"❌ Violations: {len(check['violations'])}")


def demo_bond_length_warning():
    """Example 2: Slightly distorted - warnings"""
    print("\n" + "=" * 60)
    print("Example 2: Bond Length Warning (Slight Deviation)")
    print("=" * 60)

    analyzer = GeometryAnalyzer()

    # Create water but check against slightly different constraint
    water = molecule("H2O")

    # Water O-H bonds are ~0.96 Å, we'll set constraint to 1.0-1.2 Å
    # This will trigger a warning
    constraints = {
        "bond_lengths": {
            "O-H": {
                "min": 1.0,
                "max": 1.2,
                "target": 1.1
            }
        }
    }

    result = analyzer.analyze_structure(water, constraints=constraints)
    check = result["constraints_check"]

    print(f"\n✅ Passed: {len(check['passed'])}")
    print(f"⚠️  Warnings: {len(check['warnings'])}")
    for item in check["warnings"]:
        print(f"  - {item['type']}: {item['detail']}")
        print(f"    Severity: {item['severity']}")
        print(f"    Suggestion: {item['suggestion']}")

    print(f"❌ Violations: {len(check['violations'])}")


def demo_severe_violation():
    """Example 3: Severe violation - dimensionality mismatch"""
    print("\n" + "=" * 60)
    print("Example 3: Severe Violation (Dimensionality Mismatch)")
    print("=" * 60)

    analyzer = GeometryAnalyzer()
    water = molecule("H2O")

    # Molecule is 0D, but we expect 3D - major violation
    constraints = {
        "dimensionality": 3
    }

    result = analyzer.analyze_structure(water, constraints=constraints)
    check = result["constraints_check"]

    print(f"\n✅ Passed: {len(check['passed'])}")
    print(f"⚠️  Warnings: {len(check['warnings'])}")
    print(f"❌ Violations: {len(check['violations'])}")
    for item in check["violations"]:
        print(f"  - {item['type']}: {item['detail']}")
        print(f"    Severity: {item['severity']}")
        print(f"    Suggestion: {item['suggestion']}")


def demo_geometry_likeness():
    """Example 4: Geometry likeness with order parameter"""
    print("\n" + "=" * 60)
    print("Example 4: Geometry Likeness (Order Parameter)")
    print("=" * 60)

    analyzer = GeometryAnalyzer()
    cu = bulk("Cu", "fcc", a=3.6)

    result = analyzer.analyze_structure(cu)
    obs = result["observations"]

    print("\nSite Analysis:")
    for site in obs["sites"]:
        print(f"\nElement: {site['element']}")
        print(f"  Coordination: {site['coordination']}")
        print(f"  Geometry: {site['geometry']}")
        print(f"  Order Parameter (Likeness): {site['geometry_likeness']:.4f}")
        print(f"  → {'Perfect' if site['geometry_likeness'] > 0.95 else 'Good' if site['geometry_likeness'] > 0.7 else 'Distorted'}")


def demo_tolerance_boundaries():
    """Example 5: Boundary testing"""
    print("\n" + "=" * 60)
    print("Example 5: Tolerance Boundaries")
    print("=" * 60)

    analyzer = GeometryAnalyzer()

    print("\nTesting different bond length scenarios:")
    print("-" * 60)

    test_cases = [
        ("Exactly at min", 1.6),
        ("Within range", 1.8),
        ("Exactly at max", 2.0),
        ("5% over (edge of warning)", 2.1),
        ("15% over (edge of violation)", 2.3),
        ("30% over (major violation)", 2.6),
    ]

    for description, bond_length in test_cases:
        # Create mock observation
        from server.core.validators.constraint_validator import ConstraintValidator

        validator = ConstraintValidator({
            "bond_lengths": {
                "C-O": {"min": 1.6, "max": 2.0, "target": 1.8}
            }
        })

        observations = {
            "sites": [
                {
                    "site_index": 0,
                    "element": "C",
                    "neighbors": [1],
                    "bond_lengths": {"mean": bond_length, "values": [bond_length]}
                },
                {
                    "site_index": 1,
                    "element": "O",
                    "neighbors": [0],
                    "bond_lengths": {}
                }
            ]
        }

        results = validator.validate(observations)

        status = "✅ PASS" if results["passed"] else \
                 "⚠️  WARN" if results["warnings"] else \
                 "❌ FAIL"

        print(f"{status} | {description:30s} | {bond_length:.2f} Å")


def demo_multiple_constraints():
    """Example 6: Multiple constraints simultaneously"""
    print("\n" + "=" * 60)
    print("Example 6: Multiple Constraints")
    print("=" * 60)

    analyzer = GeometryAnalyzer()
    cu = bulk("Cu", "fcc", a=3.6)

    constraints = {
        "dimensionality": 3,
        "coordination": {"Cu": 12},
        "bond_lengths": {
            "Cu-Cu": {
                "min": 2.4,
                "max": 2.7,
                "target": 2.55
            }
        },
        "geometry_likeness": {
            "Cu": {
                "type": "cuboctahedral",
                "min_likeness": 0.8
            }
        }
    }

    result = analyzer.analyze_structure(cu, constraints=constraints)
    check = result["constraints_check"]

    print("\nConstraint Validation Summary:")
    print(f"  ✅ Passed: {len(check['passed'])}")
    print(f"  ⚠️  Warnings: {len(check['warnings'])}")
    print(f"  ❌ Violations: {len(check['violations'])}")

    print("\nAll constraints:")
    all_results = check['passed'] + check['warnings'] + check['violations']
    for item in all_results:
        status = "✅" if item in check['passed'] else "⚠️ " if item in check['warnings'] else "❌"
        print(f"  {status} {item['type']}: {item['detail']}")


if __name__ == "__main__":
    print("\n")
    print("#" * 60)
    print("# Phase 1: Tolerance-Based Constraint Validation")
    print("#" * 60)

    demo_perfect_structure()
    demo_bond_length_warning()
    demo_severe_violation()
    demo_geometry_likeness()
    demo_tolerance_boundaries()
    demo_multiple_constraints()

    print("\n" + "=" * 60)
    print("Demo Complete!")
    print("=" * 60)
    print("\nKey Features Demonstrated:")
    print("  1. Three-level feedback (passed/warning/violation)")
    print("  2. Tolerance-based validation (5% / 15% thresholds)")
    print("  3. Order parameter quantification (robocrys OP)")
    print("  4. Multiple constraint types simultaneously")
    print("  5. Boundary testing and edge cases")
    print("\nNo Kabsch/RMSD needed - robocrys OP provides quantification!")
    print("=" * 60)
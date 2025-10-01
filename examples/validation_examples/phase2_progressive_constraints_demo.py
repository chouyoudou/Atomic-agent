"""Phase 2: Progressive Constraints and Freezing Demo

Demonstrates how an LLM agent can progressively add constraints
to prevent spatial cognition issues and protect completed work.

Workflow:
1. Initial structure - no constraints (free exploration)
2. Partial success - add constraints to lock good features
3. Freeze successful parts - prevent regression
4. Continue refinement with constraints
5. Final validation with all constraints
"""

import numpy as np
from ase.build import bulk
from ase import Atoms
from server.core.validators import (
    GeometryAnalyzer,
    ConstraintSuggester
)


def demo_progressive_workflow():
    """Demonstrate progressive constraint workflow for LLM agent."""
    print("=" * 70)
    print("Phase 2: Progressive Constraints and Freezing Workflow")
    print("=" * 70)

    # ==== Stage 1: Initial Structure (No Constraints) ====
    print("\n" + "=" * 70)
    print("Stage 1: Initial Exploration - No Constraints")
    print("=" * 70)

    # LLM agent creates initial BaTiO3-like structure
    atoms = bulk("Ti", "fcc", a=4.0, cubic=True)  # Starting point
    atoms.set_chemical_symbols(["Ti", "Ti", "Ti", "Ti"])

    analyzer = GeometryAnalyzer()
    result1 = analyzer.analyze_structure(atoms)

    print(f"\n✓ Created initial structure")
    print(f"  - Lattice: a={atoms.get_cell().lengths()[0]:.3f} Å")
    print(f"  - Atoms: {len(atoms)} Ti atoms")
    print(f"  - No constraints yet (free exploration)")

    # ==== Stage 2: Suggest Constraints Based on Current State ====
    print("\n" + "=" * 70)
    print("Stage 2: LLM Agent Analyzes Structure and Requests Constraint Suggestions")
    print("=" * 70)

    suggester = ConstraintSuggester()
    suggestions = suggester.suggest_constraints(
        atoms, result1["observations"], mode="normal"
    )

    print(f"\n🔍 Constraint Suggester analyzed structure:")
    print(f"\n  Suggested constraints:")
    for constraint_type, constraint_value in suggestions["constraints"].items():
        print(f"    - {constraint_type}: {constraint_value}")

    print(f"\n  Rationale:")
    for key, rationale in suggestions["rationale"].items():
        print(f"    - {key}: {rationale}")

    # ==== Stage 3: LLM Agent Adopts Lattice Constraints ====
    print("\n" + "=" * 70)
    print("Stage 3: LLM Agent Decides to Lock Lattice Parameters")
    print("=" * 70)

    # Agent decides: "I want to keep cubic symmetry, focus on atomic positions"
    constraints_stage3 = {
        "lattice": suggestions["constraints"].get("lattice", {}),
        "symmetry": suggestions["constraints"].get("symmetry", {})
    }

    print(f"\n💡 LLM Agent declares:")
    print(f"   'I want to optimize atomic positions while maintaining:")
    print(f"    - Cubic lattice (a={atoms.get_cell().lengths()[0]:.3f} Å)")
    print(f"    - Current symmetry'")

    result3 = analyzer.analyze_structure(atoms, constraints=constraints_stage3)
    check3 = result3["constraints_check"]

    print(f"\n✅ Validation results:")
    print(f"   Passed: {len(check3['passed'])}")
    print(f"   Warnings: {len(check3['warnings'])}")
    print(f"   Violations: {len(check3['violations'])}")

    # ==== Stage 4: Simulate Partial Success + Freezing ====
    print("\n" + "=" * 70)
    print("Stage 4: Partial Success - LLM Agent Freezes Good Features")
    print("=" * 70)

    # Simulate: Agent successfully placed first two atoms
    print(f"\n💭 LLM Agent reflects:")
    print(f"   'I'm happy with the positions of atoms 0 and 1.")
    print(f"    Let me freeze them so I don't accidentally break them'")

    # Save reference structure
    reference_atoms = atoms.copy()

    # Add freezing constraints
    constraints_stage4 = {
        **constraints_stage3,
        "frozen_atoms": [0, 1],  # Freeze first two atoms
    }

    print(f"\n🔒 Added freezing constraints:")
    print(f"   - frozen_atoms: [0, 1]")

    # ==== Stage 5: Simulate Modification + Freezing Violation ====
    print("\n" + "=" * 70)
    print("Stage 5: LLM Agent Modifies Structure (Accidentally Breaks Frozen Part)")
    print("=" * 70)

    # Simulate: Agent tries to optimize but accidentally moves frozen atom
    atoms_modified = atoms.copy()
    positions = atoms_modified.get_positions()
    positions[1] += [0.2, 0, 0]  # Oops! Moved frozen atom #1
    atoms_modified.set_positions(positions)

    print(f"\n⚠️  LLM Agent modified structure:")
    print(f"   - Moved atom #1 by 0.2 Å (VIOLATION!)")

    # Validate with freezing using constraint validator directly
    from server.core.validators import ConstraintValidator

    analyzer_temp = GeometryAnalyzer()
    result5_obs = analyzer_temp.analyze_structure(atoms_modified)

    validator5 = ConstraintValidator(
        constraints_stage4,
        atoms=atoms_modified,
        reference_atoms=reference_atoms
    )
    check5 = validator5.validate(
        result5_obs["observations"],
        reference_observations=result1["observations"]
    )

    print(f"\n❌ Validation results:")
    print(f"   Passed: {len(check5['passed'])}")
    print(f"   Warnings: {len(check5['warnings'])}")
    print(f"   Violations: {len(check5['violations'])}")

    for violation in check5["violations"]:
        if violation["type"] == "frozen_atom":
            print(f"\n   VIOLATION: {violation['detail']}")
            print(f"   Suggestion: {violation['suggestion']}")

    # ==== Stage 6: LLM Agent Responds to Violation ====
    print("\n" + "=" * 70)
    print("Stage 6: LLM Agent Reverts Frozen Atom")
    print("=" * 70)

    print(f"\n🤖 LLM Agent:")
    print(f"   'Oh! I violated the frozen constraint.")
    print(f"    Let me revert atom #1 to its original position'")

    # Revert
    positions[1] = reference_atoms.get_positions()[1]
    atoms_modified.set_positions(positions)

    result6_obs = analyzer_temp.analyze_structure(atoms_modified)

    validator6 = ConstraintValidator(
        constraints_stage4,
        atoms=atoms_modified,
        reference_atoms=reference_atoms
    )
    check6 = validator6.validate(
        result6_obs["observations"],
        reference_observations=result1["observations"]
    )

    print(f"\n✅ After revert - Validation results:")
    print(f"   Passed: {len(check6['passed'])}")
    print(f"   Warnings: {len(check6['warnings'])}")
    print(f"   Violations: {len(check6['violations'])}")

    # ==== Stage 7: Summary ====
    print("\n" + "=" * 70)
    print("Stage 7: Workflow Summary")
    print("=" * 70)

    print(f"\n📊 Progressive Constraint Workflow Demonstrated:")
    print(f"   1. ✓ Initial structure with no constraints")
    print(f"   2. ✓ Constraint suggestion based on current state")
    print(f"   3. ✓ LLM agent selectively adopts constraints")
    print(f"   4. ✓ LLM agent freezes successful features")
    print(f"   5. ✓ Violation detected when frozen part modified")
    print(f"   6. ✓ LLM agent responds and corrects violation")

    print(f"\n💡 Key Benefits:")
    print(f"   - LLM agent controls its own constraints")
    print(f"   - Prevents regression on completed work")
    print(f"   - Gradual refinement from rough to precise")
    print(f"   - Compensates for spatial cognition limitations")


def demo_freezing_types():
    """Demonstrate different types of freezing constraints."""
    print("\n\n" + "=" * 70)
    print("Bonus: Different Types of Freezing Constraints")
    print("=" * 70)

    atoms = bulk("Cu", "fcc", a=3.6, cubic=True)
    analyzer = GeometryAnalyzer()

    print(f"\n🔒 Freezing Constraint Types:")

    print(f"\n1. frozen_atoms: [0, 1, 2]")
    print(f"   → Atoms 0, 1, 2 should not move")

    print(f"\n2. frozen_bonds: [")
    print(f"     {{'atoms': [0, 1], 'length': 2.55}},")
    print(f"     {{'bond_type': 'Cu-Cu'}}")
    print(f"   ]")
    print(f"   → Specific bond and all Cu-Cu bonds frozen")

    print(f"\n3. frozen_angles: [")
    print(f"     {{'atoms': [0, 1, 2], 'angle': 60.0}},")
    print(f"     {{'triplet': 'Cu-Cu-Cu'}}")
    print(f"   ]")
    print(f"   → Specific angle and all Cu-Cu-Cu angles frozen")

    print(f"\n4. frozen_coordination: [0, 1]")
    print(f"   → Coordination of atoms 0 and 1 must remain unchanged")

    print(f"\n💡 Use Case:")
    print(f"   LLM Agent: 'I'm satisfied with the Ti-O bond lengths.")
    print(f"              Now let me optimize angles without changing bonds'")
    print(f"   → Add frozen_bonds constraint")
    print(f"   → Continue optimization safely")


if __name__ == "__main__":
    demo_progressive_workflow()
    demo_freezing_types()

    print("\n" + "=" * 70)
    print("Demo Complete!")
    print("=" * 70)
    print("\nThis demonstrates how Phase 2 validators help LLM agents:")
    print("  - Incrementally add constraints as design solidifies")
    print("  - Protect completed work from accidental modification")
    print("  - Compensate for spatial cognition weaknesses")
    print("  - Enable safe iterative refinement")

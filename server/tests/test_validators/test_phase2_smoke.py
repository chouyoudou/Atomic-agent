"""Smoke tests for Phase 2 validators.

Quick tests to ensure all new validators can be imported and instantiated.
Full validation logic tests will be added later.
"""

import pytest
from ase.build import bulk
from server.core.validators import (
    AngleConstraintValidator,
    LatticeConstraintValidator,
    SymmetryConstraintValidator,
    FreezingConstraintValidator,
    ConstraintSuggester
)


def test_angle_validator_import():
    """Test that AngleConstraintValidator can be imported and instantiated."""
    constraints = {
        "O-Ti-O": {"min": 85, "max": 95, "target": 90}
    }
    validator = AngleConstraintValidator(constraints)
    assert validator is not None
    assert validator.constraints == constraints


def test_lattice_validator_import():
    """Test that LatticeConstraintValidator can be imported and instantiated."""
    constraints = {
        "a": {"min": 3.5, "max": 3.7},
        "crystal_system": "cubic"
    }
    validator = LatticeConstraintValidator(constraints)
    assert validator is not None
    assert validator.constraints == constraints


def test_symmetry_validator_import():
    """Test that SymmetryConstraintValidator can be imported and instantiated."""
    constraints = {
        "space_group": 225,
        "point_group": "Oh"
    }
    validator = SymmetryConstraintValidator(constraints)
    assert validator is not None
    assert validator.constraints == constraints


def test_freezing_validator_import():
    """Test that FreezingConstraintValidator can be imported and instantiated."""
    constraints = {
        "frozen_atoms": [0, 1, 2],
        "frozen_bonds": []
    }
    cu = bulk("Cu", "fcc", a=3.6)
    validator = FreezingConstraintValidator(constraints, reference_atoms=cu)
    assert validator is not None
    assert validator.constraints == constraints
    assert validator.reference_atoms is not None


def test_constraint_suggester_import():
    """Test that ConstraintSuggester can be imported and instantiated."""
    suggester = ConstraintSuggester()
    assert suggester is not None


def test_lattice_validator_basic():
    """Test basic lattice validation on Cu FCC."""
    # Use cubic=True to get conventional cell (not primitive)
    cu = bulk("Cu", "fcc", a=3.6, cubic=True)

    cell = cu.get_cell()
    a = cell.lengths()[0]

    constraints = {
        "a": {"min": a * 0.98, "max": a * 1.02, "target": a},
        "crystal_system": "cubic"
    }

    validator = LatticeConstraintValidator(constraints)
    results = validator.validate(cu)

    assert "passed" in results
    assert "warnings" in results
    assert "violations" in results

    # Should pass cubic constraint
    assert len(results["passed"]) > 0


def test_symmetry_validator_basic():
    """Test basic symmetry validation on Cu FCC."""
    cu = bulk("Cu", "fcc", a=3.6)

    constraints = {
        "space_group": 225,  # Fm-3m
        "tolerance": 0.1
    }

    validator = SymmetryConstraintValidator(constraints)
    results = validator.validate(cu)

    assert "passed" in results
    assert "warnings" in results
    assert "violations" in results


def test_constraint_suggester_basic():
    """Test basic constraint suggestion on Cu FCC."""
    cu = bulk("Cu", "fcc", a=3.6)

    # Mock observations
    observations = {
        "dimensionality": 3,
        "sites": [
            {
                "element": "Cu",
                "coordination": 12,
                "geometry": {"type": "cuboctahedral", "likeness": 1.0}
            }
        ],
        "bond_statistics": {}
    }

    suggester = ConstraintSuggester()
    suggestions = suggester.suggest_constraints(cu, observations, mode="normal")

    assert "constraints" in suggestions
    assert "rationale" in suggestions
    assert "confidence" in suggestions

    # Should suggest dimensionality
    assert "dimensionality" in suggestions["constraints"]
    assert suggestions["constraints"]["dimensionality"] == 3

    # Should suggest coordination
    assert "coordination" in suggestions["constraints"]
    assert "Cu" in suggestions["constraints"]["coordination"]


def test_freezing_validator_basic():
    """Test basic freezing validation."""
    cu1 = bulk("Cu", "fcc", a=3.6)
    cu2 = cu1.copy()

    # Move one atom beyond threshold (0.1 Å)
    positions = cu2.get_positions()
    positions[0] += [0.15, 0, 0]  # Movement > 0.1 Å threshold
    cu2.set_positions(positions)

    constraints = {
        "frozen_atoms": [0]
    }

    validator = FreezingConstraintValidator(constraints, reference_atoms=cu1)
    observations = {"sites": []}  # Minimal observations
    results = validator.validate(cu2, observations)

    assert "passed" in results
    assert "warnings" in results
    assert "violations" in results

    # Atom 0 moved beyond threshold, should have a violation
    assert len(results["violations"]) > 0
    assert results["violations"][0]["type"] == "frozen_atom"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

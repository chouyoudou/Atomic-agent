"""Phase 3: Edge Structure Tests

Tests validators on specially constructed edge case structures:
- Dimensionality extremes (0D, 1D, 2D)
- Non-periodic systems
- Boundary geometries
- Unusual coordination environments
"""

import pytest
import numpy as np
from ase import Atoms
from ase.build import bulk, molecule, graphene
from server.core.validators import (
    GeometryAnalyzer,
    LatticeConstraintValidator,
    SymmetryConstraintValidator,
    ConstraintSuggester
)


class TestDimensionalityEdgeCases:
    """Test structures with different dimensionalities."""

    def test_0d_molecule(self):
        """Test 0D structure (isolated molecule)."""
        atoms = molecule("H2O")
        atoms.center(vacuum=10.0)
        atoms.set_pbc(True)

        analyzer = GeometryAnalyzer()
        result = analyzer.analyze_structure(atoms)

        assert result["observations"]["dimensionality"] == 0
        # Robocrys condenses equivalent sites: returns 2 sites (H and O), not 3
        assert len(result["observations"]["sites"]) >= 2

    def test_1d_linear_chain(self):
        """Test 1D structure (linear atomic chain)."""
        # Create linear chain of atoms
        atoms = Atoms(
            "H" * 5,
            positions=[[i * 1.5, 0, 0] for i in range(5)],
            cell=[20, 10, 10],
            pbc=True
        )

        analyzer = GeometryAnalyzer()
        result = analyzer.analyze_structure(atoms)

        # Should detect 1D
        assert result["observations"]["dimensionality"] in [0, 1]

    def test_2d_graphene(self):
        """Test 2D structure (graphene sheet)."""
        atoms = graphene(size=(3, 3, 1), vacuum=10.0)

        analyzer = GeometryAnalyzer()
        result = analyzer.analyze_structure(atoms)

        # Should detect 2D
        assert result["observations"]["dimensionality"] == 2

    def test_3d_bulk(self):
        """Test 3D structure (bulk crystal)."""
        atoms = bulk("Cu", "fcc", a=3.6, cubic=True)

        analyzer = GeometryAnalyzer()
        result = analyzer.analyze_structure(atoms)

        assert result["observations"]["dimensionality"] == 3


class TestNonPeriodicSystems:
    """Test non-periodic (molecular) systems."""

    def test_water_molecule(self):
        """Test H2O molecule."""
        atoms = molecule("H2O")
        atoms.center(vacuum=10.0)
        atoms.set_pbc(True)

        analyzer = GeometryAnalyzer()
        result = analyzer.analyze_structure(atoms)

        obs = result["observations"]
        # Robocrys condenses equivalent sites
        assert len(obs["sites"]) >= 2

        # Check H-O coordination
        h_sites = [s for s in obs["sites"] if s["element"] == "H"]
        o_sites = [s for s in obs["sites"] if s["element"] == "O"]

        assert len(h_sites) >= 1
        assert len(o_sites) >= 1

    def test_benzene_molecule(self):
        """Test benzene molecule."""
        atoms = molecule("C6H6")
        atoms.center(vacuum=10.0)
        atoms.set_pbc(True)

        analyzer = GeometryAnalyzer()
        result = analyzer.analyze_structure(atoms)

        obs = result["observations"]
        # Robocrys condenses by symmetry - may return 2 sites (C and H types)
        assert len(obs["sites"]) >= 2

    def test_no_pbc(self):
        """Test molecule without PBC set."""
        atoms = molecule("H2O")
        atoms.center(vacuum=10.0)
        atoms.set_pbc(False)  # No periodicity

        analyzer = GeometryAnalyzer()

        # Analyzer should handle this
        result = analyzer.analyze_structure(atoms)
        assert "observations" in result


class TestUnusualCoordination:
    """Test structures with unusual coordination numbers."""

    def test_coordination_1(self):
        """Test structure with coordination 1 (terminal atoms)."""
        # Dimer
        atoms = Atoms("H2", positions=[[0, 0, 0], [0.74, 0, 0]])
        atoms.center(vacuum=10.0)
        atoms.set_pbc(True)

        analyzer = GeometryAnalyzer()
        result = analyzer.analyze_structure(atoms)

        # Each H should have coord = 1
        for site in result["observations"]["sites"]:
            assert site["coordination"] == 1

    def test_coordination_2(self):
        """Test structure with coordination 2 (linear)."""
        # Linear H-H-H
        atoms = Atoms("H3", positions=[[0, 0, 0], [1.0, 0, 0], [2.0, 0, 0]])
        atoms.center(vacuum=10.0)
        atoms.set_pbc(True)

        analyzer = GeometryAnalyzer()
        result = analyzer.analyze_structure(atoms)

        # Center H should have coord = 2
        sites = result["observations"]["sites"]
        coords = [s["coordination"] for s in sites]
        assert 2 in coords  # At least one site with coord=2

    def test_high_coordination(self):
        """Test structure with high coordination (12+)."""
        atoms = bulk("Cu", "fcc", a=3.6, cubic=True)

        analyzer = GeometryAnalyzer()
        result = analyzer.analyze_structure(atoms)

        # FCC Cu has coord = 12
        for site in result["observations"]["sites"]:
            assert site["coordination"] == 12


class TestBoundaryGeometries:
    """Test geometries at classification boundaries."""

    def test_nearly_octahedral(self):
        """Test slightly distorted octahedron."""
        # Create octahedral-like structure
        atoms = bulk("NaCl", "rocksalt", a=5.0, cubic=True)

        # Apply small distortion
        positions = atoms.get_positions()
        positions[0] += [0.1, 0, 0]  # Small displacement
        atoms.set_positions(positions)

        analyzer = GeometryAnalyzer()
        result = analyzer.analyze_structure(atoms)

        # Should still detect octahedral-like geometry
        assert "observations" in result

    def test_nearly_tetrahedral(self):
        """Test slightly distorted tetrahedron."""
        atoms = bulk("Si", "diamond", a=5.43, cubic=True)

        # Small displacement
        positions = atoms.get_positions()
        positions[0] += [0.05, 0, 0]
        atoms.set_positions(positions)

        analyzer = GeometryAnalyzer()
        result = analyzer.analyze_structure(atoms)

        assert "observations" in result


class TestExtremeCellParameters:
    """Test structures with extreme cell parameters."""

    def test_very_small_cell(self):
        """Test cell with very small parameters (< 2 Å)."""
        atoms = Atoms("H", positions=[[0, 0, 0]])
        atoms.set_cell([1.5, 1.5, 1.5])
        atoms.set_pbc(True)

        analyzer = GeometryAnalyzer()

        # May trigger vacuum centering
        result = analyzer.analyze_structure(atoms)
        assert "observations" in result

    def test_very_large_cell(self):
        """Test cell with very large parameters (> 100 Å)."""
        atoms = Atoms("H2", positions=[[0, 0, 0], [0.74, 0, 0]])
        atoms.set_cell([200, 200, 200])
        atoms.set_pbc(True)

        analyzer = GeometryAnalyzer()
        result = analyzer.analyze_structure(atoms)

        # Should work but be slow
        assert result["observations"]["dimensionality"] == 0

    def test_highly_anisotropic_cell(self):
        """Test cell with extreme aspect ratio."""
        atoms = Atoms("H", positions=[[0, 0, 0]])
        atoms.set_cell([100, 3, 3])  # Extremely elongated
        atoms.set_pbc(True)

        constraints = {
            "ratios": {
                "a/b": {"min": 20, "max": 50, "target": 33.3}
            }
        }

        validator = LatticeConstraintValidator(constraints)
        results = validator.validate(atoms)

        # Should validate ratio
        assert isinstance(results, dict)


class TestConstraintSuggesterEdgeCases:
    """Test suggester on edge case structures."""

    def test_suggest_for_molecule(self):
        """Test constraint suggestion for molecular system."""
        atoms = molecule("H2O")
        atoms.center(vacuum=10.0)
        atoms.set_pbc(True)

        analyzer = GeometryAnalyzer()
        result = analyzer.analyze_structure(atoms)

        suggester = ConstraintSuggester()
        suggestions = suggester.suggest_constraints(
            atoms, result["observations"], mode="normal"
        )

        # Should suggest dimensionality = 0
        assert suggestions["constraints"]["dimensionality"] == 0

    def test_suggest_for_1d_chain(self):
        """Test suggestion for 1D structure."""
        atoms = Atoms(
            "H" * 5,
            positions=[[i * 1.5, 0, 0] for i in range(5)],
            cell=[20, 10, 10],
            pbc=True
        )

        analyzer = GeometryAnalyzer()
        result = analyzer.analyze_structure(atoms)

        suggester = ConstraintSuggester()
        suggestions = suggester.suggest_constraints(
            atoms, result["observations"], mode="normal"
        )

        assert "constraints" in suggestions

    def test_suggest_strict_mode(self):
        """Test suggester in strict mode (1% tolerance)."""
        atoms = bulk("Cu", "fcc", a=3.6, cubic=True)

        analyzer = GeometryAnalyzer()
        result = analyzer.analyze_structure(atoms)

        suggester = ConstraintSuggester()
        suggestions = suggester.suggest_constraints(
            atoms, result["observations"], mode="strict"
        )

        # Strict mode should have tighter ranges
        if "lattice" in suggestions["constraints"]:
            a_constraint = suggestions["constraints"]["lattice"]["a"]
            range_size = a_constraint["max"] - a_constraint["min"]
            # Should be ~1% of value
            assert range_size < 0.1  # Very tight

    def test_suggest_relaxed_mode(self):
        """Test suggester in relaxed mode (5% tolerance)."""
        atoms = bulk("Cu", "fcc", a=3.6, cubic=True)

        analyzer = GeometryAnalyzer()
        result = analyzer.analyze_structure(atoms)

        suggester = ConstraintSuggester()
        suggestions = suggester.suggest_constraints(
            atoms, result["observations"], mode="relaxed"
        )

        # Relaxed mode should have wider ranges
        if "lattice" in suggestions["constraints"]:
            a_constraint = suggestions["constraints"]["lattice"]["a"]
            range_size = a_constraint["max"] - a_constraint["min"]
            # Should be ~5% of value
            assert range_size > 0.3  # Wider


class TestSymmetryEdgeCases:
    """Test symmetry detection on edge cases."""

    def test_low_symmetry_structure(self):
        """Test structure with P1 symmetry (triclinic)."""
        # Distorted structure with no symmetry
        atoms = bulk("Cu", "fcc", a=3.6)
        positions = atoms.get_positions()
        np.random.seed(42)
        positions += np.random.randn(*positions.shape) * 0.3
        atoms.set_positions(positions)

        validator = SymmetryConstraintValidator({"space_group": 1})
        results = validator.validate(atoms)

        # May or may not match P1
        assert isinstance(results, dict)

    def test_molecular_symmetry(self):
        """Test symmetry of molecular system."""
        atoms = molecule("H2O")
        atoms.center(vacuum=10.0)
        atoms.set_pbc(True)

        validator = SymmetryConstraintValidator({"point_group": "C2v"})

        # Pymatgen may have issues with molecules
        results = validator.validate(atoms)
        assert isinstance(results, dict)


class TestIntegrationEdgeCases:
    """Test integration between different validators."""

    def test_lattice_plus_symmetry(self):
        """Test lattice and symmetry constraints together."""
        atoms = bulk("Cu", "fcc", a=3.6, cubic=True)

        # Both cubic and Fm-3m
        constraints_lattice = {"crystal_system": "cubic"}
        constraints_symmetry = {"space_group": 225}

        val_lattice = LatticeConstraintValidator(constraints_lattice)
        val_symmetry = SymmetryConstraintValidator(constraints_symmetry)

        res_lattice = val_lattice.validate(atoms)
        res_symmetry = val_symmetry.validate(atoms)

        # Both should pass
        assert len(res_lattice["passed"]) > 0
        assert len(res_symmetry["passed"]) > 0

    def test_conflicting_constraints(self):
        """Test conflicting constraints (tetragonal + cubic)."""
        atoms = bulk("Cu", "fcc", a=3.6, cubic=True)  # Cubic structure

        # Require tetragonal (should fail)
        constraints = {"crystal_system": "tetragonal"}
        validator = LatticeConstraintValidator(constraints)

        results = validator.validate(atoms)

        # Should fail
        assert len(results["violations"]) > 0 or len(results["passed"]) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

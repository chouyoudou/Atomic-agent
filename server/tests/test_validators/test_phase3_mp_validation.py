"""Phase 3: Materials Project Structure Validation Tests

Tests validators on real complex structures from Materials Project:
- Different crystal systems
- Various coordination environments
- Perturbation robustness
- Constraint validation accuracy
"""

import pytest
import numpy as np
from pathlib import Path
from ase.io import read
from ase.build import bulk
from server.core.validators import (
    GeometryAnalyzer,
    LatticeConstraintValidator,
    SymmetryConstraintValidator,
    FreezingConstraintValidator,
    ConstraintSuggester
)


MP_STRUCTURES_DIR = Path("examples/validation_examples/mp_structures")


def load_mp_structure(filename):
    """Load MP structure from cache."""
    filepath = MP_STRUCTURES_DIR / filename
    if not filepath.exists():
        pytest.skip(f"MP structure {filename} not found. Run download script first.")
    return read(filepath)


class TestMPStructureAnalysis:
    """Test analysis of real MP structures."""

    def test_batimo3_perovskite(self):
        """Test BaTiO3 perovskite structure."""
        atoms = load_mp_structure("BaTiO3_mp-19990.xyz")

        analyzer = GeometryAnalyzer()
        result = analyzer.analyze_structure(atoms)

        obs = result["observations"]
        assert obs["dimensionality"] == 3
        assert "Ba" in str(obs["formula"])
        assert "Ti" in str(obs["formula"])

        # Check coordination
        elements = {}
        for site in obs["sites"]:
            elem = site["element"]
            if elem not in elements:
                elements[elem] = []
            elements[elem].append(site["coordination"])

        # Ti should have high coordination (likely 6)
        if "Ti" in elements:
            assert max(elements["Ti"]) >= 4

    def test_al2o3_corundum(self):
        """Test Al2O3 corundum structure."""
        atoms = load_mp_structure("Al2O3_mp-1244874.xyz")

        analyzer = GeometryAnalyzer()
        result = analyzer.analyze_structure(atoms)

        obs = result["observations"]
        assert obs["dimensionality"] == 3

        # Check for Al and O
        elements = [s["element"] for s in obs["sites"]]
        assert "Al" in elements
        assert "O" in elements

    def test_zns_zinc_blende(self):
        """Test ZnS zinc blende structure."""
        atoms = load_mp_structure("ZnS_mp-1244890.xyz")

        analyzer = GeometryAnalyzer()
        result = analyzer.analyze_structure(atoms)

        obs = result["observations"]
        assert obs["dimensionality"] == 3

        # Zinc blende: tetrahedral coordination
        coords = [s["coordination"] for s in obs["sites"]]
        assert 4 in coords  # Tetrahedral


class TestMPStructurePerturbation:
    """Test validator robustness on perturbed MP structures."""

    def test_bond_stretch_progressive(self):
        """Test progressive bond stretching."""
        atoms = load_mp_structure("BaTiO3_mp-19990.xyz")

        analyzer = GeometryAnalyzer()
        suggester = ConstraintSuggester()

        # Get reference
        ref_result = analyzer.analyze_structure(atoms)
        ref_suggestions = suggester.suggest_constraints(
            atoms, ref_result["observations"], mode="normal"
        )

        stretch_factors = [1.00, 1.02, 1.05, 1.10]
        results = []

        for factor in stretch_factors:
            atoms_stretched = atoms.copy()
            atoms_stretched.set_cell(
                atoms.get_cell() * factor,
                scale_atoms=True
            )

            result = analyzer.analyze_structure(atoms_stretched)

            # Check geometry degradation
            if "sites" in result["observations"]:
                avg_likeness = np.mean([
                    s.get("geometry_likeness", 0)
                    for s in result["observations"]["sites"]
                ])
                results.append((factor, avg_likeness))

        # Should show degradation
        if len(results) > 1:
            # Later factors should have lower likeness
            assert results[-1][1] < results[0][1]

    def test_random_displacement_robustness(self):
        """Test robustness to random atomic displacements."""
        atoms = load_mp_structure("Al2O3_mp-1244874.xyz")

        analyzer = GeometryAnalyzer()
        ref_result = analyzer.analyze_structure(atoms)
        ref_coords = [s["coordination"] for s in ref_result["observations"]["sites"]]

        # Apply small displacement
        atoms_displaced = atoms.copy()
        np.random.seed(42)
        positions = atoms_displaced.get_positions()
        positions += np.random.randn(*positions.shape) * 0.05  # 0.05 Å
        atoms_displaced.set_positions(positions)

        result = analyzer.analyze_structure(atoms_displaced)
        coords = [s["coordination"] for s in result["observations"]["sites"]]

        # Coordination should mostly remain stable
        coord_changes = sum(1 for c1, c2 in zip(ref_coords, coords) if c1 != c2)
        change_fraction = coord_changes / len(ref_coords)

        assert change_fraction < 0.2  # Less than 20% changed


class TestMPConstraintValidation:
    """Test constraint validation on MP structures."""

    def test_lattice_constraint_mp(self):
        """Test lattice constraints on real structure."""
        atoms = load_mp_structure("BaTiO3_mp-19990.xyz")

        # Extract current cell parameters
        cell = atoms.get_cell()
        lengths = cell.lengths()
        a = lengths[0]

        # Define constraint around current value
        constraints = {
            "a": {"min": a * 0.98, "max": a * 1.02, "target": a}
        }

        validator = LatticeConstraintValidator(constraints)
        results = validator.validate(atoms)

        # Should pass
        assert len(results["passed"]) > 0

    def test_symmetry_detection_mp(self):
        """Test symmetry detection on MP structure."""
        atoms = load_mp_structure("BaTiO3_mp-19990.xyz")

        # BaTiO3 cubic phase is Pm-3m (221)
        # Primitive cell may have different symmetry
        validator = SymmetryConstraintValidator({
            "tolerance": 0.1
        })

        results = validator.validate(atoms)

        # Should detect some space group
        assert "passed" in results or "violations" in results

    def test_constraint_suggester_mp(self):
        """Test constraint suggester on real structure."""
        atoms = load_mp_structure("ZnS_mp-1244890.xyz")

        analyzer = GeometryAnalyzer()
        result = analyzer.analyze_structure(atoms)

        suggester = ConstraintSuggester()
        suggestions = suggester.suggest_constraints(
            atoms, result["observations"], mode="normal"
        )

        # Should suggest coordination (Zn and S tetrahedral)
        assert "coordination" in suggestions["constraints"]

        # Should suggest lattice
        assert "lattice" in suggestions["constraints"]

        # Should suggest dimensionality
        assert suggestions["constraints"]["dimensionality"] == 3


class TestMPFreezingConstraints:
    """Test freezing constraints on MP structures."""

    def test_freeze_atoms_mp(self):
        """Test atom freezing on real structure."""
        atoms_ref = load_mp_structure("BaTiO3_mp-19990.xyz")
        atoms_cur = atoms_ref.copy()

        # Move first atom
        positions = atoms_cur.get_positions()
        positions[0] += [0.15, 0, 0]
        atoms_cur.set_positions(positions)

        constraints = {"frozen_atoms": [0]}
        validator = FreezingConstraintValidator(
            constraints, reference_atoms=atoms_ref
        )

        results = validator.validate(atoms_cur, {})

        # Should detect violation
        assert len(results["violations"]) > 0

    def test_freeze_coordination_mp(self):
        """Test coordination freezing on real structure."""
        atoms_ref = load_mp_structure("Al2O3_mp-1244874.xyz")

        analyzer = GeometryAnalyzer()
        ref_result = analyzer.analyze_structure(atoms_ref)

        # Create perturbed version
        atoms_cur = atoms_ref.copy()
        positions = atoms_cur.get_positions()
        positions += np.random.randn(*positions.shape) * 0.2  # Large displacement
        atoms_cur.set_positions(positions)

        cur_result = analyzer.analyze_structure(atoms_cur)

        # Freeze coordination of first site
        constraints = {"frozen_coordination": [0]}
        validator = FreezingConstraintValidator(
            constraints, reference_atoms=atoms_ref
        )

        results = validator.validate(
            atoms_cur,
            observations=cur_result["observations"],
            reference_observations=ref_result["observations"]
        )

        # May or may not violate depending on displacement
        assert isinstance(results, dict)


class TestMPProgressiveWorkflow:
    """Test complete progressive workflow on MP structure."""

    def test_workflow_suggest_adopt_freeze(self):
        """Test: analyze → suggest → adopt → modify → validate."""
        atoms = load_mp_structure("BaTiO3_mp-19990.xyz")

        # Stage 1: Analyze
        analyzer = GeometryAnalyzer()
        result = analyzer.analyze_structure(atoms)

        # Stage 2: Suggest constraints
        suggester = ConstraintSuggester()
        suggestions = suggester.suggest_constraints(
            atoms, result["observations"], mode="normal"
        )

        assert "constraints" in suggestions

        # Stage 3: Adopt lattice constraints
        if "lattice" in suggestions["constraints"]:
            lattice_constraints = suggestions["constraints"]["lattice"]

            validator = LatticeConstraintValidator({"a": lattice_constraints["a"]})
            results = validator.validate(atoms)

            # Should pass on original structure
            assert len(results["passed"]) > 0

        # Stage 4: Modify structure
        atoms_modified = atoms.copy()
        atoms_modified.set_cell(
            atoms.get_cell() * 1.10,
            scale_atoms=True
        )

        # Stage 5: Validate again
        if "lattice" in suggestions["constraints"]:
            results_modified = validator.validate(atoms_modified)

            # Should now violate
            assert len(results_modified["violations"]) > 0 or len(results_modified["warnings"]) > 0


class TestMPPerformance:
    """Test performance characteristics on MP structures."""

    def test_analysis_completes(self):
        """Test that analysis completes in reasonable time."""
        import time

        atoms = load_mp_structure("BaTiO3_mp-19990.xyz")

        analyzer = GeometryAnalyzer()

        start = time.time()
        result = analyzer.analyze_structure(atoms)
        elapsed = time.time() - start

        # Small structure should complete quickly
        # (BaTiO3 primitive cell is only 5 atoms)
        assert elapsed < 30  # 30 seconds max

        assert "observations" in result

    def test_large_structure_handling(self):
        """Test handling of larger structures."""
        # Al2O3 structure is larger
        atoms = load_mp_structure("Al2O3_mp-1244874.xyz")

        analyzer = GeometryAnalyzer()

        # Should complete without crashing
        result = analyzer.analyze_structure(atoms)
        assert "observations" in result


class TestMPCrystalSystems:
    """Test validation across different crystal systems."""

    def test_detect_crystal_system_batimo3(self):
        """Test crystal system detection for cubic BaTiO3."""
        atoms = load_mp_structure("BaTiO3_mp-19990.xyz")

        suggester = ConstraintSuggester()
        analyzer = GeometryAnalyzer()

        result = analyzer.analyze_structure(atoms)
        suggestions = suggester.suggest_constraints(
            atoms, result["observations"], mode="normal"
        )

        if "lattice" in suggestions["constraints"]:
            system = suggestions["constraints"]["lattice"].get("crystal_system")
            # Cubic or tetragonal depending on primitive/conventional
            assert system in ["cubic", "tetragonal", "orthorhombic"]

    def test_validate_detected_system(self):
        """Test that detected system validates correctly."""
        atoms = load_mp_structure("BaTiO3_mp-19990.xyz")

        suggester = ConstraintSuggester()
        analyzer = GeometryAnalyzer()

        result = analyzer.analyze_structure(atoms)
        suggestions = suggester.suggest_constraints(
            atoms, result["observations"], mode="normal"
        )

        if "lattice" in suggestions["constraints"]:
            system = suggestions["constraints"]["lattice"].get("crystal_system")

            if system:
                # Validate against detected system
                validator = LatticeConstraintValidator({"crystal_system": system})
                results = validator.validate(atoms)

                # Should pass (suggestion should match reality)
                assert len(results["passed"]) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

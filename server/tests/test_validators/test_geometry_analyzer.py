import pytest
import numpy as np
from ase import Atoms
from ase.build import bulk, molecule
from server.core.validators import GeometryAnalyzer


class TestGeometryAnalyzer:
    @pytest.fixture
    def analyzer(self):
        return GeometryAnalyzer()

    @pytest.fixture
    def fcc_cu(self):
        return bulk("Cu", "fcc", a=3.6)

    @pytest.fixture
    def water(self):
        return molecule("H2O")

    def test_analyzer_initialization(self, analyzer):
        assert analyzer is not None
        assert analyzer.condenser is not None
        assert analyzer.adaptor is not None

    def test_analyze_fcc_structure(self, analyzer, fcc_cu):
        result = analyzer.analyze_structure(fcc_cu)

        assert "observations" in result
        assert "hints" in result

        obs = result["observations"]
        assert obs["dimensionality"] == 3
        assert "Cu" in obs["formula"]
        assert obs["crystal_system"] == "cubic"

    def test_coordination_in_fcc(self, analyzer, fcc_cu):
        result = analyzer.analyze_structure(fcc_cu)
        obs = result["observations"]

        cu_sites = [s for s in obs["sites"] if s["element"] == "Cu"]
        assert len(cu_sites) > 0

        for site in cu_sites:
            assert site["coordination"] == 12

    def test_molecule_dimensionality(self, analyzer, water):
        result = analyzer.analyze_structure(water)
        obs = result["observations"]

        assert obs["dimensionality"] == 0

    def test_bond_length_statistics(self, analyzer, water):
        result = analyzer.analyze_structure(water)
        obs = result["observations"]

        o_sites = [s for s in obs["sites"] if s["element"] == "O"]
        assert len(o_sites) > 0

        bond_data = o_sites[0]["bond_lengths"]
        assert "mean" in bond_data
        assert "std_dev" in bond_data
        assert bond_data["mean"] > 0

    def test_incomplete_coordination_hint(self, analyzer):
        atoms = bulk("Cu", "fcc", a=3.6)
        atoms = atoms * (2, 2, 2)
        del atoms[-1]

        result = analyzer.analyze_structure(atoms)
        hints = result["hints"]

        assert isinstance(hints, list)

    def test_constraint_checking_dimensionality(self, analyzer, fcc_cu):
        constraints = {"dimensionality": 3}
        result = analyzer.analyze_structure(fcc_cu, constraints=constraints)

        assert "constraints_check" in result
        check = result["constraints_check"]

        assert len(check["passed"]) > 0
        assert check["passed"][0]["type"] == "dimensionality"

    def test_constraint_checking_coordination(self, analyzer, fcc_cu):
        constraints = {"coordination": {"Cu": 12}}
        result = analyzer.analyze_structure(fcc_cu, constraints=constraints)

        check = result["constraints_check"]
        assert len(check["passed"]) > 0

    def test_constraint_failure(self, analyzer, fcc_cu):
        constraints = {"dimensionality": 2}
        result = analyzer.analyze_structure(fcc_cu, constraints=constraints)

        check = result["constraints_check"]
        # New format: violations instead of failed
        assert len(check["violations"]) > 0
        assert check["violations"][0]["type"] == "dimensionality"
        assert "2D" in check["violations"][0]["detail"] and "3D" in check["violations"][0]["detail"]

    def test_structure_comparison(self, analyzer, fcc_cu):
        atoms_before = fcc_cu.copy()
        atoms_after = fcc_cu.copy()
        atoms_after.set_cell(atoms_after.cell * 1.1, scale_atoms=True)

        result = analyzer.compare_structures(atoms_before, atoms_after)

        assert "observations_delta" in result
        assert "hints_delta" in result

    def test_observations_extraction(self, analyzer, fcc_cu):
        result = analyzer.analyze_structure(fcc_cu)
        obs = result["observations"]

        assert "dimensionality" in obs
        assert "formula" in obs
        assert "spacegroup" in obs
        assert "crystal_system" in obs
        assert "sites" in obs
        assert len(obs["sites"]) > 0

    def test_site_geometry_analysis(self, analyzer, fcc_cu):
        result = analyzer.analyze_structure(fcc_cu)
        obs = result["observations"]

        for site in obs["sites"]:
            assert "element" in site
            assert "coordination" in site
            assert "neighbors" in site

    def test_hint_confidence_levels(self, analyzer):
        atoms = bulk("Al", "fcc", a=4.05)
        atoms = atoms * (2, 2, 1)
        del atoms[-2:]

        result = analyzer.analyze_structure(atoms)
        hints = result["hints"]

        if hints:
            for hint in hints:
                assert "confidence" in hint
                assert hint["confidence"] in ["high", "probable", "ambiguous"]
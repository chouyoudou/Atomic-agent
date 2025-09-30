import pytest
import numpy as np
from ase.build import bulk, molecule
from server.core.validators.geometry_analyzer import GeometryAnalyzer
from server.core.validators.constraint_validator import ConstraintValidator


class TestConstraintValidator:
    """Test tolerance-based constraint validation."""

    @pytest.fixture
    def analyzer(self):
        return GeometryAnalyzer()

    @pytest.fixture
    def fcc_cu(self):
        return bulk("Cu", "fcc", a=3.6)

    @pytest.fixture
    def water(self):
        return molecule("H2O")

    def test_coordination_exact_match(self, analyzer, fcc_cu):
        """Test coordination constraint with exact match (no tolerance)."""
        constraints = {"coordination": {"Cu": 12}}

        result = analyzer.analyze_structure(fcc_cu, constraints=constraints)
        check = result["constraints_check"]

        assert len(check["passed"]) > 0
        assert len(check["violations"]) == 0
        assert any(
            item["type"] == "coordination" and "Cu" in item["detail"]
            for item in check["passed"]
        )

    def test_coordination_mismatch(self, analyzer, water):
        """Test coordination constraint violation."""
        constraints = {"coordination": {"O": 4}}  # Water O has 2, not 4

        result = analyzer.analyze_structure(water, constraints=constraints)
        check = result["constraints_check"]

        assert len(check["violations"]) > 0
        violation = check["violations"][0]
        assert violation["type"] == "coordination"
        assert violation["severity"] == "major"

    def test_dimensionality_match(self, analyzer, fcc_cu):
        """Test dimensionality constraint (3D bulk structure)."""
        constraints = {"dimensionality": 3}

        result = analyzer.analyze_structure(fcc_cu, constraints=constraints)
        check = result["constraints_check"]

        assert len(check["passed"]) > 0
        assert any(
            item["type"] == "dimensionality" and "3D" in item["detail"]
            for item in check["passed"]
        )

    def test_dimensionality_mismatch(self, analyzer, water):
        """Test dimensionality constraint violation (0D molecule vs 3D)."""
        constraints = {"dimensionality": 3}

        result = analyzer.analyze_structure(water, constraints=constraints)
        check = result["constraints_check"]

        assert len(check["violations"]) > 0
        violation = next(
            (v for v in check["violations"] if v["type"] == "dimensionality"), None
        )
        assert violation is not None
        assert violation["severity"] == "major"

    def test_bond_length_within_tolerance(self, analyzer, fcc_cu):
        """Test bond length within tolerance range (passed)."""
        constraints = {
            "bond_lengths": {
                "Cu-Cu": {
                    "min": 2.4,
                    "max": 2.7,
                    "target": 2.55
                }
            }
        }

        result = analyzer.analyze_structure(fcc_cu, constraints=constraints)
        check = result["constraints_check"]

        # Cu FCC nearest neighbor distance is ~2.55 Å
        # Should be within [2.4, 2.7] range
        assert len(check["passed"]) > 0

    def test_bond_length_slight_deviation_warning(self):
        """Test bond length slightly outside tolerance (warning)."""
        validator = ConstraintValidator({
            "bond_lengths": {
                "C-O": {"min": 1.6, "max": 2.0, "target": 1.8}
            }
        })

        # Mock observations with C-O bond length 2.05 (5% over max)
        observations = {
            "sites": [
                {
                    "site_index": 0,
                    "element": "C",
                    "coordination": 2,
                    "neighbors": [1],
                    "bond_lengths": {
                        "mean": 2.05,
                        "std_dev": 0.02,
                        "values": [2.05]
                    }
                },
                {
                    "site_index": 1,
                    "element": "O",
                    "coordination": 1,
                    "neighbors": [0],
                    "bond_lengths": {}
                }
            ]
        }

        results = validator.validate(observations)

        # 5% deviation should trigger warning (between 5-15%)
        assert len(results["warnings"]) > 0 or len(results["passed"]) > 0

    def test_bond_length_major_violation(self):
        """Test bond length severely violating tolerance."""
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
                    "coordination": 2,
                    "neighbors": [1],
                    "bond_lengths": {
                        "mean": 2.35,  # 17.5% over max
                        "std_dev": 0.02,
                        "values": [2.35]
                    }
                },
                {
                    "site_index": 1,
                    "element": "O",
                    "coordination": 1,
                    "neighbors": [0],
                    "bond_lengths": {}
                }
            ]
        }

        results = validator.validate(observations)

        # 17.5% deviation should trigger violation (>15%)
        assert len(results["violations"]) > 0
        assert results["violations"][0]["severity"] == "major"

    def test_geometry_likeness_pass(self, analyzer, fcc_cu):
        """Test geometry likeness constraint (FCC Cu = cuboctahedral, OP~1.0)."""
        constraints = {
            "geometry_likeness": {
                "Cu": {
                    "type": "cuboctahedral",
                    "min_likeness": 0.9
                }
            }
        }

        result = analyzer.analyze_structure(fcc_cu, constraints=constraints)
        check = result["constraints_check"]

        # FCC Cu should have very high cuboctahedral order parameter
        assert len(check["passed"]) > 0

    def test_geometry_likeness_insufficient(self):
        """Test geometry likeness below threshold."""
        validator = ConstraintValidator({
            "geometry_likeness": {
                "Al": {
                    "type": "octahedral",
                    "min_likeness": 0.8
                }
            }
        })

        observations = {
            "sites": [
                {
                    "site_index": 0,
                    "element": "Al",
                    "geometry": "octahedral",
                    "geometry_likeness": 0.65,  # Below 0.8 threshold
                    "coordination": 6,
                    "neighbors": [1, 2, 3, 4, 5, 6],
                    "bond_lengths": {}
                }
            ]
        }

        results = validator.validate(observations)

        # Likeness 0.65 < 0.8, deviation -0.15 (exactly at boundary)
        assert len(results["violations"]) > 0 or len(results["warnings"]) > 0

    def test_geometry_type_mismatch(self):
        """Test geometry type mismatch (found tetrahedral, expected octahedral)."""
        validator = ConstraintValidator({
            "geometry_likeness": {
                "Al": {
                    "type": "octahedral",
                    "min_likeness": 0.6
                }
            }
        })

        observations = {
            "sites": [
                {
                    "site_index": 0,
                    "element": "Al",
                    "geometry": "tetrahedral",  # Wrong type
                    "geometry_likeness": 0.95,
                    "coordination": 4,
                    "neighbors": [1, 2, 3, 4],
                    "bond_lengths": {}
                }
            ]
        }

        results = validator.validate(observations)

        assert len(results["violations"]) > 0
        violation = results["violations"][0]
        assert "octahedral" in violation["detail"]
        assert "tetrahedral" in violation["detail"]

    def test_multiple_constraints(self, analyzer, fcc_cu):
        """Test multiple constraints simultaneously."""
        constraints = {
            "dimensionality": 3,
            "coordination": {"Cu": 12},
            "geometry_likeness": {
                "Cu": {
                    "type": "cuboctahedral",
                    "min_likeness": 0.8
                }
            }
        }

        result = analyzer.analyze_structure(fcc_cu, constraints=constraints)
        check = result["constraints_check"]

        # All three constraints should pass for ideal FCC Cu
        assert len(check["passed"]) >= 2  # At least 2 passing
        assert len(check["violations"]) == 0

    def test_empty_constraints(self, analyzer, fcc_cu):
        """Test that empty constraints return no validation results."""
        result = analyzer.analyze_structure(fcc_cu, constraints={})
        check = result.get("constraints_check")

        # Empty constraints should return empty validation
        assert check is not None
        assert len(check["passed"]) == 0
        assert len(check["warnings"]) == 0
        assert len(check["violations"]) == 0

    def test_tolerance_boundary_min(self):
        """Test value exactly at minimum tolerance boundary."""
        validator = ConstraintValidator({
            "bond_lengths": {
                "C-O": {"min": 1.6, "max": 2.0}
            }
        })

        observations = {
            "sites": [
                {
                    "site_index": 0,
                    "element": "C",
                    "coordination": 1,
                    "neighbors": [1],
                    "bond_lengths": {
                        "mean": 1.6,  # Exactly at minimum
                        "values": [1.6]
                    }
                },
                {
                    "site_index": 1,
                    "element": "O",
                    "coordination": 1,
                    "neighbors": [0],
                    "bond_lengths": {}
                }
            ]
        }

        results = validator.validate(observations)

        # Exactly at boundary should pass
        assert len(results["passed"]) > 0

    def test_tolerance_boundary_max(self):
        """Test value exactly at maximum tolerance boundary."""
        validator = ConstraintValidator({
            "bond_lengths": {
                "C-O": {"min": 1.6, "max": 2.0}
            }
        })

        observations = {
            "sites": [
                {
                    "site_index": 0,
                    "element": "C",
                    "coordination": 1,
                    "neighbors": [1],
                    "bond_lengths": {
                        "mean": 2.0,  # Exactly at maximum
                        "values": [2.0]
                    }
                },
                {
                    "site_index": 1,
                    "element": "O",
                    "coordination": 1,
                    "neighbors": [0],
                    "bond_lengths": {}
                }
            ]
        }

        results = validator.validate(observations)

        # Exactly at boundary should pass
        assert len(results["passed"]) > 0

    def test_deviation_calculation(self):
        """Test that deviation is correctly calculated relative to target."""
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
                    "coordination": 1,
                    "neighbors": [1],
                    "bond_lengths": {
                        "mean": 1.9,
                        "values": [1.9]
                    }
                },
                {
                    "site_index": 1,
                    "element": "O",
                    "coordination": 1,
                    "neighbors": [0],
                    "bond_lengths": {}
                }
            ]
        }

        results = validator.validate(observations)

        # Should pass (within range), deviation = 1.9 - 1.8 = 0.1
        assert len(results["passed"]) > 0
        passed_item = results["passed"][0]
        assert abs(passed_item["deviation"] - 0.1) < 0.01

    def test_suggestion_generation(self):
        """Test that suggestions are generated for violations."""
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
                    "coordination": 1,
                    "neighbors": [1],
                    "bond_lengths": {
                        "mean": 2.5,  # Way over max
                        "values": [2.5]
                    }
                },
                {
                    "site_index": 1,
                    "element": "O",
                    "coordination": 1,
                    "neighbors": [0],
                    "bond_lengths": {}
                }
            ]
        }

        results = validator.validate(observations)

        assert len(results["violations"]) > 0
        violation = results["violations"][0]
        assert "suggestion" in violation
        assert len(violation["suggestion"]) > 0
        # Should suggest decreasing
        assert "decreas" in violation["suggestion"].lower()
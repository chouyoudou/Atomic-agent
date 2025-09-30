from typing import Dict, Any, Optional, List
import numpy as np
from ase import Atoms
from pymatgen.core import Structure
from pymatgen.io.ase import AseAtomsAdaptor
from robocrys import StructureCondenser
from robocrys.condense.site import SiteAnalyzer


class GeometryAnalyzer:
    """
    Crystal structure geometric analysis with quantitative deviation metrics.
    Extends robocrystallographer functionality for LLM agent feedback.
    """

    def __init__(self):
        self.condenser = StructureCondenser()
        self.adaptor = AseAtomsAdaptor()

    def analyze_structure(
        self, atoms: Atoms, constraints: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Analyze crystal structure geometry.

        Args:
            atoms: ASE Atoms object
            constraints: Optional user-defined constraints

        Returns:
            {
                "observations": {...},  # Factual measurements
                "hints": {...},         # Interpretive suggestions
                "constraints_check": {...}  # If constraints provided
            }
        """
        structure = self.adaptor.get_structure(atoms)

        try:
            structure.add_oxidation_state_by_guess()
        except:
            pass

        condensed = self.condenser.condense_structure(structure)

        result = {
            "observations": self._extract_observations(condensed, structure),
            "hints": self._generate_hints(condensed, structure),
        }

        if constraints:
            result["constraints_check"] = self._check_constraints(
                condensed, structure, constraints
            )

        return result

    def _extract_observations(
        self, condensed: Dict[str, Any], structure: Structure
    ) -> Dict[str, Any]:
        """Extract factual geometric observations."""
        observations = {
            "dimensionality": condensed.get("dimensionality"),
            "formula": condensed.get("formula"),
            "spacegroup": condensed.get("spg_symbol"),
            "crystal_system": condensed.get("crystal_system"),
            "sites": [],
        }

        for site_data in condensed.get("sites", []):
            site_obs = {
                "element": site_data["element"],
                "geometry": site_data.get("geometry", {}).get("type"),
                "coordination": site_data.get("nnn", 0),
                "neighbors": site_data.get("nn", {}).get("sites", []),
                "bond_lengths": self._extract_bond_lengths(site_data),
            }
            observations["sites"].append(site_obs)

        return observations

    def _extract_bond_lengths(self, site_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract bond length statistics from site data."""
        nn_data = site_data.get("nn", {})
        bond_lengths = []

        for neighbor_info in nn_data.get("sites", []):
            if "dist" in neighbor_info:
                bond_lengths.append(neighbor_info["dist"])

        if not bond_lengths:
            return {}

        return {
            "mean": float(np.mean(bond_lengths)),
            "std_dev": float(np.std(bond_lengths)),
            "min": float(np.min(bond_lengths)),
            "max": float(np.max(bond_lengths)),
            "values": [float(x) for x in bond_lengths],
        }

    def _generate_hints(
        self, condensed: Dict[str, Any], structure: Structure
    ) -> List[Dict[str, Any]]:
        """Generate interpretive geometric hints."""
        hints = []

        for site_data in condensed.get("sites", []):
            site_hints = self._analyze_site_geometry(site_data, structure)
            if site_hints:
                hints.extend(site_hints)

        return hints

    def _analyze_site_geometry(
        self, site_data: Dict[str, Any], structure: Structure
    ) -> List[Dict[str, Any]]:
        """Analyze individual site geometry for hints."""
        hints = []
        geometry_data = site_data.get("geometry", {})
        geometry_type = geometry_data.get("type")
        likeness = geometry_data.get("likeness", 0)

        coordination = site_data.get("nnn", 0)
        element = site_data["element"]

        if coordination == 5 and likeness < 0.8:
            hints.append(
                {
                    "site": f"{element}",
                    "interpretation": "incomplete_octahedral_possible",
                    "confidence": "probable" if likeness > 0.4 else "ambiguous",
                    "evidence": {
                        "current_coordination": coordination,
                        "current_geometry": geometry_type,
                        "expected_for_octahedral": 6,
                    },
                    "suggestion": "Consider if 6-coordination octahedral is intended",
                }
            )

        elif coordination == 4 and geometry_type in ["tetrahedral", "square_planar"]:
            if likeness < 0.6:
                hints.append(
                    {
                        "site": f"{element}",
                        "interpretation": "geometry_ambiguous",
                        "confidence": "ambiguous",
                        "evidence": {
                            "coordination": coordination,
                            "geometry_likeness": float(likeness),
                            "possible_geometries": ["tetrahedral", "square_planar"],
                        },
                    }
                )

        return hints

    def _check_constraints(
        self,
        condensed: Dict[str, Any],
        structure: Structure,
        constraints: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Check user-defined constraints."""
        results = {"passed": [], "failed": [], "warnings": []}

        if "dimensionality" in constraints:
            expected = constraints["dimensionality"]
            actual = condensed.get("dimensionality")
            if expected == actual:
                results["passed"].append(
                    {
                        "constraint": "dimensionality",
                        "expected": expected,
                        "actual": actual,
                    }
                )
            else:
                results["failed"].append(
                    {
                        "constraint": "dimensionality",
                        "expected": expected,
                        "actual": actual,
                        "message": f"Structure is {actual}D, expected {expected}D",
                    }
                )

        if "coordination" in constraints:
            self._check_coordination_constraints(
                constraints["coordination"], condensed, results
            )

        return results

    def _check_coordination_constraints(
        self, coord_constraints: Dict[str, Any], condensed: Dict[str, Any], results: Dict
    ):
        """Check coordination number constraints."""
        for site_data in condensed.get("sites", []):
            element = site_data["element"]
            actual_coord = site_data.get("nnn", 0)

            if element in coord_constraints:
                expected = coord_constraints[element]
                if actual_coord == expected:
                    results["passed"].append(
                        {
                            "constraint": f"{element}_coordination",
                            "expected": expected,
                            "actual": actual_coord,
                        }
                    )
                else:
                    results["failed"].append(
                        {
                            "constraint": f"{element}_coordination",
                            "expected": expected,
                            "actual": actual_coord,
                            "message": f"{element} has {actual_coord} neighbors, expected {expected}",
                        }
                    )

    def compare_structures(
        self, atoms_before: Atoms, atoms_after: Atoms
    ) -> Dict[str, Any]:
        """
        Compare two structures to track iterative changes.

        Returns:
            Change summary with improvements/regressions
        """
        analysis_before = self.analyze_structure(atoms_before)
        analysis_after = self.analyze_structure(atoms_after)

        return {
            "observations_delta": self._compute_observation_delta(
                analysis_before["observations"], analysis_after["observations"]
            ),
            "hints_delta": {
                "before": analysis_before["hints"],
                "after": analysis_after["hints"],
                "resolved_issues": self._count_resolved_hints(
                    analysis_before["hints"], analysis_after["hints"]
                ),
            },
        }

    def _compute_observation_delta(
        self, obs_before: Dict[str, Any], obs_after: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Compute changes in observations."""
        delta = {}

        if obs_before.get("dimensionality") != obs_after.get("dimensionality"):
            delta["dimensionality"] = {
                "before": obs_before.get("dimensionality"),
                "after": obs_after.get("dimensionality"),
            }

        return delta

    def _count_resolved_hints(
        self, hints_before: List[Dict], hints_after: List[Dict]
    ) -> int:
        """Count how many geometric issues were resolved."""
        issues_before = {h.get("interpretation") for h in hints_before}
        issues_after = {h.get("interpretation") for h in hints_after}
        return len(issues_before - issues_after)
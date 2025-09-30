from typing import Dict, Any, Optional, List
import numpy as np
from ase import Atoms
from pymatgen.core import Structure
from pymatgen.io.ase import AseAtomsAdaptor
from robocrys import StructureCondenser
from robocrys.condense.site import SiteAnalyzer
from .constraint_validator import ConstraintValidator


class GeometryAnalyzer:
    """
    Crystal structure geometric analysis with quantitative deviation metrics.
    Extends robocrystallographer functionality for LLM agent feedback.
    """

    def __init__(self):
        self.condenser = StructureCondenser()
        self.adaptor = AseAtomsAdaptor()

    @staticmethod
    def _strip_oxidation_state(element_str: str) -> str:
        """Remove oxidation state from element string (e.g., 'Cu0+' -> 'Cu')"""
        import re
        return re.sub(r'[\d\+\-]+$', '', element_str)

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
        if atoms.cell.volume < 0.1:
            atoms = atoms.copy()
            atoms.center(vacuum=10.0)
            atoms.set_pbc(True)

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

        if constraints is not None:
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

        distances = condensed.get("distances", {})
        sites_dict = condensed.get("sites", {})

        for site_index, site_data in sites_dict.items():
            nn_list = site_data.get("nn", [])
            coordination = len(nn_list) if isinstance(nn_list, list) else 0

            geometry_data = site_data.get("geometry", {})
            geometry_type = geometry_data.get("type") if isinstance(geometry_data, dict) else None

            element_str = site_data["element"]
            element_clean = self._strip_oxidation_state(element_str)

            geometry_likeness = geometry_data.get("likeness", 0) if isinstance(geometry_data, dict) else 0

            site_obs = {
                "site_index": site_index,
                "element": element_clean,
                "element_with_oxidation": element_str,
                "geometry": geometry_type,
                "geometry_likeness": float(geometry_likeness),
                "coordination": coordination,
                "neighbors": nn_list,
                "bond_lengths": self._extract_bond_lengths(site_index, distances),
            }
            observations["sites"].append(site_obs)

        return observations

    def _extract_bond_lengths(
        self, site_index: int, distances: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Extract bond length statistics from distances dict."""
        site_distances = distances.get(site_index, {})
        if not isinstance(site_distances, dict):
            return {}

        bond_lengths = []
        for neighbor_index, dist_list in site_distances.items():
            if isinstance(dist_list, list):
                bond_lengths.extend(dist_list)

        if not bond_lengths:
            return {}

        return {
            "mean": float(np.mean(bond_lengths)),
            "std_dev": float(np.std(bond_lengths)),
            "min": float(np.min(bond_lengths)),
            "max": float(np.max(bond_lengths)),
            "count": len(bond_lengths),
            "values": [float(x) for x in bond_lengths],
        }

    def _generate_hints(
        self, condensed: Dict[str, Any], structure: Structure
    ) -> List[Dict[str, Any]]:
        """Generate interpretive geometric hints."""
        hints = []

        sites_dict = condensed.get("sites", {})
        for site_index, site_data in sites_dict.items():
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
        if not isinstance(geometry_data, dict):
            return hints

        geometry_type = geometry_data.get("type")
        likeness = geometry_data.get("likeness", 0)

        nn_list = site_data.get("nn", [])
        coordination = len(nn_list) if isinstance(nn_list, list) else 0
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
        """Check user-defined constraints using ConstraintValidator."""
        observations = self._extract_observations(condensed, structure)

        distances = condensed.get("distances", {})
        angles = condensed.get("angles", {})

        validator = ConstraintValidator(constraints)
        results = validator.validate(
            observations=observations,
            structure_distances=distances,
            structure_angles=angles
        )

        return results

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
from typing import Any, Dict, List, Optional
import numpy as np
from ase import Atoms
from pymatgen.io.ase import AseAtomsAdaptor
from pymatgen.symmetry.analyzer import SpacegroupAnalyzer


class ConstraintSuggester:
    """Suggests reasonable constraints based on current structure.

    Helps LLM agents by analyzing a structure and recommending
    constraints that match its current state. Agents can then
    adopt these suggestions to 'lock in' successful features.
    """

    def __init__(self):
        """Initialize the constraint suggester."""
        pass

    def suggest_constraints(
        self,
        atoms: Atoms,
        observations: Dict[str, Any],
        mode: str = "normal"
    ) -> Dict[str, Any]:
        """Suggest constraints based on structure analysis.

        Args:
            atoms: ASE Atoms object
            observations: Structure observations from GeometryAnalyzer
            mode: Suggestion mode
                - "relaxed": Wide tolerances (±5%)
                - "normal": Standard tolerances (±2%)
                - "strict": Tight tolerances (±1%)

        Returns:
            Dict with suggested constraints and rationales
        """
        # Set tolerance based on mode
        tolerances = {
            "relaxed": 0.05,
            "normal": 0.02,
            "strict": 0.01
        }
        tolerance = tolerances.get(mode, 0.02)

        suggestions = {
            "constraints": {},
            "rationale": {},
            "confidence": {}
        }

        # Suggest dimensionality constraint
        self._suggest_dimensionality(observations, suggestions)

        # Suggest coordination constraints
        self._suggest_coordination(observations, suggestions)

        # Suggest lattice constraints
        self._suggest_lattice(atoms, tolerance, suggestions)

        # Suggest symmetry constraints
        self._suggest_symmetry(atoms, suggestions)

        # Suggest bond length constraints
        self._suggest_bond_lengths(observations, tolerance, suggestions)

        # Suggest geometry likeness constraints
        self._suggest_geometry_likeness(observations, suggestions)

        return suggestions

    def _suggest_dimensionality(
        self,
        observations: Dict[str, Any],
        suggestions: Dict[str, Any]
    ):
        """Suggest dimensionality constraint.

        Args:
            observations: Structure observations
            suggestions: Suggestions dict to update
        """
        dim = observations.get("dimensionality")
        if dim is not None:
            suggestions["constraints"]["dimensionality"] = dim
            suggestions["rationale"]["dimensionality"] = (
                f"Structure detected as {dim}D"
            )
            suggestions["confidence"]["dimensionality"] = "high"

    def _suggest_coordination(
        self,
        observations: Dict[str, Any],
        suggestions: Dict[str, Any]
    ):
        """Suggest coordination number constraints.

        Args:
            observations: Structure observations
            suggestions: Suggestions dict to update
        """
        coord_map = {}
        geometry_map = {}

        for site in observations.get("sites", []):
            element = site["element"]
            coord = site["coordination"]

            # Handle both dict and string geometry representations
            geometry_data = site.get("geometry", {})
            if isinstance(geometry_data, dict):
                geometry = geometry_data.get("type", "unknown")
                likeness = geometry_data.get("likeness", 0)
            else:
                # Legacy string format
                geometry = str(geometry_data) if geometry_data else "unknown"
                likeness = 0

            # Use most common coordination for each element
            if element not in coord_map:
                coord_map[element] = []
                geometry_map[element] = []

            coord_map[element].append(coord)
            geometry_map[element].append((geometry, likeness))

        # Build suggestions
        coordination_constraints = {}
        for element, coords in coord_map.items():
            # Use mode (most common value)
            unique, counts = np.unique(coords, return_counts=True)
            most_common_coord = unique[np.argmax(counts)]

            coordination_constraints[element] = most_common_coord

            # Find best geometry for this element
            geometries = geometry_map[element]
            # Filter to matching coordination
            matching_geoms = [
                (g, l) for g, l in geometries
                if element in coord_map and most_common_coord in coords
            ]
            if matching_geoms:
                best_geom = max(matching_geoms, key=lambda x: x[1])
                suggestions["rationale"][f"coordination.{element}"] = (
                    f"Detected {most_common_coord}-fold {best_geom[0]} "
                    f"coordination (likeness={best_geom[1]:.2f})"
                )
            else:
                suggestions["rationale"][f"coordination.{element}"] = (
                    f"Most common coordination: {most_common_coord}"
                )

        if coordination_constraints:
            suggestions["constraints"]["coordination"] = coordination_constraints
            suggestions["confidence"]["coordination"] = "high"

    def _suggest_lattice(
        self,
        atoms: Atoms,
        tolerance: float,
        suggestions: Dict[str, Any]
    ):
        """Suggest lattice parameter constraints.

        Args:
            atoms: ASE Atoms object
            tolerance: Relative tolerance for ranges
            suggestions: Suggestions dict to update
        """
        # Handle empty structures or structures without cell
        try:
            cell = atoms.get_cell()
            lengths = cell.lengths()
            angles = cell.angles()
            volume = atoms.get_volume()
        except (ValueError, ZeroDivisionError):
            # No cell or zero volume - skip lattice suggestions
            return

        lattice_constraints = {}

        # Suggest individual parameter ranges
        for i, (param_name, value) in enumerate([
            ('a', lengths[0]),
            ('b', lengths[1]),
            ('c', lengths[2]),
            ('alpha', angles[0]),
            ('beta', angles[1]),
            ('gamma', angles[2])
        ]):
            # For lengths, use relative tolerance
            # For angles, use absolute tolerance
            if param_name in ['a', 'b', 'c']:
                delta = value * tolerance
            else:
                delta = 2.0  # degrees

            lattice_constraints[param_name] = {
                "min": value - delta,
                "max": value + delta,
                "target": value
            }

        # Detect crystal system
        crystal_system = self._detect_crystal_system(lengths, angles)
        if crystal_system:
            lattice_constraints["crystal_system"] = crystal_system
            suggestions["rationale"]["lattice.crystal_system"] = (
                f"Cell metrics indicate {crystal_system} system"
            )
            suggestions["confidence"]["lattice.crystal_system"] = "high"

        # Suggest volume constraint
        lattice_constraints["volume"] = {
            "min": volume * (1 - tolerance),
            "max": volume * (1 + tolerance),
            "target": volume
        }

        suggestions["constraints"]["lattice"] = lattice_constraints
        suggestions["rationale"]["lattice"] = (
            f"Current cell: a={lengths[0]:.3f}, b={lengths[1]:.3f}, c={lengths[2]:.3f}, "
            f"V={volume:.2f} Ų"
        )
        suggestions["confidence"]["lattice"] = "high"

    def _detect_crystal_system(
        self,
        lengths: np.ndarray,
        angles: np.ndarray
    ) -> Optional[str]:
        """Detect crystal system from cell parameters.

        Args:
            lengths: Cell lengths [a, b, c]
            angles: Cell angles [alpha, beta, gamma]

        Returns:
            Crystal system name or None
        """
        a, b, c = lengths
        alpha, beta, gamma = angles

        # Check conditions
        abc_equal = np.allclose([a, b, c], a, rtol=0.01)
        ab_equal = np.isclose(a, b, rtol=0.01)
        angles_90 = np.allclose(angles, 90, atol=1.0)
        alpha_beta_90 = np.allclose([alpha, beta], 90, atol=1.0)
        gamma_120 = np.isclose(gamma, 120, atol=1.0)
        angles_equal = np.allclose(angles, alpha, atol=1.0)

        if abc_equal and angles_90:
            return "cubic"
        elif ab_equal and angles_90 and not np.isclose(a, c, rtol=0.01):
            return "tetragonal"
        elif ab_equal and alpha_beta_90 and gamma_120 and not np.isclose(a, c, rtol=0.01):
            return "hexagonal"
        elif abc_equal and angles_equal and not angles_90:
            return "rhombohedral"
        elif angles_90:
            return "orthorhombic"
        elif alpha_beta_90 and not np.isclose(beta, 90, atol=1.0):
            return "monoclinic"
        else:
            return "triclinic"

    def _suggest_symmetry(
        self,
        atoms: Atoms,
        suggestions: Dict[str, Any]
    ):
        """Suggest symmetry constraints.

        Args:
            atoms: ASE Atoms object
            suggestions: Suggestions dict to update
        """
        try:
            adaptor = AseAtomsAdaptor()
            structure = adaptor.get_structure(atoms)
            analyzer = SpacegroupAnalyzer(structure, symprec=0.1)

            space_group_number = analyzer.get_space_group_number()
            space_group_symbol = analyzer.get_space_group_symbol()
            point_group = analyzer.get_point_group_symbol()

            suggestions["constraints"]["symmetry"] = {
                "space_group": space_group_number,
                "point_group": point_group,
                "tolerance": 0.1
            }

            suggestions["rationale"]["symmetry"] = (
                f"Detected space group: {space_group_symbol} ({space_group_number}), "
                f"point group: {point_group}"
            )
            suggestions["confidence"]["symmetry"] = "high"

        except Exception as e:
            suggestions["rationale"]["symmetry"] = (
                f"Symmetry detection failed: {str(e)}"
            )
            suggestions["confidence"]["symmetry"] = "low"

    def _suggest_bond_lengths(
        self,
        observations: Dict[str, Any],
        tolerance: float,
        suggestions: Dict[str, Any]
    ):
        """Suggest bond length constraints.

        Args:
            observations: Structure observations
            tolerance: Relative tolerance
            suggestions: Suggestions dict to update
        """
        # Extract bond statistics
        bond_stats = observations.get("bond_statistics", {})

        if not bond_stats:
            return

        bond_length_constraints = {}

        for bond_type, stats in bond_stats.items():
            mean_length = stats.get("mean")
            if mean_length is None:
                continue

            delta = mean_length * tolerance

            bond_length_constraints[bond_type] = {
                "min": mean_length - delta,
                "max": mean_length + delta,
                "target": mean_length
            }

            count = stats.get("count", 0)
            suggestions["rationale"][f"bond_lengths.{bond_type}"] = (
                f"Detected {count} {bond_type} bonds, "
                f"mean length: {mean_length:.3f} Å"
            )

        if bond_length_constraints:
            suggestions["constraints"]["bond_lengths"] = bond_length_constraints
            suggestions["confidence"]["bond_lengths"] = "high"

    def _suggest_geometry_likeness(
        self,
        observations: Dict[str, Any],
        suggestions: Dict[str, Any]
    ):
        """Suggest geometry likeness constraints.

        Args:
            observations: Structure observations
            suggestions: Suggestions dict to update
        """
        geometry_constraints = {}

        for site in observations.get("sites", []):
            element = site["element"]
            geometry_data = site.get("geometry", {})

            # Handle both dict and string geometry representations
            if isinstance(geometry_data, dict):
                geometry_type = geometry_data.get("type", "unknown")
                likeness = geometry_data.get("likeness", 0)
            else:
                geometry_type = str(geometry_data) if geometry_data else "unknown"
                likeness = 0

            if likeness < 0.5:
                continue  # Skip ambiguous geometries

            # Set threshold based on current likeness
            # Allow some degradation but not too much
            if likeness >= 0.9:
                min_likeness = 0.85
            elif likeness >= 0.7:
                min_likeness = 0.6
            else:
                min_likeness = 0.5

            if element not in geometry_constraints:
                geometry_constraints[element] = {
                    "type": geometry_type,
                    "min_likeness": min_likeness
                }

                suggestions["rationale"][f"geometry_likeness.{element}"] = (
                    f"Current {geometry_type} geometry has likeness={likeness:.2f}"
                )

        if geometry_constraints:
            suggestions["constraints"]["geometry_likeness"] = geometry_constraints
            suggestions["confidence"]["geometry_likeness"] = "medium"

    def suggest_freezing(
        self,
        observations: Dict[str, Any],
        satisfied_constraints: Dict[str, List[Dict[str, Any]]]
    ) -> Dict[str, Any]:
        """Suggest what to freeze based on satisfied constraints.

        Args:
            observations: Structure observations
            satisfied_constraints: Results from constraint validation
                (only 'passed' items)

        Returns:
            Dict with freezing suggestions
        """
        suggestions = {
            "frozen_atoms": [],
            "frozen_bonds": [],
            "frozen_angles": [],
            "frozen_coordination": [],
            "rationale": []
        }

        passed = satisfied_constraints.get("passed", [])

        # Suggest freezing atoms with correct coordination
        for result in passed:
            if result["type"] == "coordination":
                # Extract site index if available
                # This would require site_index in the result
                pass

        # Suggest freezing bonds that pass constraints
        for result in passed:
            if result["type"] == "bond_length":
                # Extract bond info
                bond_pair = result.get("atoms")
                if bond_pair:
                    suggestions["frozen_bonds"].append({
                        "atoms": bond_pair,
                        "length": result.get("value")
                    })
                    suggestions["rationale"].append(
                        f"Bond {bond_pair[0]}-{bond_pair[1]} satisfies constraints"
                    )

        # Suggest freezing angles that pass
        for result in passed:
            if result["type"] == "bond_angle":
                triplet = result.get("triplet")
                if triplet:
                    suggestions["frozen_angles"].append({
                        "triplet": triplet
                    })
                    suggestions["rationale"].append(
                        f"Angle {triplet} satisfies constraints"
                    )

        return suggestions

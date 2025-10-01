from typing import Any, Dict, List
import numpy as np


class AngleConstraintValidator:
    """Validates bond angles against user-defined constraints.

    Extracts angle data from robocrys condensed structure and validates
    against element triplet specifications (e.g., "O-Ti-O").

    Angles are categorized by connectivity:
    - edge: angles between edge-sharing polyhedra
    - corner: angles at corner-sharing vertices
    - face: angles within face-sharing polyhedra
    """

    WARNING_THRESHOLD = 0.05  # 5% deviation triggers warning
    VIOLATION_THRESHOLD = 0.15  # 15% deviation triggers violation

    def __init__(self, angle_constraints: Dict[str, Dict[str, float]]):
        """Initialize with angle constraints.

        Args:
            angle_constraints: Dict mapping element triplets to ranges
                Example: {
                    "O-Ti-O": {"min": 85, "max": 95, "target": 90},
                    "O-Al-O": {"min": 105, "max": 115, "target": 109.47}
                }
        """
        self.constraints = angle_constraints

    def validate(
        self,
        observations: Dict[str, Any],
        structure_angles: Dict[int, Dict[int, Dict[str, List[float]]]]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Validate angles against constraints.

        Args:
            observations: Structure observations with site element info
            structure_angles: Robocrys angle data
                Format: angles[site_idx][neighbor_idx] = {
                    "edge": [angles...],
                    "corner": [angles...],
                    "face": [angles...]
                }

        Returns:
            Dict with 'passed', 'warnings', and 'violations' lists
        """
        results = {
            "passed": [],
            "warnings": [],
            "violations": []
        }

        if not structure_angles:
            return results

        # Build element mapping
        site_elements = self._build_element_map(observations)

        # Extract angles by element triplet
        angle_groups = self._extract_angle_groups(
            structure_angles, site_elements, observations
        )

        # Validate each constrained triplet
        for triplet, constraint in self.constraints.items():
            if triplet not in angle_groups:
                continue

            angles = angle_groups[triplet]
            self._validate_triplet(triplet, angles, constraint, results)

        return results

    def _build_element_map(self, observations: Dict[str, Any]) -> Dict[int, str]:
        """Build mapping from site index to element symbol.

        Args:
            observations: Structure observations

        Returns:
            Dict mapping site_idx -> element symbol
        """
        element_map = {}
        for site in observations.get("sites", []):
            site_idx = site.get("site_index", len(element_map))
            element_map[site_idx] = site["element"]
        return element_map

    def _extract_angle_groups(
        self,
        structure_angles: Dict[int, Dict[int, Dict[str, List[float]]]],
        site_elements: Dict[int, str],
        observations: Dict[str, Any]
    ) -> Dict[str, List[float]]:
        """Extract angles grouped by element triplet.

        Args:
            structure_angles: Robocrys angle data
            site_elements: Site index to element mapping
            observations: Structure observations

        Returns:
            Dict mapping element triplets (e.g., "O-Ti-O") to angle lists
        """
        angle_groups = {}

        for site_idx, neighbor_angles in structure_angles.items():
            center_element = site_elements.get(site_idx)
            if not center_element:
                continue

            # Get neighbor elements for this site
            site_data = self._get_site_data(observations, site_idx)
            if not site_data:
                continue

            neighbor_indices = site_data.get("nn", [])

            # Extract angles from all connectivity types
            for neighbor_idx, angle_data in neighbor_angles.items():
                for connectivity_type in ["edge", "corner", "face"]:
                    angles = angle_data.get(connectivity_type, [])

                    # For simplicity, assume angles involve center and two neighbors
                    # Format: neighbor1-center-neighbor2
                    for angle in angles:
                        # Try to match with neighbor elements
                        triplet = self._infer_triplet(
                            center_element, neighbor_indices, site_elements
                        )
                        if triplet:
                            if triplet not in angle_groups:
                                angle_groups[triplet] = []
                            angle_groups[triplet].append(angle)

        return angle_groups

    def _get_site_data(
        self, observations: Dict[str, Any], site_idx: int
    ) -> Dict[str, Any]:
        """Get site data for given index.

        Args:
            observations: Structure observations
            site_idx: Site index

        Returns:
            Site data dict or empty dict
        """
        for site in observations.get("sites", []):
            if site.get("site_index") == site_idx:
                return site
        return {}

    def _infer_triplet(
        self,
        center_element: str,
        neighbor_indices: List[int],
        site_elements: Dict[int, str]
    ) -> str:
        """Infer element triplet from center and neighbors.

        Args:
            center_element: Central atom element
            neighbor_indices: List of neighbor site indices
            site_elements: Site index to element mapping

        Returns:
            Triplet string like "O-Ti-O" or empty string
        """
        if len(neighbor_indices) < 2:
            return ""

        # Get most common neighbor element
        neighbor_elements = [
            site_elements.get(idx, "") for idx in neighbor_indices[:2]
        ]
        neighbor_elements = [e for e in neighbor_elements if e]

        if not neighbor_elements:
            return ""

        # Format: neighbor1-center-neighbor2
        # Use most common neighbor element (assume homogeneous)
        neighbor_elem = neighbor_elements[0]
        return f"{neighbor_elem}-{center_element}-{neighbor_elem}"

    def _validate_triplet(
        self,
        triplet: str,
        angles: List[float],
        constraint: Dict[str, float],
        results: Dict[str, List[Dict[str, Any]]]
    ):
        """Validate angles for a specific triplet.

        Args:
            triplet: Element triplet (e.g., "O-Ti-O")
            angles: List of measured angles
            constraint: Constraint dict with min/max/target
            results: Results dict to update
        """
        min_angle = constraint.get("min", 0)
        max_angle = constraint.get("max", 180)
        target = constraint.get("target", (min_angle + max_angle) / 2)

        # Calculate tolerance range
        tolerance = (max_angle - min_angle) / 2
        warning_range = tolerance * self.WARNING_THRESHOLD
        violation_range = tolerance * self.VIOLATION_THRESHOLD

        passed_angles = []
        warning_angles = []
        violation_angles = []

        for angle in angles:
            if min_angle <= angle <= max_angle:
                passed_angles.append(angle)
            elif (min_angle - warning_range <= angle < min_angle or
                  max_angle < angle <= max_angle + warning_range):
                warning_angles.append(angle)
            else:
                violation_angles.append(angle)

        # Report results
        if passed_angles:
            results["passed"].append({
                "type": "bond_angle",
                "triplet": triplet,
                "detail": f"{triplet}: {len(passed_angles)}/{len(angles)} angles in range [{min_angle:.1f}, {max_angle:.1f}]°",
                "count": len(passed_angles),
                "mean_angle": float(np.mean(passed_angles)),
                "target": target
            })

        if warning_angles:
            mean_dev = np.mean([
                abs(a - target) / tolerance for a in warning_angles
            ])
            results["warnings"].append({
                "type": "bond_angle",
                "triplet": triplet,
                "detail": f"{triplet}: {len(warning_angles)} angles slightly outside range",
                "severity": f"{mean_dev*100:.1f}% deviation",
                "angles": [float(a) for a in warning_angles],
                "expected_range": f"[{min_angle:.1f}, {max_angle:.1f}]°",
                "suggestion": f"Consider adjusting {triplet} angles toward {target:.1f}°"
            })

        if violation_angles:
            mean_dev = np.mean([
                abs(a - target) / tolerance for a in violation_angles
            ])
            results["violations"].append({
                "type": "bond_angle",
                "triplet": triplet,
                "detail": f"{triplet}: {len(violation_angles)} angles severely outside range",
                "severity": f"{mean_dev*100:.1f}% deviation",
                "angles": [float(a) for a in violation_angles],
                "expected_range": f"[{min_angle:.1f}, {max_angle:.1f}]°",
                "suggestion": f"Angles significantly deviate from {target:.1f}°, major adjustment needed"
            })

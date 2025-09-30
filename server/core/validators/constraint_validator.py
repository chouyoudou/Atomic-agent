from typing import Any, Dict, List, Optional
import numpy as np


class ConstraintValidator:
    """Validates crystal structures against user-defined constraints with tolerance levels.

    Provides three-level feedback:
    - passed: within tolerance range [min, max]
    - warning: slightly outside tolerance (5-15% deviation)
    - violation: severely violating constraints (>15% deviation)
    """

    WARNING_THRESHOLD = 0.05  # 5% beyond tolerance triggers warning
    VIOLATION_THRESHOLD = 0.15  # 15% beyond tolerance triggers violation

    def __init__(self, constraints: Dict[str, Any]):
        self.constraints = constraints

    def validate(
        self,
        observations: Dict[str, Any],
        structure_distances: Optional[Dict[int, Dict[int, List[float]]]] = None,
        structure_angles: Optional[Dict[int, Dict[str, List[float]]]] = None
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Validate observations against constraints.

        Args:
            observations: Observations from GeometryAnalyzer
            structure_distances: Bond distance data from robocrys
            structure_angles: Bond angle data from robocrys

        Returns:
            Dict with 'passed', 'warnings', and 'violations' lists
        """
        results = {
            "passed": [],
            "warnings": [],
            "violations": []
        }

        if "coordination" in self.constraints:
            self._validate_coordination(observations, results)

        if "dimensionality" in self.constraints:
            self._validate_dimensionality(observations, results)

        if "bond_lengths" in self.constraints:
            self._validate_bond_lengths(
                observations, structure_distances, results
            )

        if "bond_angles" in self.constraints and structure_angles:
            self._validate_bond_angles(
                observations, structure_angles, results
            )

        if "geometry_likeness" in self.constraints:
            self._validate_geometry_likeness(observations, results)

        return results

    def _validate_coordination(
        self, observations: Dict[str, Any], results: Dict[str, List[Dict]]
    ):
        """Validate coordination numbers (exact match, no tolerance)."""
        coord_constraints = self.constraints["coordination"]

        for site in observations["sites"]:
            element = site["element"]
            if element not in coord_constraints:
                continue

            expected = coord_constraints[element]
            actual = site["coordination"]

            if actual == expected:
                results["passed"].append({
                    "type": "coordination",
                    "detail": f"{element}: {actual} (expected: {expected})",
                    "deviation": 0
                })
            else:
                deviation = actual - expected
                results["violations"].append({
                    "type": "coordination",
                    "detail": f"{element}: {actual} (expected: {expected})",
                    "deviation": deviation,
                    "severity": "major",
                    "suggestion": (
                        f"Coordination mismatch: found {actual}, expected {expected}"
                    )
                })

    def _validate_dimensionality(
        self, observations: Dict[str, Any], results: Dict[str, List[Dict]]
    ):
        """Validate dimensionality (exact match)."""
        expected_dim = self.constraints["dimensionality"]
        actual_dim = observations["dimensionality"]

        if actual_dim == expected_dim:
            results["passed"].append({
                "type": "dimensionality",
                "detail": f"{actual_dim}D structure",
                "deviation": 0
            })
        else:
            results["violations"].append({
                "type": "dimensionality",
                "detail": f"Found {actual_dim}D, expected {expected_dim}D",
                "deviation": actual_dim - expected_dim,
                "severity": "major",
                "suggestion": f"Structure dimensionality mismatch"
            })

    def _validate_bond_lengths(
        self,
        observations: Dict[str, Any],
        structure_distances: Dict[int, Dict[int, List[float]]],
        results: Dict[str, List[Dict]]
    ):
        """Validate bond lengths with tolerance ranges."""
        length_constraints = self.constraints["bond_lengths"]

        # Build site index to element mapping
        site_index_to_element = {
            site.get("site_index"): site["element"]
            for site in observations["sites"]
            if "site_index" in site
        }

        for site in observations["sites"]:
            element_a = site["element"]
            bond_data = site.get("bond_lengths", {})

            if not bond_data or "mean" not in bond_data:
                continue

            mean_length = bond_data["mean"]

            # Get neighbor elements
            neighbor_indices = site.get("neighbors", [])
            if not neighbor_indices:
                continue

            # Try to find matching constraint
            for bond_key, constraint in length_constraints.items():
                parts = bond_key.split("-")
                if len(parts) != 2:
                    continue

                elem_a, elem_b = parts

                # Check if this site matches either end of the bond
                if element_a == elem_a:
                    # Check if any neighbor is elem_b
                    has_match = any(
                        site_index_to_element.get(idx) == elem_b
                        for idx in neighbor_indices
                    )
                    if has_match:
                        self._check_range_constraint(
                            constraint=constraint,
                            actual_value=mean_length,
                            constraint_type="bond_length",
                            detail_prefix=bond_key,
                            unit="Å",
                            results=results
                        )
                elif element_a == elem_b:
                    # Reverse bond
                    has_match = any(
                        site_index_to_element.get(idx) == elem_a
                        for idx in neighbor_indices
                    )
                    if has_match:
                        self._check_range_constraint(
                            constraint=constraint,
                            actual_value=mean_length,
                            constraint_type="bond_length",
                            detail_prefix=bond_key,
                            unit="Å",
                            results=results
                        )

    def _validate_bond_angles(
        self,
        observations: Dict[str, Any],
        structure_angles: Dict[int, Dict[str, List[float]]],
        results: Dict[str, List[Dict]]
    ):
        """Validate bond angles with tolerance ranges."""
        angle_constraints = self.constraints["bond_angles"]

        for angle_key, constraint in angle_constraints.items():
            # Parse angle key like "O-Al-O"
            parts = angle_key.split("-")
            if len(parts) != 3:
                continue

            elem_a, center_elem, elem_b = parts

            # Find matching angles in structure
            for site in observations["sites"]:
                if site["element"] != center_elem:
                    continue

                # Extract actual angles from connectivity data
                # This requires access to robocrys angle data
                # For now, we'll use a simplified approach

                # If angles are provided in observations
                if "angles" in site:
                    angles = site["angles"]
                    if angles:
                        mean_angle = np.mean(angles)

                        self._check_range_constraint(
                            constraint=constraint,
                            actual_value=mean_angle,
                            constraint_type="bond_angle",
                            detail_prefix=angle_key,
                            unit="°",
                            results=results
                        )

    def _validate_geometry_likeness(
        self, observations: Dict[str, Any], results: Dict[str, List[Dict]]
    ):
        """Validate geometry likeness using robocrys order parameters."""
        likeness_constraints = self.constraints["geometry_likeness"]

        for site in observations["sites"]:
            element = site["element"]
            if element not in likeness_constraints:
                continue

            constraint = likeness_constraints[element]
            expected_type = constraint["type"]
            min_likeness = constraint.get("min_likeness", 0.4)

            geometry = site.get("geometry")
            if not geometry:
                continue

            actual_type = geometry if isinstance(geometry, str) else geometry
            likeness = site.get("geometry_likeness", 0.0)

            if actual_type == expected_type and likeness >= min_likeness:
                results["passed"].append({
                    "type": "geometry_likeness",
                    "detail": f"{element} {expected_type}: OP={likeness:.3f}",
                    "deviation": 0
                })
            elif actual_type == expected_type and likeness < min_likeness:
                deviation = likeness - min_likeness
                severity = "major" if abs(deviation) > 0.15 else "minor"

                target_list = results["violations" if severity == "major" else "warnings"]
                target_list.append({
                    "type": "geometry_likeness",
                    "detail": f"{element} {expected_type}: OP={likeness:.3f} (min: {min_likeness:.3f})",
                    "deviation": deviation,
                    "severity": severity,
                    "suggestion": f"Significant distortion from ideal {expected_type} geometry"
                })
            else:
                results["violations"].append({
                    "type": "geometry_likeness",
                    "detail": f"{element}: found {actual_type}, expected {expected_type}",
                    "deviation": 1.0,
                    "severity": "major",
                    "suggestion": f"Geometry type mismatch"
                })

    def _check_range_constraint(
        self,
        constraint: Dict[str, float],
        actual_value: float,
        constraint_type: str,
        detail_prefix: str,
        unit: str,
        results: Dict[str, List[Dict]]
    ):
        """Check if value is within tolerance range and classify result.

        Args:
            constraint: Dict with 'min', 'max', optional 'target'
            actual_value: Measured value
            constraint_type: Type name for reporting
            detail_prefix: Prefix for detail string (e.g., "C-O")
            unit: Unit string (e.g., "Å" or "°")
            results: Results dict to append to
        """
        min_val = constraint["min"]
        max_val = constraint["max"]
        target = constraint.get("target", (min_val + max_val) / 2)

        # Calculate range and deviation
        range_size = max_val - min_val

        if min_val <= actual_value <= max_val:
            # Within tolerance - passed
            deviation = actual_value - target
            results["passed"].append({
                "type": constraint_type,
                "detail": f"{detail_prefix}: {actual_value:.2f} {unit} (range: {min_val}-{max_val} {unit})",
                "deviation": deviation
            })
        else:
            # Outside tolerance - calculate severity
            if actual_value < min_val:
                absolute_deviation = min_val - actual_value
                relative_deviation = absolute_deviation / range_size if range_size > 0 else 1.0
                deviation = actual_value - target
            else:  # actual_value > max_val
                absolute_deviation = actual_value - max_val
                relative_deviation = absolute_deviation / range_size if range_size > 0 else 1.0
                deviation = actual_value - target

            if relative_deviation < self.WARNING_THRESHOLD:
                # Very minor - still pass (edge case)
                results["passed"].append({
                    "type": constraint_type,
                    "detail": f"{detail_prefix}: {actual_value:.2f} {unit} (range: {min_val}-{max_val} {unit})",
                    "deviation": deviation
                })
            elif relative_deviation < self.VIOLATION_THRESHOLD:
                # Warning
                suggestion = self._generate_adjustment_suggestion(
                    actual_value, min_val, max_val, target, unit
                )
                results["warnings"].append({
                    "type": constraint_type,
                    "detail": f"{detail_prefix}: {actual_value:.2f} {unit} (range: {min_val}-{max_val} {unit})",
                    "deviation": deviation,
                    "severity": "minor",
                    "suggestion": suggestion
                })
            else:
                # Violation
                suggestion = self._generate_adjustment_suggestion(
                    actual_value, min_val, max_val, target, unit
                )
                results["violations"].append({
                    "type": constraint_type,
                    "detail": f"{detail_prefix}: {actual_value:.2f} {unit} (range: {min_val}-{max_val} {unit})",
                    "deviation": deviation,
                    "severity": "major",
                    "suggestion": suggestion
                })

    def _generate_adjustment_suggestion(
        self,
        actual: float,
        min_val: float,
        max_val: float,
        target: float,
        unit: str
    ) -> str:
        """Generate direction suggestion without specific coordinates."""
        if actual < min_val:
            amount = min_val - actual
            return f"Consider increasing by ~{amount:.2f} {unit} toward target"
        else:
            amount = actual - max_val
            return f"Consider decreasing by ~{amount:.2f} {unit} toward target"
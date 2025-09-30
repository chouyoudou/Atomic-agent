from typing import Dict, Any, List, Optional
import numpy as np


class GeometryHintGenerator:
    """Generate interpretive hints for crystal structure geometry.

    Provides directional suggestions without specific atomic coordinates.
    Quantifies deviations using robocrystallographer order parameters.
    """

    CONFIDENCE_THRESHOLDS = {
        "high": 0.7,
        "probable": 0.5,
        "ambiguous": 0.3
    }

    def generate_hints(
        self,
        observations: Dict[str, Any],
        constraints: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Generate geometry hints from observations.

        Args:
            observations: Factual observations from GeometryAnalyzer
            constraints: Optional user constraints for context

        Returns:
            List of hint dicts with suggestions and confidence levels
        """
        hints = []

        for site in observations.get("sites", []):
            site_hints = self._analyze_site(site, constraints)
            hints.extend(site_hints)

        structure_hints = self._analyze_overall_structure(observations, constraints)
        hints.extend(structure_hints)

        return hints

    def _analyze_site(
        self,
        site: Dict[str, Any],
        constraints: Optional[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Analyze individual site for geometry hints."""
        hints = []

        element = site["element"]
        coordination = site["coordination"]
        geometry = site.get("geometry")
        likeness = site.get("geometry_likeness", 0.0)

        # Incomplete octahedral check
        if coordination == 5:
            hints.append({
                "site": element,
                "type": "incomplete_coordination",
                "observation": f"{coordination}-coordinate {geometry or 'unknown'}",
                "suggestion": "Consider if 6-coordinate octahedral is intended",
                "confidence": self._classify_confidence(likeness),
                "quantified_deviation": {
                    "current": coordination,
                    "likely_target": 6
                }
            })

        # Distorted geometry check
        if geometry and likeness < 0.7:
            severity = self._classify_distortion_severity(likeness)
            if severity != "negligible":
                hints.append({
                    "site": element,
                    "type": "distorted_geometry",
                    "observation": f"{geometry} with OP={likeness:.3f}",
                    "suggestion": self._suggest_geometry_improvement(
                        geometry, likeness
                    ),
                    "confidence": self._classify_confidence(likeness),
                    "quantified_deviation": {
                        "order_parameter": likeness,
                        "ideal": 1.0,
                        "deviation": 1.0 - likeness,
                        "severity": severity
                    }
                })

        # Bond length consistency check
        bond_data = site.get("bond_lengths", {})
        if bond_data and "std_dev" in bond_data:
            mean = bond_data["mean"]
            std = bond_data["std_dev"]
            if std / mean > 0.05:  # >5% variation
                hints.append({
                    "site": element,
                    "type": "inconsistent_bond_lengths",
                    "observation": f"Bond lengths: {mean:.3f}±{std:.3f} Å (CV: {std/mean*100:.1f}%)",
                    "suggestion": "Consider regularizing bond lengths for more uniform coordination",
                    "confidence": "high",
                    "quantified_deviation": {
                        "coefficient_of_variation": std / mean,
                        "tolerance": 0.05
                    }
                })

        # Constraint-specific hints
        if constraints and "geometry_likeness" in constraints:
            likeness_constraint = constraints["geometry_likeness"].get(element)
            if likeness_constraint:
                expected_geom = likeness_constraint["type"]
                min_likeness = likeness_constraint.get("min_likeness", 0.4)

                if geometry != expected_geom:
                    hints.append({
                        "site": element,
                        "type": "geometry_mismatch",
                        "observation": f"Found {geometry}, expected {expected_geom}",
                        "suggestion": f"Restructure toward {expected_geom} coordination",
                        "confidence": "high",
                        "quantified_deviation": {
                            "current_type": geometry,
                            "expected_type": expected_geom
                        }
                    })
                elif likeness < min_likeness:
                    deficit = min_likeness - likeness
                    hints.append({
                        "site": element,
                        "type": "insufficient_likeness",
                        "observation": f"{expected_geom} OP={likeness:.3f} (min: {min_likeness:.3f})",
                        "suggestion": f"Improve {expected_geom} regularity by ΔOP~{deficit:.3f}",
                        "confidence": "high",
                        "quantified_deviation": {
                            "current_op": likeness,
                            "minimum_op": min_likeness,
                            "deficit": deficit
                        }
                    })

        return hints

    def _analyze_overall_structure(
        self,
        observations: Dict[str, Any],
        constraints: Optional[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Analyze overall structure properties."""
        hints = []

        dimensionality = observations.get("dimensionality")
        formula = observations.get("formula")

        # Dimensionality hints
        if constraints and "dimensionality" in constraints:
            expected_dim = constraints["dimensionality"]
            if dimensionality != expected_dim:
                hints.append({
                    "site": "overall",
                    "type": "dimensionality_mismatch",
                    "observation": f"Structure is {dimensionality}D, expected {expected_dim}D",
                    "suggestion": self._suggest_dimensionality_change(
                        dimensionality, expected_dim
                    ),
                    "confidence": "high",
                    "quantified_deviation": {
                        "current": dimensionality,
                        "expected": expected_dim
                    }
                })

        # Coordination statistics
        coordinations = [s["coordination"] for s in observations.get("sites", [])]
        if coordinations:
            coord_std = np.std(coordinations)
            if coord_std > 2.0:
                hints.append({
                    "site": "overall",
                    "type": "heterogeneous_coordination",
                    "observation": f"High coordination variance (σ={coord_std:.2f})",
                    "suggestion": "Structure shows diverse coordination environments",
                    "confidence": "high",
                    "quantified_deviation": {
                        "std_dev": coord_std,
                        "typical_threshold": 2.0
                    }
                })

        return hints

    def _classify_confidence(self, likeness: float) -> str:
        """Classify confidence level based on order parameter."""
        if likeness >= self.CONFIDENCE_THRESHOLDS["high"]:
            return "high"
        elif likeness >= self.CONFIDENCE_THRESHOLDS["probable"]:
            return "probable"
        else:
            return "ambiguous"

    def _classify_distortion_severity(self, likeness: float) -> str:
        """Classify geometry distortion severity."""
        if likeness >= 0.9:
            return "negligible"
        elif likeness >= 0.7:
            return "minor"
        elif likeness >= 0.5:
            return "moderate"
        else:
            return "major"

    def _suggest_geometry_improvement(
        self,
        geometry_type: str,
        current_likeness: float
    ) -> str:
        """Generate suggestion for improving geometry."""
        deficit = 1.0 - current_likeness

        if "octahedral" in geometry_type.lower():
            if deficit < 0.2:
                return "Consider slight adjustments to O-M-O angles toward 90°/180°"
            else:
                return "Significant octahedral distortion - check bond angles and lengths"
        elif "tetrahedral" in geometry_type.lower():
            if deficit < 0.2:
                return "Consider adjusting bond angles toward ideal 109.47°"
            else:
                return "Major tetrahedral distortion - verify coordination geometry"
        elif "planar" in geometry_type.lower():
            return "Consider improving planarity - check out-of-plane distances"
        else:
            return f"Consider regularizing {geometry_type} coordination"

    def _suggest_dimensionality_change(
        self,
        current_dim: int,
        target_dim: int
    ) -> str:
        """Generate suggestion for dimensionality adjustment."""
        if current_dim < target_dim:
            if current_dim == 0 and target_dim == 1:
                return "Consider connecting molecules along preferred axis"
            elif current_dim == 1 and target_dim == 2:
                return "Consider extending chain structure into 2D layer"
            elif target_dim == 3:
                return "Consider connecting lower-dimensional units into 3D framework"
        else:
            if current_dim == 3 and target_dim == 2:
                return "Consider isolating 2D layers (check interlayer connectivity)"
            elif current_dim == 3 and target_dim == 1:
                return "Consider isolating 1D chains"
            elif target_dim == 0:
                return "Consider creating discrete molecular units"

        return f"Adjust connectivity to achieve {target_dim}D structure"
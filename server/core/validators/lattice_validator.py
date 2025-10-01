from typing import Any, Dict, List
import numpy as np
from ase import Atoms


class LatticeConstraintValidator:
    """Validates lattice parameters against user-defined constraints.

    Supports:
    - Individual parameter constraints (a, b, c, α, β, γ)
    - Crystal system constraints (cubic, orthorhombic, etc.)
    - Volume constraints
    - Parameter ratio constraints
    """

    WARNING_THRESHOLD = 0.05  # 5% deviation triggers warning
    VIOLATION_THRESHOLD = 0.15  # 15% deviation triggers violation

    CRYSTAL_SYSTEMS = {
        "cubic": {
            "conditions": ["a=b=c", "α=β=γ=90"],
            "check": lambda params: (
                np.allclose([params['a'], params['b'], params['c']], params['a'], rtol=0.01) and
                np.allclose([params['alpha'], params['beta'], params['gamma']], 90, atol=1.0)
            )
        },
        "tetragonal": {
            "conditions": ["a=b≠c", "α=β=γ=90"],
            "check": lambda params: (
                np.isclose(params['a'], params['b'], rtol=0.01) and
                not np.isclose(params['a'], params['c'], rtol=0.01) and
                np.allclose([params['alpha'], params['beta'], params['gamma']], 90, atol=1.0)
            )
        },
        "orthorhombic": {
            "conditions": ["a≠b≠c", "α=β=γ=90"],
            "check": lambda params: (
                np.allclose([params['alpha'], params['beta'], params['gamma']], 90, atol=1.0)
            )
        },
        "hexagonal": {
            "conditions": ["a=b≠c", "α=β=90, γ=120"],
            "check": lambda params: (
                np.isclose(params['a'], params['b'], rtol=0.01) and
                not np.isclose(params['a'], params['c'], rtol=0.01) and
                np.allclose([params['alpha'], params['beta']], 90, atol=1.0) and
                np.isclose(params['gamma'], 120, atol=1.0)
            )
        },
        "rhombohedral": {
            "conditions": ["a=b=c", "α=β=γ≠90"],
            "check": lambda params: (
                np.allclose([params['a'], params['b'], params['c']], params['a'], rtol=0.01) and
                np.allclose([params['alpha'], params['beta'], params['gamma']], params['alpha'], atol=1.0) and
                not np.isclose(params['alpha'], 90, atol=1.0)
            )
        },
        "monoclinic": {
            "conditions": ["a≠b≠c", "α=γ=90≠β"],
            "check": lambda params: (
                np.allclose([params['alpha'], params['gamma']], 90, atol=1.0) and
                not np.isclose(params['beta'], 90, atol=1.0)
            )
        },
        "triclinic": {
            "conditions": ["a≠b≠c", "α≠β≠γ"],
            "check": lambda params: True  # No constraints
        }
    }

    def __init__(self, lattice_constraints: Dict[str, Any]):
        """Initialize with lattice constraints.

        Args:
            lattice_constraints: Dict with lattice constraints
                Example: {
                    "a": {"min": 3.5, "max": 3.7, "target": 3.61},
                    "alpha": {"value": 90, "tolerance": 0.5},
                    "volume": {"min": 45, "max": 50},
                    "crystal_system": "cubic"
                }
        """
        self.constraints = lattice_constraints

    def validate(
        self,
        atoms: Atoms
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Validate lattice parameters against constraints.

        Args:
            atoms: ASE Atoms object

        Returns:
            Dict with 'passed', 'warnings', and 'violations' lists
        """
        results = {
            "passed": [],
            "warnings": [],
            "violations": []
        }

        # Extract lattice parameters
        params = self._extract_parameters(atoms)

        # Validate individual parameters
        for param_name in ['a', 'b', 'c', 'alpha', 'beta', 'gamma']:
            if param_name in self.constraints:
                self._validate_parameter(
                    param_name, params[param_name],
                    self.constraints[param_name], results
                )

        # Validate crystal system
        if "crystal_system" in self.constraints:
            self._validate_crystal_system(
                params, self.constraints["crystal_system"], results
            )

        # Validate volume
        if "volume" in self.constraints:
            self._validate_volume(params["volume"], self.constraints["volume"], results)

        # Validate ratios
        if "ratios" in self.constraints:
            self._validate_ratios(params, self.constraints["ratios"], results)

        return results

    def _extract_parameters(self, atoms: Atoms) -> Dict[str, float]:
        """Extract lattice parameters from ASE Atoms.

        Args:
            atoms: ASE Atoms object

        Returns:
            Dict with a, b, c (Angstroms), alpha, beta, gamma (degrees), volume
        """
        cell = atoms.get_cell()
        lengths = cell.lengths()  # a, b, c
        angles = cell.angles()    # alpha, beta, gamma
        volume = atoms.get_volume()

        return {
            "a": float(lengths[0]),
            "b": float(lengths[1]),
            "c": float(lengths[2]),
            "alpha": float(angles[0]),
            "beta": float(angles[1]),
            "gamma": float(angles[2]),
            "volume": float(volume)
        }

    def _validate_parameter(
        self,
        param_name: str,
        param_value: float,
        constraint: Dict[str, float],
        results: Dict[str, List[Dict[str, Any]]]
    ):
        """Validate individual parameter.

        Args:
            param_name: Parameter name (a, b, c, alpha, beta, gamma)
            param_value: Measured value
            constraint: Constraint dict with min/max/target or value/tolerance
            results: Results dict to update
        """
        # Handle two formats: {min, max} or {value, tolerance}
        if "value" in constraint:
            # Exact value with tolerance
            target = constraint["value"]
            tolerance = constraint.get("tolerance", target * 0.02)  # Default 2%
            min_val = target - tolerance
            max_val = target + tolerance
        else:
            # Range format
            min_val = constraint.get("min", float('-inf'))
            max_val = constraint.get("max", float('inf'))
            target = constraint.get("target", (min_val + max_val) / 2)

        # Calculate deviation
        if min_val <= param_value <= max_val:
            results["passed"].append({
                "type": "lattice_parameter",
                "parameter": param_name,
                "detail": f"{param_name} = {param_value:.3f} (expected: [{min_val:.3f}, {max_val:.3f}])",
                "value": param_value,
                "target": target
            })
        else:
            # Calculate severity
            range_size = max_val - min_val
            if param_value < min_val:
                deviation = (min_val - param_value) / range_size
            else:
                deviation = (param_value - max_val) / range_size

            if deviation < self.VIOLATION_THRESHOLD:
                results["warnings"].append({
                    "type": "lattice_parameter",
                    "parameter": param_name,
                    "detail": f"{param_name} = {param_value:.3f} slightly outside [{min_val:.3f}, {max_val:.3f}]",
                    "severity": f"{deviation*100:.1f}% deviation",
                    "value": param_value,
                    "expected_range": f"[{min_val:.3f}, {max_val:.3f}]",
                    "suggestion": f"Adjust {param_name} toward {target:.3f}"
                })
            else:
                results["violations"].append({
                    "type": "lattice_parameter",
                    "parameter": param_name,
                    "detail": f"{param_name} = {param_value:.3f} severely outside [{min_val:.3f}, {max_val:.3f}]",
                    "severity": f"{deviation*100:.1f}% deviation",
                    "value": param_value,
                    "expected_range": f"[{min_val:.3f}, {max_val:.3f}]",
                    "suggestion": f"Major adjustment needed: {param_name} → {target:.3f}"
                })

    def _validate_crystal_system(
        self,
        params: Dict[str, float],
        expected_system: str,
        results: Dict[str, List[Dict[str, Any]]]
    ):
        """Validate crystal system.

        Args:
            params: Lattice parameters
            expected_system: Expected crystal system name
            results: Results dict to update
        """
        if expected_system not in self.CRYSTAL_SYSTEMS:
            results["violations"].append({
                "type": "crystal_system",
                "detail": f"Unknown crystal system: {expected_system}",
                "suggestion": f"Valid systems: {list(self.CRYSTAL_SYSTEMS.keys())}"
            })
            return

        system_def = self.CRYSTAL_SYSTEMS[expected_system]
        is_valid = system_def["check"](params)

        if is_valid:
            results["passed"].append({
                "type": "crystal_system",
                "detail": f"Crystal system: {expected_system}",
                "conditions": system_def["conditions"],
                "system": expected_system
            })
        else:
            results["violations"].append({
                "type": "crystal_system",
                "detail": f"Does not match {expected_system} crystal system",
                "expected_conditions": system_def["conditions"],
                "actual_parameters": {
                    "a": params["a"],
                    "b": params["b"],
                    "c": params["c"],
                    "α": params["alpha"],
                    "β": params["beta"],
                    "γ": params["gamma"]
                },
                "suggestion": f"Adjust cell to satisfy {expected_system} constraints: {', '.join(system_def['conditions'])}"
            })

    def _validate_volume(
        self,
        volume: float,
        constraint: Dict[str, float],
        results: Dict[str, List[Dict[str, Any]]]
    ):
        """Validate cell volume.

        Args:
            volume: Measured volume
            constraint: Constraint dict with min/max
            results: Results dict to update
        """
        min_vol = constraint.get("min", 0)
        max_vol = constraint.get("max", float('inf'))
        target = constraint.get("target", (min_vol + max_vol) / 2)

        if min_vol <= volume <= max_vol:
            results["passed"].append({
                "type": "lattice_volume",
                "detail": f"Volume = {volume:.2f} Ų (expected: [{min_vol:.2f}, {max_vol:.2f}])",
                "value": volume,
                "target": target
            })
        else:
            range_size = max_vol - min_vol
            if volume < min_vol:
                deviation = (min_vol - volume) / range_size
            else:
                deviation = (volume - max_vol) / range_size

            if deviation < self.VIOLATION_THRESHOLD:
                results["warnings"].append({
                    "type": "lattice_volume",
                    "detail": f"Volume = {volume:.2f} Ų slightly outside range",
                    "severity": f"{deviation*100:.1f}% deviation",
                    "value": volume,
                    "expected_range": f"[{min_vol:.2f}, {max_vol:.2f}] Ų",
                    "suggestion": f"Adjust cell volume toward {target:.2f} Ų"
                })
            else:
                results["violations"].append({
                    "type": "lattice_volume",
                    "detail": f"Volume = {volume:.2f} Ų severely outside range",
                    "severity": f"{deviation*100:.1f}% deviation",
                    "value": volume,
                    "expected_range": f"[{min_vol:.2f}, {max_vol:.2f}] Ų",
                    "suggestion": f"Major volume adjustment needed: → {target:.2f} Ų"
                })

    def _validate_ratios(
        self,
        params: Dict[str, float],
        ratio_constraints: Dict[str, Dict[str, float]],
        results: Dict[str, List[Dict[str, Any]]]
    ):
        """Validate parameter ratios.

        Args:
            params: Lattice parameters
            ratio_constraints: Ratio constraints
                Example: {"c/a": {"min": 1.5, "max": 1.7, "target": 1.6}}
            results: Results dict to update
        """
        for ratio_name, constraint in ratio_constraints.items():
            # Parse ratio (e.g., "c/a")
            parts = ratio_name.split('/')
            if len(parts) != 2:
                continue

            numerator = params.get(parts[0].strip())
            denominator = params.get(parts[1].strip())

            if numerator is None or denominator is None or denominator == 0:
                continue

            ratio_value = numerator / denominator
            self._validate_parameter(
                f"ratio_{ratio_name}", ratio_value, constraint, results
            )

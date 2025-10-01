from typing import Any, Dict, List, Union
from ase import Atoms
from pymatgen.io.ase import AseAtomsAdaptor
from pymatgen.symmetry.analyzer import SpacegroupAnalyzer


class SymmetryConstraintValidator:
    """Validates crystal symmetry against user-defined constraints.

    Uses pymatgen SpacegroupAnalyzer to detect space groups and
    validates against expected symmetry.

    Supports:
    - Space group number or symbol
    - Point group
    - Equivalent space group handling
    - Symmetry detection tolerance
    """

    # Mapping of common equivalent space group representations
    SPACE_GROUP_EQUIVALENTS = {
        225: ["Fm-3m", "Fm3m", "F m -3 m"],
        221: ["Pm-3m", "Pm3m", "P m -3 m"],
        227: ["Fd-3m", "Fd3m", "F d -3 m"],
        194: ["P6_3/mmc", "P 63/m m c"],
        166: ["R-3m", "R3m", "R -3 m"],
        # Add more as needed
    }

    def __init__(self, symmetry_constraints: Dict[str, Any]):
        """Initialize with symmetry constraints.

        Args:
            symmetry_constraints: Dict with symmetry constraints
                Example: {
                    "space_group": 225,  # or "Fm-3m"
                    "point_group": "Oh",
                    "tolerance": 0.1  # Angstroms for symmetry detection
                }
        """
        self.constraints = symmetry_constraints
        self.tolerance = symmetry_constraints.get("tolerance", 0.1)

    def validate(
        self,
        atoms: Atoms
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Validate symmetry against constraints.

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

        try:
            # Convert to pymatgen Structure
            adaptor = AseAtomsAdaptor()
            structure = adaptor.get_structure(atoms)

            # Analyze symmetry
            analyzer = SpacegroupAnalyzer(structure, symprec=self.tolerance)
            detected_sg_number = analyzer.get_space_group_number()
            detected_sg_symbol = analyzer.get_space_group_symbol()
            detected_pg = analyzer.get_point_group_symbol()

            # Store detected symmetry
            symmetry_info = {
                "space_group_number": detected_sg_number,
                "space_group_symbol": detected_sg_symbol,
                "point_group": detected_pg,
                "crystal_system": analyzer.get_crystal_system(),
                "hall_number": analyzer.get_hall()
            }

            # Validate space group
            if "space_group" in self.constraints:
                self._validate_space_group(
                    self.constraints["space_group"],
                    symmetry_info,
                    results
                )

            # Validate point group
            if "point_group" in self.constraints:
                self._validate_point_group(
                    self.constraints["point_group"],
                    symmetry_info,
                    results
                )

        except Exception as e:
            results["violations"].append({
                "type": "symmetry_analysis",
                "detail": f"Symmetry analysis failed: {str(e)}",
                "suggestion": "Structure may be too distorted or have invalid cell parameters"
            })

        return results

    def _validate_space_group(
        self,
        expected: Union[int, str],
        symmetry_info: Dict[str, Any],
        results: Dict[str, List[Dict[str, Any]]]
    ):
        """Validate space group.

        Args:
            expected: Expected space group (number or symbol)
            symmetry_info: Detected symmetry information
            results: Results dict to update
        """
        detected_number = symmetry_info["space_group_number"]
        detected_symbol = symmetry_info["space_group_symbol"]

        # Normalize expected value
        if isinstance(expected, int):
            expected_number = expected
            expected_symbol = self._get_symbol_for_number(expected)
        else:
            expected_symbol = expected
            expected_number = self._get_number_for_symbol(expected)

        # Check if match
        is_match = (
            detected_number == expected_number or
            detected_symbol == expected_symbol or
            self._are_equivalent(expected_number, detected_symbol) or
            self._are_equivalent(expected_symbol, detected_number)
        )

        if is_match:
            results["passed"].append({
                "type": "space_group",
                "detail": f"Space group: {detected_symbol} ({detected_number})",
                "expected": f"{expected_symbol or expected_number}",
                "detected": {
                    "number": detected_number,
                    "symbol": detected_symbol
                }
            })
        else:
            results["violations"].append({
                "type": "space_group",
                "detail": f"Space group mismatch: expected {expected}, detected {detected_symbol} ({detected_number})",
                "expected": f"{expected_symbol or expected_number}",
                "detected": {
                    "number": detected_number,
                    "symbol": detected_symbol
                },
                "suggestion": f"Structure symmetry is {detected_symbol}, not {expected}. Adjust atomic positions to restore symmetry."
            })

    def _validate_point_group(
        self,
        expected: str,
        symmetry_info: Dict[str, Any],
        results: Dict[str, List[Dict[str, Any]]]
    ):
        """Validate point group.

        Args:
            expected: Expected point group symbol
            symmetry_info: Detected symmetry information
            results: Results dict to update
        """
        detected = symmetry_info["point_group"]

        if detected == expected:
            results["passed"].append({
                "type": "point_group",
                "detail": f"Point group: {detected}",
                "expected": expected,
                "detected": detected
            })
        else:
            results["violations"].append({
                "type": "point_group",
                "detail": f"Point group mismatch: expected {expected}, detected {detected}",
                "expected": expected,
                "detected": detected,
                "suggestion": f"Structure has {detected} symmetry instead of {expected}"
            })

    def _get_symbol_for_number(self, number: int) -> str:
        """Get space group symbol from number.

        Args:
            number: Space group number

        Returns:
            Space group symbol or empty string
        """
        # Use mapping if available
        if number in self.SPACE_GROUP_EQUIVALENTS:
            return self.SPACE_GROUP_EQUIVALENTS[number][0]
        return ""

    def _get_number_for_symbol(self, symbol: str) -> int:
        """Get space group number from symbol.

        Args:
            symbol: Space group symbol

        Returns:
            Space group number or 0
        """
        # Reverse lookup in equivalents
        for number, symbols in self.SPACE_GROUP_EQUIVALENTS.items():
            if symbol in symbols:
                return number
        return 0

    def _are_equivalent(
        self,
        reference: Union[int, str],
        detected: Union[int, str]
    ) -> bool:
        """Check if two space group representations are equivalent.

        Args:
            reference: Reference space group (number or symbol)
            detected: Detected space group (number or symbol)

        Returns:
            True if equivalent
        """
        # If reference is a number, check if detected matches any equivalent symbol
        if isinstance(reference, int):
            if reference in self.SPACE_GROUP_EQUIVALENTS:
                return detected in self.SPACE_GROUP_EQUIVALENTS[reference]

        # If reference is a symbol, find its number and check equivalents
        if isinstance(reference, str):
            for number, symbols in self.SPACE_GROUP_EQUIVALENTS.items():
                if reference in symbols:
                    # Check if detected matches this number or any equivalent
                    if detected == number or detected in symbols:
                        return True

        return False

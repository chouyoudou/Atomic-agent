from typing import Any, Dict, List, Optional
import numpy as np
from ase import Atoms


class FreezingConstraintValidator:
    """Validates that 'frozen' structural features remain unchanged.

    Allows LLM agents to mark parts of a structure as 'complete' and
    prevent subsequent iterations from breaking them.

    Supports freezing:
    - Individual atoms (position should not change)
    - Bond lengths between specific atom pairs
    - Bond angles for specific triplets
    - Entire coordination environments

    Requires a reference structure to compare against.
    """

    # Thresholds for detecting violations
    ATOM_POSITION_THRESHOLD = 0.1  # Angstroms
    BOND_LENGTH_THRESHOLD = 0.05  # Angstroms
    BOND_ANGLE_THRESHOLD = 2.0  # Degrees

    def __init__(
        self,
        freezing_constraints: Dict[str, Any],
        reference_atoms: Optional[Atoms] = None
    ):
        """Initialize with freezing constraints.

        Args:
            freezing_constraints: Dict with freezing specifications
                Example: {
                    "frozen_atoms": [0, 1, 2],
                    "frozen_bonds": [
                        {"atoms": [0, 1], "length": 1.95},
                        {"bond_type": "Ti-O"}  # All Ti-O bonds
                    ],
                    "frozen_angles": [
                        {"atoms": [0, 1, 2], "angle": 90.0},
                        {"triplet": "O-Ti-O"}  # All O-Ti-O angles
                    ],
                    "frozen_coordination": [0, 1]  # Coordination of these atoms
                }
            reference_atoms: Reference structure to compare against
        """
        self.constraints = freezing_constraints
        self.reference_atoms = reference_atoms

    def validate(
        self,
        current_atoms: Atoms,
        observations: Optional[Dict[str, Any]] = None,
        reference_observations: Optional[Dict[str, Any]] = None
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Validate that frozen features remain unchanged.

        Args:
            current_atoms: Current structure
            observations: Current structure observations (for coordination)
            reference_observations: Reference observations

        Returns:
            Dict with 'passed', 'warnings', and 'violations' lists
        """
        results = {
            "passed": [],
            "warnings": [],
            "violations": []
        }

        if self.reference_atoms is None:
            results["violations"].append({
                "type": "freezing_check",
                "detail": "No reference structure provided for freezing validation",
                "suggestion": "Set a reference structure before using freezing constraints"
            })
            return results

        # Validate frozen atoms
        if "frozen_atoms" in self.constraints:
            self._validate_frozen_atoms(
                self.constraints["frozen_atoms"],
                current_atoms,
                results
            )

        # Validate frozen bonds
        if "frozen_bonds" in self.constraints:
            self._validate_frozen_bonds(
                self.constraints["frozen_bonds"],
                current_atoms,
                results
            )

        # Validate frozen angles
        if "frozen_angles" in self.constraints:
            self._validate_frozen_angles(
                self.constraints["frozen_angles"],
                current_atoms,
                results
            )

        # Validate frozen coordination
        if "frozen_coordination" in self.constraints and observations:
            self._validate_frozen_coordination(
                self.constraints["frozen_coordination"],
                observations,
                reference_observations,
                results
            )

        return results

    def _validate_frozen_atoms(
        self,
        frozen_indices: List[int],
        current_atoms: Atoms,
        results: Dict[str, List[Dict[str, Any]]]
    ):
        """Validate that frozen atoms haven't moved.

        Args:
            frozen_indices: List of atom indices to check
            current_atoms: Current structure
            results: Results dict to update
        """
        ref_positions = self.reference_atoms.get_positions()
        cur_positions = current_atoms.get_positions()

        for idx in frozen_indices:
            if idx >= len(ref_positions) or idx >= len(cur_positions):
                results["violations"].append({
                    "type": "frozen_atom",
                    "atom_index": idx,
                    "detail": f"Frozen atom #{idx} not found in structure",
                    "suggestion": "Atom may have been deleted"
                })
                continue

            # Calculate displacement
            displacement = np.linalg.norm(
                cur_positions[idx] - ref_positions[idx]
            )

            if displacement < self.ATOM_POSITION_THRESHOLD:
                results["passed"].append({
                    "type": "frozen_atom",
                    "atom_index": idx,
                    "detail": f"Atom #{idx} position unchanged ({displacement:.3f} Å)",
                    "displacement": float(displacement)
                })
            else:
                element = current_atoms[idx].symbol
                results["violations"].append({
                    "type": "frozen_atom",
                    "atom_index": idx,
                    "element": element,
                    "detail": f"Frozen atom #{idx} ({element}) moved {displacement:.3f} Å",
                    "displacement": float(displacement),
                    "threshold": self.ATOM_POSITION_THRESHOLD,
                    "old_position": ref_positions[idx].tolist(),
                    "new_position": cur_positions[idx].tolist(),
                    "suggestion": f"This atom was marked as frozen. Consider reverting to original position."
                })

    def _validate_frozen_bonds(
        self,
        frozen_bonds: List[Dict[str, Any]],
        current_atoms: Atoms,
        results: Dict[str, List[Dict[str, Any]]]
    ):
        """Validate that frozen bond lengths haven't changed.

        Args:
            frozen_bonds: List of bond specifications
            current_atoms: Current structure
            results: Results dict to update
        """
        for bond_spec in frozen_bonds:
            if "atoms" in bond_spec:
                # Specific bond between two atoms
                atom1, atom2 = bond_spec["atoms"]
                ref_length = bond_spec.get("length")

                if ref_length is None:
                    # Calculate from reference
                    ref_length = self.reference_atoms.get_distance(
                        atom1, atom2, mic=True
                    )

                cur_length = current_atoms.get_distance(atom1, atom2, mic=True)
                deviation = abs(cur_length - ref_length)

                if deviation < self.BOND_LENGTH_THRESHOLD:
                    results["passed"].append({
                        "type": "frozen_bond",
                        "atoms": [atom1, atom2],
                        "detail": f"Bond {atom1}-{atom2}: {cur_length:.3f} Å (unchanged)",
                        "length": float(cur_length),
                        "reference": float(ref_length)
                    })
                else:
                    results["violations"].append({
                        "type": "frozen_bond",
                        "atoms": [atom1, atom2],
                        "detail": f"Frozen bond {atom1}-{atom2} changed by {deviation:.3f} Å",
                        "old_length": float(ref_length),
                        "new_length": float(cur_length),
                        "deviation": float(deviation),
                        "threshold": self.BOND_LENGTH_THRESHOLD,
                        "suggestion": f"This bond was marked as frozen. Target length: {ref_length:.3f} Å"
                    })

            elif "bond_type" in bond_spec:
                # All bonds of a specific type (e.g., "Ti-O")
                bond_type = bond_spec["bond_type"]
                self._validate_bond_type(
                    bond_type, current_atoms, results
                )

    def _validate_bond_type(
        self,
        bond_type: str,
        current_atoms: Atoms,
        results: Dict[str, List[Dict[str, Any]]]
    ):
        """Validate all bonds of a specific element pair.

        Args:
            bond_type: Bond type string (e.g., "Ti-O")
            current_atoms: Current structure
            results: Results dict to update
        """
        # Parse bond type
        elements = bond_type.split('-')
        if len(elements) != 2:
            return

        elem1, elem2 = elements

        # Find all such bonds in reference
        ref_symbols = self.reference_atoms.get_chemical_symbols()
        cur_symbols = current_atoms.get_chemical_symbols()

        for i, sym1 in enumerate(ref_symbols):
            if sym1 not in [elem1, elem2]:
                continue

            for j, sym2 in enumerate(ref_symbols):
                if i >= j:
                    continue
                if sym2 not in [elem1, elem2]:
                    continue
                if sorted([sym1, sym2]) != sorted([elem1, elem2]):
                    continue

                # Check this bond
                ref_length = self.reference_atoms.get_distance(i, j, mic=True)
                cur_length = current_atoms.get_distance(i, j, mic=True)
                deviation = abs(cur_length - ref_length)

                if deviation >= self.BOND_LENGTH_THRESHOLD:
                    results["violations"].append({
                        "type": "frozen_bond_type",
                        "bond_type": bond_type,
                        "atoms": [i, j],
                        "detail": f"{bond_type} bond {i}-{j} changed by {deviation:.3f} Å",
                        "old_length": float(ref_length),
                        "new_length": float(cur_length),
                        "suggestion": f"All {bond_type} bonds were marked as frozen"
                    })

    def _validate_frozen_angles(
        self,
        frozen_angles: List[Dict[str, Any]],
        current_atoms: Atoms,
        results: Dict[str, List[Dict[str, Any]]]
    ):
        """Validate that frozen bond angles haven't changed.

        Args:
            frozen_angles: List of angle specifications
            current_atoms: Current structure
            results: Results dict to update
        """
        for angle_spec in frozen_angles:
            if "atoms" in angle_spec:
                # Specific angle
                atom1, atom2, atom3 = angle_spec["atoms"]
                ref_angle = angle_spec.get("angle")

                if ref_angle is None:
                    ref_angle = self.reference_atoms.get_angle(
                        atom1, atom2, atom3, mic=True
                    )

                cur_angle = current_atoms.get_angle(atom1, atom2, atom3, mic=True)
                deviation = abs(cur_angle - ref_angle)

                if deviation < self.BOND_ANGLE_THRESHOLD:
                    results["passed"].append({
                        "type": "frozen_angle",
                        "atoms": [atom1, atom2, atom3],
                        "detail": f"Angle {atom1}-{atom2}-{atom3}: {cur_angle:.1f}° (unchanged)",
                        "angle": float(cur_angle),
                        "reference": float(ref_angle)
                    })
                else:
                    results["violations"].append({
                        "type": "frozen_angle",
                        "atoms": [atom1, atom2, atom3],
                        "detail": f"Frozen angle {atom1}-{atom2}-{atom3} changed by {deviation:.1f}°",
                        "old_angle": float(ref_angle),
                        "new_angle": float(cur_angle),
                        "deviation": float(deviation),
                        "threshold": self.BOND_ANGLE_THRESHOLD,
                        "suggestion": f"This angle was marked as frozen. Target: {ref_angle:.1f}°"
                    })

    def _validate_frozen_coordination(
        self,
        frozen_indices: List[int],
        observations: Dict[str, Any],
        reference_observations: Optional[Dict[str, Any]],
        results: Dict[str, List[Dict[str, Any]]]
    ):
        """Validate that frozen coordination environments haven't changed.

        Args:
            frozen_indices: Atom indices with frozen coordination
            observations: Current observations
            reference_observations: Reference observations
            results: Results dict to update
        """
        if reference_observations is None:
            results["violations"].append({
                "type": "frozen_coordination",
                "detail": "No reference observations for coordination check",
                "suggestion": "Provide reference observations"
            })
            return

        # Build coordination maps
        current_coords = {
            site["site_index"]: site["coordination"]
            for site in observations.get("sites", [])
        }
        ref_coords = {
            site["site_index"]: site["coordination"]
            for site in reference_observations.get("sites", [])
        }

        for idx in frozen_indices:
            cur_coord = current_coords.get(idx)
            ref_coord = ref_coords.get(idx)

            if cur_coord is None or ref_coord is None:
                results["violations"].append({
                    "type": "frozen_coordination",
                    "atom_index": idx,
                    "detail": f"Cannot find coordination for atom #{idx}",
                    "suggestion": "Atom may have been deleted or observations incomplete"
                })
                continue

            if cur_coord == ref_coord:
                results["passed"].append({
                    "type": "frozen_coordination",
                    "atom_index": idx,
                    "detail": f"Atom #{idx} coordination unchanged: {cur_coord}",
                    "coordination": cur_coord
                })
            else:
                results["violations"].append({
                    "type": "frozen_coordination",
                    "atom_index": idx,
                    "detail": f"Frozen atom #{idx} coordination changed: {ref_coord} → {cur_coord}",
                    "old_coordination": ref_coord,
                    "new_coordination": cur_coord,
                    "suggestion": f"This atom's coordination was marked as frozen at {ref_coord}"
                })

    def set_reference(self, reference_atoms: Atoms):
        """Update the reference structure.

        Args:
            reference_atoms: New reference structure
        """
        self.reference_atoms = reference_atoms.copy()

import numpy as np
from typing import Dict, List, Optional, Tuple, Any, Union
from ase import Atoms, Atom
from ase.build import bulk, molecule, fcc111, bcc110, hcp0001
from ase.geometry import get_distances
from ase.io import read, write
from ase.calculators.emt import EMT
from ase.optimize import BFGS
from ase.units import Bohr, Hartree
import json
import tempfile
import os
from pathlib import Path


class ASEEngine:
    """
    ASE Core Engine - Encapsulates Atomic Simulation Environment functionality
    """

    def __init__(self):
        self.structures = {}
        self.calculators = {
            'emt': EMT
        }

    def create_bulk_structure(
        self,
        formula: str,
        crystal_structure: str = 'fcc',
        lattice_constant: Optional[float] = None,
        size: Tuple[int, int, int] = (1, 1, 1)
    ) -> Atoms:
        """
        Create bulk crystal structure

        Args:
            formula: Chemical formula, e.g., 'Cu', 'NaCl'
            crystal_structure: Crystal structure type 'fcc', 'bcc', 'hcp', 'diamond', 'sc'
            lattice_constant: Lattice constant
            size: Supercell size (nx, ny, nz)

        Returns:
            Atoms object
        """
        try:
            atoms = bulk(
                formula,
                crystal_structure,
                a=lattice_constant,
                cubic=True
            )

            if size != (1, 1, 1):
                atoms = atoms.repeat(size)

            return atoms

        except Exception as e:
            raise ValueError(f"Failed to create bulk structure: {str(e)}")

    def create_molecule_structure(self, name: str) -> Atoms:
        """
        Create molecular structure

        Args:
            name: Molecule name, e.g., 'H2O', 'CH4', 'C6H6'

        Returns:
            Atoms object
        """
        try:
            atoms = molecule(name)
            return atoms
        except Exception as e:
            raise ValueError(f"Failed to create molecular structure: {str(e)}")

    def create_surface_structure(
        self,
        symbol: str,
        crystal_structure: str = 'fcc',
        miller: Tuple[int, int, int] = (1, 1, 1),
        layers: int = 4,
        size: Tuple[int, int] = (2, 2),
        vacuum: float = 10.0
    ) -> Atoms:
        """
        Create surface structure

        Args:
            symbol: Element symbol
            crystal_structure: Crystal structure type
            miller: Miller indices
            layers: Number of layers
            size: Surface supercell size
            vacuum: Vacuum layer thickness

        Returns:
            Atoms object
        """
        try:
            if crystal_structure == 'fcc':
                atoms = fcc111(symbol, size=size, layers=layers, vacuum=vacuum)
            elif crystal_structure == 'bcc':
                atoms = bcc110(symbol, size=size, layers=layers, vacuum=vacuum)
            elif crystal_structure == 'hcp':
                atoms = hcp0001(symbol, size=size, layers=layers, vacuum=vacuum)
            else:
                raise ValueError(f"Unsupported surface structure: {crystal_structure}")

            return atoms

        except Exception as e:
            raise ValueError(f"Failed to create surface structure: {str(e)}")

    def modify_structure(
        self,
        atoms: Atoms,
        operation: str,
        parameters: Dict[str, Any]
    ) -> Atoms:
        """
        Modify atomic structure

        Args:
            atoms: Input atomic structure
            operation: Operation type
            parameters: Operation parameters

        Returns:
            Modified Atoms object
        """
        atoms_copy = atoms.copy()

        try:
            if operation == 'rotate':
                axis = parameters.get('axis', [0, 0, 1])
                angle = parameters.get('angle', 0)
                center = parameters.get('center', atoms_copy.get_center_of_mass())
                atoms_copy.rotate(np.radians(angle), axis, center=center)

            elif operation == 'translate':
                vector = parameters.get('vector', [0, 0, 0])
                atoms_copy.translate(vector)

            elif operation == 'scale':
                factor = parameters.get('factor', 1.0)
                atoms_copy.set_cell(atoms_copy.get_cell() * factor, scale_atoms=True)

            elif operation == 'supercell':
                size = parameters.get('size', [2, 2, 2])
                atoms_copy = atoms_copy.repeat(size)

            elif operation == 'remove_atoms':
                indices = parameters.get('indices', [])
                mask = np.ones(len(atoms_copy), dtype=bool)
                mask[indices] = False
                atoms_copy = atoms_copy[mask]

            elif operation == 'add_atom':
                symbol = parameters.get('symbol', 'H')
                position = parameters.get('position', [0, 0, 0])
                atoms_copy.append(Atom(symbol, position))

            elif operation == 'modify_cell':
                new_cell = parameters.get('cell')
                scale_atoms = parameters.get('scale_atoms', False)
                if new_cell is not None:
                    atoms_copy.set_cell(new_cell, scale_atoms=scale_atoms)

            elif operation == 'modify_positions':
                positions = parameters.get('positions')
                indices = parameters.get('indices', None)
                if positions is not None:
                    if indices is not None:
                        # Modify positions of specified atoms
                        atoms_copy.positions[indices] = positions
                    else:
                        # Modify positions of all atoms
                        atoms_copy.set_positions(positions)

            elif operation == 'replace_atoms':
                # Complete replacement of atomic structure
                symbols = parameters.get('symbols', [])
                positions = parameters.get('positions', [])
                cell = parameters.get('cell', atoms_copy.get_cell())

                if len(symbols) != len(positions):
                    raise ValueError("Number of symbols and positions do not match")

                atoms_copy = Atoms(symbols=symbols, positions=positions, cell=cell, pbc=True)

            elif operation == 'change_species':
                # Change atomic species
                indices = parameters.get('indices', [])
                new_symbols = parameters.get('symbols', [])

                if len(indices) != len(new_symbols):
                    raise ValueError("Number of indices and new symbols do not match")

                current_symbols = list(atoms_copy.get_chemical_symbols())
                for idx, symbol in zip(indices, new_symbols):
                    current_symbols[idx] = symbol
                atoms_copy.set_chemical_symbols(current_symbols)

            elif operation == 'duplicate_atoms':
                # Duplicate specified atoms
                indices = parameters.get('indices', [])
                offset = parameters.get('offset', [0, 0, 1])

                for idx in indices:
                    new_pos = atoms_copy.positions[idx] + np.array(offset)
                    atoms_copy.append(Atom(atoms_copy[idx].symbol, new_pos))

            elif operation == 'create_vacancy':
                # Create vacancy (remove atoms but keep cell)
                indices = parameters.get('indices', [])
                if indices:
                    mask = np.ones(len(atoms_copy), dtype=bool)
                    mask[indices] = False
                    atoms_copy = atoms_copy[mask]

            else:
                raise ValueError(f"Unknown operation type: {operation}")

            return atoms_copy

        except Exception as e:
            raise ValueError(f"Structure modification failed: {str(e)}")

    def calculate_properties(
        self,
        atoms: Atoms,
        calculator: str = 'emt',
        properties: List[str] = ['energy']
    ) -> Dict[str, Any]:
        """
        Calculate properties of atomic structure

        Args:
            atoms: Atomic structure
            calculator: Calculator type
            properties: List of properties to calculate

        Returns:
            Properties dictionary
        """
        try:
            if calculator not in self.calculators:
                raise ValueError(f"Unsupported calculator: {calculator}")

            calc = self.calculators[calculator]()
            atoms.set_calculator(calc)

            results = {}

            if 'energy' in properties:
                results['energy'] = atoms.get_potential_energy()

            if 'forces' in properties:
                results['forces'] = atoms.get_forces().tolist()

            if 'stress' in properties:
                results['stress'] = atoms.get_stress().tolist()

            if 'dipole' in properties:
                try:
                    results['dipole'] = atoms.get_dipole_moment().tolist()
                except:
                    results['dipole'] = None

            return results

        except Exception as e:
            raise ValueError(f"Property calculation failed: {str(e)}")

    def optimize_structure(
        self,
        atoms: Atoms,
        calculator: str = 'emt',
        fmax: float = 0.01,
        steps: int = 100
    ) -> Tuple[Atoms, Dict[str, Any]]:
        """
        Optimize atomic structure

        Args:
            atoms: Input structure
            calculator: Calculator type
            fmax: Convergence threshold
            steps: Maximum optimization steps

        Returns:
            Optimized structure and optimization info
        """
        try:
            atoms_copy = atoms.copy()

            if calculator not in self.calculators:
                raise ValueError(f"Unsupported calculator: {calculator}")

            calc = self.calculators[calculator]()
            atoms_copy.set_calculator(calc)

            optimizer = BFGS(atoms_copy)

            initial_energy = atoms_copy.get_potential_energy()
            optimizer.run(fmax=fmax, steps=steps)
            final_energy = atoms_copy.get_potential_energy()

            optimization_info = {
                'converged': optimizer.converged(),
                'initial_energy': initial_energy,
                'final_energy': final_energy,
                'energy_change': final_energy - initial_energy,
                'steps': optimizer.get_number_of_steps()
            }

            return atoms_copy, optimization_info

        except Exception as e:
            raise ValueError(f"Structure optimization failed: {str(e)}")

    def convert_to_dict(self, atoms: Atoms) -> Dict[str, Any]:
        """
        将Atoms对象转换为字典格式

        Args:
            atoms: Atoms对象

        Returns:
            字典表示
        """
        try:
            return {
                'symbols': atoms.get_chemical_symbols(),
                'positions': atoms.get_positions().tolist(),
                'cell': atoms.get_cell().tolist(),
                'pbc': atoms.get_pbc().tolist(),
                'numbers': atoms.get_atomic_numbers().tolist(),
                'masses': atoms.get_masses().tolist(),
                'total_atoms': len(atoms),
                'formula': atoms.get_chemical_formula(),
                'center_of_mass': atoms.get_center_of_mass().tolist(),
                'volume': atoms.get_volume() if atoms.get_pbc().any() else None
            }
        except Exception as e:
            raise ValueError(f"Conversion to dictionary failed: {str(e)}")

    def convert_from_dict(self, data: Dict[str, Any]) -> Atoms:
        """
        Create Atoms object from dictionary

        Args:
            data: Dictionary data

        Returns:
            Atoms object
        """
        try:
            atoms = Atoms(
                symbols=data['symbols'],
                positions=data['positions'],
                cell=data['cell'],
                pbc=data['pbc']
            )
            return atoms
        except Exception as e:
            raise ValueError(f"Failed to create structure from dictionary: {str(e)}")

    def save_structure(
        self,
        atoms: Atoms,
        filename: str,
        format: str = None
    ) -> str:
        """
        Save structure to file

        Args:
            atoms: Atomic structure
            filename: File name
            format: File format, if None, infer from file extension

        Returns:
            Saved file path
        """
        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(filename), exist_ok=True)

            write(filename, atoms, format=format)
            return filename

        except Exception as e:
            raise ValueError(f"Failed to save structure: {str(e)}")

    def load_structure(self, filename: str) -> Atoms:
        """
        Load structure from file

        Args:
            filename: File path

        Returns:
            Atoms object
        """
        try:
            atoms = read(filename)
            return atoms
        except Exception as e:
            raise ValueError(f"Failed to load structure: {str(e)}")

    def get_structure_info(self, atoms: Atoms) -> Dict[str, Any]:
        """
        Get basic information about the structure

        Args:
            atoms: Atomic structure

        Returns:
            Structure information dictionary
        """
        try:
            info = {
                'formula': atoms.get_chemical_formula(),
                'total_atoms': len(atoms),
                'unique_elements': list(set(atoms.get_chemical_symbols())),
                'cell_volume': atoms.get_volume() if atoms.get_pbc().any() else None,
                'center_of_mass': atoms.get_center_of_mass().tolist(),
                'cell_parameters': atoms.get_cell().tolist(),
                'periodic_boundary_conditions': atoms.get_pbc().tolist(),
                'atomic_numbers': atoms.get_atomic_numbers().tolist(),
                'masses': atoms.get_masses().tolist()
            }

            # Calculate bond length information
            if len(atoms) > 1:
                distances = atoms.get_all_distances()
                non_zero_distances = distances[distances > 0]
                if len(non_zero_distances) > 0:
                    info['min_distance'] = float(np.min(non_zero_distances))
                    info['max_distance'] = float(np.max(non_zero_distances))
                    info['avg_distance'] = float(np.mean(non_zero_distances))

            return info

        except Exception as e:
            raise ValueError(f"Failed to get structure information: {str(e)}")
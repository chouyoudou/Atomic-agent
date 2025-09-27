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
    ASE核心引擎，封装原子模拟环境的功能
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
        创建块体晶体结构

        Args:
            formula: 化学式，如 'Cu', 'NaCl'
            crystal_structure: 晶体结构类型 'fcc', 'bcc', 'hcp', 'diamond', 'sc'
            lattice_constant: 晶格常数
            size: 超胞大小 (nx, ny, nz)

        Returns:
            Atoms对象
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
            raise ValueError(f"创建块体结构失败: {str(e)}")

    def create_molecule_structure(self, name: str) -> Atoms:
        """
        创建分子结构

        Args:
            name: 分子名称，如 'H2O', 'CH4', 'C6H6'

        Returns:
            Atoms对象
        """
        try:
            atoms = molecule(name)
            return atoms
        except Exception as e:
            raise ValueError(f"创建分子结构失败: {str(e)}")

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
        创建表面结构

        Args:
            symbol: 元素符号
            crystal_structure: 晶体结构
            miller: 米勒指数
            layers: 层数
            size: 表面超胞大小
            vacuum: 真空层厚度

        Returns:
            Atoms对象
        """
        try:
            if crystal_structure == 'fcc':
                atoms = fcc111(symbol, size=size, layers=layers, vacuum=vacuum)
            elif crystal_structure == 'bcc':
                atoms = bcc110(symbol, size=size, layers=layers, vacuum=vacuum)
            elif crystal_structure == 'hcp':
                atoms = hcp0001(symbol, size=size, layers=layers, vacuum=vacuum)
            else:
                raise ValueError(f"不支持的表面结构: {crystal_structure}")

            return atoms

        except Exception as e:
            raise ValueError(f"创建表面结构失败: {str(e)}")

    def modify_structure(
        self,
        atoms: Atoms,
        operation: str,
        parameters: Dict[str, Any]
    ) -> Atoms:
        """
        修改原子结构

        Args:
            atoms: 输入的原子结构
            operation: 操作类型
            parameters: 操作参数

        Returns:
            修改后的Atoms对象
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

            else:
                raise ValueError(f"未知的操作类型: {operation}")

            return atoms_copy

        except Exception as e:
            raise ValueError(f"结构修改失败: {str(e)}")

    def calculate_properties(
        self,
        atoms: Atoms,
        calculator: str = 'emt',
        properties: List[str] = ['energy']
    ) -> Dict[str, Any]:
        """
        计算原子结构的属性

        Args:
            atoms: 原子结构
            calculator: 计算器类型
            properties: 要计算的属性列表

        Returns:
            属性字典
        """
        try:
            if calculator not in self.calculators:
                raise ValueError(f"不支持的计算器: {calculator}")

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
            raise ValueError(f"属性计算失败: {str(e)}")

    def optimize_structure(
        self,
        atoms: Atoms,
        calculator: str = 'emt',
        fmax: float = 0.01,
        steps: int = 100
    ) -> Tuple[Atoms, Dict[str, Any]]:
        """
        优化原子结构

        Args:
            atoms: 输入结构
            calculator: 计算器类型
            fmax: 收敛阈值
            steps: 最大优化步数

        Returns:
            优化后的结构和优化信息
        """
        try:
            atoms_copy = atoms.copy()

            if calculator not in self.calculators:
                raise ValueError(f"不支持的计算器: {calculator}")

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
            raise ValueError(f"结构优化失败: {str(e)}")

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
            raise ValueError(f"转换为字典失败: {str(e)}")

    def convert_from_dict(self, data: Dict[str, Any]) -> Atoms:
        """
        从字典创建Atoms对象

        Args:
            data: 字典数据

        Returns:
            Atoms对象
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
            raise ValueError(f"从字典创建结构失败: {str(e)}")

    def save_structure(
        self,
        atoms: Atoms,
        filename: str,
        format: str = None
    ) -> str:
        """
        保存结构到文件

        Args:
            atoms: 原子结构
            filename: 文件名
            format: 文件格式，如果为None则从文件扩展名推断

        Returns:
            保存的文件路径
        """
        try:
            # 确保目录存在
            os.makedirs(os.path.dirname(filename), exist_ok=True)

            write(filename, atoms, format=format)
            return filename

        except Exception as e:
            raise ValueError(f"保存结构失败: {str(e)}")

    def load_structure(self, filename: str) -> Atoms:
        """
        从文件加载结构

        Args:
            filename: 文件路径

        Returns:
            Atoms对象
        """
        try:
            atoms = read(filename)
            return atoms
        except Exception as e:
            raise ValueError(f"加载结构失败: {str(e)}")

    def get_structure_info(self, atoms: Atoms) -> Dict[str, Any]:
        """
        获取结构的基本信息

        Args:
            atoms: 原子结构

        Returns:
            结构信息字典
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

            # 计算键长信息
            if len(atoms) > 1:
                distances = atoms.get_all_distances()
                non_zero_distances = distances[distances > 0]
                if len(non_zero_distances) > 0:
                    info['min_distance'] = float(np.min(non_zero_distances))
                    info['max_distance'] = float(np.max(non_zero_distances))
                    info['avg_distance'] = float(np.mean(non_zero_distances))

            return info

        except Exception as e:
            raise ValueError(f"获取结构信息失败: {str(e)}")
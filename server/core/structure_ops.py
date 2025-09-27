import numpy as np
from typing import Dict, List, Optional, Tuple, Any, Union
from ase import Atoms
from ase.geometry import find_mic, get_distances
from ase.neighborlist import NeighborList, natural_cutoffs
from ase.build import add_adsorbate, cut
from ase.constraints import FixAtoms, FixBondLengths
import json


class StructureOperations:
    """
    结构操作类，提供高级的结构修改和分析功能
    """

    @staticmethod
    def get_bonds(
        atoms: Atoms,
        cutoff_factor: float = 1.2,
        max_cutoff: float = 3.0
    ) -> List[Dict[str, Any]]:
        """
        获取原子间的键连接信息

        Args:
            atoms: 原子结构
            cutoff_factor: 截断因子
            max_cutoff: 最大截断距离

        Returns:
            键连接列表
        """
        try:
            cutoffs = natural_cutoffs(atoms, mult=cutoff_factor)
            cutoffs = np.minimum(cutoffs, max_cutoff)

            nl = NeighborList(cutoffs, self_interaction=False, bothways=False)
            nl.update(atoms)

            bonds = []
            for i in range(len(atoms)):
                indices, offsets = nl.get_neighbors(i)
                for j, offset in zip(indices, offsets):
                    distance = atoms.get_distance(i, j, mic=True)
                    bonds.append({
                        'atom1': int(i),
                        'atom2': int(j),
                        'distance': float(distance),
                        'symbols': [atoms[i].symbol, atoms[j].symbol],
                        'offset': offset.tolist()
                    })

            return bonds

        except Exception as e:
            raise ValueError(f"获取键连接失败: {str(e)}")

    @staticmethod
    def get_coordination_numbers(
        atoms: Atoms,
        cutoff_factor: float = 1.2
    ) -> Dict[int, int]:
        """
        计算每个原子的配位数

        Args:
            atoms: 原子结构
            cutoff_factor: 截断因子

        Returns:
            原子索引到配位数的映射
        """
        try:
            cutoffs = natural_cutoffs(atoms, mult=cutoff_factor)
            nl = NeighborList(cutoffs, self_interaction=False, bothways=False)
            nl.update(atoms)

            coordination = {}
            for i in range(len(atoms)):
                indices, _ = nl.get_neighbors(i)
                coordination[i] = len(indices)

            return coordination

        except Exception as e:
            raise ValueError(f"计算配位数失败: {str(e)}")

    @staticmethod
    def add_adsorbate_to_surface(
        surface: Atoms,
        adsorbate: Atoms,
        position: Tuple[float, float] = None,
        height: float = 2.0,
        site: str = 'top'
    ) -> Atoms:
        """
        在表面上添加吸附分子

        Args:
            surface: 表面结构
            adsorbate: 吸附分子
            position: 吸附位置 (x, y)
            height: 吸附高度
            site: 吸附位点类型

        Returns:
            添加吸附分子后的结构
        """
        try:
            surface_copy = surface.copy()

            if position is None:
                # 使用表面中心作为默认位置
                cell = surface.get_cell()
                position = (cell[0, 0] / 2, cell[1, 1] / 2)

            add_adsorbate(
                surface_copy,
                adsorbate,
                height=height,
                position=position
            )

            return surface_copy

        except Exception as e:
            raise ValueError(f"添加吸附分子失败: {str(e)}")

    @staticmethod
    def create_defect(
        atoms: Atoms,
        defect_type: str,
        parameters: Dict[str, Any]
    ) -> Atoms:
        """
        创建缺陷结构

        Args:
            atoms: 原始结构
            defect_type: 缺陷类型 ('vacancy', 'interstitial', 'substitution')
            parameters: 缺陷参数

        Returns:
            含缺陷的结构
        """
        try:
            atoms_copy = atoms.copy()

            if defect_type == 'vacancy':
                # 空位缺陷
                index = parameters.get('index', 0)
                del atoms_copy[index]

            elif defect_type == 'interstitial':
                # 间隙缺陷
                symbol = parameters.get('symbol', 'H')
                position = parameters.get('position', atoms.get_center_of_mass())
                atoms_copy.append(symbol)
                atoms_copy.positions[-1] = position

            elif defect_type == 'substitution':
                # 替代缺陷
                index = parameters.get('index', 0)
                new_symbol = parameters.get('symbol', 'H')
                atoms_copy[index].symbol = new_symbol

            else:
                raise ValueError(f"未知的缺陷类型: {defect_type}")

            return atoms_copy

        except Exception as e:
            raise ValueError(f"创建缺陷失败: {str(e)}")

    @staticmethod
    def apply_strain(
        atoms: Atoms,
        strain_tensor: Union[float, List[List[float]]]
    ) -> Atoms:
        """
        对结构施加应变

        Args:
            atoms: 原子结构
            strain_tensor: 应变张量或标量应变

        Returns:
            施加应变后的结构
        """
        try:
            atoms_copy = atoms.copy()

            if isinstance(strain_tensor, (int, float)):
                # 各向同性应变
                strain_matrix = np.eye(3) * (1 + strain_tensor)
            else:
                # 应变张量
                strain_matrix = np.array(strain_tensor)

            # 应用应变到晶胞
            new_cell = np.dot(atoms_copy.get_cell(), strain_matrix)
            atoms_copy.set_cell(new_cell, scale_atoms=True)

            return atoms_copy

        except Exception as e:
            raise ValueError(f"施加应变失败: {str(e)}")

    @staticmethod
    def get_surface_atoms(
        atoms: Atoms,
        direction: str = 'z',
        threshold: float = 1.0
    ) -> List[int]:
        """
        识别表面原子

        Args:
            atoms: 原子结构
            direction: 表面方向
            threshold: 表面阈值

        Returns:
            表面原子索引列表
        """
        try:
            positions = atoms.get_positions()

            if direction == 'z':
                coord = positions[:, 2]
            elif direction == 'y':
                coord = positions[:, 1]
            elif direction == 'x':
                coord = positions[:, 0]
            else:
                raise ValueError(f"未知的方向: {direction}")

            max_coord = np.max(coord)
            surface_indices = np.where(coord > max_coord - threshold)[0]

            return surface_indices.tolist()

        except Exception as e:
            raise ValueError(f"识别表面原子失败: {str(e)}")

    @staticmethod
    def create_interface(
        substrate: Atoms,
        overlayer: Atoms,
        gap: float = 3.0,
        match_lattice: bool = True
    ) -> Atoms:
        """
        创建界面结构

        Args:
            substrate: 衬底结构
            overlayer: 覆盖层结构
            gap: 界面间隙
            match_lattice: 是否匹配晶格

        Returns:
            界面结构
        """
        try:
            substrate_copy = substrate.copy()
            overlayer_copy = overlayer.copy()

            if match_lattice:
                # 匹配覆盖层的晶格到衬底
                substrate_cell = substrate_copy.get_cell()
                overlayer_copy.set_cell(substrate_cell[:2], scale_atoms=True)

            # 移动覆盖层到衬底上方
            substrate_top = np.max(substrate_copy.positions[:, 2])
            overlayer_bottom = np.min(overlayer_copy.positions[:, 2])
            shift = substrate_top + gap - overlayer_bottom

            overlayer_copy.positions[:, 2] += shift

            # 合并结构
            interface = substrate_copy + overlayer_copy

            # 调整晶胞大小
            max_z = np.max(interface.positions[:, 2])
            new_cell = interface.get_cell()
            new_cell[2, 2] = max_z + gap
            interface.set_cell(new_cell)

            return interface

        except Exception as e:
            raise ValueError(f"创建界面失败: {str(e)}")

    @staticmethod
    def analyze_structure_symmetry(atoms: Atoms) -> Dict[str, Any]:
        """
        分析结构对称性

        Args:
            atoms: 原子结构

        Returns:
            对称性分析结果
        """
        try:
            # 这是一个简化的对称性分析
            # 在实际应用中可以使用spglib等库进行更详细的分析

            cell = atoms.get_cell()
            positions = atoms.get_scaled_positions()

            # 检查晶胞是否为立方
            a, b, c = np.linalg.norm(cell, axis=1)
            is_cubic = np.allclose([a, b, c], a, rtol=0.01)

            # 检查晶胞角度
            angles = []
            for i in range(3):
                for j in range(i + 1, 3):
                    cos_angle = np.dot(cell[i], cell[j]) / (np.linalg.norm(cell[i]) * np.linalg.norm(cell[j]))
                    angle = np.degrees(np.arccos(np.clip(cos_angle, -1, 1)))
                    angles.append(angle)

            is_orthogonal = np.allclose(angles, 90, atol=1)

            symmetry_info = {
                'lattice_parameters': [a, b, c],
                'lattice_angles': angles,
                'is_cubic': is_cubic,
                'is_orthogonal': is_orthogonal,
                'volume': atoms.get_volume() if atoms.get_pbc().any() else None,
                'density': len(atoms) / atoms.get_volume() if atoms.get_pbc().any() else None
            }

            return symmetry_info

        except Exception as e:
            raise ValueError(f"对称性分析失败: {str(e)}")

    @staticmethod
    def create_nanoparticle(
        element: str,
        size: int,
        shape: str = 'sphere',
        lattice_constant: float = None
    ) -> Atoms:
        """
        创建纳米粒子

        Args:
            element: 元素符号
            size: 粒子大小(原子数)
            shape: 形状 ('sphere', 'cube')
            lattice_constant: 晶格常数

        Returns:
            纳米粒子结构
        """
        try:
            from ase.cluster import Icosahedron, Octahedron
            from ase.data import atomic_numbers, covalent_radii

            if shape == 'icosahedron':
                # 创建二十面体纳米粒子
                surfaces = [(1, 0, 0), (1, 1, 0), (1, 1, 1)]
                layers = int(np.ceil((size / 13) ** (1/3)))  # 粗略估计层数
                atoms = Icosahedron(element, noshells=layers)

            elif shape == 'octahedron':
                # 创建八面体纳米粒子
                surfaces = [(1, 0, 0), (1, 1, 0), (1, 1, 1)]
                layers = int(np.ceil((size / 6) ** (1/3)))
                atoms = Octahedron(element, length=layers)

            else:
                # 简单的球形粒子
                from ase.build import bulk
                atoms = bulk(element, cubic=True)
                atoms = atoms.repeat((3, 3, 3))

                center = atoms.get_center_of_mass()
                distances = np.linalg.norm(atoms.positions - center, axis=1)
                radius = np.sort(distances)[size] if size < len(atoms) else np.max(distances)

                # 保留半径内的原子
                mask = distances <= radius
                atoms = atoms[mask]

            return atoms

        except Exception as e:
            raise ValueError(f"创建纳米粒子失败: {str(e)}")
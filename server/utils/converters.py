"""
格式转换工具
支持多种文件格式的读写和转换
"""

import io
import json
import tempfile
import os
from typing import Dict, Any, Optional, Union
from pathlib import Path

from ase import Atoms
from ase.io import read, write
import numpy as np


class StructureConverter:
    """结构格式转换器"""

    SUPPORTED_FORMATS = {
        'cif': 'Crystallographic Information File',
        'xyz': 'XYZ coordinate format',
        'pdb': 'Protein Data Bank format',
        'json': 'JSON format',
        'vasp': 'VASP POSCAR format',
        'lammps': 'LAMMPS data format',
        'cube': 'Gaussian cube format',
        'mol': 'MDL MOL format',
        'sdf': 'Structure Data Format'
    }

    @staticmethod
    def atoms_to_dict(atoms: Atoms) -> Dict[str, Any]:
        """将Atoms对象转换为字典"""
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

    @staticmethod
    def dict_to_atoms(data: Dict[str, Any]) -> Atoms:
        """从字典创建Atoms对象"""
        atoms = Atoms(
            symbols=data['symbols'],
            positions=data['positions'],
            cell=data['cell'],
            pbc=data['pbc']
        )
        return atoms

    @staticmethod
    def atoms_to_string(atoms: Atoms, format: str = 'xyz') -> str:
        """将Atoms对象转换为字符串"""
        with tempfile.NamedTemporaryFile(mode='w+', suffix=f'.{format}', delete=False) as f:
            try:
                write(f.name, atoms, format=format)
                with open(f.name, 'r') as rf:
                    content = rf.read()
                return content
            finally:
                os.unlink(f.name)

    @staticmethod
    def string_to_atoms(content: str, format: str = 'xyz') -> Atoms:
        """从字符串创建Atoms对象"""
        with tempfile.NamedTemporaryFile(mode='w', suffix=f'.{format}', delete=False) as f:
            try:
                f.write(content)
                f.flush()
                atoms = read(f.name, format=format)
                return atoms
            finally:
                os.unlink(f.name)

    @staticmethod
    def convert_format(atoms: Atoms, target_format: str) -> str:
        """转换结构到指定格式"""
        if target_format == 'json':
            return json.dumps(StructureConverter.atoms_to_dict(atoms), indent=2)
        else:
            return StructureConverter.atoms_to_string(atoms, target_format)

    @staticmethod
    def get_format_info(format: str) -> Dict[str, Any]:
        """获取格式信息"""
        return {
            'name': format.upper(),
            'description': StructureConverter.SUPPORTED_FORMATS.get(format, 'Unknown format'),
            'extensions': [f'.{format}'],
            'supports_cell': format in ['cif', 'vasp', 'lammps'],
            'supports_forces': format in ['xyz', 'vasp'],
            'text_based': format in ['xyz', 'cif', 'pdb', 'json', 'vasp']
        }


class PropertyCalculator:
    """属性计算工具"""

    @staticmethod
    def calculate_distances(atoms: Atoms) -> Dict[str, Any]:
        """计算原子间距离"""
        positions = atoms.get_positions()
        n_atoms = len(atoms)

        if n_atoms < 2:
            return {'min_distance': None, 'max_distance': None, 'avg_distance': None}

        distances = []
        for i in range(n_atoms):
            for j in range(i + 1, n_atoms):
                if atoms.get_pbc().any():
                    # 考虑周期性边界条件
                    distance = atoms.get_distance(i, j, mic=True)
                else:
                    # 不考虑周期性边界条件
                    distance = np.linalg.norm(positions[i] - positions[j])
                distances.append(distance)

        distances = np.array(distances)

        return {
            'min_distance': float(np.min(distances)),
            'max_distance': float(np.max(distances)),
            'avg_distance': float(np.mean(distances)),
            'std_distance': float(np.std(distances)),
            'total_pairs': len(distances)
        }

    @staticmethod
    def calculate_geometry(atoms: Atoms) -> Dict[str, Any]:
        """计算几何属性"""
        positions = atoms.get_positions()

        # 边界盒
        min_coords = np.min(positions, axis=0)
        max_coords = np.max(positions, axis=0)
        box_size = max_coords - min_coords

        # 质心
        masses = atoms.get_masses()
        center_of_mass = np.average(positions, weights=masses, axis=0)

        # 惯性张量
        relative_positions = positions - center_of_mass
        inertia_tensor = np.zeros((3, 3))
        for i, mass in enumerate(masses):
            r = relative_positions[i]
            inertia_tensor += mass * (np.dot(r, r) * np.eye(3) - np.outer(r, r))

        # 主惯性矩
        eigenvalues, eigenvectors = np.linalg.eigh(inertia_tensor)
        principal_moments = eigenvalues

        result = {
            'bounding_box': {
                'min': min_coords.tolist(),
                'max': max_coords.tolist(),
                'size': box_size.tolist(),
                'volume': float(np.prod(box_size))
            },
            'center_of_mass': center_of_mass.tolist(),
            'inertia_tensor': inertia_tensor.tolist(),
            'principal_moments': principal_moments.tolist(),
            'principal_axes': eigenvectors.tolist()
        }

        # 如果有晶胞，计算晶胞属性
        if atoms.get_pbc().any():
            cell = atoms.get_cell()
            result['cell_properties'] = {
                'volume': float(atoms.get_volume()),
                'lengths': np.linalg.norm(cell, axis=1).tolist(),
                'angles': [],  # 需要计算晶胞角度
                'reciprocal_cell': np.linalg.inv(cell).T.tolist()
            }

            # 计算晶胞角度
            for i in range(3):
                for j in range(i + 1, 3):
                    cos_angle = np.dot(cell[i], cell[j]) / (
                        np.linalg.norm(cell[i]) * np.linalg.norm(cell[j])
                    )
                    angle = np.degrees(np.arccos(np.clip(cos_angle, -1, 1)))
                    result['cell_properties']['angles'].append(float(angle))

        return result

    @staticmethod
    def analyze_composition(atoms: Atoms) -> Dict[str, Any]:
        """分析成分"""
        symbols = atoms.get_chemical_symbols()
        numbers = atoms.get_atomic_numbers()
        masses = atoms.get_masses()

        # 元素统计
        unique_symbols = list(set(symbols))
        composition = {}
        mass_composition = {}

        total_mass = np.sum(masses)

        for symbol in unique_symbols:
            indices = [i for i, s in enumerate(symbols) if s == symbol]
            count = len(indices)
            element_mass = np.sum([masses[i] for i in indices])

            composition[symbol] = {
                'count': count,
                'fraction': count / len(atoms),
                'mass': float(element_mass),
                'mass_fraction': float(element_mass / total_mass)
            }

        # 化学式
        formula = atoms.get_chemical_formula()
        reduced_formula = atoms.get_chemical_formula(mode='reduce')

        return {
            'total_atoms': len(atoms),
            'total_mass': float(total_mass),
            'unique_elements': unique_symbols,
            'composition': composition,
            'chemical_formula': formula,
            'reduced_formula': reduced_formula,
            'density': float(total_mass / atoms.get_volume()) if atoms.get_pbc().any() else None
        }


class ValidationUtils:
    """验证工具"""

    @staticmethod
    def validate_atoms(atoms: Atoms) -> Dict[str, Any]:
        """验证Atoms对象"""
        issues = []
        warnings = []

        # 检查原子数量
        if len(atoms) == 0:
            issues.append("结构中没有原子")

        # 检查位置
        positions = atoms.get_positions()
        if np.any(np.isnan(positions)) or np.any(np.isinf(positions)):
            issues.append("原子位置包含NaN或无穷大值")

        # 检查重叠原子
        if len(atoms) > 1:
            min_distance = PropertyCalculator.calculate_distances(atoms)['min_distance']
            if min_distance is not None and min_distance < 0.5:
                warnings.append(f"存在原子间距离过近的情况: {min_distance:.3f} Å")

        # 检查晶胞
        if atoms.get_pbc().any():
            cell = atoms.get_cell()
            if np.linalg.det(cell) <= 0:
                issues.append("晶胞体积为负或零")

            # 检查原子是否在晶胞内
            scaled_positions = atoms.get_scaled_positions()
            if np.any(scaled_positions < -0.1) or np.any(scaled_positions > 1.1):
                warnings.append("部分原子位于晶胞外")

        return {
            'valid': len(issues) == 0,
            'issues': issues,
            'warnings': warnings
        }

    @staticmethod
    def suggest_fixes(atoms: Atoms, validation_result: Dict[str, Any]) -> Dict[str, Any]:
        """建议修复方法"""
        suggestions = []

        for issue in validation_result['issues']:
            if "没有原子" in issue:
                suggestions.append("添加原子到结构中")
            elif "NaN或无穷大" in issue:
                suggestions.append("检查并修复原子坐标")
            elif "晶胞体积" in issue:
                suggestions.append("检查并修正晶胞参数")

        for warning in validation_result['warnings']:
            if "原子间距离过近" in warning:
                suggestions.append("考虑结构优化以消除原子重叠")
            elif "原子位于晶胞外" in warning:
                suggestions.append("将原子包装到晶胞内")

        return {
            'suggestions': suggestions,
            'auto_fixable': len([s for s in suggestions if "包装" in s or "优化" in s]) > 0
        }


class FileManager:
    """文件管理工具"""

    @staticmethod
    def save_structure(
        atoms: Atoms,
        filepath: Union[str, Path],
        format: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """保存结构到文件"""
        filepath = Path(filepath)

        # 创建目录
        filepath.parent.mkdir(parents=True, exist_ok=True)

        # 推断格式
        if format is None:
            format = filepath.suffix[1:] if filepath.suffix else 'xyz'

        try:
            # 保存结构文件
            write(str(filepath), atoms, format=format)

            # 保存元数据
            if metadata:
                metadata_file = filepath.with_suffix('.json')
                with open(metadata_file, 'w') as f:
                    json.dump(metadata, f, indent=2)

            file_size = filepath.stat().st_size

            return {
                'success': True,
                'filepath': str(filepath),
                'format': format,
                'file_size': file_size,
                'metadata_saved': metadata is not None
            }

        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'filepath': str(filepath)
            }

    @staticmethod
    def load_structure(
        filepath: Union[str, Path],
        format: Optional[str] = None
    ) -> Dict[str, Any]:
        """从文件加载结构"""
        filepath = Path(filepath)

        if not filepath.exists():
            return {
                'success': False,
                'error': f'文件不存在: {filepath}'
            }

        try:
            # 加载结构
            atoms = read(str(filepath), format=format)

            # 加载元数据
            metadata = None
            metadata_file = filepath.with_suffix('.json')
            if metadata_file.exists():
                with open(metadata_file, 'r') as f:
                    metadata = json.load(f)

            return {
                'success': True,
                'atoms': atoms,
                'metadata': metadata,
                'filepath': str(filepath),
                'file_size': filepath.stat().st_size
            }

        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'filepath': str(filepath)
            }

    @staticmethod
    def list_supported_formats() -> Dict[str, Any]:
        """列出支持的格式"""
        return {
            'formats': StructureConverter.SUPPORTED_FORMATS,
            'total_count': len(StructureConverter.SUPPORTED_FORMATS)
        }
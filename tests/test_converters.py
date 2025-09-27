import pytest
import json
from ase import Atoms

from server.utils.converters import (
    StructureConverter,
    PropertyCalculator,
    ValidationUtils
)


class TestStructureConverter:
    """结构转换器测试"""

    def setup_method(self):
        """测试前准备"""
        # 创建一个简单的测试结构
        self.atoms = Atoms(['H', 'H'], positions=[[0, 0, 0], [0, 0, 0.74]])

    def test_atoms_to_dict(self):
        """测试Atoms转字典"""
        data = StructureConverter.atoms_to_dict(self.atoms)

        assert isinstance(data, dict)
        assert "symbols" in data
        assert "positions" in data
        assert "formula" in data
        assert data["symbols"] == ['H', 'H']
        assert data["total_atoms"] == 2

    def test_dict_to_atoms(self):
        """测试字典转Atoms"""
        data = StructureConverter.atoms_to_dict(self.atoms)
        reconstructed = StructureConverter.dict_to_atoms(data)

        assert len(reconstructed) == len(self.atoms)
        assert reconstructed.get_chemical_symbols() == self.atoms.get_chemical_symbols()

    def test_atoms_to_string_xyz(self):
        """测试Atoms转XYZ字符串"""
        xyz_string = StructureConverter.atoms_to_string(self.atoms, "xyz")

        assert isinstance(xyz_string, str)
        assert "2" in xyz_string  # 原子数量
        assert "H" in xyz_string  # 元素符号

    def test_convert_format_json(self):
        """测试转换为JSON格式"""
        json_string = StructureConverter.convert_format(self.atoms, "json")

        data = json.loads(json_string)
        assert isinstance(data, dict)
        assert "symbols" in data

    def test_get_format_info(self):
        """测试获取格式信息"""
        info = StructureConverter.get_format_info("xyz")

        assert "name" in info
        assert "description" in info
        assert info["name"] == "XYZ"


class TestPropertyCalculator:
    """属性计算器测试"""

    def setup_method(self):
        """测试前准备"""
        # 创建一个简单的H2分子
        self.h2 = Atoms(['H', 'H'], positions=[[0, 0, 0], [0, 0, 0.74]])

        # 创建一个立方体Cu结构
        self.cu = Atoms(['Cu', 'Cu'],
                       positions=[[0, 0, 0], [1.8, 1.8, 1.8]],
                       cell=[3.6, 3.6, 3.6],
                       pbc=True)

    def test_calculate_distances(self):
        """测试距离计算"""
        distances = PropertyCalculator.calculate_distances(self.h2)

        assert "min_distance" in distances
        assert "max_distance" in distances
        assert "avg_distance" in distances
        assert distances["min_distance"] == distances["max_distance"]  # 只有一对原子
        assert abs(distances["min_distance"] - 0.74) < 0.01

    def test_calculate_geometry(self):
        """测试几何属性计算"""
        geometry = PropertyCalculator.calculate_geometry(self.h2)

        assert "bounding_box" in geometry
        assert "center_of_mass" in geometry
        assert "inertia_tensor" in geometry

    def test_analyze_composition(self):
        """测试成分分析"""
        composition = PropertyCalculator.analyze_composition(self.h2)

        assert "total_atoms" in composition
        assert "unique_elements" in composition
        assert "composition" in composition
        assert composition["total_atoms"] == 2
        assert "H" in composition["unique_elements"]
        assert composition["composition"]["H"]["count"] == 2

    def test_calculate_geometry_with_cell(self):
        """测试带晶胞的几何计算"""
        geometry = PropertyCalculator.calculate_geometry(self.cu)

        assert "cell_properties" in geometry
        assert "volume" in geometry["cell_properties"]
        assert geometry["cell_properties"]["volume"] > 0


class TestValidationUtils:
    """验证工具测试"""

    def setup_method(self):
        """测试前准备"""
        self.valid_atoms = Atoms(['H', 'H'], positions=[[0, 0, 0], [0, 0, 0.74]])
        self.invalid_atoms = Atoms(['H', 'H'], positions=[[0, 0, 0], [0, 0, 0]])  # 重叠原子

    def test_validate_valid_atoms(self):
        """测试验证有效结构"""
        result = ValidationUtils.validate_atoms(self.valid_atoms)

        assert result["valid"] is True
        assert len(result["issues"]) == 0

    def test_validate_invalid_atoms(self):
        """测试验证无效结构"""
        result = ValidationUtils.validate_atoms(self.invalid_atoms)

        # 应该有关于原子距离过近的警告
        assert len(result["warnings"]) > 0

    def test_validate_empty_structure(self):
        """测试验证空结构"""
        empty_atoms = Atoms()
        result = ValidationUtils.validate_atoms(empty_atoms)

        assert result["valid"] is False
        assert len(result["issues"]) > 0

    def test_suggest_fixes(self):
        """测试修复建议"""
        validation_result = ValidationUtils.validate_atoms(self.invalid_atoms)
        suggestions = ValidationUtils.suggest_fixes(self.invalid_atoms, validation_result)

        assert "suggestions" in suggestions
        assert isinstance(suggestions["suggestions"], list)


if __name__ == "__main__":
    pytest.main([__file__])
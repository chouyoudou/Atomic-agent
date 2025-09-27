import pytest
import numpy as np
from ase import Atoms

from server.core.ase_engine import ASEEngine


class TestASEEngine:
    """ASE引擎测试"""

    def setup_method(self):
        """测试前准备"""
        self.engine = ASEEngine()

    def test_create_bulk_structure(self):
        """测试创建块体结构"""
        atoms = self.engine.create_bulk_structure("Cu", "fcc", size=(2, 2, 2))

        assert len(atoms) == 32  # 2x2x2的FCC结构有32个原子
        assert atoms.get_chemical_formula() == "Cu32"
        assert atoms.get_pbc().all()  # 应该有周期性边界条件

    def test_create_molecule_structure(self):
        """测试创建分子结构"""
        atoms = self.engine.create_molecule_structure("H2O")

        assert len(atoms) == 3  # 水分子有3个原子
        assert "H" in atoms.get_chemical_symbols()
        assert "O" in atoms.get_chemical_symbols()

    def test_modify_structure_rotate(self):
        """测试旋转结构"""
        atoms = self.engine.create_bulk_structure("Cu", "fcc", size=(1, 1, 1))
        original_positions = atoms.get_positions().copy()

        modified_atoms = self.engine.modify_structure(
            atoms, "rotate", {"axis": [0, 0, 1], "angle": 45}
        )

        # 位置应该发生变化
        assert not np.allclose(original_positions, modified_atoms.get_positions())
        # 原子数量不变
        assert len(modified_atoms) == len(atoms)

    def test_modify_structure_translate(self):
        """测试平移结构"""
        atoms = self.engine.create_bulk_structure("Cu", "fcc", size=(1, 1, 1))
        original_positions = atoms.get_positions().copy()

        modified_atoms = self.engine.modify_structure(
            atoms, "translate", {"vector": [1, 2, 3]}
        )

        # 所有原子都应该移动[1, 2, 3]
        expected_positions = original_positions + np.array([1, 2, 3])
        assert np.allclose(modified_atoms.get_positions(), expected_positions)

    def test_modify_structure_supercell(self):
        """测试超胞操作"""
        atoms = self.engine.create_bulk_structure("Cu", "fcc", size=(1, 1, 1))
        original_count = len(atoms)

        modified_atoms = self.engine.modify_structure(
            atoms, "supercell", {"size": [2, 2, 2]}
        )

        # 原子数量应该增加8倍
        assert len(modified_atoms) == original_count * 8

    def test_calculate_properties(self):
        """测试属性计算"""
        atoms = self.engine.create_bulk_structure("Cu", "fcc", size=(1, 1, 1))

        properties = self.engine.calculate_properties(
            atoms, "emt", ["energy", "forces"]
        )

        assert "energy" in properties
        assert "forces" in properties
        assert isinstance(properties["energy"], float)
        assert isinstance(properties["forces"], list)

    def test_convert_to_dict(self):
        """测试转换为字典"""
        atoms = self.engine.create_bulk_structure("Cu", "fcc", size=(1, 1, 1))

        data = self.engine.convert_to_dict(atoms)

        assert "symbols" in data
        assert "positions" in data
        assert "cell" in data
        assert "formula" in data
        assert data["formula"] == atoms.get_chemical_formula()

    def test_convert_from_dict(self):
        """测试从字典创建"""
        atoms = self.engine.create_bulk_structure("Cu", "fcc", size=(1, 1, 1))
        data = self.engine.convert_to_dict(atoms)

        reconstructed_atoms = self.engine.convert_from_dict(data)

        assert len(reconstructed_atoms) == len(atoms)
        assert reconstructed_atoms.get_chemical_formula() == atoms.get_chemical_formula()
        assert np.allclose(reconstructed_atoms.get_positions(), atoms.get_positions())

    def test_get_structure_info(self):
        """测试获取结构信息"""
        atoms = self.engine.create_bulk_structure("Cu", "fcc", size=(2, 2, 2))

        info = self.engine.get_structure_info(atoms)

        assert "formula" in info
        assert "total_atoms" in info
        assert "unique_elements" in info
        assert info["formula"] == "Cu32"
        assert info["total_atoms"] == 32
        assert "Cu" in info["unique_elements"]

    def test_invalid_structure_type(self):
        """测试无效的结构类型"""
        with pytest.raises(ValueError):
            self.engine.create_bulk_structure("InvalidElement", "invalid_structure")

    def test_invalid_operation(self):
        """测试无效的操作"""
        atoms = self.engine.create_bulk_structure("Cu", "fcc")

        with pytest.raises(ValueError):
            self.engine.modify_structure(atoms, "invalid_operation", {})


if __name__ == "__main__":
    pytest.main([__file__])
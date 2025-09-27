import React, { useRef, useEffect, useState, useMemo } from 'react';
import { Canvas, useFrame, useThree } from '@react-three/fiber';
import { OrbitControls, Text, Html } from '@react-three/drei';
import * as THREE from 'three';

// 原子颜色映射 (CPK颜色)
const ATOM_COLORS = {
  'H': '#FFFFFF',   // 白色
  'He': '#D9FFFF',  // 浅青色
  'Li': '#CC80FF',  // 紫色
  'Be': '#C2FF00',  // 亮绿色
  'B': '#FFB5B5',   // 粉红色
  'C': '#909090',   // 灰色
  'N': '#3050F8',   // 蓝色
  'O': '#FF0D0D',   // 红色
  'F': '#90E050',   // 绿色
  'Ne': '#B3E3F5',  // 浅蓝色
  'Na': '#AB5CF2',  // 紫色
  'Mg': '#8AFF00',  // 亮绿色
  'Al': '#BFA6A6',  // 浅灰色
  'Si': '#F0C8A0',  // 浅橙色
  'P': '#FF8000',   // 橙色
  'S': '#FFFF30',   // 黄色
  'Cl': '#1FF01F',  // 亮绿色
  'Ar': '#80D1E3',  // 浅蓝色
  'K': '#8F40D4',   // 紫色
  'Ca': '#3DFF00',  // 亮绿色
  'Sc': '#E6E6E6',  // 浅灰色
  'Ti': '#BFC2C7',  // 银色
  'V': '#A6A6AB',   // 灰色
  'Cr': '#8A99C7',  // 蓝灰色
  'Mn': '#9C7AC7',  // 紫色
  'Fe': '#E06633',  // 橙红色
  'Co': '#F090A0',  // 粉红色
  'Ni': '#50D050',  // 绿色
  'Cu': '#C88033',  // 棕色
  'Zn': '#7D80B0',  // 蓝灰色
  'Ga': '#C28F8F',  // 浅棕色
  'Ge': '#668F8F',  // 蓝绿色
  'As': '#BD80E3',  // 紫色
  'Se': '#FFA100',  // 橙色
  'Br': '#A62929',  // 深红色
  'Kr': '#5CB8D1',  // 蓝色
  'default': '#FF1493'  // 深粉红色 (未知元素)
};

// 原子半径映射 (范德华半径，单位：埃)
const ATOM_RADII = {
  'H': 1.2, 'He': 1.4, 'Li': 1.82, 'Be': 1.53, 'B': 1.92, 'C': 1.7,
  'N': 1.55, 'O': 1.52, 'F': 1.47, 'Ne': 1.54, 'Na': 2.27, 'Mg': 1.73,
  'Al': 1.84, 'Si': 2.1, 'P': 1.8, 'S': 1.8, 'Cl': 1.75, 'Ar': 1.88,
  'K': 2.75, 'Ca': 2.31, 'Sc': 2.11, 'Ti': 1.87, 'V': 1.79, 'Cr': 1.89,
  'Mn': 1.97, 'Fe': 1.94, 'Co': 1.92, 'Ni': 1.84, 'Cu': 1.32, 'Zn': 1.22,
  'Ga': 1.87, 'Ge': 2.11, 'As': 1.85, 'Se': 1.9, 'Br': 1.85, 'Kr': 2.02,
  'default': 1.5
};

// 单个原子组件
function Atom({ position, symbol, index, isSelected, onSelect, scaleFactor = 1.0 }) {
  const meshRef = useRef();
  const [hovered, setHovered] = useState(false);

  const color = ATOM_COLORS[symbol] || ATOM_COLORS.default;
  const radius = (ATOM_RADII[symbol] || ATOM_RADII.default) * scaleFactor * 0.2;

  useFrame(() => {
    if (meshRef.current) {
      // 选中时添加轻微的动画效果
      if (isSelected) {
        meshRef.current.scale.setScalar(1.2 + 0.1 * Math.sin(Date.now() * 0.005));
      } else {
        meshRef.current.scale.setScalar(hovered ? 1.1 : 1.0);
      }
    }
  });

  return (
    <group position={position}>
      <mesh
        ref={meshRef}
        onClick={() => onSelect && onSelect(index)}
        onPointerOver={() => setHovered(true)}
        onPointerOut={() => setHovered(false)}
      >
        <sphereGeometry args={[radius, 32, 16]} />
        <meshStandardMaterial
          color={color}
          emissive={isSelected ? color : '#000000'}
          emissiveIntensity={isSelected ? 0.2 : 0}
          metalness={0.1}
          roughness={0.4}
        />
      </mesh>

      {/* 原子标签 */}
      {(hovered || isSelected) && (
        <Html distanceFactor={10}>
          <div
            style={{
              color: 'white',
              backgroundColor: 'rgba(0,0,0,0.8)',
              padding: '2px 6px',
              borderRadius: '4px',
              fontSize: '12px',
              pointerEvents: 'none',
              userSelect: 'none'
            }}
          >
            {symbol} ({index})
          </div>
        </Html>
      )}
    </group>
  );
}

// 化学键组件
function Bond({ start, end, order = 1 }) {
  const direction = new THREE.Vector3().subVectors(end, start);
  const length = direction.length();
  const position = new THREE.Vector3().addVectors(start, end).multiplyScalar(0.5);

  // 计算旋转
  const axis = new THREE.Vector3(0, 1, 0);
  const quaternion = new THREE.Quaternion().setFromUnitVectors(axis, direction.normalize());

  return (
    <group position={position} quaternion={quaternion}>
      <mesh>
        <cylinderGeometry args={[0.05, 0.05, length, 8]} />
        <meshStandardMaterial color="#666666" />
      </mesh>
    </group>
  );
}

// 晶胞边框组件
function UnitCell({ cell, visible = true }) {
  if (!visible || !cell) return null;

  const vertices = useMemo(() => {
    // 计算晶胞的8个顶点
    const [a, b, c] = cell;
    return [
      [0, 0, 0],
      a,
      [...b],
      [a[0] + b[0], a[1] + b[1], a[2] + b[2]],
      [...c],
      [a[0] + c[0], a[1] + c[1], a[2] + c[2]],
      [b[0] + c[0], b[1] + c[1], b[2] + c[2]],
      [a[0] + b[0] + c[0], a[1] + b[1] + c[1], a[2] + b[2] + c[2]]
    ];
  }, [cell]);

  const edges = [
    [0, 1], [1, 3], [3, 2], [2, 0], // 底面
    [4, 5], [5, 7], [7, 6], [6, 4], // 顶面
    [0, 4], [1, 5], [2, 6], [3, 7]  // 竖直边
  ];

  return (
    <group>
      {edges.map(([i, j], index) => (
        <Bond
          key={index}
          start={new THREE.Vector3(...vertices[i])}
          end={new THREE.Vector3(...vertices[j])}
        />
      ))}
    </group>
  );
}

// 坐标轴组件
function Axes({ size = 5 }) {
  return (
    <group>
      {/* X轴 - 红色 */}
      <mesh position={[size / 2, 0, 0]}>
        <cylinderGeometry args={[0.02, 0.02, size, 8]} rotation={[0, 0, Math.PI / 2]} />
        <meshStandardMaterial color="#ff0000" />
      </mesh>
      <Text
        position={[size + 0.5, 0, 0]}
        fontSize={0.5}
        color="#ff0000"
        anchorX="center"
        anchorY="middle"
      >
        X
      </Text>

      {/* Y轴 - 绿色 */}
      <mesh position={[0, size / 2, 0]}>
        <cylinderGeometry args={[0.02, 0.02, size, 8]} />
        <meshStandardMaterial color="#00ff00" />
      </mesh>
      <Text
        position={[0, size + 0.5, 0]}
        fontSize={0.5}
        color="#00ff00"
        anchorX="center"
        anchorY="middle"
      >
        Y
      </Text>

      {/* Z轴 - 蓝色 */}
      <mesh position={[0, 0, size / 2]} rotation={[Math.PI / 2, 0, 0]}>
        <cylinderGeometry args={[0.02, 0.02, size, 8]} />
        <meshStandardMaterial color="#0000ff" />
      </mesh>
      <Text
        position={[0, 0, size + 0.5]}
        fontSize={0.5}
        color="#0000ff"
        anchorX="center"
        anchorY="middle"
      >
        Z
      </Text>
    </group>
  );
}

// 相机控制组件
function CameraController({ structure }) {
  const { camera, scene } = useThree();

  useEffect(() => {
    if (structure && structure.positions) {
      // 计算结构的边界盒
      const positions = structure.positions;
      const box = new THREE.Box3();

      positions.forEach(pos => {
        box.expandByPoint(new THREE.Vector3(...pos));
      });

      const center = box.getCenter(new THREE.Vector3());
      const size = box.getSize(new THREE.Vector3()).length();

      // 设置相机位置
      const distance = size * 2;
      camera.position.set(
        center.x + distance,
        center.y + distance,
        center.z + distance
      );
      camera.lookAt(center);
      camera.updateProjectionMatrix();
    }
  }, [structure, camera]);

  return null;
}

// 主要的3D查看器组件
function Viewer3D({
  structure,
  selectedAtoms = [],
  onAtomSelect,
  showBonds = true,
  showUnitCell = true,
  showAxes = true,
  scaleFactor = 1.0,
  backgroundColor = '#000000'
}) {
  const [bonds, setBonds] = useState([]);

  // 计算化学键
  useEffect(() => {
    if (structure && showBonds) {
      // 这里应该调用后端API获取键连接信息
      // 暂时使用简单的距离判断
      const calculatedBonds = calculateBonds(structure);
      setBonds(calculatedBonds);
    } else {
      setBonds([]);
    }
  }, [structure, showBonds]);

  // 简单的键计算函数
  const calculateBonds = (structure) => {
    if (!structure.positions || structure.positions.length < 2) return [];

    const bonds = [];
    const positions = structure.positions;
    const symbols = structure.symbols;

    for (let i = 0; i < positions.length; i++) {
      for (let j = i + 1; j < positions.length; j++) {
        const pos1 = new THREE.Vector3(...positions[i]);
        const pos2 = new THREE.Vector3(...positions[j]);
        const distance = pos1.distanceTo(pos2);

        // 简单的键长判断 (需要根据元素类型优化)
        const maxBondLength = 3.0;
        const minBondLength = 0.5;

        if (distance > minBondLength && distance < maxBondLength) {
          bonds.push({
            start: pos1,
            end: pos2,
            distance: distance,
            atoms: [i, j],
            symbols: [symbols[i], symbols[j]]
          });
        }
      }
    }

    return bonds;
  };

  if (!structure) {
    return (
      <div
        style={{
          width: '100%',
          height: '100%',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          backgroundColor: '#f0f0f0',
          color: '#666'
        }}
      >
        <div>
          <h3>暂无结构数据</h3>
          <p>请选择一个会话或创建新的结构</p>
        </div>
      </div>
    );
  }

  return (
    <div style={{ width: '100%', height: '100%' }}>
      <Canvas
        camera={{ position: [10, 10, 10], fov: 50 }}
        style={{ background: backgroundColor }}
      >
        {/* 光源 */}
        <ambientLight intensity={0.6} />
        <directionalLight position={[10, 10, 5]} intensity={0.8} />
        <pointLight position={[-10, -10, -5]} intensity={0.4} />

        {/* 相机控制器 */}
        <CameraController structure={structure} />

        {/* 原子 */}
        {structure.positions && structure.positions.map((position, index) => (
          <Atom
            key={index}
            position={position}
            symbol={structure.symbols[index]}
            index={index}
            isSelected={selectedAtoms.includes(index)}
            onSelect={onAtomSelect}
            scaleFactor={scaleFactor}
          />
        ))}

        {/* 化学键 */}
        {bonds.map((bond, index) => (
          <Bond
            key={index}
            start={bond.start}
            end={bond.end}
            order={1}
          />
        ))}

        {/* 晶胞边框 */}
        {showUnitCell && (
          <UnitCell
            cell={structure.cell}
            visible={showUnitCell}
          />
        )}

        {/* 坐标轴 */}
        {showAxes && <Axes size={5} />}

        {/* 轨道控制 */}
        <OrbitControls
          enablePan={true}
          enableZoom={true}
          enableRotate={true}
          dampingFactor={0.05}
        />
      </Canvas>

      {/* 结构信息覆盖层 */}
      <div
        style={{
          position: 'absolute',
          top: 10,
          left: 10,
          backgroundColor: 'rgba(0,0,0,0.7)',
          color: 'white',
          padding: '10px',
          borderRadius: '5px',
          fontSize: '12px',
          pointerEvents: 'none'
        }}
      >
        <div>分子式: {structure.formula}</div>
        <div>原子数: {structure.total_atoms}</div>
        {structure.volume && (
          <div>体积: {structure.volume.toFixed(2)} Ų</div>
        )}
        {selectedAtoms.length > 0 && (
          <div>选中原子: {selectedAtoms.length}</div>
        )}
      </div>
    </div>
  );
}

export default Viewer3D;
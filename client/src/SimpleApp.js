import React, { useState, useEffect, useRef } from 'react';

function SimpleApp() {
  const [sessions, setSessions] = useState([]);
  const [currentSession, setCurrentSession] = useState(null);
  const [wsConnected, setWsConnected] = useState(false);
  const [messages, setMessages] = useState([]);
  const [structureData, setStructureData] = useState(null);
  const [error, setError] = useState(null);
  const viewerRef = useRef(null);
  const containerRef = useRef(null);

  // 添加错误边界处理
  useEffect(() => {
    const handleError = (error) => {
      console.error('App Error:', error);
      setError(error.message || 'Unknown error occurred');
    };

    window.addEventListener('error', handleError);
    window.addEventListener('unhandledrejection', handleError);

    return () => {
      window.removeEventListener('error', handleError);
      window.removeEventListener('unhandledrejection', handleError);
    };
  }, []);

  useEffect(() => {
    // 连接WebSocket
    const ws = new WebSocket('ws://localhost:8001');

    ws.onopen = () => {
      console.log('WebSocket连接成功');
      setWsConnected(true);
      setMessages(prev => [...prev, { type: 'system', text: 'WebSocket连接成功', timestamp: new Date() }]);
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        console.log('收到WebSocket消息:', data);
        setMessages(prev => [...prev, { type: 'websocket', data, timestamp: new Date() }]);

        // 如果是结构更新
        if (data.type === 'structure_updated' || data.type === 'structure_created') {
          setStructureData(data.data);
        }
      } catch (error) {
        console.error('WebSocket消息解析错误:', error);
      }
    };

    ws.onclose = () => {
      console.log('WebSocket连接关闭');
      setWsConnected(false);
      setMessages(prev => [...prev, { type: 'system', text: 'WebSocket连接关闭', timestamp: new Date() }]);
    };

    ws.onerror = (error) => {
      console.error('WebSocket错误:', error);
      setMessages(prev => [...prev, { type: 'error', text: 'WebSocket连接错误', timestamp: new Date() }]);
    };

    return () => {
      ws.close();
    };
  }, []);

  // 获取会话列表
  const fetchSessions = async () => {
    try {
      const response = await fetch('/api/sessions');
      const data = await response.json();
      setSessions(data.sessions || []);
    } catch (error) {
      console.error('获取会话列表失败:', error);
    }
  };

  // 获取会话结构数据
  const fetchSessionStructure = async (sessionId) => {
    try {
      console.log('正在获取会话结构:', sessionId);
      const response = await fetch(`/api/sessions/${sessionId}`);
      console.log('响应状态:', response.status);
      const data = await response.json();
      console.log('完整响应数据:', data);

      if (data.success && data.structure) {
        console.log('结构数据详情:', data.structure);
        setStructureData(data.structure);
        renderMoleculeWith3DMol(data.structure);
      } else {
        setStructureData(null);
        console.log('该会话暂无结构数据', data);
      }
    } catch (error) {
      console.error('获取结构数据失败:', error);
      setStructureData(null);
    }
  };

  // 使用3Dmol.js渲染分子
  const renderMoleculeWith3DMol = (structure) => {
    if (!containerRef.current || !structure) {
      console.log('容器或结构数据缺失');
      return;
    }

    // 检查3Dmol是否可用
    if (typeof window.$3Dmol === 'undefined') {
      console.error('3Dmol.js库未加载，请检查CDN连接');
      return;
    }

    console.log('开始使用3Dmol.js渲染分子:', structure);

    // 清除之前的viewer
    if (viewerRef.current) {
      viewerRef.current.clear();
    }

    // 创建3Dmol viewer
    const viewer = window.$3Dmol.createViewer(containerRef.current, {
      defaultcolors: window.$3Dmol.elementColors.Jmol,
      backgroundColor: 0xffffff,
      width: containerRef.current.clientWidth,
      height: containerRef.current.clientHeight
    });
    viewerRef.current = viewer;

    console.log('3Dmol viewer创建完成');

    // 将ASE数据转换为3Dmol格式
    const symbols = structure.symbols;
    const positions = structure.positions;

    if (!symbols || !positions) {
      console.error('结构数据格式错误');
      return;
    }

    console.log(`准备渲染 ${symbols.length} 个原子`);

    // 创建XYZ格式数据
    let xyzData = `${symbols.length}\nASE structure\n`;
    for (let i = 0; i < symbols.length; i++) {
      xyzData += `${symbols[i]} ${positions[i][0]} ${positions[i][1]} ${positions[i][2]}\n`;
    }

    // 添加模型
    const model = viewer.addModel(xyzData, 'xyz');
    console.log('模型添加成功');

    // 设置样式
    viewer.setStyle({}, {
      sphere: {
        scale: 0.3
      },
      stick: {
        radius: 0.1
      }
    });

    // 添加晶胞边界框（如果有晶胞信息）
    if (structure.cell && structure.cell.length === 3) {
      addUnitCellBox(viewer, structure.cell);
      console.log('晶胞边界框添加成功');
    }

    // 添加坐标轴
    addCoordinateAxes(viewer);
    console.log('坐标轴添加成功');

    // 设置背景和渲染
    viewer.setBackgroundColor(0xffffff);
    viewer.zoomTo();
    viewer.render();

    console.log('3Dmol渲染完成');

    // 添加旋转动画
    viewer.rotate(1, { x: 0, y: 1, z: 0 });
  };

  // 初始化3Dmol
  useEffect(() => {
    if (containerRef.current && structureData) {
      renderMoleculeWith3DMol(structureData);
    }
  }, [structureData]);

  // 添加晶胞边界框
  const addUnitCellBox = (viewer, cell) => {
    if (!cell || cell.length !== 3) return;

    console.log('添加晶胞边界框...');

    // 晶胞矢量
    const a = cell[0];
    const b = cell[1];
    const c = cell[2];

    // 晶胞的8个顶点
    const vertices = [
      [0, 0, 0],                    // 原点
      a,                            // a矢量端点
      b,                            // b矢量端点
      c,                            // c矢量端点
      [a[0] + b[0], a[1] + b[1], a[2] + b[2]],          // a+b
      [a[0] + c[0], a[1] + c[1], a[2] + c[2]],          // a+c
      [b[0] + c[0], b[1] + c[1], b[2] + c[2]],          // b+c
      [a[0] + b[0] + c[0], a[1] + b[1] + c[1], a[2] + b[2] + c[2]]  // a+b+c
    ];

    // 晶胞的12条边
    const edges = [
      [0, 1], [0, 2], [0, 3],       // 从原点出发的3条边
      [1, 4], [1, 5],               // 从a端点的边
      [2, 4], [2, 6],               // 从b端点的边
      [3, 5], [3, 6],               // 从c端点的边
      [4, 7], [5, 7], [6, 7]        // 到对角顶点的边
    ];

    // 添加边线
    edges.forEach((edge) => {
      const start = vertices[edge[0]];
      const end = vertices[edge[1]];

      viewer.addCylinder({
        start: {x: start[0], y: start[1], z: start[2]},
        end: {x: end[0], y: end[1], z: end[2]},
        radius: 0.05,
        color: 'black',
        alpha: 0.6
      });
    });

    console.log('晶胞边界框添加完成');
  };

  // 添加坐标轴
  const addCoordinateAxes = (viewer) => {
    console.log('添加坐标轴...');

    const axisLength = 3.0;
    const axisRadius = 0.1;

    // a轴 (红色)
    viewer.addCylinder({
      start: {x: 0, y: 0, z: 0},
      end: {x: axisLength, y: 0, z: 0},
      radius: axisRadius,
      color: 'red',
      alpha: 0.9
    });

    viewer.addSphere({
      center: {x: axisLength, y: 0, z: 0},
      radius: axisRadius * 2,
      color: 'red'
    });

    // b轴 (绿色)
    viewer.addCylinder({
      start: {x: 0, y: 0, z: 0},
      end: {x: 0, y: axisLength, z: 0},
      radius: axisRadius,
      color: 'green',
      alpha: 0.9
    });

    viewer.addSphere({
      center: {x: 0, y: axisLength, z: 0},
      radius: axisRadius * 2,
      color: 'green'
    });

    // c轴 (蓝色)
    viewer.addCylinder({
      start: {x: 0, y: 0, z: 0},
      end: {x: 0, y: 0, z: axisLength},
      radius: axisRadius,
      color: 'blue',
      alpha: 0.9
    });

    viewer.addSphere({
      center: {x: 0, y: 0, z: axisLength},
      radius: axisRadius * 2,
      color: 'blue'
    });

    console.log('坐标轴添加完成');
  };

  useEffect(() => {
    fetchSessions();
    const interval = setInterval(fetchSessions, 5000); // 每5秒刷新
    return () => clearInterval(interval);
  }, []);

  const styles = {
    container: {
      fontFamily: 'Arial, sans-serif',
      maxWidth: '1200px',
      margin: '0 auto',
      padding: '20px'
    },
    header: {
      backgroundColor: '#2c3e50',
      color: 'white',
      padding: '20px',
      borderRadius: '8px',
      marginBottom: '20px'
    },
    status: {
      display: 'inline-block',
      padding: '5px 10px',
      borderRadius: '4px',
      marginTop: '10px',
      backgroundColor: wsConnected ? '#27ae60' : '#e74c3c',
      color: 'white'
    },
    grid: {
      display: 'grid',
      gridTemplateColumns: '1fr 2fr',
      gap: '20px'
    },
    panel: {
      border: '1px solid #ddd',
      borderRadius: '8px',
      padding: '15px',
      backgroundColor: 'white'
    },
    sessionItem: {
      padding: '10px',
      border: '1px solid #eee',
      borderRadius: '4px',
      marginBottom: '10px',
      cursor: 'pointer',
      backgroundColor: '#f9f9f9'
    },
    activeSession: {
      backgroundColor: '#3498db',
      color: 'white'
    },
    messagesList: {
      height: '300px',
      overflowY: 'auto',
      border: '1px solid #eee',
      padding: '10px',
      backgroundColor: '#f8f9fa'
    },
    message: {
      margin: '5px 0',
      padding: '8px',
      borderRadius: '4px',
      fontSize: '12px'
    },
    systemMessage: {
      backgroundColor: '#d4edda',
      border: '1px solid #c3e6cb',
      color: '#155724'
    },
    wsMessage: {
      backgroundColor: '#d1ecf1',
      border: '1px solid #bee5eb',
      color: '#0c5460'
    },
    errorMessage: {
      backgroundColor: '#f8d7da',
      border: '1px solid #f5c6cb',
      color: '#721c24'
    },
    button: {
      backgroundColor: '#3498db',
      color: 'white',
      border: 'none',
      padding: '10px 15px',
      borderRadius: '4px',
      cursor: 'pointer',
      marginBottom: '10px'
    },
    viewerContainer: {
      width: '100%',
      height: '400px',
      border: '1px solid #ccc',
      borderRadius: '4px',
      backgroundColor: '#f8f9fa',
      position: 'relative'
    }
  };

  // 如果有错误，显示错误信息
  if (error) {
    return (
      <div style={styles.container}>
        <header style={{...styles.header, backgroundColor: '#e74c3c'}}>
          <h1>ASE MCP - 错误</h1>
          <div style={{color: 'white', marginTop: '10px'}}>
            错误: {error}
          </div>
          <button
            onClick={() => setError(null)}
            style={{marginTop: '10px', padding: '5px 10px'}}
          >
            重试
          </button>
        </header>
        <div style={styles.panel}>
          <h3>调试信息</h3>
          <p>如果看到这个错误页面，说明React应用正常加载，但3D渲染有问题。</p>
          <p>请检查浏览器控制台获取更多错误信息。</p>
          <p>您可以访问 <a href="/debug.html">/debug.html</a> 进行进一步调试。</p>
        </div>
      </div>
    );
  }

  return (
    <div style={styles.container}>
      <header style={styles.header}>
        <h1>ASE MCP 实时监控</h1>
        <div style={styles.status}>
          WebSocket: {wsConnected ? '已连接' : '未连接'}
        </div>
      </header>

      <div style={styles.grid}>
        <div style={styles.panel}>
          <h3>会话列表</h3>
          <button style={styles.button} onClick={fetchSessions}>刷新</button>
          <div>
            {sessions.map(session => (
              <div
                key={session.id}
                style={{
                  ...styles.sessionItem,
                  ...(currentSession?.id === session.id ? styles.activeSession : {})
                }}
                onClick={() => {
                  setCurrentSession(session);
                  if (session.has_structure) {
                    fetchSessionStructure(session.id);
                  } else {
                    setStructureData(null);
                  }
                }}
              >
                <div><strong>{session.id.substring(0, 8)}...</strong></div>
                <div>{session.has_structure ? '✅ 有结构' : '❌ 无结构'}</div>
                <div>{new Date(session.modified_at).toLocaleTimeString()}</div>
              </div>
            ))}
            {sessions.length === 0 && <div>暂无会话</div>}
          </div>
        </div>

        <div>
          <div style={styles.panel}>
            <h3>3D结构视图</h3>
            {currentSession ? (
              <div>
                <div><strong>会话:</strong> {currentSession.id.substring(0, 8)}...</div>
                {structureData ? (
                  <div>
                    <div style={{ marginBottom: '10px' }}>
                      <strong>原子数:</strong> {structureData.symbols?.length || 0}
                      <br />
                      <strong>元素:</strong> {structureData.symbols ? [...new Set(structureData.symbols)].join(', ') : '无'}
                    </div>
                    <div
                      ref={containerRef}
                      style={styles.viewerContainer}
                    />
                    <div style={{ fontSize: '12px', color: '#666', marginTop: '5px' }}>
                      💡 鼠标拖拽旋转，滚轮缩放
                    </div>
                  </div>
                ) : (
                  <div>该会话暂无结构数据</div>
                )}
              </div>
            ) : (
              <div>请选择一个会话查看结构</div>
            )}
          </div>

          <div style={styles.panel}>
            <h3>实时消息 (最新10条)</h3>
            <div style={styles.messagesList}>
              {messages.slice(-10).map((msg, index) => (
                <div
                  key={index}
                  style={{
                    ...styles.message,
                    ...(msg.type === 'system' ? styles.systemMessage :
                        msg.type === 'error' ? styles.errorMessage : styles.wsMessage)
                  }}
                >
                  <strong>{msg.timestamp.toLocaleTimeString()}</strong>
                  <br />
                  {msg.text || JSON.stringify(msg.data)}
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default SimpleApp;
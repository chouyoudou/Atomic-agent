import React, { useState, useEffect, useCallback } from 'react';
import { Layout, message, Spin } from 'antd';
import './App.css';

import Viewer3D from './components/Viewer3D';
import ControlPanel from './components/ControlPanel';
import SessionList from './components/SessionList';
import websocketService from './services/websocket';

const { Header, Content, Sider } = Layout;

function App() {
  // 状态管理
  const [isConnected, setIsConnected] = useState(false);
  const [sessions, setSessions] = useState([]);
  const [currentSessionId, setCurrentSessionId] = useState(null);
  const [currentStructure, setCurrentStructure] = useState(null);
  const [selectedAtoms, setSelectedAtoms] = useState([]);
  const [canUndo, setCanUndo] = useState(false);
  const [canRedo, setCanRedo] = useState(false);
  const [loading, setLoading] = useState(true);

  // 查看器设置
  const [viewerSettings, setViewerSettings] = useState({
    showBonds: true,
    showUnitCell: true,
    showAxes: true,
    scaleFactor: 1.0,
    backgroundColor: '#000000'
  });

  // 初始化WebSocket连接
  useEffect(() => {
    const initWebSocket = async () => {
      try {
        await websocketService.connect();
        setIsConnected(true);
        message.success('WebSocket连接成功');
      } catch (error) {
        console.error('WebSocket连接失败:', error);
        message.error('WebSocket连接失败');
        setIsConnected(false);
      }
    };

    initWebSocket();

    // 设置WebSocket事件监听
    const unsubscribers = [
      websocketService.subscribe('structureUpdate', handleStructureUpdate),
      websocketService.subscribe('propertyUpdate', handlePropertyUpdate),
      websocketService.subscribe('sessionState', handleSessionState),
      websocketService.subscribe('sessionsList', handleSessionsList),
      websocketService.subscribe('sessionDeleted', handleSessionDeleted),
      websocketService.subscribe('error', handleWebSocketError),
      websocketService.subscribe('maxReconnectAttemptsReached', () => {
        setIsConnected(false);
        message.error('WebSocket连接断开，请刷新页面重试');
      })
    ];

    // 请求会话列表
    websocketService.requestSessionsList();

    // 清理函数
    return () => {
      unsubscribers.forEach(unsubscribe => unsubscribe());
      websocketService.disconnect();
    };
  }, []);

  // WebSocket事件处理器
  const handleStructureUpdate = useCallback((data) => {
    const { sessionId, structure, structureInfo, operation } = data;

    if (sessionId === currentSessionId) {
      setCurrentStructure(structure);
      message.success(`结构已更新: ${operation.type}`);
    }

    // 更新会话列表中的结构信息
    setSessions(prev => prev.map(session =>
      session.id === sessionId
        ? { ...session, has_structure: true, structure_summary: structureInfo }
        : session
    ));
  }, [currentSessionId]);

  const handlePropertyUpdate = useCallback((data) => {
    const { sessionId, properties } = data;

    if (sessionId === currentSessionId) {
      message.success('属性计算完成');
      console.log('属性更新:', properties);
    }
  }, [currentSessionId]);

  const handleSessionState = useCallback((data) => {
    const { sessionId, session, structure } = data;

    if (sessionId === currentSessionId) {
      setCurrentStructure(structure);
      // 可以在这里设置撤销/重做状态
      setCanUndo(session.history_index >= 0);
      setCanRedo(session.history_index + 1 < session.history?.length);
    }
  }, [currentSessionId]);

  const handleSessionsList = useCallback((data) => {
    setSessions(data.sessions);
    setLoading(false);
  }, []);

  const handleSessionDeleted = useCallback((data) => {
    const { sessionId } = data;

    setSessions(prev => prev.filter(session => session.id !== sessionId));

    if (sessionId === currentSessionId) {
      setCurrentSessionId(null);
      setCurrentStructure(null);
      setSelectedAtoms([]);
    }

    message.info('会话已删除');
  }, [currentSessionId]);

  const handleWebSocketError = useCallback((data) => {
    message.error(`WebSocket错误: ${data.message}`);
  }, []);

  // 会话操作
  const handleSessionSelect = useCallback((sessionId) => {
    setCurrentSessionId(sessionId);
    setSelectedAtoms([]);
    websocketService.subscribeToSession(sessionId);
  }, []);

  const handleSessionCreate = useCallback(async (sessionData) => {
    // 这里应该调用API创建会话
    // 暂时模拟创建会话
    const newSessionId = `session_${Date.now()}`;

    const newSession = {
      id: newSessionId,
      created_at: new Date().toISOString(),
      modified_at: new Date().toISOString(),
      status: 'active',
      has_structure: false,
      metadata: {
        name: sessionData.name,
        description: sessionData.description,
        tags: sessionData.tags || []
      }
    };

    setSessions(prev => [newSession, ...prev]);
    setCurrentSessionId(newSessionId);
    websocketService.subscribeToSession(newSessionId);

    message.success('会话创建成功');
  }, []);

  const handleSessionDelete = useCallback(async (sessionId) => {
    // 这里应该调用API删除会话
    setSessions(prev => prev.filter(session => session.id !== sessionId));

    if (sessionId === currentSessionId) {
      setCurrentSessionId(null);
      setCurrentStructure(null);
      setSelectedAtoms([]);
    }

    message.success('会话删除成功');
  }, [currentSessionId]);

  const handleRefreshSessions = useCallback(() => {
    setLoading(true);
    websocketService.requestSessionsList();
  }, []);

  // 结构操作 (这些应该调用后端API)
  const handleCreateStructure = useCallback(async (structureData) => {
    // 模拟API调用
    console.log('创建结构:', structureData);

    // 模拟结构数据
    const mockStructure = {
      formula: structureData.formula,
      total_atoms: 8,
      symbols: ['Cu', 'Cu', 'Cu', 'Cu', 'Cu', 'Cu', 'Cu', 'Cu'],
      positions: [
        [0, 0, 0], [1.8, 1.8, 0], [1.8, 0, 1.8], [0, 1.8, 1.8],
        [0, 0, 3.6], [1.8, 1.8, 3.6], [1.8, 0, 5.4], [0, 1.8, 5.4]
      ],
      cell: [[3.6, 0, 0], [0, 3.6, 0], [0, 0, 7.2]],
      volume: 93.31,
      center_of_mass: [0.9, 0.9, 2.7],
      unique_elements: ['Cu']
    };

    setCurrentStructure(mockStructure);

    // 更新会话状态
    setSessions(prev => prev.map(session =>
      session.id === currentSessionId
        ? { ...session, has_structure: true, structure_summary: { formula: mockStructure.formula, total_atoms: mockStructure.total_atoms } }
        : session
    ));
  }, [currentSessionId]);

  const handleModifyStructure = useCallback(async (modifyData) => {
    console.log('修改结构:', modifyData);
    // 这里应该调用API
  }, []);

  const handleCalculateProperties = useCallback(async (calcData) => {
    console.log('计算属性:', calcData);
    // 这里应该调用API
  }, []);

  const handleOptimizeStructure = useCallback(async (optimizeData) => {
    console.log('优化结构:', optimizeData);
    // 这里应该调用API
  }, []);

  const handleUndo = useCallback(() => {
    console.log('撤销操作');
    // 这里应该调用API
  }, []);

  const handleRedo = useCallback(() => {
    console.log('重做操作');
    // 这里应该调用API
  }, []);

  const handleSaveStructure = useCallback((saveData) => {
    console.log('保存结构:', saveData);
    // 这里应该调用API
    message.success('结构保存成功');
  }, []);

  // 原子选择
  const handleAtomSelect = useCallback((atomIndex) => {
    setSelectedAtoms(prev => {
      if (prev.includes(atomIndex)) {
        return prev.filter(i => i !== atomIndex);
      } else {
        return [...prev, atomIndex];
      }
    });
  }, []);

  return (
    <div className="App">
      <Layout style={{ height: '100vh' }}>
        <Header
          style={{
            backgroundColor: '#001529',
            color: 'white',
            padding: '0 20px',
            display: 'flex',
            alignItems: 'center'
          }}
        >
          <h2 style={{ color: 'white', margin: 0 }}>
            ASE MCP - 原子模拟环境
          </h2>
        </Header>

        <Layout>
          {/* 会话列表侧边栏 */}
          <Sider
            width={300}
            style={{
              backgroundColor: 'white',
              borderRight: '1px solid #f0f0f0'
            }}
          >
            <SessionList
              sessions={sessions}
              currentSessionId={currentSessionId}
              onSessionSelect={handleSessionSelect}
              onSessionCreate={handleSessionCreate}
              onSessionDelete={handleSessionDelete}
              onRefresh={handleRefreshSessions}
              loading={loading}
            />
          </Sider>

          {/* 主内容区域 */}
          <Layout>
            <Content style={{ padding: 0, overflow: 'hidden' }}>
              <div style={{ height: '100%', display: 'flex' }}>
                {/* 3D查看器 */}
                <div style={{ flex: 1 }}>
                  <Viewer3D
                    structure={currentStructure}
                    selectedAtoms={selectedAtoms}
                    onAtomSelect={handleAtomSelect}
                    showBonds={viewerSettings.showBonds}
                    showUnitCell={viewerSettings.showUnitCell}
                    showAxes={viewerSettings.showAxes}
                    scaleFactor={viewerSettings.scaleFactor}
                    backgroundColor={viewerSettings.backgroundColor}
                  />
                </div>

                {/* 控制面板 */}
                <div
                  style={{
                    width: 320,
                    backgroundColor: 'white',
                    borderLeft: '1px solid #f0f0f0',
                    padding: '16px'
                  }}
                >
                  <ControlPanel
                    currentSession={currentSessionId}
                    structure={currentStructure}
                    onCreateStructure={handleCreateStructure}
                    onModifyStructure={handleModifyStructure}
                    onCalculateProperties={handleCalculateProperties}
                    onOptimizeStructure={handleOptimizeStructure}
                    onUndo={handleUndo}
                    onRedo={handleRedo}
                    onSaveStructure={handleSaveStructure}
                    canUndo={canUndo}
                    canRedo={canRedo}
                    isConnected={isConnected}
                    viewerSettings={viewerSettings}
                    onViewerSettingsChange={setViewerSettings}
                  />
                </div>
              </div>
            </Content>
          </Layout>
        </Layout>
      </Layout>
    </div>
  );
}

export default App;
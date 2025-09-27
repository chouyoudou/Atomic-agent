import React, { useState, useEffect } from 'react';
import {
  Card,
  Button,
  Select,
  Slider,
  Switch,
  Form,
  Input,
  Space,
  Divider,
  Collapse,
  Tooltip,
  message,
  InputNumber,
  Row,
  Col
} from 'antd';
import {
  PlayCircleOutlined,
  PauseCircleOutlined,
  ReloadOutlined,
  SettingOutlined,
  EyeOutlined,
  EyeInvisibleOutlined,
  UndoOutlined,
  RedoOutlined,
  SaveOutlined,
  DownloadOutlined
} from '@ant-design/icons';

const { Option } = Select;
const { Panel } = Collapse;

function ControlPanel({
  currentSession,
  structure,
  onCreateStructure,
  onModifyStructure,
  onCalculateProperties,
  onOptimizeStructure,
  onUndo,
  onRedo,
  onSaveStructure,
  canUndo = false,
  canRedo = false,
  isConnected = false,
  viewerSettings,
  onViewerSettingsChange
}) {
  const [form] = Form.useForm();
  const [modifyForm] = Form.useForm();
  const [isCreating, setIsCreating] = useState(false);
  const [isModifying, setIsModifying] = useState(false);
  const [isCalculating, setIsCalculating] = useState(false);
  const [isOptimizing, setIsOptimizing] = useState(false);

  // 创建结构
  const handleCreateStructure = async (values) => {
    setIsCreating(true);
    try {
      await onCreateStructure(values);
      message.success('结构创建成功');
      form.resetFields();
    } catch (error) {
      message.error(`创建失败: ${error.message}`);
    } finally {
      setIsCreating(false);
    }
  };

  // 修改结构
  const handleModifyStructure = async (values) => {
    if (!currentSession) {
      message.warning('请先选择一个会话');
      return;
    }

    setIsModifying(true);
    try {
      await onModifyStructure({
        session_id: currentSession,
        operation: values.operation,
        parameters: values.parameters
      });
      message.success('结构修改成功');
    } catch (error) {
      message.error(`修改失败: ${error.message}`);
    } finally {
      setIsModifying(false);
    }
  };

  // 计算属性
  const handleCalculateProperties = async (properties) => {
    if (!currentSession) {
      message.warning('请先选择一个会话');
      return;
    }

    setIsCalculating(true);
    try {
      await onCalculateProperties({
        session_id: currentSession,
        properties: properties
      });
      message.success('属性计算完成');
    } catch (error) {
      message.error(`计算失败: ${error.message}`);
    } finally {
      setIsCalculating(false);
    }
  };

  // 优化结构
  const handleOptimizeStructure = async () => {
    if (!currentSession) {
      message.warning('请先选择一个会话');
      return;
    }

    setIsOptimizing(true);
    try {
      await onOptimizeStructure({
        session_id: currentSession,
        calculator: 'emt',
        fmax: 0.01,
        steps: 100
      });
      message.success('结构优化完成');
    } catch (error) {
      message.error(`优化失败: ${error.message}`);
    } finally {
      setIsOptimizing(false);
    }
  };

  // 保存结构
  const handleSaveStructure = () => {
    if (!currentSession) {
      message.warning('请先选择一个会话');
      return;
    }

    const filename = `structure_${currentSession}_${Date.now()}.cif`;
    onSaveStructure({
      session_id: currentSession,
      filename: filename,
      format: 'cif'
    });
  };

  return (
    <div style={{ height: '100%', overflow: 'auto' }}>
      <Space direction="vertical" style={{ width: '100%' }} size="middle">

        {/* 连接状态 */}
        <Card size="small">
          <Space>
            <div style={{
              width: 8,
              height: 8,
              borderRadius: '50%',
              backgroundColor: isConnected ? '#52c41a' : '#ff4d4f'
            }} />
            <span>
              {isConnected ? '已连接' : '未连接'}
            </span>
          </Space>
        </Card>

        {/* 会话操作 */}
        <Card title="会话操作" size="small">
          <Space direction="vertical" style={{ width: '100%' }}>
            <Space wrap>
              <Tooltip title="撤销">
                <Button
                  icon={<UndoOutlined />}
                  disabled={!canUndo}
                  onClick={onUndo}
                />
              </Tooltip>
              <Tooltip title="重做">
                <Button
                  icon={<RedoOutlined />}
                  disabled={!canRedo}
                  onClick={onRedo}
                />
              </Tooltip>
              <Tooltip title="保存结构">
                <Button
                  icon={<SaveOutlined />}
                  disabled={!structure}
                  onClick={handleSaveStructure}
                />
              </Tooltip>
            </Space>
            {currentSession && (
              <div style={{ fontSize: '12px', color: '#666' }}>
                当前会话: {currentSession.substring(0, 8)}...
              </div>
            )}
          </Space>
        </Card>

        {/* 创建结构 */}
        <Card title="创建结构" size="small">
          <Form
            form={form}
            layout="vertical"
            onFinish={handleCreateStructure}
            size="small"
          >
            <Form.Item
              name="type"
              label="结构类型"
              rules={[{ required: true }]}
            >
              <Select placeholder="选择结构类型">
                <Option value="bulk">块体晶体</Option>
                <Option value="molecule">分子</Option>
                <Option value="surface">表面</Option>
                <Option value="nanoparticle">纳米粒子</Option>
              </Select>
            </Form.Item>

            <Form.Item
              name="formula"
              label="化学式"
              rules={[{ required: true }]}
            >
              <Input placeholder="如: Cu, H2O, NaCl" />
            </Form.Item>

            <Form.Item
              noStyle
              shouldUpdate={(prevValues, currentValues) =>
                prevValues.type !== currentValues.type
              }
            >
              {({ getFieldValue }) => {
                const structureType = getFieldValue('type');
                return structureType === 'bulk' ? (
                  <Form.Item
                    name="crystal_structure"
                    label="晶体结构"
                  >
                    <Select placeholder="选择晶体结构">
                      <Option value="fcc">面心立方(FCC)</Option>
                      <Option value="bcc">体心立方(BCC)</Option>
                      <Option value="hcp">密排六方(HCP)</Option>
                      <Option value="diamond">金刚石</Option>
                      <Option value="sc">简单立方(SC)</Option>
                    </Select>
                  </Form.Item>
                ) : null;
              }}
            </Form.Item>

            <Row gutter={8}>
              <Col span={12}>
                <Form.Item name="size" label="超胞大小">
                  <Space.Compact>
                    <InputNumber placeholder="X" min={1} max={10} />
                    <InputNumber placeholder="Y" min={1} max={10} />
                    <InputNumber placeholder="Z" min={1} max={10} />
                  </Space.Compact>
                </Form.Item>
              </Col>
              <Col span={12}>
                <Form.Item name="lattice_constant" label="晶格常数(Å)">
                  <InputNumber
                    placeholder="自动"
                    min={1}
                    max={20}
                    step={0.1}
                    style={{ width: '100%' }}
                  />
                </Form.Item>
              </Col>
            </Row>

            <Form.Item>
              <Button
                type="primary"
                htmlType="submit"
                loading={isCreating}
                block
              >
                创建结构
              </Button>
            </Form.Item>
          </Form>
        </Card>

        {/* 修改结构 */}
        {structure && (
          <Card title="修改结构" size="small">
            <Collapse size="small">
              <Panel header="几何变换" key="transform">
                <Form
                  form={modifyForm}
                  layout="vertical"
                  onFinish={handleModifyStructure}
                  size="small"
                >
                  <Form.Item
                    name="operation"
                    label="操作类型"
                    rules={[{ required: true }]}
                  >
                    <Select placeholder="选择操作">
                      <Option value="rotate">旋转</Option>
                      <Option value="translate">平移</Option>
                      <Option value="scale">缩放</Option>
                      <Option value="supercell">超胞</Option>
                    </Select>
                  </Form.Item>

                  <Form.Item
                    noStyle
                    shouldUpdate={(prevValues, currentValues) =>
                      prevValues.operation !== currentValues.operation
                    }
                  >
                    {({ getFieldValue }) => {
                      const operation = getFieldValue('operation');

                      if (operation === 'rotate') {
                        return (
                          <>
                            <Form.Item name={['parameters', 'angle']} label="角度(度)">
                              <InputNumber
                                min={-360}
                                max={360}
                                style={{ width: '100%' }}
                              />
                            </Form.Item>
                            <Form.Item name={['parameters', 'axis']} label="旋转轴">
                              <Space.Compact>
                                <InputNumber placeholder="X" />
                                <InputNumber placeholder="Y" />
                                <InputNumber placeholder="Z" />
                              </Space.Compact>
                            </Form.Item>
                          </>
                        );
                      } else if (operation === 'translate') {
                        return (
                          <Form.Item name={['parameters', 'vector']} label="平移向量(Å)">
                            <Space.Compact>
                              <InputNumber placeholder="X" />
                              <InputNumber placeholder="Y" />
                              <InputNumber placeholder="Z" />
                            </Space.Compact>
                          </Form.Item>
                        );
                      } else if (operation === 'scale') {
                        return (
                          <Form.Item name={['parameters', 'factor']} label="缩放因子">
                            <InputNumber
                              min={0.1}
                              max={10}
                              step={0.1}
                              style={{ width: '100%' }}
                            />
                          </Form.Item>
                        );
                      } else if (operation === 'supercell') {
                        return (
                          <Form.Item name={['parameters', 'size']} label="超胞大小">
                            <Space.Compact>
                              <InputNumber placeholder="X" min={1} max={5} />
                              <InputNumber placeholder="Y" min={1} max={5} />
                              <InputNumber placeholder="Z" min={1} max={5} />
                            </Space.Compact>
                          </Form.Item>
                        );
                      }
                      return null;
                    }}
                  </Form.Item>

                  <Form.Item>
                    <Button
                      type="primary"
                      htmlType="submit"
                      loading={isModifying}
                      block
                    >
                      应用修改
                    </Button>
                  </Form.Item>
                </Form>
              </Panel>
            </Collapse>
          </Card>
        )}

        {/* 计算和分析 */}
        {structure && (
          <Card title="计算和分析" size="small">
            <Space direction="vertical" style={{ width: '100%' }}>
              <Button
                onClick={() => handleCalculateProperties(['energy'])}
                loading={isCalculating}
                block
              >
                计算能量
              </Button>
              <Button
                onClick={() => handleCalculateProperties(['energy', 'forces'])}
                loading={isCalculating}
                block
              >
                计算能量和力
              </Button>
              <Button
                onClick={handleOptimizeStructure}
                loading={isOptimizing}
                block
                type="primary"
              >
                几何优化
              </Button>
            </Space>
          </Card>
        )}

        {/* 显示设置 */}
        <Card title="显示设置" size="small">
          <Space direction="vertical" style={{ width: '100%' }}>
            <div>
              <span>显示化学键</span>
              <Switch
                size="small"
                checked={viewerSettings?.showBonds}
                onChange={(checked) =>
                  onViewerSettingsChange({ ...viewerSettings, showBonds: checked })
                }
                style={{ float: 'right' }}
              />
            </div>

            <div>
              <span>显示晶胞</span>
              <Switch
                size="small"
                checked={viewerSettings?.showUnitCell}
                onChange={(checked) =>
                  onViewerSettingsChange({ ...viewerSettings, showUnitCell: checked })
                }
                style={{ float: 'right' }}
              />
            </div>

            <div>
              <span>显示坐标轴</span>
              <Switch
                size="small"
                checked={viewerSettings?.showAxes}
                onChange={(checked) =>
                  onViewerSettingsChange({ ...viewerSettings, showAxes: checked })
                }
                style={{ float: 'right' }}
              />
            </div>

            <div>
              <div>原子大小</div>
              <Slider
                min={0.5}
                max={2.0}
                step={0.1}
                value={viewerSettings?.scaleFactor || 1.0}
                onChange={(value) =>
                  onViewerSettingsChange({ ...viewerSettings, scaleFactor: value })
                }
                tooltip={{ formatter: (value) => `${value}x` }}
              />
            </div>

            <div>
              <div>背景颜色</div>
              <Select
                value={viewerSettings?.backgroundColor || '#000000'}
                onChange={(value) =>
                  onViewerSettingsChange({ ...viewerSettings, backgroundColor: value })
                }
                style={{ width: '100%' }}
                size="small"
              >
                <Option value="#000000">黑色</Option>
                <Option value="#FFFFFF">白色</Option>
                <Option value="#F0F0F0">浅灰色</Option>
                <Option value="#2F2F2F">深灰色</Option>
              </Select>
            </div>
          </Space>
        </Card>

        {/* 结构信息 */}
        {structure && (
          <Card title="结构信息" size="small">
            <div style={{ fontSize: '12px' }}>
              <div>分子式: {structure.formula}</div>
              <div>原子数: {structure.total_atoms}</div>
              <div>唯一元素: {structure.unique_elements?.join(', ')}</div>
              {structure.volume && (
                <div>体积: {structure.volume.toFixed(2)} Ų</div>
              )}
              {structure.center_of_mass && (
                <div>
                  质心: ({structure.center_of_mass.map(x => x.toFixed(2)).join(', ')})
                </div>
              )}
            </div>
          </Card>
        )}
      </Space>
    </div>
  );
}

export default ControlPanel;
import React, { useState, useEffect } from 'react';
import {
  List,
  Card,
  Button,
  Modal,
  Form,
  Input,
  Select,
  Space,
  Tag,
  Tooltip,
  Popconfirm,
  Empty,
  Spin,
  Badge,
  Typography,
  Row,
  Col
} from 'antd';
import {
  PlusOutlined,
  DeleteOutlined,
  EyeOutlined,
  ClockCircleOutlined,
  ExperimentOutlined,
  ReloadOutlined
} from '@ant-design/icons';
import moment from 'moment';

const { Option } = Select;
const { Text } = Typography;

function SessionList({
  sessions = [],
  currentSessionId,
  onSessionSelect,
  onSessionCreate,
  onSessionDelete,
  onRefresh,
  loading = false
}) {
  const [isCreateModalVisible, setIsCreateModalVisible] = useState(false);
  const [createForm] = Form.useForm();
  const [filter, setFilter] = useState('all');

  // 过滤会话
  const filteredSessions = sessions.filter(session => {
    if (filter === 'all') return true;
    if (filter === 'active') return session.status === 'active';
    if (filter === 'with_structure') return session.has_structure;
    return true;
  });

  // 创建新会话
  const handleCreateSession = async (values) => {
    try {
      await onSessionCreate(values);
      setIsCreateModalVisible(false);
      createForm.resetFields();
    } catch (error) {
      console.error('创建会话失败:', error);
    }
  };

  // 删除会话
  const handleDeleteSession = async (sessionId) => {
    try {
      await onSessionDelete(sessionId);
    } catch (error) {
      console.error('删除会话失败:', error);
    }
  };

  // 格式化时间
  const formatTime = (timeString) => {
    return moment(timeString).format('MM-DD HH:mm');
  };

  // 获取相对时间
  const getRelativeTime = (timeString) => {
    return moment(timeString).fromNow();
  };

  // 获取状态颜色
  const getStatusColor = (status) => {
    switch (status) {
      case 'active': return 'green';
      case 'inactive': return 'orange';
      case 'completed': return 'blue';
      case 'error': return 'red';
      default: return 'default';
    }
  };

  // 渲染会话项
  const renderSessionItem = (session) => {
    const isSelected = session.id === currentSessionId;

    return (
      <List.Item
        key={session.id}
        style={{
          backgroundColor: isSelected ? '#e6f7ff' : 'transparent',
          border: isSelected ? '1px solid #1890ff' : '1px solid transparent',
          borderRadius: '6px',
          margin: '4px 0',
          padding: '12px'
        }}
      >
        <div style={{ width: '100%' }}>
          {/* 头部信息 */}
          <Row justify="space-between" align="middle" style={{ marginBottom: '8px' }}>
            <Col>
              <Space>
                <Badge
                  status={session.has_structure ? 'success' : 'default'}
                  text={
                    <Text strong style={{ fontSize: '13px' }}>
                      {session.metadata?.name || `会话 ${session.id.substring(0, 8)}`}
                    </Text>
                  }
                />
                <Tag color={getStatusColor(session.status)} size="small">
                  {session.status}
                </Tag>
              </Space>
            </Col>
            <Col>
              <Space size="small">
                <Tooltip title="查看详情">
                  <Button
                    type="text"
                    size="small"
                    icon={<EyeOutlined />}
                    onClick={() => onSessionSelect(session.id)}
                  />
                </Tooltip>
                <Popconfirm
                  title="确定删除此会话吗？"
                  onConfirm={() => handleDeleteSession(session.id)}
                  okText="删除"
                  cancelText="取消"
                >
                  <Button
                    type="text"
                    size="small"
                    icon={<DeleteOutlined />}
                    danger
                  />
                </Popconfirm>
              </Space>
            </Col>
          </Row>

          {/* 结构信息 */}
          {session.structure_summary && (
            <div style={{ marginBottom: '8px' }}>
              <Space size="small">
                <ExperimentOutlined style={{ color: '#52c41a' }} />
                <Text type="secondary" style={{ fontSize: '12px' }}>
                  {session.structure_summary.formula} - {session.structure_summary.total_atoms} 原子
                </Text>
              </Space>
            </div>
          )}

          {/* 描述 */}
          {session.metadata?.description && (
            <div style={{ marginBottom: '8px' }}>
              <Text type="secondary" style={{ fontSize: '12px' }}>
                {session.metadata.description}
              </Text>
            </div>
          )}

          {/* 标签 */}
          {session.metadata?.tags && session.metadata.tags.length > 0 && (
            <div style={{ marginBottom: '8px' }}>
              {session.metadata.tags.map(tag => (
                <Tag key={tag} size="small" style={{ margin: '0 2px' }}>
                  {tag}
                </Tag>
              ))}
            </div>
          )}

          {/* 时间信息 */}
          <div>
            <Space split={<span style={{ color: '#d9d9d9' }}>|</span>}>
              <Tooltip title={`创建时间: ${formatTime(session.created_at)}`}>
                <Text type="secondary" style={{ fontSize: '11px' }}>
                  <ClockCircleOutlined /> 创建 {getRelativeTime(session.created_at)}
                </Text>
              </Tooltip>
              <Tooltip title={`修改时间: ${formatTime(session.modified_at)}`}>
                <Text type="secondary" style={{ fontSize: '11px' }}>
                  修改 {getRelativeTime(session.modified_at)}
                </Text>
              </Tooltip>
            </Space>
          </div>
        </div>
      </List.Item>
    );
  };

  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      {/* 头部控制 */}
      <Card size="small" style={{ marginBottom: '8px' }}>
        <Row justify="space-between" align="middle">
          <Col>
            <Select
              value={filter}
              onChange={setFilter}
              size="small"
              style={{ width: 120 }}
            >
              <Option value="all">全部会话</Option>
              <Option value="active">活跃会话</Option>
              <Option value="with_structure">有结构</Option>
            </Select>
          </Col>
          <Col>
            <Space>
              <Tooltip title="刷新列表">
                <Button
                  type="text"
                  size="small"
                  icon={<ReloadOutlined />}
                  onClick={onRefresh}
                />
              </Tooltip>
              <Button
                type="primary"
                size="small"
                icon={<PlusOutlined />}
                onClick={() => setIsCreateModalVisible(true)}
              >
                新建
              </Button>
            </Space>
          </Col>
        </Row>
      </Card>

      {/* 会话列表 */}
      <div style={{ flex: 1, overflow: 'auto' }}>
        <Spin spinning={loading}>
          {filteredSessions.length > 0 ? (
            <List
              dataSource={filteredSessions}
              renderItem={renderSessionItem}
              style={{ padding: '0 8px' }}
            />
          ) : (
            <Empty
              image={Empty.PRESENTED_IMAGE_SIMPLE}
              description="暂无会话"
              style={{ marginTop: '50px' }}
            >
              <Button
                type="primary"
                icon={<PlusOutlined />}
                onClick={() => setIsCreateModalVisible(true)}
              >
                创建第一个会话
              </Button>
            </Empty>
          )}
        </Spin>
      </div>

      {/* 创建会话对话框 */}
      <Modal
        title="创建新会话"
        open={isCreateModalVisible}
        onCancel={() => {
          setIsCreateModalVisible(false);
          createForm.resetFields();
        }}
        footer={null}
        width={400}
      >
        <Form
          form={createForm}
          layout="vertical"
          onFinish={handleCreateSession}
        >
          <Form.Item
            name="name"
            label="会话名称"
            rules={[{ required: true, message: '请输入会话名称' }]}
          >
            <Input placeholder="为会话起个名字" />
          </Form.Item>

          <Form.Item
            name="description"
            label="描述"
          >
            <Input.TextArea
              placeholder="简要描述这个会话的用途"
              rows={3}
            />
          </Form.Item>

          <Form.Item
            name="tags"
            label="标签"
          >
            <Select
              mode="tags"
              placeholder="添加标签 (回车创建)"
              style={{ width: '100%' }}
            >
              <Option value="计算">计算</Option>
              <Option value="分析">分析</Option>
              <Option value="优化">优化</Option>
              <Option value="测试">测试</Option>
            </Select>
          </Form.Item>

          <Form.Item style={{ marginBottom: 0 }}>
            <Space style={{ float: 'right' }}>
              <Button onClick={() => setIsCreateModalVisible(false)}>
                取消
              </Button>
              <Button type="primary" htmlType="submit">
                创建
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}

export default SessionList;
import { io } from 'socket.io-client';

class WebSocketService {
  constructor() {
    this.socket = null;
    this.isConnected = false;
    this.reconnectAttempts = 0;
    this.maxReconnectAttempts = 5;
    this.reconnectDelay = 1000;
    this.subscribers = new Map();
    this.currentSessionId = null;
  }

  connect(url = 'ws://localhost:8001') {
    return new Promise((resolve, reject) => {
      try {
        // 使用原生WebSocket而不是Socket.IO
        this.socket = new WebSocket(url);

        this.socket.onopen = () => {
          console.log('WebSocket连接成功');
          this.isConnected = true;
          this.reconnectAttempts = 0;
          this.startHeartbeat();
          resolve();
        };

        this.socket.onmessage = (event) => {
          try {
            const message = JSON.parse(event.data);
            this.handleMessage(message);
          } catch (error) {
            console.error('解析WebSocket消息失败:', error);
          }
        };

        this.socket.onclose = () => {
          console.log('WebSocket连接关闭');
          this.isConnected = false;
          this.stopHeartbeat();
          this.attemptReconnect();
        };

        this.socket.onerror = (error) => {
          console.error('WebSocket错误:', error);
          reject(error);
        };

      } catch (error) {
        reject(error);
      }
    });
  }

  disconnect() {
    if (this.socket) {
      this.socket.close();
      this.socket = null;
      this.isConnected = false;
      this.stopHeartbeat();
    }
  }

  send(message) {
    if (this.isConnected && this.socket) {
      this.socket.send(JSON.stringify(message));
      return true;
    }
    console.warn('WebSocket未连接，消息发送失败');
    return false;
  }

  subscribe(eventType, callback) {
    if (!this.subscribers.has(eventType)) {
      this.subscribers.set(eventType, new Set());
    }
    this.subscribers.get(eventType).add(callback);

    // 返回取消订阅函数
    return () => {
      this.unsubscribe(eventType, callback);
    };
  }

  unsubscribe(eventType, callback) {
    if (this.subscribers.has(eventType)) {
      this.subscribers.get(eventType).delete(callback);
    }
  }

  handleMessage(message) {
    const { type, data, session_id } = message;

    // 触发通用订阅者
    this.notifySubscribers(type, { data, session_id });

    // 触发所有消息订阅者
    this.notifySubscribers('*', message);

    // 处理特定消息类型
    switch (type) {
      case 'connection_established':
        this.clientId = data.client_id;
        console.log('WebSocket客户端ID:', this.clientId);
        break;

      case 'structure_update':
        this.notifySubscribers('structureUpdate', {
          sessionId: session_id,
          structure: data.structure,
          structureInfo: data.structure_info,
          operation: data.operation,
          timestamp: data.timestamp
        });
        break;

      case 'property_update':
        this.notifySubscribers('propertyUpdate', {
          sessionId: session_id,
          properties: data.properties,
          timestamp: data.timestamp
        });
        break;

      case 'session_state':
        this.notifySubscribers('sessionState', {
          sessionId: session_id,
          session: data.session,
          structure: data.structure,
          timestamp: data.timestamp
        });
        break;

      case 'sessions_list':
        this.notifySubscribers('sessionsList', {
          sessions: data.sessions,
          pagination: data.pagination
        });
        break;

      case 'session_deleted':
        this.notifySubscribers('sessionDeleted', {
          sessionId: session_id,
          message: data.message
        });
        break;

      case 'error':
        this.notifySubscribers('error', {
          sessionId: session_id,
          message: data.message
        });
        console.error('WebSocket错误:', data.message);
        break;

      case 'pong':
        // 心跳响应
        break;

      default:
        console.log('未处理的WebSocket消息类型:', type, message);
    }
  }

  notifySubscribers(eventType, data) {
    if (this.subscribers.has(eventType)) {
      this.subscribers.get(eventType).forEach(callback => {
        try {
          callback(data);
        } catch (error) {
          console.error('订阅回调执行失败:', error);
        }
      });
    }
  }

  // 会话相关方法
  subscribeToSession(sessionId) {
    this.currentSessionId = sessionId;
    this.send({
      type: 'subscribe',
      session_id: sessionId
    });
  }

  unsubscribeFromSession(sessionId) {
    if (this.currentSessionId === sessionId) {
      this.currentSessionId = null;
    }
    this.send({
      type: 'unsubscribe',
      session_id: sessionId
    });
  }

  requestSessionsList(limit = 20, offset = 0, statusFilter = null) {
    this.send({
      type: 'get_sessions',
      limit,
      offset,
      status_filter: statusFilter
    });
  }

  // 心跳机制
  startHeartbeat() {
    this.heartbeatInterval = setInterval(() => {
      if (this.isConnected) {
        this.send({ type: 'ping' });
      }
    }, 30000); // 30秒心跳
  }

  stopHeartbeat() {
    if (this.heartbeatInterval) {
      clearInterval(this.heartbeatInterval);
      this.heartbeatInterval = null;
    }
  }

  // 重连机制
  attemptReconnect() {
    if (this.reconnectAttempts < this.maxReconnectAttempts) {
      this.reconnectAttempts++;
      console.log(`尝试重连 ${this.reconnectAttempts}/${this.maxReconnectAttempts}`);

      setTimeout(() => {
        this.connect();
      }, this.reconnectDelay * this.reconnectAttempts);
    } else {
      console.error('达到最大重连次数，停止重连');
      this.notifySubscribers('maxReconnectAttemptsReached', {
        attempts: this.reconnectAttempts
      });
    }
  }

  // 获取连接状态
  getConnectionState() {
    return {
      isConnected: this.isConnected,
      clientId: this.clientId,
      currentSessionId: this.currentSessionId,
      reconnectAttempts: this.reconnectAttempts
    };
  }
}

// 创建单例实例
const websocketService = new WebSocketService();

export default websocketService;
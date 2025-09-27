import axios from 'axios';

class APIService {
  constructor(baseURL = 'http://localhost:8000') {
    this.client = axios.create({
      baseURL,
      timeout: 30000,
      headers: {
        'Content-Type': 'application/json',
      },
    });

    // 请求拦截器
    this.client.interceptors.request.use(
      (config) => {
        console.log(`API Request: ${config.method?.toUpperCase()} ${config.url}`);
        return config;
      },
      (error) => {
        return Promise.reject(error);
      }
    );

    // 响应拦截器
    this.client.interceptors.response.use(
      (response) => {
        return response.data;
      },
      (error) => {
        console.error('API Error:', error);

        if (error.response) {
          // 服务器响应错误
          throw new Error(error.response.data?.detail || error.response.statusText);
        } else if (error.request) {
          // 网络错误
          throw new Error('网络连接失败，请检查服务器状态');
        } else {
          // 其他错误
          throw new Error(error.message);
        }
      }
    );
  }

  // 健康检查
  async healthCheck() {
    return this.client.get('/health');
  }

  // 会话管理
  async getSessions(params = {}) {
    const { limit = 20, offset = 0, status_filter } = params;
    return this.client.get('/api/sessions', {
      params: { limit, offset, status_filter }
    });
  }

  async getSession(sessionId) {
    return this.client.get(`/api/sessions/${sessionId}`);
  }

  async deleteSession(sessionId) {
    return this.client.delete(`/api/sessions/${sessionId}`);
  }

  // WebSocket信息
  async getWebSocketInfo() {
    return this.client.get('/api/websocket/info');
  }

  // MCP工具调用（通过REST API代理）
  async callMCPTool(toolName, parameters) {
    return this.client.post('/api/mcp/call', {
      tool: toolName,
      parameters: parameters
    });
  }

  // 结构操作的便捷方法
  async createStructure(params) {
    return this.callMCPTool('create_structure', params);
  }

  async modifyStructure(params) {
    return this.callMCPTool('modify_structure', params);
  }

  async calculateProperties(params) {
    return this.callMCPTool('calculate_properties', params);
  }

  async optimizeStructure(params) {
    return this.callMCPTool('optimize_structure', params);
  }

  async previewStructure(params) {
    return this.callMCPTool('preview_structure', params);
  }

  async saveStructure(params) {
    return this.callMCPTool('save_structure', params);
  }

  async undoOperation(sessionId) {
    return this.callMCPTool('undo_operation', { session_id: sessionId });
  }

  async redoOperation(sessionId) {
    return this.callMCPTool('redo_operation', { session_id: sessionId });
  }

  async getStructureInfo(sessionId) {
    return this.callMCPTool('get_structure_info', { session_id: sessionId });
  }

  // 文件上传下载
  async uploadStructureFile(file, format) {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('format', format);

    return this.client.post('/api/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
  }

  async downloadStructure(sessionId, format = 'cif') {
    return this.client.get(`/api/sessions/${sessionId}/download`, {
      params: { format },
      responseType: 'blob'
    });
  }

  // 批量操作
  async batchCreateStructures(structures) {
    return this.client.post('/api/batch/create', { structures });
  }

  async batchModifyStructures(operations) {
    return this.client.post('/api/batch/modify', { operations });
  }

  // 性能监控
  async getMetrics() {
    return this.client.get('/api/metrics');
  }

  // 系统信息
  async getSystemInfo() {
    return this.client.get('/api/system/info');
  }
}

// 创建单例实例
const apiService = new APIService();

export default apiService;
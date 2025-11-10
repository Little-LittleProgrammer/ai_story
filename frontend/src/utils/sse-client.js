/**
 * SSE客户端工具类
 * 用于连接后端SSE流式接口并接收实时数据
 */

export class SSEClient {
  constructor(projectId, stageName = null) {
    this.projectId = projectId;
    this.stageName = stageName;
    this.eventSource = null;
    this.handlers = {
      connected: [],
      token: [],
      stage_update: [],
      progress: [],
      done: [],
      error: [],
      stream_end: []
    };
  }

  /**
   * 连接SSE流
   * @param {Object} options - 配置选项
   * @param {boolean} options.withAuth - 是否使用认证接口
   * @param {string} options.token - 认证Token
   */
  connect(options = {}) {
    const { withAuth = false, token = null } = options;

    // 构建URL
    let url;
    if (this.stageName) {
      // 订阅单个阶段
      url = withAuth
        ? `/api/v1/sse/projects/${this.projectId}/stages/${this.stageName}/stream/`
        : `/api/v1/sse/projects/${this.projectId}/stages/${this.stageName}/`;
    } else {
      // 订阅所有阶段
      url = withAuth
        ? `/api/v1/sse/projects/${this.projectId}/stream/`
        : `/api/v1/sse/projects/${this.projectId}/`;
    }

    // 添加认证头 (EventSource不支持自定义headers，需要通过URL参数传递token)
    if (withAuth && token) {
      url += `?token=${token}`;
    }

    // 创建EventSource连接
    this.eventSource = new EventSource(url);

    // 监听消息
    this.eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        this._handleMessage(data);
      } catch (error) {
        console.error('SSE消息解析失败:', error);
      }
    };

    // 监听错误
    this.eventSource.onerror = (error) => {
      console.error('SSE连接错误:', error);
      this._trigger('error', { error: 'SSE连接错误' });
      this.disconnect();
    };

    console.log(`SSE连接已建立: ${url}`);
  }

  /**
   * 断开SSE连接
   */
  disconnect() {
    if (this.eventSource) {
      this.eventSource.close();
      this.eventSource = null;
      console.log('SSE连接已关闭');
    }
  }

  /**
   * 注册事件处理器
   * @param {string} event - 事件类型
   * @param {Function} handler - 处理函数
   */
  on(event, handler) {
    if (this.handlers[event]) {
      this.handlers[event].push(handler);
    }
    return this; // 支持链式调用
  }

  /**
   * 移除事件处理器
   * @param {string} event - 事件类型
   * @param {Function} handler - 处理函数
   */
  off(event, handler) {
    if (this.handlers[event]) {
      const index = this.handlers[event].indexOf(handler);
      if (index > -1) {
        this.handlers[event].splice(index, 1);
      }
    }
    return this;
  }

  /**
   * 处理接收到的消息
   * @private
   */
  _handleMessage(data) {
    const { type } = data;

    // 触发对应类型的处理器
    this._trigger(type, data);

    // 自动断开连接的消息类型
    if (type === 'done' || type === 'error' || type === 'stream_end') {
      setTimeout(() => this.disconnect(), 100);
    }
  }

  /**
   * 触发事件处理器
   * @private
   */
  _trigger(event, data) {
    if (this.handlers[event]) {
      this.handlers[event].forEach(handler => {
        try {
          handler(data);
        } catch (error) {
          console.error(`事件处理器执行失败 (${event}):`, error);
        }
      });
    }
  }

  /**
   * 检查连接状态
   */
  isConnected() {
    return this.eventSource !== null && this.eventSource.readyState === EventSource.OPEN;
  }
}

/**
 * 创建SSE客户端的便捷函数
 * @param {string} projectId - 项目ID
 * @param {string} stageName - 阶段名称 (可选)
 * @returns {SSEClient}
 */
export function createSSEClient(projectId, stageName = null) {
  return new SSEClient(projectId, stageName);
}

/**
 * Vue 3 Composition API Hook
 * @param {string} projectId - 项目ID
 * @param {string} stageName - 阶段名称 (可选)
 */
export function useSSE(projectId, stageName = null) {
  const client = new SSEClient(projectId, stageName);
  const isConnected = ref(false);
  const fullText = ref('');
  const progress = ref(0);
  const error = ref(null);

  // 连接状态
  client.on('connected', () => {
    isConnected.value = true;
  });

  // Token消息
  client.on('token', (data) => {
    fullText.value = data.full_text;
  });

  // 阶段更新
  client.on('stage_update', (data) => {
    if (data.progress !== undefined) {
      progress.value = data.progress;
    }
  });

  // 进度消息
  client.on('progress', (data) => {
    progress.value = data.progress;
  });

  // 完成
  client.on('done', (data) => {
    fullText.value = data.full_text;
    progress.value = 100;
  });

  // 错误
  client.on('error', (data) => {
    error.value = data.error;
    isConnected.value = false;
  });

  // 流结束
  client.on('stream_end', () => {
    isConnected.value = false;
  });

  // 清理函数
  const cleanup = () => {
    client.disconnect();
  };

  return {
    client,
    isConnected,
    fullText,
    progress,
    error,
    connect: (options) => client.connect(options),
    disconnect: () => client.disconnect(),
    cleanup
  };
}

export default SSEClient;

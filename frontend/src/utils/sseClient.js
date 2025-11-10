/**
 * SSE(Server-Sent Events)客户端工具
 * 用于接收服务器推送的实时事件流
 */

class SSEClient {
  constructor() {
    this.eventSource = null;
    this.listeners = {};
  }

  /**
   * 连接SSE端点
   * @param {string} url - SSE端点URL
   * @param {Object} options - 配置选项
   */
  connect(url, options = {}) {
    // 如果已有连接,先关闭
    if (this.eventSource) {
      this.disconnect();
    }

    // 创建EventSource连接
    this.eventSource = new EventSource(url, options);

    // 监听message事件(默认事件类型)
    this.eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        this.emit('message', data);

        // 根据type触发特定事件
        if (data.type) {
          this.emit(data.type, data);
        }
      } catch (error) {
        console.error('Failed to parse SSE message:', error);
        this.emit('error', { error: 'Parse error', originalData: event.data });
      }
    };

    // 监听连接打开
    this.eventSource.onopen = () => {
      console.log('SSE connection opened');
      this.emit('open');
    };

    // 监听错误
    this.eventSource.onerror = (error) => {
      console.error('SSE connection error:', error);
      this.emit('error', error);

      // 连接关闭时自动清理
      if (this.eventSource.readyState === EventSource.CLOSED) {
        this.emit('close');
        this.cleanup();
      }
    };

    return this;
  }

  /**
   * 监听事件
   * @param {string} event - 事件名称
   * @param {Function} handler - 事件处理函数
   */
  on(event, handler) {
    if (!this.listeners[event]) {
      this.listeners[event] = [];
    }
    this.listeners[event].push(handler);
    return this;
  }

  /**
   * 移除事件监听
   * @param {string} event - 事件名称
   * @param {Function} handler - 事件处理函数
   */
  off(event, handler) {
    if (!this.listeners[event]) return;

    if (handler) {
      this.listeners[event] = this.listeners[event].filter((h) => h !== handler);
    } else {
      delete this.listeners[event];
    }
    return this;
  }

  /**
   * 触发事件
   * @param {string} event - 事件名称
   * @param {*} data - 事件数据
   */
  emit(event, data) {
    if (!this.listeners[event]) return;

    this.listeners[event].forEach((handler) => {
      try {
        handler(data);
      } catch (error) {
        console.error(`Error in SSE event handler for "${event}":`, error);
      }
    });
  }

  /**
   * 断开连接
   */
  disconnect() {
    if (this.eventSource) {
      this.eventSource.close();
      this.cleanup();
    }
  }

  /**
   * 清理资源
   */
  cleanup() {
    this.eventSource = null;
    this.listeners = {};
  }

  /**
   * 获取连接状态
   */
  getReadyState() {
    if (!this.eventSource) return EventSource.CLOSED;
    return this.eventSource.readyState;
  }

  /**
   * 是否已连接
   */
  isConnected() {
    return this.eventSource && this.eventSource.readyState === EventSource.OPEN;
  }
}

/**
 * 创建一个用于项目阶段流式执行的SSE客户端
 * @param {string} projectId - 项目ID
 * @param {string} stageName - 阶段名称(rewrite/storyboard/image_generation/camera_movement/video_generation)
 * @param {Object} inputData - 输入数据
 * @param {boolean} useStreaming - 是否使用SSE流式模式(默认false，使用Celery异步)
 * @returns {SSEClient} SSE客户端实例
 */
export function createStageStreamClient(projectId, stageName, inputData = {}, useStreaming = true) {
  const client = new SSEClient();

  // 使用统一的 execute-stage 接口
  const url = `/api/v1/projects/projects/${projectId}/execute_stage/`;

  // 使用fetch代替EventSource以支持POST
  const connectWithFetch = async () => {
    try {
      // 获取认证令牌
      const token = localStorage.getItem('access_token');

      const headers = {
        'Content-Type': 'application/json',
      };

      // 如果有token,添加认证头
      if (token) {
        headers['Authorization'] = `Bearer ${token}`;
      }

      // 构建请求体
      const requestBody = {
        stage_name: stageName,
        input_data: inputData,
        use_streaming: useStreaming, // 启用SSE流式模式
      };

      const response = await fetch(url, {
        method: 'POST',
        headers: headers,
        body: JSON.stringify(requestBody),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();

      client.emit('open');

      // 读取流
      let buffer = '';
      while (true) {
        const { done, value } = await reader.read();

        if (done) {
          console.log('[SSE] Stream完成');
          client.emit('close');
          break;
        }

        // 解码数据
        buffer += decoder.decode(value, { stream: true });

        // 按行分割
        const lines = buffer.split('\n');
        buffer = lines.pop(); // 保留最后一个不完整的行

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const jsonData = line.slice(6);
              console.log('[SSE] 接收到数据:', jsonData);
              const data = JSON.parse(jsonData);
              console.log('[SSE] 解析后的数据:', data);
              client.emit('message', data);

              // 根据type触发特定事件
              if (data.type) {
                console.log('[SSE] 触发事件:', data.type);
                client.emit(data.type, data);
              }
            } catch (error) {
              console.error('[SSE] 解析失败:', error, '原始数据:', line);
            }
          }
        }
      }
    } catch (error) {
      console.error('SSE fetch error:', error);
      client.emit('error', error);
    }
  };

  // 启动连接
  connectWithFetch();

  return client;
}

export default SSEClient;

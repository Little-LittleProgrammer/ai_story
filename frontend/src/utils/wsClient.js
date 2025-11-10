/**
 * WebSocket客户端工具
 * 用于订阅Redis Pub/Sub频道，接收Celery任务的实时进度
 */

class WSClient {
  constructor() {
    this.ws = null;
    this.listeners = {};
    this.reconnectAttempts = 0;
    this.maxReconnectAttempts = 5;
    this.reconnectDelay = 1000; // 初始重连延迟1秒
  }

  /**
   * 连接WebSocket
   * @param {string} projectId - 项目ID
   * @param {string} stageName - 阶段名称
   * @param {Object} options - 配置选项
   */
  connect(projectId, stageName, options = {}) {
    // 如果已有连接,先关闭
    if (this.ws) {
      this.disconnect();
    }

    // 构建WebSocket URL
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = options.host || window.location.host;
    const url = `${protocol}//${host}/ws/projects/${projectId}/stage/${stageName}/`;

    console.log('[WebSocket] 连接到:', url);

    try {
      this.ws = new WebSocket(url);

      // 连接打开
      this.ws.onopen = () => {
        console.log('[WebSocket] 连接已建立');
        this.reconnectAttempts = 0; // 重置重连计数
        this.emit('open');
      };

      // 接收消息
      this.ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          console.log('[WebSocket] 收到消息:', data);

          this.emit('message', data);

          // 根据type触发特定事件
          if (data.type) {
            this.emit(data.type, data);
          }
        } catch (error) {
          console.error('[WebSocket] 解析消息失败:', error);
          this.emit('error', { error: 'Parse error', originalData: event.data });
        }
      };

      // 连接关闭
      this.ws.onclose = (event) => {
        console.log('[WebSocket] 连接已关闭', event.code, event.reason);
        this.emit('close', { code: event.code, reason: event.reason });

        // 如果不是正常关闭,尝试重连
        if (event.code !== 1000 && this.reconnectAttempts < this.maxReconnectAttempts) {
          this.attemptReconnect(projectId, stageName, options);
        }
      };

      // 连接错误
      this.ws.onerror = (error) => {
        console.error('[WebSocket] 连接错误:', error);
        this.emit('error', error);
      };
    } catch (error) {
      console.error('[WebSocket] 创建连接失败:', error);
      this.emit('error', error);
    }

    return this;
  }

  /**
   * 尝试重连
   */
  attemptReconnect(projectId, stageName, options) {
    this.reconnectAttempts++;
    const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1); // 指数退避

    console.log(`[WebSocket] ${delay}ms后尝试第${this.reconnectAttempts}次重连...`);

    setTimeout(() => {
      this.connect(projectId, stageName, options);
    }, delay);
  }

  /**
   * 发送消息
   * @param {Object} data - 要发送的数据
   */
  send(data) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(data));
    } else {
      console.warn('[WebSocket] 连接未打开,无法发送消息');
    }
  }

  /**
   * 发送心跳
   */
  sendHeartbeat() {
    this.send({ type: 'ping', timestamp: Date.now() });
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
        console.error(`[WebSocket] 事件处理器错误 "${event}":`, error);
      }
    });
  }

  /**
   * 断开连接
   */
  disconnect() {
    if (this.ws) {
      this.ws.close(1000, 'Client disconnect'); // 正常关闭
      this.cleanup();
    }
  }

  /**
   * 清理资源
   */
  cleanup() {
    this.ws = null;
    this.listeners = {};
    this.reconnectAttempts = 0;
  }

  /**
   * 获取连接状态
   */
  getReadyState() {
    if (!this.ws) return WebSocket.CLOSED;
    return this.ws.readyState;
  }

  /**
   * 是否已连接
   */
  isConnected() {
    return this.ws && this.ws.readyState === WebSocket.OPEN;
  }
}

/**
 * 创建一个用于项目阶段执行的WebSocket客户端
 * @param {string} projectId - 项目ID
 * @param {string} stageName - 阶段名称
 * @param {Object} options - 配置选项
 * @returns {WSClient} WebSocket客户端实例
 */
export function createStageWSClient(projectId, stageName, options = {}) {
  const client = new WSClient();
  client.connect(projectId, stageName, options);

  // 启动心跳 (可选)
  if (options.heartbeat !== false) {
    const heartbeatInterval = setInterval(() => {
      if (client.isConnected()) {
        client.sendHeartbeat();
      } else {
        clearInterval(heartbeatInterval);
      }
    }, 30000); // 每30秒发送一次心跳

    // 清理时停止心跳
    client.on('close', () => {
      clearInterval(heartbeatInterval);
    });
  }

  return client;
}

export default WSClient;

import io from 'socket.io-client';

class WebSocketClient {
  constructor() {
    this.socket = null;
    this.listeners = new Map();
  }

  connect(projectId) {
    if (this.socket) {
      this.disconnect();
    }

    // 临时禁用 WebSocket 连接
    // 原因：后端 Django Channels Consumer 尚未实现
    // TODO: 实现 apps/projects/consumers.py 后启用
    console.warn('[WebSocket] 连接已禁用 - 后端 Consumer 尚未实现');
    return this;

    /* eslint-disable no-unreachable */
    // 以下代码待后端实现后启用
    const wsUrl = process.env.VUE_APP_WS_URL || 'ws://localhost:8000';
    this.socket = io(`${wsUrl}/ws/projects/${projectId}/`, {
      transports: ['websocket'],
      reconnection: true,
      reconnectionDelay: 1000,
      reconnectionAttempts: 5,
      timeout: 3000,
      autoConnect: false, // 禁用自动连接
    });

    this.socket.on('connect', () => {
      console.log('[WebSocket] 已连接');
    });

    this.socket.on('disconnect', (reason) => {
      console.log('[WebSocket] 已断开:', reason);
    });

    this.socket.on('connect_error', (error) => {
      console.error('[WebSocket] 连接错误:', error.message);
    });

    this.socket.on('error', (error) => {
      console.error('[WebSocket] 错误:', error);
    });

    // 手动连接
    this.socket.connect();

    return this;
    /* eslint-enable no-unreachable */
  }

  disconnect() {
    if (this.socket) {
      this.socket.disconnect();
      this.socket = null;
      this.listeners.clear();
    }
  }

  on(event, callback) {
    if (!this.socket) {
      console.warn('WebSocket not connected');
      return;
    }

    this.socket.on(event, callback);
    this.listeners.set(event, callback);
  }

  off(event) {
    if (!this.socket) {
      return;
    }

    const callback = this.listeners.get(event);
    if (callback) {
      this.socket.off(event, callback);
      this.listeners.delete(event);
    }
  }

  emit(event, data) {
    if (!this.socket) {
      console.warn('WebSocket not connected');
      return;
    }

    this.socket.emit(event, data);
  }
}

export default new WebSocketClient();

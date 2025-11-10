<template>
  <div class="sse-stream-viewer">
    <!-- 连接状态 -->
    <div class="status-bar" :class="statusClass">
      <div class="status-indicator">
        <span class="status-dot" :class="{ active: isConnected }"></span>
        <span class="status-text">{{ statusText }}</span>
      </div>
      <button v-if="!isConnected" @click="connect" class="btn btn-sm btn-primary">
        连接
      </button>
      <button v-else @click="disconnect" class="btn btn-sm btn-error">
        断开
      </button>
    </div>

    <!-- 进度条 -->
    <div v-if="isConnected && progress > 0" class="progress-bar">
      <div class="progress-fill" :style="{ width: progress + '%' }">
        {{ progress }}%
      </div>
    </div>

    <!-- 错误提示 -->
    <div v-if="error" class="alert alert-error">
      <svg xmlns="http://www.w3.org/2000/svg" class="stroke-current shrink-0 h-6 w-6" fill="none" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
      <span>{{ error }}</span>
    </div>

    <!-- 流式内容显示 -->
    <div class="content-viewer">
      <div class="content-header">
        <h3>生成内容</h3>
        <span v-if="isStreaming" class="streaming-indicator">
          <span class="loading loading-dots loading-sm"></span>
          正在生成...
        </span>
      </div>
      <div class="content-body">
        <pre v-if="fullText">{{ fullText }}</pre>
        <div v-else class="empty-state">
          等待内容生成...
        </div>
      </div>
    </div>

    <!-- 消息日志 (可选) -->
    <div v-if="showLogs" class="message-logs">
      <div class="logs-header">
        <h4>消息日志</h4>
        <button @click="clearLogs" class="btn btn-xs btn-ghost">清空</button>
      </div>
      <div class="logs-body">
        <div v-for="(log, index) in logs" :key="index" class="log-item" :class="`log-${log.type}`">
          <span class="log-time">{{ log.time }}</span>
          <span class="log-type">{{ log.type }}</span>
          <span class="log-message">{{ log.message }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, computed, onMounted, onUnmounted } from 'vue';
import { createSSEClient } from '@/utils/sse-client';

export default {
  name: 'SSEStreamViewer',
  props: {
    projectId: {
      type: String,
      required: true
    },
    stageName: {
      type: String,
      default: null
    },
    autoConnect: {
      type: Boolean,
      default: false
    },
    showLogs: {
      type: Boolean,
      default: false
    }
  },
  emits: ['connected', 'token', 'progress', 'done', 'error', 'disconnected'],
  setup(props, { emit }) {
    // 状态
    const isConnected = ref(false);
    const isStreaming = ref(false);
    const fullText = ref('');
    const progress = ref(0);
    const error = ref(null);
    const logs = ref([]);

    // SSE客户端
    let sseClient = null;

    // 计算属性
    const statusClass = computed(() => ({
      'status-connected': isConnected.value,
      'status-disconnected': !isConnected.value,
      'status-error': error.value
    }));

    const statusText = computed(() => {
      if (error.value) return '连接错误';
      if (isConnected.value) return '已连接';
      return '未连接';
    });

    // 添加日志
    const addLog = (type, message) => {
      const time = new Date().toLocaleTimeString();
      logs.value.push({ type, message, time });
      // 限制日志数量
      if (logs.value.length > 100) {
        logs.value.shift();
      }
    };

    // 清空日志
    const clearLogs = () => {
      logs.value = [];
    };

    // 连接SSE
    const connect = () => {
      if (sseClient) {
        disconnect();
      }

      // 创建客户端
      sseClient = createSSEClient(props.projectId, props.stageName);

      // 注册事件处理器
      sseClient
        .on('connected', (data) => {
          isConnected.value = true;
          isStreaming.value = true;
          error.value = null;
          addLog('connected', '连接已建立');
          emit('connected', data);
        })
        .on('token', (data) => {
          fullText.value = data.full_text;
          addLog('token', `Token: ${data.content}`);
          emit('token', data);
        })
        .on('stage_update', (data) => {
          if (data.progress !== undefined) {
            progress.value = data.progress;
          }
          addLog('stage_update', `状态: ${data.status}, 进度: ${data.progress}%`);
          emit('progress', data);
        })
        .on('progress', (data) => {
          progress.value = data.progress;
          const message = data.item_name
            ? `进度: ${data.current}/${data.total} (${data.item_name})`
            : `进度: ${data.current}/${data.total}`;
          addLog('progress', message);
          emit('progress', data);
        })
        .on('done', (data) => {
          fullText.value = data.full_text;
          progress.value = 100;
          isStreaming.value = false;
          addLog('done', '生成完成');
          emit('done', data);
        })
        .on('error', (data) => {
          error.value = data.error;
          isConnected.value = false;
          isStreaming.value = false;
          addLog('error', data.error);
          emit('error', data);
        })
        .on('stream_end', () => {
          isConnected.value = false;
          isStreaming.value = false;
          addLog('stream_end', '流已关闭');
          emit('disconnected');
        });

      // 连接
      sseClient.connect();
    };

    // 断开连接
    const disconnect = () => {
      if (sseClient) {
        sseClient.disconnect();
        sseClient = null;
      }
      isConnected.value = false;
      isStreaming.value = false;
    };

    // 生命周期
    onMounted(() => {
      if (props.autoConnect) {
        connect();
      }
    });

    onUnmounted(() => {
      disconnect();
    });

    return {
      isConnected,
      isStreaming,
      fullText,
      progress,
      error,
      logs,
      statusClass,
      statusText,
      connect,
      disconnect,
      clearLogs
    };
  }
};
</script>

<style scoped>
.sse-stream-viewer {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  padding: 1rem;
  background: white;
  border-radius: 0.5rem;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

/* 状态栏 */
.status-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.75rem 1rem;
  border-radius: 0.375rem;
  transition: all 0.3s;
}

.status-bar.status-connected {
  background: #d1fae5;
  border: 1px solid #10b981;
}

.status-bar.status-disconnected {
  background: #f3f4f6;
  border: 1px solid #d1d5db;
}

.status-bar.status-error {
  background: #fee2e2;
  border: 1px solid #ef4444;
}

.status-indicator {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.status-dot {
  width: 0.75rem;
  height: 0.75rem;
  border-radius: 50%;
  background: #9ca3af;
  transition: all 0.3s;
}

.status-dot.active {
  background: #10b981;
  animation: pulse 2s infinite;
}

@keyframes pulse {
  0%, 100% {
    opacity: 1;
  }
  50% {
    opacity: 0.5;
  }
}

.status-text {
  font-weight: 500;
  color: #374151;
}

/* 进度条 */
.progress-bar {
  height: 2rem;
  background: #f3f4f6;
  border-radius: 0.375rem;
  overflow: hidden;
  position: relative;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #3b82f6, #8b5cf6);
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  font-weight: 600;
  transition: width 0.3s ease;
}

/* 内容查看器 */
.content-viewer {
  border: 1px solid #e5e7eb;
  border-radius: 0.375rem;
  overflow: hidden;
}

.content-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.75rem 1rem;
  background: #f9fafb;
  border-bottom: 1px solid #e5e7eb;
}

.content-header h3 {
  margin: 0;
  font-size: 1rem;
  font-weight: 600;
  color: #111827;
}

.streaming-indicator {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  color: #6b7280;
  font-size: 0.875rem;
}

.content-body {
  padding: 1rem;
  min-height: 200px;
  max-height: 400px;
  overflow-y: auto;
}

.content-body pre {
  margin: 0;
  white-space: pre-wrap;
  word-wrap: break-word;
  font-family: 'Courier New', monospace;
  font-size: 0.875rem;
  line-height: 1.5;
  color: #111827;
}

.empty-state {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 200px;
  color: #9ca3af;
  font-style: italic;
}

/* 消息日志 */
.message-logs {
  border: 1px solid #e5e7eb;
  border-radius: 0.375rem;
  overflow: hidden;
}

.logs-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.75rem 1rem;
  background: #f9fafb;
  border-bottom: 1px solid #e5e7eb;
}

.logs-header h4 {
  margin: 0;
  font-size: 0.875rem;
  font-weight: 600;
  color: #111827;
}

.logs-body {
  max-height: 300px;
  overflow-y: auto;
  padding: 0.5rem;
}

.log-item {
  display: flex;
  gap: 0.5rem;
  padding: 0.5rem;
  font-size: 0.75rem;
  border-radius: 0.25rem;
  margin-bottom: 0.25rem;
}

.log-item:hover {
  background: #f9fafb;
}

.log-time {
  color: #9ca3af;
  min-width: 80px;
}

.log-type {
  font-weight: 600;
  min-width: 100px;
}

.log-connected .log-type { color: #10b981; }
.log-token .log-type { color: #3b82f6; }
.log-stage_update .log-type { color: #8b5cf6; }
.log-progress .log-type { color: #f59e0b; }
.log-done .log-type { color: #10b981; }
.log-error .log-type { color: #ef4444; }
.log-stream_end .log-type { color: #6b7280; }

.log-message {
  color: #374151;
  flex: 1;
}
</style>

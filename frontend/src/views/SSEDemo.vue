<template>
  <div class="sse-demo-page">
    <div class="page-header">
      <h1>SSE流式输出演示</h1>
      <p>基于Redis Pub/Sub的实时流式数据传输</p>
    </div>

    <div class="demo-grid">
      <!-- 单个阶段订阅 -->
      <div class="demo-card">
        <div class="card-header">
          <h2>单个阶段订阅</h2>
          <p>订阅项目的指定阶段</p>
        </div>
        <div class="card-body">
          <div class="form-group">
            <label>项目ID</label>
            <input
              v-model="singleStageConfig.projectId"
              type="text"
              class="input input-bordered w-full"
              placeholder="输入项目ID"
            />
          </div>
          <div class="form-group">
            <label>阶段名称</label>
            <select v-model="singleStageConfig.stageName" class="select select-bordered w-full">
              <option value="rewrite">文案改写</option>
              <option value="storyboard">分镜生成</option>
              <option value="image_generation">文生图</option>
              <option value="camera_movement">运镜生成</option>
              <option value="video_generation">图生视频</option>
            </select>
          </div>
          <SSEStreamViewer
            v-if="singleStageConfig.projectId"
            :project-id="singleStageConfig.projectId"
            :stage-name="singleStageConfig.stageName"
            :show-logs="true"
            @connected="onConnected"
            @token="onToken"
            @progress="onProgress"
            @done="onDone"
            @error="onError"
          />
        </div>
      </div>

      <!-- 所有阶段订阅 -->
      <div class="demo-card">
        <div class="card-header">
          <h2>所有阶段订阅</h2>
          <p>订阅项目的所有阶段消息</p>
        </div>
        <div class="card-body">
          <div class="form-group">
            <label>项目ID</label>
            <input
              v-model="allStagesConfig.projectId"
              type="text"
              class="input input-bordered w-full"
              placeholder="输入项目ID"
            />
          </div>
          <SSEStreamViewer
            v-if="allStagesConfig.projectId"
            :project-id="allStagesConfig.projectId"
            :stage-name="null"
            :show-logs="true"
            @connected="onConnected"
            @token="onToken"
            @progress="onProgress"
            @done="onDone"
            @error="onError"
          />
        </div>
      </div>
    </div>

    <!-- 事件日志 -->
    <div class="event-log-card">
      <div class="card-header">
        <h2>事件日志</h2>
        <button @click="clearEventLog" class="btn btn-sm btn-ghost">清空</button>
      </div>
      <div class="card-body">
        <div class="event-log">
          <div v-for="(event, index) in eventLog" :key="index" class="event-item" :class="`event-${event.type}`">
            <span class="event-time">{{ event.time }}</span>
            <span class="event-type">{{ event.type }}</span>
            <span class="event-data">{{ event.data }}</span>
          </div>
          <div v-if="eventLog.length === 0" class="empty-log">
            暂无事件
          </div>
        </div>
      </div>
    </div>

    <!-- 使用说明 -->
    <div class="usage-card">
      <div class="card-header">
        <h2>使用说明</h2>
      </div>
      <div class="card-body">
        <div class="usage-steps">
          <div class="step">
            <div class="step-number">1</div>
            <div class="step-content">
              <h3>启动Redis服务</h3>
              <code>redis-server</code>
            </div>
          </div>
          <div class="step">
            <div class="step-number">2</div>
            <div class="step-content">
              <h3>启动Celery Worker</h3>
              <code>cd backend && celery -A config worker -Q llm,image,video -l info</code>
            </div>
          </div>
          <div class="step">
            <div class="step-number">3</div>
            <div class="step-content">
              <h3>启动Django服务器 (ASGI)</h3>
              <code>cd backend && daphne -b 0.0.0.0 -p 8000 config.asgi:application</code>
            </div>
          </div>
          <div class="step">
            <div class="step-number">4</div>
            <div class="step-content">
              <h3>创建项目并执行阶段</h3>
              <code>POST /api/v1/projects/{id}/execute_stage/</code>
            </div>
          </div>
          <div class="step">
            <div class="step-number">5</div>
            <div class="step-content">
              <h3>在此页面输入项目ID并连接</h3>
              <p>实时查看生成进度和结果</p>
            </div>
          </div>
        </div>

        <div class="api-endpoints">
          <h3>API端点</h3>
          <ul>
            <li>
              <code>GET /api/v1/sse/projects/{project_id}/stages/{stage_name}/</code>
              <span>订阅单个阶段 (无认证)</span>
            </li>
            <li>
              <code>GET /api/v1/sse/projects/{project_id}/</code>
              <span>订阅所有阶段 (无认证)</span>
            </li>
            <li>
              <code>GET /api/v1/sse/projects/{project_id}/stages/{stage_name}/stream/</code>
              <span>订阅单个阶段 (需认证)</span>
            </li>
            <li>
              <code>GET /api/v1/sse/projects/{project_id}/stream/</code>
              <span>订阅所有阶段 (需认证)</span>
            </li>
          </ul>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { ref } from 'vue';
import SSEStreamViewer from '@/components/SSEStreamViewer.vue';

export default {
  name: 'SSEDemo',
  components: {
    SSEStreamViewer
  },
  setup() {
    // 配置
    const singleStageConfig = ref({
      projectId: '',
      stageName: 'rewrite'
    });

    const allStagesConfig = ref({
      projectId: ''
    });

    // 事件日志
    const eventLog = ref([]);

    // 添加事件日志
    const addEventLog = (type, data) => {
      const time = new Date().toLocaleTimeString();
      eventLog.value.unshift({ type, data: JSON.stringify(data), time });
      // 限制日志数量
      if (eventLog.value.length > 50) {
        eventLog.value.pop();
      }
    };

    // 清空事件日志
    const clearEventLog = () => {
      eventLog.value = [];
    };

    // 事件处理器
    const onConnected = (data) => {
      addEventLog('connected', data);
      console.log('SSE已连接:', data);
    };

    const onToken = (data) => {
      addEventLog('token', { content: data.content });
      console.log('Token:', data.content);
    };

    const onProgress = (data) => {
      addEventLog('progress', { progress: data.progress });
      console.log('进度:', data.progress);
    };

    const onDone = (data) => {
      addEventLog('done', { message: '生成完成' });
      console.log('完成:', data);
    };

    const onError = (data) => {
      addEventLog('error', { error: data.error });
      console.error('错误:', data.error);
    };

    return {
      singleStageConfig,
      allStagesConfig,
      eventLog,
      clearEventLog,
      onConnected,
      onToken,
      onProgress,
      onDone,
      onError
    };
  }
};
</script>

<style scoped>
.sse-demo-page {
  padding: 2rem;
  max-width: 1400px;
  margin: 0 auto;
}

.page-header {
  margin-bottom: 2rem;
}

.page-header h1 {
  font-size: 2rem;
  font-weight: 700;
  color: #111827;
  margin-bottom: 0.5rem;
}

.page-header p {
  color: #6b7280;
  font-size: 1rem;
}

.demo-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(500px, 1fr));
  gap: 1.5rem;
  margin-bottom: 1.5rem;
}

.demo-card,
.event-log-card,
.usage-card {
  background: white;
  border-radius: 0.5rem;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  overflow: hidden;
}

.card-header {
  padding: 1.5rem;
  border-bottom: 1px solid #e5e7eb;
}

.card-header h2 {
  font-size: 1.25rem;
  font-weight: 600;
  color: #111827;
  margin-bottom: 0.25rem;
}

.card-header p {
  color: #6b7280;
  font-size: 0.875rem;
  margin: 0;
}

.card-body {
  padding: 1.5rem;
}

.form-group {
  margin-bottom: 1rem;
}

.form-group label {
  display: block;
  font-weight: 500;
  color: #374151;
  margin-bottom: 0.5rem;
  font-size: 0.875rem;
}

/* 事件日志 */
.event-log {
  max-height: 400px;
  overflow-y: auto;
  font-family: 'Courier New', monospace;
  font-size: 0.75rem;
}

.event-item {
  display: flex;
  gap: 0.75rem;
  padding: 0.5rem;
  border-bottom: 1px solid #f3f4f6;
}

.event-time {
  color: #9ca3af;
  min-width: 80px;
}

.event-type {
  font-weight: 600;
  min-width: 100px;
}

.event-connected .event-type { color: #10b981; }
.event-token .event-type { color: #3b82f6; }
.event-progress .event-type { color: #f59e0b; }
.event-done .event-type { color: #10b981; }
.event-error .event-type { color: #ef4444; }

.event-data {
  color: #374151;
  flex: 1;
  word-break: break-all;
}

.empty-log {
  text-align: center;
  padding: 2rem;
  color: #9ca3af;
  font-style: italic;
}

/* 使用说明 */
.usage-steps {
  margin-bottom: 2rem;
}

.step {
  display: flex;
  gap: 1rem;
  margin-bottom: 1.5rem;
}

.step-number {
  width: 2rem;
  height: 2rem;
  border-radius: 50%;
  background: #3b82f6;
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 600;
  flex-shrink: 0;
}

.step-content h3 {
  font-size: 1rem;
  font-weight: 600;
  color: #111827;
  margin-bottom: 0.5rem;
}

.step-content code {
  display: block;
  padding: 0.5rem;
  background: #f3f4f6;
  border-radius: 0.25rem;
  font-size: 0.875rem;
  color: #1f2937;
  overflow-x: auto;
}

.step-content p {
  color: #6b7280;
  font-size: 0.875rem;
  margin: 0;
}

.api-endpoints h3 {
  font-size: 1rem;
  font-weight: 600;
  color: #111827;
  margin-bottom: 1rem;
}

.api-endpoints ul {
  list-style: none;
  padding: 0;
  margin: 0;
}

.api-endpoints li {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  padding: 0.75rem;
  background: #f9fafb;
  border-radius: 0.25rem;
  margin-bottom: 0.5rem;
}

.api-endpoints code {
  font-size: 0.875rem;
  color: #3b82f6;
  font-weight: 500;
}

.api-endpoints span {
  font-size: 0.75rem;
  color: #6b7280;
}
</style>

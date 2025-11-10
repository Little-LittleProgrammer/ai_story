# 前端 API 迁移指南

## 📋 变更概述

后端 API 已从独立的 `rewrite_stream` 端点迁移到统一的 `execute-stage` 端点，并支持两种模式：

1. **Celery异步模式** (推荐) - 通过WebSocket接收实时进度
2. **SSE流式模式** (兼容) - 保留旧的EventSource行为

---

## 🔄 API 变更

### 旧接口 (已废弃)
```javascript
POST /api/v1/projects/projects/{projectId}/rewrite_stream/
Body: { input_data: {...} }
```

### 新接口 (统一)
```javascript
POST /api/v1/projects/projects/{projectId}/execute-stage/
Body: {
  stage_name: "rewrite",  // 阶段名称
  input_data: {...},
  use_streaming: true     // 可选，启用SSE模式
}
```

---

## 🚀 迁移步骤

### 步骤1: 更新 SSE 客户端 (已完成)

**文件**: `src/utils/sseClient.js`

#### 旧代码
```javascript
export function createStageStreamClient(projectId, stageType, inputData = {}) {
  const url = `/api/v1/projects/projects/${projectId}/rewrite_stream/`;
  // ...
  body: JSON.stringify({ input_data: inputData })
}
```

#### 新代码
```javascript
export function createStageStreamClient(projectId, stageName, inputData = {}, useStreaming = true) {
  const url = `/api/v1/projects/projects/${projectId}/execute-stage/`;
  // ...
  body: JSON.stringify({
    stage_name: stageName,
    input_data: inputData,
    use_streaming: useStreaming
  })
}
```

### 步骤2: 更新组件调用 (已完成)

**文件**: `src/components/projects/StageContent.vue`

#### 旧代码
```javascript
this.sseClient = createStageStreamClient(
  this.projectId,
  'rewrite',  // 硬编码
  JSON.parse(inputText)
);
```

#### 新代码
```javascript
this.sseClient = createStageStreamClient(
  this.projectId,
  this.stageType,  // 使用动态阶段类型
  JSON.parse(inputText),
  true  // 启用SSE流式模式
);
```

### 步骤3: 添加 WebSocket 客户端 (新增)

**文件**: `src/utils/wsClient.js` (已创建)

用于 Celery 异步模式的 WebSocket 连接。

---

## 📡 使用方式

### 方式1: SSE 流式模式 (兼容旧代码)

```javascript
import { createStageStreamClient } from '@/utils/sseClient';

// 创建SSE客户端
const client = createStageStreamClient(
  projectId,
  'rewrite',
  { original_text: '...' },
  true  // 启用SSE模式
);

// 监听事件
client.on('token', (data) => {
  console.log('Token:', data.content);
  this.outputText = data.full_text;
});

client.on('done', (data) => {
  console.log('完成:', data.full_text);
  client.disconnect();
});

client.on('error', (data) => {
  console.error('错误:', data.error);
});
```

### 方式2: WebSocket 模式 (推荐)

```javascript
import { createStageWSClient } from '@/utils/wsClient';
import api from '@/api';

// 1. 启动Celery任务
const response = await api.projects.executeStage(projectId, {
  stage_name: 'rewrite',
  input_data: { original_text: '...' }
  // use_streaming 默认为 false，使用Celery模式
});

const { task_id, channel } = response.data;

// 2. 连接WebSocket订阅进度
const wsClient = createStageWSClient(projectId, 'rewrite');

wsClient.on('connected', () => {
  console.log('WebSocket已连接');
});

wsClient.on('token', (data) => {
  console.log('Token:', data.content);
  this.outputText = data.full_text;
});

wsClient.on('done', (data) => {
  console.log('完成:', data.full_text);
  wsClient.disconnect();
});

wsClient.on('error', (data) => {
  console.error('错误:', data.error);
});
```

---

## 🔧 API 服务层更新

### 添加新的 API 方法

**文件**: `src/api/projects.js`

```javascript
export default {
  // 执行阶段 (Celery异步模式)
  executeStage(projectId, data) {
    return request({
      url: `/projects/projects/${projectId}/execute-stage/`,
      method: 'post',
      data: {
        stage_name: data.stage_name,
        input_data: data.input_data,
        use_streaming: false  // 使用Celery模式
      }
    });
  },

  // 查询任务状态
  getTaskStatus(projectId, taskId) {
    return request({
      url: `/projects/projects/${projectId}/task-status/`,
      method: 'get',
      params: { task_id: taskId }
    });
  },

  // 执行阶段 (SSE流式模式) - 兼容旧代码
  executeStageStreaming(projectId, data) {
    // 使用 createStageStreamClient 处理
    // 不需要单独的API方法
  }
};
```

---

## 📊 功能对比

| 特性 | SSE模式 | WebSocket模式 |
|------|---------|--------------|
| 实时性 | 高 | 高 |
| 连接方式 | HTTP长连接 | WebSocket |
| 重连机制 | 手动 | 自动 |
| 心跳检测 | 无 | 有 |
| 并发支持 | 受限 | 优秀 |
| 服务器负载 | 较高 | 较低 |
| 浏览器兼容 | 所有现代浏览器 | 所有现代浏览器 |
| 推荐场景 | 开发调试 | 生产环境 |

---

## 🎯 完整示例

### 示例1: 在 Vue 组件中使用 SSE 模式

```vue
<template>
  <div>
    <textarea v-model="inputText"></textarea>
    <button @click="executeWithSSE" :disabled="isProcessing">
      执行 (SSE模式)
    </button>
    <div>{{ outputText }}</div>
  </div>
</template>

<script>
import { createStageStreamClient } from '@/utils/sseClient';

export default {
  data() {
    return {
      inputText: '',
      outputText: '',
      isProcessing: false,
      sseClient: null
    };
  },

  methods: {
    executeWithSSE() {
      this.isProcessing = true;
      this.outputText = '';

      // 创建SSE客户端
      this.sseClient = createStageStreamClient(
        this.projectId,
        'rewrite',
        { original_text: this.inputText },
        true  // 启用SSE模式
      );

      // 监听事件
      this.sseClient.on('token', (data) => {
        this.outputText = data.full_text;
      });

      this.sseClient.on('done', (data) => {
        this.outputText = data.full_text;
        this.isProcessing = false;
        this.$message.success('完成');
        this.sseClient.disconnect();
      });

      this.sseClient.on('error', (data) => {
        this.isProcessing = false;
        this.$message.error(data.error);
        this.sseClient.disconnect();
      });
    }
  },

  beforeDestroy() {
    if (this.sseClient) {
      this.sseClient.disconnect();
    }
  }
};
</script>
```

### 示例2: 在 Vue 组件中使用 WebSocket 模式

```vue
<template>
  <div>
    <textarea v-model="inputText"></textarea>
    <button @click="executeWithWS" :disabled="isProcessing">
      执行 (WebSocket模式)
    </button>
    <div>{{ outputText }}</div>
    <div>任务ID: {{ taskId }}</div>
  </div>
</template>

<script>
import { createStageWSClient } from '@/utils/wsClient';
import api from '@/api';

export default {
  data() {
    return {
      inputText: '',
      outputText: '',
      isProcessing: false,
      taskId: null,
      wsClient: null
    };
  },

  methods: {
    async executeWithWS() {
      this.isProcessing = true;
      this.outputText = '';

      try {
        // 1. 启动Celery任务
        const response = await api.projects.executeStage(this.projectId, {
          stage_name: 'rewrite',
          input_data: { original_text: this.inputText }
        });

        this.taskId = response.data.task_id;
        const channel = response.data.channel;

        // 2. 连接WebSocket
        this.wsClient = createStageWSClient(this.projectId, 'rewrite');

        this.wsClient.on('connected', () => {
          this.$message.info('已连接到实时流');
        });

        this.wsClient.on('token', (data) => {
          this.outputText = data.full_text;
        });

        this.wsClient.on('done', (data) => {
          this.outputText = data.full_text;
          this.isProcessing = false;
          this.$message.success('完成');
          this.wsClient.disconnect();
        });

        this.wsClient.on('error', (data) => {
          this.isProcessing = false;
          this.$message.error(data.error);
          this.wsClient.disconnect();
        });

      } catch (error) {
        this.isProcessing = false;
        this.$message.error('启动任务失败: ' + error.message);
      }
    }
  },

  beforeDestroy() {
    if (this.wsClient) {
      this.wsClient.disconnect();
    }
  }
};
</script>
```

---

## ⚠️ 注意事项

### 1. 阶段名称映射

确保使用正确的阶段名称：

| 前端显示 | API参数 |
|---------|---------|
| 文案改写 | `rewrite` |
| 分镜生成 | `storyboard` |
| 文生图 | `image_generation` |
| 运镜生成 | `camera_movement` |
| 图生视频 | `video_generation` |

### 2. WebSocket URL

WebSocket URL 格式：
```
ws://localhost:8000/ws/projects/{project_id}/stage/{stage_name}/
```

生产环境使用 `wss://` 协议。

### 3. 错误处理

两种模式都需要处理以下错误：
- 连接失败
- 任务执行失败
- 超时
- 网络中断

### 4. 资源清理

组件销毁时务必断开连接：
```javascript
beforeDestroy() {
  if (this.sseClient) {
    this.sseClient.disconnect();
  }
  if (this.wsClient) {
    this.wsClient.disconnect();
  }
}
```

---

## 🔍 调试技巧

### 1. 查看 WebSocket 连接

Chrome DevTools → Network → WS 标签

### 2. 查看 SSE 连接

Chrome DevTools → Network → EventStream 类型

### 3. 控制台日志

两个客户端都会输出详细的日志：
```javascript
[WebSocket] 连接到: ws://localhost:8000/ws/projects/xxx/stage/rewrite/
[WebSocket] 收到消息: {type: "token", content: "..."}
```

---

## 📚 相关文档

- [后端 API 迁移指南](../backend/API_MIGRATION_GUIDE.md)
- [Celery + Redis 架构文档](../backend/CELERY_REDIS_STREAMING.md)
- [WebSocket API 文档](https://developer.mozilla.org/en-US/docs/Web/API/WebSocket)

---

**最后更新**: 2025-11-03

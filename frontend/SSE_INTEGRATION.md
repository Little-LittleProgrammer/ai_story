# SSE 流式接口集成文档

## 概述

本文档说明如何在前端使用 SSE (Server-Sent Events) 接口对接后端的 `ProjectStageSSEView`。

## 后端接口

### 1. 单阶段 SSE 流

**接口地址:** `GET /api/v1/sse/projects/{project_id}/stages/{stage_name}/`

**参数:**
- `project_id`: 项目ID
- `stage_name`: 阶段名称
  - `rewrite` - 文案改写
  - `storyboard` - 分镜生成
  - `image_generation` - 文生图
  - `camera_movement` - 运镜生成
  - `video_generation` - 图生视频

**示例:**
```
GET http://localhost:8000/api/v1/sse/projects/123/stages/rewrite/
```

### 2. 所有阶段 SSE 流

**接口地址:** `GET /api/v1/sse/projects/{project_id}/`

**参数:**
- `project_id`: 项目ID

**示例:**
```
GET http://localhost:8000/api/v1/sse/projects/123/
```

## SSE 消息格式

所有 SSE 消息都遵循以下格式:

```
data: {"type": "...", ...}

```

### 消息类型

| 类型 | 说明 | 数据字段 |
|------|------|----------|
| `connected` | 连接成功 | `project_id`, `stage`, `message` |
| `token` | LLM 流式输出的 token | `content`, `full_text` |
| `stage_update` | 阶段状态更新 | `stage`, `status`, `progress` |
| `progress` | 进度更新 | `progress`, `message` |
| `done` | 阶段完成 | `stage`, `result`, `full_text` |
| `error` | 错误 | `error`, `project_id` |
| `stream_end` | 流结束 | `project_id`, `message` |

## 前端使用方法

### 方法 1: 使用 SSE 服务类

```javascript
import { createProjectStageSSE, SSE_EVENT_TYPES } from '@/services/sseService';

// 创建 SSE 客户端
const client = createProjectStageSSE('project-123', 'rewrite', {
  autoReconnect: true, // 自动重连
});

// 监听事件
client
  .on(SSE_EVENT_TYPES.CONNECTED, (data) => {
    console.log('连接成功:', data);
  })
  .on(SSE_EVENT_TYPES.TOKEN, (data) => {
    console.log('收到 token:', data.content);
    console.log('完整文本:', data.full_text);
  })
  .on(SSE_EVENT_TYPES.PROGRESS, (data) => {
    console.log('进度:', data.progress);
  })
  .on(SSE_EVENT_TYPES.DONE, (data) => {
    console.log('完成:', data);
  })
  .on(SSE_EVENT_TYPES.ERROR, (data) => {
    console.error('错误:', data.error);
  });

// 断开连接
client.disconnect();
```

### 方法 2: 使用 Vue Mixin

```vue
<template>
  <div>
    <div v-if="sseConnected">已连接</div>
    <div v-if="sseError">错误: {{ sseError }}</div>
    <div v-for="msg in sseMessages" :key="msg.id">
      {{ msg.type }}: {{ msg.content }}
    </div>
  </div>
</template>

<script>
import { sseClientMixin } from '@/services/sseService';

export default {
  mixins: [sseClientMixin],
  data() {
    return {
      projectId: 'project-123',
      stageName: 'rewrite',
    };
  },
  mounted() {
    // 连接 SSE
    this.connectSSE(this.projectId, this.stageName, {
      autoReconnect: true,
    });
  },
  methods: {
    // 可选: 实现事件处理方法
    onSSEConnected(data) {
      console.log('连接成功:', data);
    },
    onSSEToken(data) {
      console.log('收到 token:', data);
    },
    onSSEProgress(data) {
      console.log('进度:', data.progress);
    },
    onSSEDone(data) {
      console.log('完成:', data);
    },
    onSSEError(data) {
      console.error('错误:', data);
    },
  },
};
</script>
```

### 方法 3: 使用示例组件

直接使用封装好的 `ProjectStageSSE` 组件:

```vue
<template>
  <div>
    <ProjectStageSSE
      :initial-project-id="projectId"
      :initial-stage-name="stageName"
    />
  </div>
</template>

<script>
import ProjectStageSSE from '@/components/ProjectStageSSE.vue';

export default {
  components: {
    ProjectStageSSE,
  },
  data() {
    return {
      projectId: 'project-123',
      stageName: 'rewrite',
    };
  },
};
</script>
```

## 完整示例: 实时显示文案改写进度

```vue
<template>
  <div class="rewrite-progress">
    <div class="card bg-base-100 shadow-xl">
      <div class="card-body">
        <h2 class="card-title">文案改写中...</h2>

        <!-- 进度条 -->
        <progress
          v-if="progress < 100"
          class="progress progress-primary"
          :value="progress"
          max="100"
        ></progress>

        <!-- 实时文本 -->
        <div class="bg-base-200 p-4 rounded-lg">
          <p class="whitespace-pre-wrap">{{ fullText }}</p>
        </div>

        <!-- 状态 -->
        <div class="alert" :class="statusClass">
          <span>{{ statusMessage }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { createProjectStageSSE, SSE_EVENT_TYPES } from '@/services/sseService';

export default {
  name: 'RewriteProgress',
  props: {
    projectId: {
      type: String,
      required: true,
    },
  },
  data() {
    return {
      sseClient: null,
      fullText: '',
      progress: 0,
      status: 'connecting', // connecting, processing, done, error
      errorMessage: '',
    };
  },
  computed: {
    statusMessage() {
      const messages = {
        connecting: '正在连接...',
        processing: '正在生成...',
        done: '生成完成!',
        error: `错误: ${this.errorMessage}`,
      };
      return messages[this.status] || '';
    },
    statusClass() {
      const classes = {
        connecting: 'alert-info',
        processing: 'alert-warning',
        done: 'alert-success',
        error: 'alert-error',
      };
      return classes[this.status] || 'alert-info';
    },
  },
  mounted() {
    this.connectSSE();
  },
  methods: {
    connectSSE() {
      // 创建 SSE 客户端
      this.sseClient = createProjectStageSSE(this.projectId, 'rewrite');

      // 监听事件
      this.sseClient
        .on(SSE_EVENT_TYPES.CONNECTED, () => {
          this.status = 'processing';
        })
        .on(SSE_EVENT_TYPES.TOKEN, (data) => {
          // 实时更新文本
          this.fullText = data.full_text || '';
        })
        .on(SSE_EVENT_TYPES.PROGRESS, (data) => {
          // 更新进度
          this.progress = data.progress || 0;
        })
        .on(SSE_EVENT_TYPES.DONE, (data) => {
          // 完成
          this.status = 'done';
          this.fullText = data.full_text || data.result || '';
          this.progress = 100;
        })
        .on(SSE_EVENT_TYPES.ERROR, (data) => {
          // 错误
          this.status = 'error';
          this.errorMessage = data.error || '未知错误';
        });
    },
  },
  beforeDestroy() {
    // 组件销毁时断开连接
    if (this.sseClient) {
      this.sseClient.disconnect();
    }
  },
};
</script>
```

## 注意事项

### 1. CORS 配置

后端已配置 CORS 支持:
```python
response['Access-Control-Allow-Origin'] = '*'
response['Access-Control-Allow-Methods'] = 'GET'
response['Access-Control-Allow-Headers'] = 'Content-Type'
```

### 2. 连接超时

- 单阶段 SSE: 默认 10 分钟超时
- 所有阶段 SSE: 默认 30 分钟超时

### 3. 自动重连

SSE 服务支持自动重连功能:
```javascript
const client = createProjectStageSSE('project-123', 'rewrite', {
  autoReconnect: true, // 启用自动重连
});
```

默认重连策略:
- 最大重连次数: 3 次
- 重连延迟: 1秒、2秒、3秒 (递增)

### 4. 环境变量配置

确保在 `.env` 文件中配置正确的 API 地址:

```bash
# .env.development
VUE_APP_API_BASE_URL=http://localhost:8000

# .env.production
VUE_APP_API_BASE_URL=https://your-production-domain.com
```

### 5. 浏览器兼容性

SSE (EventSource) 支持所有现代浏览器:
- Chrome 6+
- Firefox 6+
- Safari 5+
- Edge 79+

**不支持 IE**

## 测试

### 1. 启动后端服务

```bash
cd backend

# 启动 Redis
brew services start redis  # macOS
# 或 docker run -d -p 6379:6379 redis:latest

# 启动 ASGI 服务器 (支持 SSE)
./run_asgi.sh
# 或 daphne -b 0.0.0.0 -p 8000 config.asgi:application

# 启动 Celery Worker
uv run celery -A config worker -Q llm,image,video -l info
```

### 2. 启动前端服务

```bash
cd frontend
npm run dev
```

### 3. 访问测试页面

在浏览器中访问:
```
http://localhost:3000/sse-demo
```

或在任何页面中使用 `ProjectStageSSE` 组件。

## 故障排查

### 问题 1: 连接失败

**检查项:**
1. 后端服务是否启动 (ASGI 模式)
2. Redis 是否运行
3. CORS 配置是否正确
4. 项目 ID 是否存在

### 问题 2: 收不到消息

**检查项:**
1. Celery Worker 是否启动
2. 后端是否正确发布 Redis 消息
3. 浏览器控制台是否有错误

### 问题 3: 消息解析失败

**检查项:**
1. 后端返回的消息格式是否正确
2. 是否是有效的 JSON
3. 查看浏览器控制台的详细错误信息

## API 参考

### SSEClient 类

#### 方法

- `connect(url, options)` - 连接到 SSE 端点
- `on(event, handler)` - 监听事件
- `off(event, handler)` - 移除事件监听
- `disconnect()` - 断开连接
- `isConnected()` - 检查连接状态
- `getReadyState()` - 获取连接状态码

#### 事件

- `open` - 连接打开
- `close` - 连接关闭
- `error` - 连接错误
- `parse_error` - 消息解析错误
- `message` - 收到消息 (通用)
- `connected` - 业务: 连接成功
- `token` - 业务: LLM token
- `stage_update` - 业务: 阶段更新
- `progress` - 业务: 进度更新
- `done` - 业务: 完成
- `stream_end` - 业务: 流结束

### 工具函数

- `createProjectStageSSE(projectId, stageName, options)` - 创建单阶段 SSE 客户端
- `createProjectAllStagesSSE(projectId, options)` - 创建所有阶段 SSE 客户端

### Vue Mixin

- `sseClientMixin` - Vue 2 Mixin，提供 SSE 功能

#### Mixin 数据

- `sseClient` - SSE 客户端实例
- `sseConnected` - 连接状态
- `sseMessages` - 消息列表
- `sseError` - 错误信息

#### Mixin 方法

- `connectSSE(projectId, stageName, options)` - 连接 SSE
- `disconnectSSE()` - 断开连接
- `clearSSEMessages()` - 清空消息

#### Mixin 钩子 (可选实现)

- `onSSEOpen()` - 连接打开
- `onSSEMessage(data)` - 收到消息
- `onSSEConnected(data)` - 连接成功
- `onSSEToken(data)` - 收到 token
- `onSSEStageUpdate(data)` - 阶段更新
- `onSSEProgress(data)` - 进度更新
- `onSSEDone(data)` - 完成
- `onSSEError(data)` - 错误
- `onSSEClose()` - 连接关闭

## 相关文件

### 后端

- [backend/apps/projects/sse_views.py](../backend/apps/projects/sse_views.py) - SSE 视图
- [backend/apps/projects/urls.py](../backend/apps/projects/urls.py) - URL 配置
- [backend/core/redis/subscriber.py](../backend/core/redis/subscriber.py) - Redis 订阅器
- [backend/core/redis/publisher.py](../backend/core/redis/publisher.py) - Redis 发布器

### 前端

- [frontend/src/services/sseService.js](./src/services/sseService.js) - SSE 服务
- [frontend/src/components/ProjectStageSSE.vue](./src/components/ProjectStageSSE.vue) - SSE 示例组件

## 更多信息

详细的 Celery + Redis + SSE 架构说明，请参考:
- [backend/CELERY_REDIS_STREAMING.md](../backend/CELERY_REDIS_STREAMING.md)

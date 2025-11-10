# SSE流式系统实现文档

## 概述

基于Redis Pub/Sub的Server-Sent Events (SSE)流式数据传输系统，用于实时推送AI生成任务的进度和结果。

## 架构图

```
┌─────────────────┐      ┌──────────────┐      ┌─────────────────┐
│  Celery任务     │─────▶│ Redis Pub/Sub│─────▶│ SSE视图         │
│  (发布器)       │      │              │      │ (订阅器)        │
└─────────────────┘      └──────────────┘      └─────────────────┘
                                                         │
                                                         ▼
                                                ┌─────────────────┐
                                                │  前端EventSource│
                                                │  (接收实时数据) │
                                                └─────────────────┘
```

## 已实现的组件

### 后端组件

#### 1. RedisStreamPublisher (发布器)
**文件**: `backend/core/redis/publisher.py`

**职责**: 在Celery任务中发布流式数据到Redis频道

**核心方法**:
- `publish_token()` - 发布流式文本片段
- `publish_stage_update()` - 发布阶段状态更新
- `publish_progress()` - 发布批量处理进度
- `publish_done()` - 发布完成消息
- `publish_error()` - 发布错误消息

**使用示例**:
```python
from core.redis import RedisStreamPublisher

with RedisStreamPublisher(project_id, stage_name) as publisher:
    publisher.publish_token(content="Hello", full_text="Hello")
    publisher.publish_done(full_text="Hello World")
```

#### 2. RedisStreamSubscriber (接收器)
**文件**: `backend/core/redis/subscriber.py`

**职责**: 订阅Redis频道并接收流式数据

**核心方法**:
- `subscribe()` - 订阅频道
- `listen()` - 监听消息 (生成器)
- `get_message()` - 获取单条消息 (非阻塞)
- `unsubscribe()` - 取消订阅

**使用示例**:
```python
from core.redis import RedisStreamSubscriber

with RedisStreamSubscriber(project_id, stage_name) as subscriber:
    for message in subscriber.listen(timeout=300):
        print(f"收到消息: {message['type']}")
        if message['type'] == 'done':
            break
```

#### 3. SSE视图
**文件**: `backend/core/redis/sse_views.py`

**提供的API端点**:

| 端点 | 方法 | 说明 | 认证 |
|------|------|------|------|
| `/api/v1/sse/projects/{project_id}/stages/{stage_name}/` | GET | 订阅单个阶段 | 否 |
| `/api/v1/sse/projects/{project_id}/` | GET | 订阅所有阶段 | 否 |
| `/api/v1/sse/projects/{project_id}/stages/{stage_name}/stream/` | GET | 订阅单个阶段 | 是 |
| `/api/v1/sse/projects/{project_id}/stream/` | GET | 订阅所有阶段 | 是 |

**核心类**:
- `ProjectStageSSEView` - 单个阶段SSE视图
- `ProjectAllStagesSSEView` - 所有阶段SSE视图
- `project_stage_sse_stream()` - DRF函数视图 (带认证)
- `project_all_stages_sse_stream()` - DRF函数视图 (带认证)

### 前端组件

#### 1. SSEClient (客户端工具类)
**文件**: `frontend/src/utils/sse-client.js`

**职责**: 封装EventSource API，提供易用的SSE客户端

**核心方法**:
- `connect()` - 连接SSE流
- `disconnect()` - 断开连接
- `on()` - 注册事件处理器
- `off()` - 移除事件处理器
- `isConnected()` - 检查连接状态

**使用示例**:
```javascript
import { createSSEClient } from '@/utils/sse-client';

const client = createSSEClient(projectId, stageName);

client
  .on('connected', (data) => console.log('已连接'))
  .on('token', (data) => console.log('Token:', data.content))
  .on('done', (data) => console.log('完成'))
  .connect();
```

#### 2. SSEStreamViewer (Vue组件)
**文件**: `frontend/src/components/SSEStreamViewer.vue`

**职责**: 可复用的SSE流式内容查看器组件

**Props**:
- `projectId` - 项目ID (必需)
- `stageName` - 阶段名称 (可选，null表示订阅所有阶段)
- `autoConnect` - 是否自动连接 (默认false)
- `showLogs` - 是否显示消息日志 (默认false)

**Events**:
- `@connected` - 连接建立
- `@token` - 收到Token消息
- `@progress` - 收到进度消息
- `@done` - 生成完成
- `@error` - 发生错误
- `@disconnected` - 连接断开

**使用示例**:
```vue
<template>
  <SSEStreamViewer
    :project-id="projectId"
    :stage-name="stageName"
    :show-logs="true"
    @done="onDone"
  />
</template>

<script>
import SSEStreamViewer from '@/components/SSEStreamViewer.vue';

export default {
  components: { SSEStreamViewer },
  setup() {
    const onDone = (data) => {
      console.log('生成完成:', data.full_text);
    };
    return { onDone };
  }
};
</script>
```

#### 3. SSEDemo (演示页面)
**文件**: `frontend/src/views/SSEDemo.vue`

**职责**: SSE功能演示和测试页面

**功能**:
- 单个阶段订阅演示
- 所有阶段订阅演示
- 实时事件日志
- 使用说明和API文档

## 消息格式

### 1. Token消息 (流式文本)
```json
{
  "type": "token",
  "content": "这是",
  "full_text": "这是一段流式生成的文本这是",
  "stage": "rewrite",
  "project_id": "123",
  "timestamp": 1234567890.123
}
```

### 2. 阶段状态更新
```json
{
  "type": "stage_update",
  "stage": "rewrite",
  "status": "processing",
  "progress": 50,
  "message": "正在生成文案...",
  "project_id": "123",
  "timestamp": 1234567890.123
}
```

### 3. 进度消息
```json
{
  "type": "progress",
  "stage": "image_generation",
  "current": 3,
  "total": 10,
  "progress": 30,
  "item_name": "分镜3",
  "project_id": "123",
  "timestamp": 1234567890.123
}
```

### 4. 完成消息
```json
{
  "type": "done",
  "stage": "rewrite",
  "project_id": "123",
  "full_text": "完整的生成结果...",
  "metadata": {
    "tokens_used": 1000,
    "latency_ms": 2500
  },
  "timestamp": 1234567890.123
}
```

### 5. 错误消息
```json
{
  "type": "error",
  "stage": "rewrite",
  "project_id": "123",
  "error": "API调用失败: 超时",
  "retry_count": 1,
  "timestamp": 1234567890.123
}
```

## Redis频道命名规范

```
ai_story:project:{project_id}:stage:{stage_name}
```

**示例**:
- `ai_story:project:123:stage:rewrite` - 文案改写阶段
- `ai_story:project:123:stage:storyboard` - 分镜生成阶段
- `ai_story:project:123:stage:*` - 项目所有阶段 (模式匹配)

## 使用流程

### 1. 启动服务

```bash
# 1. 启动Redis
redis-server

# 2. 启动Celery Worker
cd backend
celery -A config worker -Q llm,image,video -l info

# 3. 启动Django服务器 (ASGI)
cd backend
daphne -b 0.0.0.0 -p 8000 config.asgi:application

# 4. 启动前端开发服务器
cd frontend
npm run dev
```

### 2. 执行任务

```bash
# 创建项目并执行阶段
POST /api/v1/projects/{id}/execute_stage/
{
  "stage_name": "rewrite",
  "input_data": {...}
}

# 返回
{
  "task_id": "celery-task-id",
  "channel": "ai_story:project:123:stage:rewrite",
  "message": "任务已启动"
}
```

### 3. 前端订阅

```javascript
// 方式1: 使用SSEClient
import { createSSEClient } from '@/utils/sse-client';

const client = createSSEClient(projectId, stageName);
client.on('token', (data) => {
  console.log('Token:', data.content);
});
client.connect();

// 方式2: 使用SSEStreamViewer组件
<SSEStreamViewer
  :project-id="projectId"
  :stage-name="stageName"
  @done="onDone"
/>
```

## 测试

### 后端测试

```bash
cd backend

# 运行测试脚本
python core/redis/test_sse.py
```

**测试内容**:
- 基本发布订阅
- 进度消息
- 错误处理
- 上下文管理器
- 订阅所有阶段

### 前端测试

1. 访问演示页面: `http://localhost:3000/sse-demo`
2. 输入项目ID和阶段名称
3. 点击"连接"按钮
4. 在后端执行任务，观察实时数据流

### 集成测试

```bash
# 1. 启动所有服务 (Redis, Celery, Django, Frontend)

# 2. 使用curl测试SSE接口
curl -N http://localhost:8000/api/v1/sse/projects/123/stages/rewrite/

# 3. 在另一个终端触发任务
curl -X POST http://localhost:8000/api/v1/projects/123/execute_stage/ \
  -H "Content-Type: application/json" \
  -d '{"stage_name": "rewrite", "input_data": {}}'

# 4. 观察第一个终端的SSE输出
```

## 部署注意事项

### 1. ASGI服务器

SSE需要ASGI服务器支持:

```bash
# 使用Daphne (推荐)
daphne -b 0.0.0.0 -p 8000 config.asgi:application

# 或使用Uvicorn
uvicorn config.asgi:application --host 0.0.0.0 --port 8000
```

### 2. Nginx配置

```nginx
location /api/v1/sse/ {
    proxy_pass http://backend:8000;
    proxy_http_version 1.1;
    proxy_set_header Connection "";
    proxy_buffering off;           # 禁用缓冲
    proxy_cache off;               # 禁用缓存
    proxy_read_timeout 600s;       # 增加超时时间
}
```

### 3. Redis配置

```bash
# redis.conf
# Pub/Sub不需要持久化
save ""
appendonly no

# 增加最大客户端连接数
maxclients 10000
```

### 4. 防火墙配置

确保以下端口开放:
- 8000 (Django)
- 6379 (Redis)
- 3000 (Frontend)

## 性能优化

### 1. 消息批量发送

```python
# 避免频繁发送小消息
buffer = []
for token in tokens:
    buffer.append(token)
    if len(buffer) >= 10:  # 每10个token发送一次
        publisher.publish_token(content=''.join(buffer))
        buffer = []
```

### 2. 连接池管理

```python
# 使用连接池
redis_pool = redis.ConnectionPool.from_url(
    redis_url,
    max_connections=50,
    decode_responses=True
)
redis_client = redis.Redis(connection_pool=redis_pool)
```

### 3. 超时控制

```python
# 设置合理的超时时间
subscriber.listen(timeout=300)  # 5分钟
```

## 故障排查

### 问题1: SSE连接立即断开

**原因**:
- ASGI服务器未运行
- Nginx缓冲未禁用
- 防火墙阻止连接

**解决**:
```bash
# 检查ASGI服务器
ps aux | grep daphne

# 检查Nginx配置
nginx -t

# 检查防火墙
sudo ufw status
```

### 问题2: 收不到消息

**原因**:
- Redis未启动
- 频道名称不匹配
- 发布器未正常工作

**解决**:
```bash
# 检查Redis
redis-cli ping

# 监控Redis频道
redis-cli psubscribe "ai_story:*"

# 查看订阅者数量
redis-cli pubsub numsub "ai_story:project:123:stage:rewrite"
```

### 问题3: 消息延迟

**原因**:
- 网络延迟
- Redis性能问题
- 消息发送频率过高

**解决**:
- 检查网络延迟
- 优化Redis配置
- 减少消息发送频率 (批量发送)

## 相关文档

- [Redis Pub/Sub README](backend/core/redis/README.md) - 详细使用文档
- [CELERY_REDIS_STREAMING.md](backend/CELERY_REDIS_STREAMING.md) - Celery + Redis架构文档
- [Django Channels文档](https://channels.readthedocs.io/)
- [Redis Pub/Sub文档](https://redis.io/docs/manual/pubsub/)
- [Server-Sent Events规范](https://html.spec.whatwg.org/multipage/server-sent-events.html)

## 文件清单

### 后端文件
- ✅ `backend/core/redis/publisher.py` - Redis发布器
- ✅ `backend/core/redis/subscriber.py` - Redis接收器
- ✅ `backend/core/redis/sse_views.py` - SSE视图
- ✅ `backend/core/redis/__init__.py` - 模块导出
- ✅ `backend/core/redis/README.md` - 详细文档
- ✅ `backend/core/redis/test_sse.py` - 测试脚本
- ✅ `backend/config/urls.py` - URL路由配置

### 前端文件
- ✅ `frontend/src/utils/sse-client.js` - SSE客户端工具类
- ✅ `frontend/src/components/SSEStreamViewer.vue` - SSE查看器组件
- ✅ `frontend/src/views/SSEDemo.vue` - 演示页面

### 文档文件
- ✅ `SSE_IMPLEMENTATION.md` - 本文档

## 下一步计划

### 短期 (1-2周)
- [ ] 添加单元测试和集成测试
- [ ] 完善错误处理和重连机制
- [ ] 添加认证和权限验证
- [ ] 优化前端组件样式

### 中期 (1个月)
- [ ] 实现消息持久化 (可选)
- [ ] 添加消息压缩
- [ ] 实现断点续传
- [ ] 添加性能监控

### 长期 (3个月)
- [ ] 支持WebSocket作为备选方案
- [ ] 实现消息队列优先级
- [ ] 添加消息过滤和路由
- [ ] 实现分布式部署支持

## 总结

本次实现完成了基于Redis Pub/Sub的SSE流式系统，包括:

1. ✅ **后端组件**: 发布器、接收器、SSE视图
2. ✅ **前端组件**: SSE客户端、查看器组件、演示页面
3. ✅ **文档**: 详细使用文档、API文档、测试文档
4. ✅ **测试**: 后端测试脚本、前端演示页面

系统已经可以投入使用，支持实时推送AI生成任务的进度和结果。

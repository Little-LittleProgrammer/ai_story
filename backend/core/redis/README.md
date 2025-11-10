# Redis流式发布订阅系统

基于Redis Pub/Sub的实时流式数据传输系统，支持AI生成任务的实时进度推送。

## 架构设计

```
Celery任务 → RedisStreamPublisher → Redis Pub/Sub → RedisStreamSubscriber → SSE视图 → 前端
```

## 核心组件

### 1. RedisStreamPublisher (发布器)

**职责**: 在Celery任务中发布流式数据到Redis频道

**使用场景**:
- LLM流式文本生成
- 图片/视频生成进度推送
- 阶段状态更新

**示例代码**:

```python
from core.redis import RedisStreamPublisher

# 在Celery任务中使用
@celery_app.task
def execute_llm_stage(project_id, stage_name, input_data):
    # 创建发布器
    publisher = RedisStreamPublisher(project_id, stage_name)

    try:
        # 发布阶段开始消息
        publisher.publish_stage_update(status='processing', progress=0)

        # 流式生成文本
        full_text = ""
        for token in llm_client.generate_stream(prompt):
            full_text += token
            # 发布Token消息
            publisher.publish_token(content=token, full_text=full_text)

        # 发布完成消息
        publisher.publish_done(full_text=full_text, metadata={
            'tokens_used': 1000,
            'latency_ms': 2500
        })

    except Exception as e:
        # 发布错误消息
        publisher.publish_error(error=str(e))
    finally:
        publisher.close()
```

**上下文管理器用法**:

```python
with RedisStreamPublisher(project_id, stage_name) as publisher:
    publisher.publish_token(content="Hello")
    publisher.publish_done(full_text="Hello World")
```

### 2. RedisStreamSubscriber (接收器)

**职责**: 订阅Redis频道并接收流式数据

**使用场景**:
- SSE视图中订阅实时数据
- 后台监控任务进度
- 日志收集

**示例代码**:

```python
from core.redis import RedisStreamSubscriber

# 订阅单个阶段
subscriber = RedisStreamSubscriber(project_id='123', stage_name='rewrite')

try:
    for message in subscriber.listen(timeout=300):
        print(f"收到消息: {message['type']}")

        if message['type'] == 'token':
            print(f"Token: {message['content']}")
        elif message['type'] == 'done':
            print(f"完成: {message['full_text']}")
            break
        elif message['type'] == 'error':
            print(f"错误: {message['error']}")
            break
finally:
    subscriber.close()
```

**订阅所有阶段**:

```python
# stage_name=None 表示订阅项目所有阶段
subscriber = RedisStreamSubscriber(project_id='123', stage_name=None)

for message in subscriber.listen():
    print(f"阶段: {message['stage']}, 类型: {message['type']}")
```

**上下文管理器用法**:

```python
with RedisStreamSubscriber(project_id, stage_name) as subscriber:
    for message in subscriber.listen():
        process_message(message)
```

### 3. SSE视图 (Server-Sent Events)

**职责**: 提供HTTP SSE接口，将Redis消息推送给前端

**API端点**:

#### 方式1: 无权限验证 (开发/测试)

```bash
# 订阅单个阶段
GET /api/v1/sse/projects/{project_id}/stages/{stage_name}/

# 订阅所有阶段
GET /api/v1/sse/projects/{project_id}/
```

#### 方式2: 带权限验证 (生产环境推荐)

```bash
# 订阅单个阶段 (需要认证)
GET /api/v1/sse/projects/{project_id}/stages/{stage_name}/stream/
Authorization: Bearer <token>

# 订阅所有阶段 (需要认证)
GET /api/v1/sse/projects/{project_id}/stream/
Authorization: Bearer <token>
```

## 前端使用示例

### JavaScript EventSource

```javascript
// 创建SSE连接
const eventSource = new EventSource(
  `http://localhost:8000/api/v1/sse/projects/${projectId}/stages/rewrite/`
);

// 监听消息
eventSource.onmessage = (event) => {
  const data = JSON.parse(event.data);

  switch (data.type) {
    case 'connected':
      console.log('SSE连接已建立');
      break;

    case 'token':
      // 流式文本片段
      console.log('Token:', data.content);
      updateUI(data.full_text);
      break;

    case 'stage_update':
      // 阶段状态更新
      console.log('进度:', data.progress + '%');
      updateProgress(data.progress);
      break;

    case 'progress':
      // 批量处理进度
      console.log(`处理进度: ${data.current}/${data.total}`);
      break;

    case 'done':
      // 完成
      console.log('生成完成:', data.full_text);
      eventSource.close();
      break;

    case 'error':
      // 错误
      console.error('错误:', data.error);
      eventSource.close();
      break;

    case 'stream_end':
      // 流结束
      console.log('SSE流已关闭');
      eventSource.close();
      break;
  }
};

// 错误处理
eventSource.onerror = (error) => {
  console.error('SSE连接错误:', error);
  eventSource.close();
};

// 关闭连接
// eventSource.close();
```

### Vue 3 Composition API

```vue
<script setup>
import { ref, onMounted, onUnmounted } from 'vue';

const projectId = ref('123');
const stageName = ref('rewrite');
const fullText = ref('');
const progress = ref(0);
const isConnected = ref(false);
let eventSource = null;

const connectSSE = () => {
  const url = `http://localhost:8000/api/v1/sse/projects/${projectId.value}/stages/${stageName.value}/`;
  eventSource = new EventSource(url);

  eventSource.onmessage = (event) => {
    const data = JSON.parse(event.data);

    switch (data.type) {
      case 'connected':
        isConnected.value = true;
        break;
      case 'token':
        fullText.value = data.full_text;
        break;
      case 'stage_update':
        progress.value = data.progress;
        break;
      case 'done':
        console.log('完成');
        disconnectSSE();
        break;
      case 'error':
        console.error(data.error);
        disconnectSSE();
        break;
    }
  };

  eventSource.onerror = () => {
    isConnected.value = false;
    disconnectSSE();
  };
};

const disconnectSSE = () => {
  if (eventSource) {
    eventSource.close();
    eventSource = null;
    isConnected.value = false;
  }
};

onMounted(() => {
  connectSSE();
});

onUnmounted(() => {
  disconnectSSE();
});
</script>

<template>
  <div>
    <div v-if="isConnected" class="status">已连接</div>
    <div class="progress">进度: {{ progress }}%</div>
    <div class="content">{{ fullText }}</div>
  </div>
</template>
```

## 消息格式

### 1. Token消息 (流式文本片段)

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

### 3. 进度消息 (批量处理)

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

### 6. 连接消息

```json
{
  "type": "connected",
  "project_id": "123",
  "stage": "rewrite",
  "message": "SSE连接已建立"
}
```

### 7. 流结束消息

```json
{
  "type": "stream_end",
  "project_id": "123",
  "message": "SSE流已关闭"
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

## 配置说明

### Django Settings

```python
# settings.py

# Redis配置 (使用Celery的Redis连接)
CELERY_BROKER_URL = 'redis://localhost:6379/5'

# 或单独配置
REDIS_URL = 'redis://localhost:6379/5'
```

### Redis连接参数

```python
redis.from_url(
    redis_url,
    decode_responses=True,      # 自动解码为字符串
    socket_connect_timeout=5,   # 连接超时
    socket_timeout=5,           # 操作超时
    retry_on_timeout=True,      # 超时重试
    health_check_interval=30    # 健康检查间隔
)
```

## 部署注意事项

### 1. ASGI服务器

SSE需要ASGI服务器支持 (如Daphne、Uvicorn)：

```bash
# 使用Daphne
daphne -b 0.0.0.0 -p 8000 config.asgi:application

# 或使用启动脚本
./run_asgi.sh
```

### 2. Nginx配置

禁用缓冲以支持SSE流式输出：

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

### 3. Redis持久化

生产环境建议关闭Redis持久化 (Pub/Sub不需要持久化)：

```bash
# redis.conf
save ""
appendonly no
```

### 4. 连接池管理

```python
# 使用连接池避免频繁创建连接
redis_pool = redis.ConnectionPool.from_url(
    redis_url,
    max_connections=50,
    decode_responses=True
)

redis_client = redis.Redis(connection_pool=redis_pool)
```

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

### 2. 超时控制

```python
# 设置合理的超时时间
subscriber.listen(timeout=300)  # 5分钟超时
```

### 3. 资源清理

```python
# 使用上下文管理器自动清理
with RedisStreamPublisher(project_id, stage_name) as publisher:
    # 自动调用close()
    pass
```

## 故障排查

### 1. 检查Redis连接

```bash
redis-cli ping
# 应返回: PONG
```

### 2. 监控Redis频道

```bash
# 订阅所有频道
redis-cli psubscribe "ai_story:*"

# 查看活跃频道
redis-cli pubsub channels "ai_story:*"

# 查看订阅者数量
redis-cli pubsub numsub "ai_story:project:123:stage:rewrite"
```

### 3. 日志调试

```python
import logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger('core.redis')
```

### 4. 常见问题

**问题1**: SSE连接立即断开
- 检查ASGI服务器是否运行
- 检查Nginx缓冲配置
- 检查防火墙/代理设置

**问题2**: 收不到消息
- 检查Redis连接
- 检查频道名称是否匹配
- 检查发布器是否正常工作

**问题3**: 消息延迟
- 检查网络延迟
- 检查Redis性能
- 减少消息发送频率

## 测试

### 单元测试

```python
import pytest
from core.redis import RedisStreamPublisher, RedisStreamSubscriber

def test_publish_subscribe():
    project_id = 'test-123'
    stage_name = 'rewrite'

    # 创建订阅器
    subscriber = RedisStreamSubscriber(project_id, stage_name)

    # 创建发布器
    publisher = RedisStreamPublisher(project_id, stage_name)

    # 发布消息
    publisher.publish_token(content='Hello')

    # 接收消息
    message = subscriber.get_message(timeout=1.0)
    assert message['type'] == 'token'
    assert message['content'] == 'Hello'

    # 清理
    publisher.close()
    subscriber.close()
```

### 集成测试

```bash
# 启动Redis
redis-server

# 启动Celery Worker
celery -A config worker -Q llm -l info

# 启动Django服务器
daphne -b 0.0.0.0 -p 8000 config.asgi:application

# 测试SSE接口
curl -N http://localhost:8000/api/v1/sse/projects/123/stages/rewrite/
```

## 相关文档

- [CELERY_REDIS_STREAMING.md](../../CELERY_REDIS_STREAMING.md) - Celery + Redis流式架构文档
- [Django Channels文档](https://channels.readthedocs.io/)
- [Redis Pub/Sub文档](https://redis.io/docs/manual/pubsub/)
- [Server-Sent Events规范](https://html.spec.whatwg.org/multipage/server-sent-events.html)

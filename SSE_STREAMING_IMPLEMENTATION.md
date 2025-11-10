# 文案改写SSE流式功能实施总结

## 概述

本次实施为AI Story生成系统添加了SSE(Server-Sent Events)流式响应功能,实现了文案改写阶段的实时生成效果。用户可以在前端实时看到AI生成的文本逐字显示,提升了用户体验。

## 技术架构

### 后端实现

#### 1. AI客户端层 (`core/ai_client/openai_client.py`)

**新增功能:**
- `generate_stream()` 异步生成器方法,支持OpenAI流式API
- 实时解析SSE流并yield事件数据
- 事件类型: `token`(文本片段)、`done`(完成)、`error`(错误)

**关键代码:**
```python
async def generate_stream(self, prompt: str, ...) -> AsyncGenerator[Dict[str, Any], None]:
    # 设置stream=True启用流式
    payload = {'model': self.model_name, 'stream': True, ...}

    # 读取SSE流
    async for line in response.content:
        if line.startswith('data: '):
            chunk = json.loads(line[6:])
            content = chunk['choices'][0]['delta'].get('content', '')
            if content:
                yield {'type': 'token', 'content': content, 'full_text': full_text}
```

#### 2. 处理器层 (`apps/content/processors/rewrite.py`)

**新增功能:**
- `process_stream()` 方法,流式执行文案改写
- 实时更新ProjectStage状态
- 保存到ContentRewrite模型

**事件流程:**
1. `stage_update` - 阶段状态更新为running
2. `info` - 提示信息(开始生成)
3. `token` - 每个文本片段(实时推送)
4. `done` - 完成并保存结果
5. `error` - 错误处理

**关键特性:**
- 支持自定义输入文本
- 自动构建提示词
- 异常安全处理

#### 3. 视图层 (`apps/projects/views.py`)

**新增Action:**
- `rewrite_stream` - POST /api/v1/projects/{id}/rewrite-stream/
- 返回StreamingHttpResponse with content_type='text/event-stream'
- 使用asyncio将异步生成器转换为同步流

**关键代码:**
```python
@action(detail=True, methods=['post'])
def rewrite_stream(self, request, pk=None):
    async def event_stream():
        processor = RewriteProcessor()
        async for chunk in processor.process_stream(project_id, input_data):
            event_data = json.dumps(chunk, ensure_ascii=False)
            yield f"data: {event_data}\n\n"

    return StreamingHttpResponse(sync_event_stream(), content_type='text/event-stream')
```

### 前端实现

#### 1. SSE客户端工具 (`frontend/src/utils/sseClient.js`)

**功能:**
- `SSEClient` 类 - 封装EventSource和fetch流式读取
- `createStageStreamClient()` - 专用于项目阶段流式执行
- 支持POST请求(使用fetch + ReadableStream)
- 事件驱动架构,支持on/off/emit

**使用示例:**
```javascript
const client = createStageStreamClient(projectId, 'rewrite', {original_text: '...'});

client.on('token', (data) => {
  // 实时显示文本
  this.output = data.full_text;
});

client.on('done', (data) => {
  // 完成处理
  this.isStreaming = false;
});
```

#### 2. StageContent组件 (`frontend/src/components/projects/StageContent.vue`)

**新增功能:**
- `isStreaming` 状态管理
- `handleStreamExecute()` - 流式执行方法
- 实时更新输出文本区域
- 自动断开SSE连接(组件销毁时)

**用户体验优化:**
- 流式生成时禁用按钮
- 显示"执行中..."状态
- 实时文本动画效果
- 错误提示和恢复

#### 3. ProjectDetail视图 (`frontend/src/views/projects/ProjectDetail.vue`)

**集成:**
- 传递projectId prop到StageContent
- 监听`stage-updated`事件刷新数据
- 横向Tab布局支持各阶段独立操作

## 数据流

```
用户点击"AI生成"
  ↓
StageContent.handleStreamExecute()
  ↓
createStageStreamClient() → POST /api/v1/projects/{id}/rewrite-stream/
  ↓
ProjectViewSet.rewrite_stream()
  ↓
RewriteProcessor.process_stream()
  ↓
OpenAIClient.generate_stream() → OpenAI API (stream=true)
  ↓
SSE流: data: {"type":"token","content":"生","full_text":"生"}\n\n
  ↓
SSEClient解析并触发'token'事件
  ↓
StageContent更新localOutputData
  ↓
用户实时看到文本逐字显示
  ↓
SSE流: data: {"type":"done","full_text":"...","stage":{...}}\n\n
  ↓
保存到数据库,更新阶段状态
```

## 关键技术点

### 1. 异步生成器(AsyncGenerator)

```python
async def process_stream(...) -> AsyncGenerator[Dict[str, Any], None]:
    async for chunk in ai_client.generate_stream(...):
        yield {'type': 'token', 'content': chunk['content']}
```

### 2. SSE格式

```
data: {"type":"token","content":"文本片段"}\n\n
data: {"type":"done","full_text":"完整文本"}\n\n
```

### 3. Django StreamingHttpResponse

```python
response = StreamingHttpResponse(generator, content_type='text/event-stream')
response['Cache-Control'] = 'no-cache'
response['X-Accel-Buffering'] = 'no'  # 禁用Nginx缓冲
```

### 4. 前端ReadableStream

```javascript
const reader = response.body.getReader();
while (true) {
    const {done, value} = await reader.read();
    if (done) break;
    // 处理数据
}
```

## 配置要求

### 后端依赖

```toml
# pyproject.toml
dependencies = [
    "django>=3.2.15",
    "djangorestframework>=3.14",
    "aiohttp>=3.8",
    "asgiref>=3.5",
]
```

### 环境变量

```bash
# .env
OPENAI_API_KEY=sk-xxx
OPENAI_API_URL=https://api.openai.com/v1
```

### Nginx配置(生产环境)

```nginx
location /api/v1/projects/ {
    proxy_pass http://backend;
    proxy_buffering off;  # 关键:禁用缓冲
    proxy_read_timeout 300s;
    proxy_connect_timeout 75s;
}
```

## 使用说明

### 1. 配置AI模型提供商

在Django Admin中配置:
- ModelProvider: 添加OpenAI兼容的LLM提供商
- 设置api_url、api_key、model_name
- provider_type设为'llm'
- is_active=True

### 2. 创建项目

```bash
POST /api/v1/projects/
{
  "name": "测试项目",
  "original_topic": "介绍AI技术的发展历程"
}
```

### 3. 执行流式改写

在前端ProjectDetail页面:
1. 切换到"文案改写"Tab
2. 输入原始文案
3. 点击"AI生成"按钮
4. 实时查看生成结果

## 性能优化

### 后端

1. **数据库查询优化:**
   - 使用`sync_to_async`包装Django ORM
   - 避免N+1查询

2. **流式响应优化:**
   - 使用异步生成器减少内存占用
   - 分块发送数据(每个token立即发送)

3. **错误恢复:**
   - 自动重试机制(max_retries=3)
   - 异常捕获并推送错误事件

### 前端

1. **连接管理:**
   - 组件销毁时自动断开SSE
   - 错误时自动清理资源

2. **状态同步:**
   - 通过事件机制实时更新UI
   - 避免不必要的数据刷新

## 扩展性

### 1. 其他阶段流式支持

可以复用相同架构实现:
- 分镜生成(storyboard_stream)
- 运镜生成(camera_stream)

只需:
1. 创建对应的Processor
2. 添加ViewSet action
3. 前端调用createStageStreamClient()

### 2. 多模型支持

当前架构支持:
- 不同LLM提供商(OpenAI/Claude/自定义)
- 负载均衡策略
- 模型切换

### 3. 实时协作

SSE架构天然支持:
- 多用户查看同一任务进度
- WebSocket升级(更复杂交互)
- 进度百分比显示

## 测试建议

### 单元测试

```python
# test_rewrite_processor.py
async def test_process_stream():
    processor = RewriteProcessor()
    events = []
    async for chunk in processor.process_stream(project_id, input_data):
        events.append(chunk)

    assert events[-1]['type'] == 'done'
    assert 'full_text' in events[-1]
```

### 集成测试

```javascript
// StageContent.spec.js
test('should display streaming text', async () => {
    const wrapper = mount(StageContent, {props: {stageType: 'rewrite', projectId: '123'}});
    await wrapper.vm.handleStreamExecute();

    // 模拟SSE事件
    wrapper.vm.sseClient.emit('token', {full_text: '测试文本'});
    expect(wrapper.vm.localOutputData).toBe('测试文本');
});
```

### 端到端测试

使用Cypress/Playwright:
1. 创建测试项目
2. 点击AI生成
3. 验证文本逐字显示
4. 验证最终保存成功

## 已知限制

1. **浏览器兼容性:**
   - IE不支持EventSource
   - 需要polyfill或fallback

2. **并发限制:**
   - 同一浏览器同域名最多6个SSE连接
   - 建议一个页面一个连接

3. **超时设置:**
   - Nginx默认60s超时
   - 需要调整proxy_read_timeout

4. **认证:**
   - EventSource不支持自定义headers
   - 使用fetch + ReadableStream替代

## 后续改进

1. **断点续传:**
   - 保存中间状态
   - 支持网络中断恢复

2. **进度显示:**
   - 添加预估时长
   - 显示生成速度(tokens/s)

3. **多轮对话:**
   - 支持用户中途修改提示
   - 交互式改写

4. **缓存机制:**
   - 相同输入返回缓存结果
   - Redis存储历史生成

## 总结

本次实施成功实现了文案改写的SSE流式生成功能,主要成果:

✅ 后端OpenAI流式API集成
✅ Django StreamingHttpResponse支持
✅ 前端SSE客户端封装
✅ 实时UI更新
✅ 完整的错误处理
✅ 横向Tab布局改造

**遵循的设计原则:**
- **单一职责(SRP):** 每个类/函数职责明确
- **开闭原则(OCP):** 易于扩展新阶段
- **依赖倒置(DIP):** 依赖抽象的AI客户端接口
- **接口隔离(ISP):** 流式/非流式分离

**用户体验提升:**
- 实时反馈,减少等待焦虑
- 可视化生成过程
- 更好的错误提示

项目已具备完整的流式生成能力,可在此基础上扩展更多AI阶段!

# StageContent 组件 SSE 集成说明

## 概述

`StageContent.vue` 组件已成功集成 SSE (Server-Sent Events) 流式接口，实现了实时的 AI 生成内容展示。

## 功能特性

### ✅ 已实现功能

1. **实时流式输出**
   - 文本内容实时显示在输出框中
   - 自动滚动到最新内容
   - 流畅的打字机效果

2. **进度显示**
   - 实时进度条显示生成进度
   - 百分比数字显示
   - 流式生成动画指示器

3. **错误处理**
   - SSE 连接错误提示
   - 生成失败错误信息展示
   - 自动断开连接和资源清理

4. **状态管理**
   - 连接状态实时更新
   - 禁用按钮防止重复执行
   - 组件销毁时自动断开连接

## 使用方法

### 1. 基本使用

组件已自动集成 SSE，无需额外配置。点击"AI生成"按钮即可触发 SSE 流式生成。

```vue
<StageContent
  :stage-type="stageType"
  :stage="stage"
  :all-stages="allStages"
  :project-id="projectId"
  :original-topic="originalTopic"
  @execute="handleExecute"
  @save="handleSave"
  @stage-completed="handleStageCompleted"
/>
```

### 2. 事件监听

组件会触发以下事件：

#### `execute` 事件
当用户点击"AI生成"按钮时触发。

```javascript
handleExecute(data) {
  console.log('开始执行:', data.stageType, data.inputData);
  // 父组件可以在这里调用后端 API 触发 Celery 任务
}
```

#### `stage-completed` 事件
当 SSE 流式生成完成时触发。

```javascript
handleStageCompleted(data) {
  console.log('阶段完成:', data.stageType);
  // 父组件应该刷新项目数据
  this.fetchProjectData();
}
```

#### `save` 事件
当用户点击"保存数据"按钮时触发。

```javascript
handleSave(data) {
  console.log('保存数据:', data.stageType, data.inputData, data.outputData);
  // 保存到后端
}
```

## 工作流程

### 完整的执行流程

```
用户点击"AI生成"
    ↓
1. 保存输入数据 (触发 save 事件)
    ↓
2. 清空输出和错误信息
    ↓
3. 建立 SSE 连接
    ↓
4. 触发 execute 事件 (父组件调用后端 API)
    ↓
5. 后端启动 Celery 任务
    ↓
6. Celery 任务通过 Redis Pub/Sub 发布消息
    ↓
7. SSE 视图订阅 Redis 消息并推送给前端
    ↓
8. 前端实时更新输出内容和进度
    ↓
9. 生成完成，触发 stage-completed 事件
    ↓
10. 自动断开 SSE 连接
```

## SSE 消息处理

### 支持的消息类型

| 消息类型 | 处理方式 | 说明 |
|---------|---------|------|
| `connected` | 日志记录 | SSE 连接成功 |
| `token` | 更新输出文本 | LLM 流式输出的 token |
| `stage_update` | 更新进度 | 阶段状态更新 |
| `progress` | 更新进度条 | 进度百分比 |
| `done` | 完成生成 | 生成完成，触发 stage-completed 事件 |
| `error` | 显示错误 | 错误信息展示 |
| `stream_end` | 关闭连接 | 流结束 |

### 消息数据格式

#### token 消息
```json
{
  "type": "token",
  "content": "新生成的文本片段",
  "full_text": "完整的累积文本"
}
```

#### progress 消息
```json
{
  "type": "progress",
  "progress": 50,
  "message": "正在生成..."
}
```

#### done 消息
```json
{
  "type": "done",
  "full_text": "完整的生成结果",
  "result": { /* 结构化数据 */ }
}
```

#### error 消息
```json
{
  "type": "error",
  "error": "错误信息描述"
}
```

## UI 展示

### 1. 流式生成中

- 输出框右上角显示"实时生成中"动画标签
- 输出框边框变为蓝色 (`textarea-info`)
- 进度条实时更新
- "AI生成"按钮变为"执行中..."并禁用

### 2. 生成完成

- 移除动画标签
- 进度条显示 100%
- 按钮恢复可用状态
- 显示成功提示消息

### 3. 生成失败

- 显示红色错误提示框
- 错误信息详细说明
- 按钮恢复可用状态
- 显示错误提示消息

## 后端配置要求

### 1. 启动 ASGI 服务器

SSE 需要 ASGI 服务器支持：

```bash
cd backend
./run_asgi.sh
# 或
daphne -b 0.0.0.0 -p 8000 config.asgi:application
```

### 2. 启动 Redis

```bash
# macOS
brew services start redis

# Docker
docker run -d -p 6379:6379 redis:latest
```

### 3. 启动 Celery Worker

```bash
cd backend
uv run celery -A config worker -Q llm,image,video -l info
```

### 4. 后端 API 实现

父组件需要在 `execute` 事件中调用后端 API 触发 Celery 任务：

```javascript
async handleExecute(data) {
  try {
    // 调用后端 API 触发 Celery 任务
    await this.$store.dispatch('projects/executeStage', {
      projectId: this.projectId,
      stageType: data.stageType,
      inputData: data.inputData,
    });
  } catch (error) {
    console.error('执行失败:', error);
    this.$message?.error('执行失败，请重试');
  }
}
```

## 调试技巧

### 1. 查看 SSE 连接状态

打开浏览器开发者工具 → Network → 筛选 EventStream 类型：

```
GET /api/v1/sse/projects/{project_id}/stages/{stage_name}/
Status: 200 OK
Content-Type: text/event-stream
```

### 2. 查看 SSE 消息

在 Network 面板中点击 SSE 请求，查看 EventStream 标签页：

```
data: {"type":"connected","project_id":"123","stage":"rewrite","message":"SSE连接已建立"}

data: {"type":"token","content":"改写","full_text":"改写"}

data: {"type":"token","content":"后的","full_text":"改写后的"}

data: {"type":"done","full_text":"改写后的完整文本"}
```

### 3. 查看控制台日志

组件会输出详细的日志信息：

```
[StageContent] 连接 SSE: project-123 rewrite
[StageContent] SSE 连接已建立
[StageContent] SSE 连接成功: {type: "connected", ...}
[StageContent] 收到 token: {type: "token", content: "...", full_text: "..."}
[StageContent] 进度更新: {type: "progress", progress: 50}
[StageContent] 生成完成: {type: "done", full_text: "..."}
[StageContent] SSE 连接关闭
```

## 常见问题

### Q1: 点击"AI生成"后没有反应？

**检查项:**
1. 后端 ASGI 服务器是否启动
2. Redis 是否运行
3. Celery Worker 是否启动
4. 浏览器控制台是否有错误
5. Network 面板是否有 SSE 连接

### Q2: SSE 连接失败？

**可能原因:**
1. 后端使用了 WSGI 而非 ASGI
2. CORS 配置问题
3. 项目 ID 不存在
4. 网络问题

**解决方法:**
```bash
# 确保使用 ASGI 服务器
cd backend
./run_asgi.sh
```

### Q3: 收不到实时消息？

**检查项:**
1. Celery 任务是否正常执行
2. Redis Pub/Sub 是否正常工作
3. 后端是否正确发布消息到 Redis
4. SSE 视图是否正确订阅 Redis 频道

**调试命令:**
```bash
# 监控 Redis 消息
redis-cli
> PSUBSCRIBE project:*

# 查看 Celery 任务
cd backend
uv run celery -A config inspect active
```

### Q4: 输出文本不完整？

**可能原因:**
1. SSE 连接中断
2. 后端消息格式错误
3. 前端解析失败

**解决方法:**
查看浏览器控制台和后端日志，确认消息格式正确。

## 性能优化

### 1. 自动滚动优化

使用 `$nextTick` 确保 DOM 更新后再滚动：

```javascript
this.$nextTick(() => {
  const textarea = this.$refs.outputTextarea;
  if (textarea) {
    textarea.scrollTop = textarea.scrollHeight;
  }
});
```

### 2. 避免重复连接

在建立新连接前先断开旧连接：

```javascript
connectSSE() {
  this.disconnectSSE(); // 先断开旧连接
  this.sseClient = createProjectStageSSE(...);
}
```

### 3. 资源清理

组件销毁时自动清理：

```javascript
beforeDestroy() {
  this.disconnectSSE();
}
```

## 相关文件

- [StageContent.vue](./src/components/projects/StageContent.vue) - 主组件
- [sseService.js](./src/services/sseService.js) - SSE 服务
- [SSE_INTEGRATION.md](./SSE_INTEGRATION.md) - SSE 集成文档
- [backend/apps/projects/sse_views.py](../backend/apps/projects/sse_views.py) - 后端 SSE 视图

## 下一步

1. 测试所有阶段的 SSE 流式生成
2. 优化错误处理和重试机制
3. 添加断点续传功能
4. 实现生成历史记录
5. 添加生成速度控制

## 更新日志

### 2025-11-03
- ✅ 集成 SSE 服务到 StageContent 组件
- ✅ 添加实时进度显示
- ✅ 添加错误提示
- ✅ 实现自动滚动
- ✅ 完善事件处理
- ✅ 添加资源清理

# SSE 连接断开问题修复

## 问题描述

点击"AI生成"按钮后，SSE连接会被意外断开，导致无法接收实时流式数据。

## 根本原因

在 `StageContent.vue` 的 `handleSSEExecute()` 方法中：

1. **执行流程**：
   - 触发 `save` 事件保存输入数据
   - 建立 SSE 连接
   - 触发 `execute` 事件开始执行

2. **问题所在**：
   - 父组件 `ProjectDetail.vue` 的 `handleSaveStage()` 方法会调用 `fetchData()` 刷新整个页面数据
   - 数据刷新会触发 `StageContent` 组件的 `watch` 监听器重新加载数据
   - 组件可能会重新渲染，导致 `beforeDestroy` 钩子被调用
   - `beforeDestroy` 中会调用 `disconnectSSE()` 断开 SSE 连接

## 解决方案

### 1. 跳过执行前的数据刷新

**修改文件**: `frontend/src/components/projects/StageContent.vue:375-399`

在 `handleSSEExecute()` 中，保存数据时传递 `skipRefresh: true` 参数：

```javascript
this.$emit('save', {
  stageType: this.stageType,
  inputData: inputData,
  outputData: this.parseData(this.localOutputData),
  skipRefresh: true, // 关键：跳过数据刷新
});
```

### 2. 父组件支持跳过刷新

**修改文件**: `frontend/src/views/projects/ProjectDetail.vue:297-313`

在 `handleSaveStage()` 方法中添加 `skipRefresh` 参数：

```javascript
async handleSaveStage({ stageType, inputData, outputData, skipRefresh = false }) {
  try {
    await this.updateStageData({
      projectId: this.project.id,
      stageName: stageType,
      data: { input_data: inputData, output_data: outputData },
    });
    this.$message.success('保存成功');
    // 只有在非流式生成期间才刷新数据，避免断开SSE连接
    if (!skipRefresh) {
      await this.fetchData();
    }
  } catch (error) {
    console.error('Failed to save stage:', error);
    this.$message.error('保存失败');
  }
},
```

### 3. 保护流式生成期间的数据加载

**修改文件**: `frontend/src/components/projects/StageContent.vue:199-222`

在 `watch` 监听器中添加 `isStreaming` 状态检查：

```javascript
watch: {
  stage: {
    immediate: true,
    handler(newStage) {
      // 只有在非流式状态下才加载数据，避免在SSE连接期间重新加载导致数据丢失
      if (!this.isStreaming) {
        this.loadData(newStage);
      } else {
        console.log('[StageContent] 流式生成中，跳过数据加载');
      }
    },
  },
  allStages: {
    deep: true,
    handler() {
      // 当所有阶段数据更新时,重新加载当前阶段数据
      // 但在流式生成期间不加载，避免覆盖正在接收的SSE数据
      if (!this.isStreaming) {
        this.loadData(this.stage);
      } else {
        console.log('[StageContent] 流式生成中，跳过阶段数据加载');
      }
    },
  },
}
```

### 4. 完成后再刷新数据

**修改文件**: `frontend/src/components/projects/StageContent.vue:454-476`

在 SSE `DONE` 事件中，使用 `$nextTick` 确保状态更新后再通知父组件：

```javascript
.on(SSE_EVENT_TYPES.DONE, (data) => {
  console.log('[StageContent] 生成完成:', data);
  // 更新最终输出
  if (data.full_text !== undefined) {
    this.localOutputData = data.full_text;
  } else if (data.result !== undefined) {
    this.localOutputData = typeof data.result === 'string'
      ? data.result
      : JSON.stringify(data.result, null, 2);
  }
  this.streamProgress = 100;
  this.isStreaming = false;

  // 延迟通知父组件刷新数据，确保 isStreaming 状态已更新
  this.$nextTick(() => {
    this.$emit('stage-completed', {
      stageType: this.stageType,
    });
  });

  // 显示成功提示
  this.$message?.success(`${this.getStageName()} 生成完成！`);
})
```

### 5. 添加完成事件处理

**修改文件**: `frontend/src/views/projects/ProjectDetail.vue`

为所有 `StageContent` 组件添加 `@stage-completed` 事件监听，并实现处理方法：

```javascript
handleStageCompleted(stageData) {
  // 当阶段完成时,刷新数据以获取最新的阶段状态
  console.log('Stage completed:', stageData);
  this.fetchData();
},
```

## 修复效果

1. ✅ 点击"AI生成"后，SSE连接不会被意外断开
2. ✅ 流式生成期间，数据不会被外部刷新覆盖
3. ✅ 生成完成后，自动刷新获取最新的阶段状态
4. ✅ 手动保存数据时，仍然会正常刷新页面

## 测试建议

1. 点击"AI生成"按钮，观察控制台日志，确认 SSE 连接建立且不会断开
2. 在流式生成期间，观察输出文本框实时更新
3. 生成完成后，确认数据已保存到后端
4. 手动点击"保存数据"按钮，确认页面正常刷新

## 相关文件

- `frontend/src/components/projects/StageContent.vue` - 阶段内容组件
- `frontend/src/views/projects/ProjectDetail.vue` - 项目详情页面
- `frontend/src/services/sseService.js` - SSE 服务封装

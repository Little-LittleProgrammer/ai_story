# 文生图阶段处理器使用指南

## 概述

`Text2ImageStageProcessor` 是基于 `generate_image` 函数封装的文生图处理器，遵循项目的Pipeline架构设计。

## 特性

✅ **批量处理**: 自动为所有分镜生成图片
✅ **流式进度**: 支持SSE实时推送生成进度
✅ **错误处理**: 失败自动记录,支持部分成功
✅ **数据持久化**: 自动保存到 `GeneratedImage` 模型
✅ **配置灵活**: 支持项目级和系统级模型配置

## 架构设计

```
ProjectStage(storyboard)
    ↓ 输入: 分镜列表
Text2ImageStageProcessor
    ↓ 调用: generate_image()
GeneratedImage 模型
    ↓ 输出: 图片URL列表
ProjectStage(image_generation)
```

## 使用方式

### 1. 在 Pipeline 中使用 (非流式)

```python
from core.pipeline import ProjectPipeline
from apps.content.processors.text2image_stage import Text2ImageStageProcessor

# 创建处理器
processor = Text2ImageStageProcessor()

# 添加到Pipeline
pipeline = ProjectPipeline()
pipeline.add_stage(processor)

# 执行
context = await pipeline.execute(project_id='xxx')
```

### 2. 独立流式调用 (SSE推送)

```python
from apps.content.processors.text2image_stage import Text2ImageStageProcessor

processor = Text2ImageStageProcessor()

# 流式生成 - 生成所有分镜
async for event in processor.process_stream(project_id='xxx'):
    if event['type'] == 'progress':
        print(f"进度: {event['current']}/{event['total']}")
    elif event['type'] == 'image_generated':
        print(f"图片已生成: {event['image']['url']}")
    elif event['type'] == 'done':
        print(f"完成: {event['data']}")
    elif event['type'] == 'error':
        print(f"错误: {event['error']}")

# 流式生成 - 仅生成指定分镜
async for event in processor.process_stream(
    project_id='xxx',
    storyboard_ids=['uuid1', 'uuid2']
):
    # 处理事件...
```

### 3. 在 Django View 中使用

```python
from django.http import StreamingHttpResponse
from apps.content.processors.text2image_stage import Text2ImageStageProcessor
import json

async def generate_images_stream(request, project_id):
    """SSE流式生成图片"""

    async def event_stream():
        processor = Text2ImageStageProcessor()

        async for event in processor.process_stream(project_id):
            # SSE格式
            yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"

    response = StreamingHttpResponse(
        event_stream(),
        content_type='text/event-stream'
    )
    response['Cache-Control'] = 'no-cache'
    response['X-Accel-Buffering'] = 'no'
    return response
```

## 事件类型说明

### 流式输出事件

| 事件类型 | 说明 | 数据字段 |
|---------|------|---------|
| `stage_update` | 阶段状态更新 | `stage: {id, status, stage_type, started_at}` |
| `info` | 信息提示 | `message: str` |
| `progress` | 生成进度 | `current, total, message, storyboard` |
| `image_generated` | 单张图片生成完成 | `storyboard_id, image: {id, url, width, height}` |
| `warning` | 警告信息 | `message: str` |
| `error` | 错误信息 | `error: str, storyboard_id (可选)` |
| `done` | 全部完成 | `message, data, stage` |

### process() 返回值

```python
StageResult(
    success=True,
    data={
        'total_storyboards': 5,      # 总分镜数
        'success_count': 5,           # 成功数量
        'failed_count': 0,            # 失败数量
        'generated_image_ids': [...]  # 生成的图片ID列表
    }
)
```

## 配置说明

### 模型提供商配置

**优先级顺序:**
1. 项目模型配置 (`ProjectModelConfig.image_providers`)
2. 系统默认提供商 (`ModelProvider.provider_type='text2image'`)

**必需字段:**
- `api_key`: 作为 `session_id` 传递给 `generate_image()`
- `model_name`: 模型名称 (如 "jimeng-4.0")
- `api_url`: API地址 (当前硬编码为 `http://localhost:5100/v1/images/generations`)

### 生成参数

可在 `_generate_single_image()` 方法中自定义:

```python
ratio: str = "16:9"      # 图片比例 (1:1, 16:9, 4:3等)
resolution: str = "2k"   # 分辨率 (2k, 4k等)
```

## 数据模型

### 输入要求

- **前置阶段**: `storyboard` 阶段必须已完成
- **必需数据**: 至少有一个 `Storyboard` 记录
- **必需字段**: `Storyboard.image_prompt` (文生图提示词)

### 输出结果

保存到 `GeneratedImage` 模型:

```python
GeneratedImage:
    - id: UUID
    - storyboard: ForeignKey -> Storyboard
    - image_url: str          # 图片URL
    - thumbnail_url: str      # 缩略图URL (可选)
    - generation_params: dict # 生成参数
    - model_provider: FK      # 使用的模型
    - status: str            # pending/processing/completed/failed
    - width, height: int     # 图片尺寸
    - file_size: int         # 文件大小
```

## 错误处理

### 验证失败场景

- 项目不存在
- `storyboard` 阶段未完成
- 没有分镜数据
- 未配置文生图模型提供商

### 生成失败处理

1. **单个分镜失败**: 记录错误日志,继续处理下一个
2. **全部失败**: 阶段状态设为 `failed`
3. **部分失败**: 阶段状态设为 `partial`

### 重试机制

当前版本未实现自动重试,可通过以下方式手动重试:

```python
# 重新调用process_stream,只处理失败的分镜
failed_storyboard_ids = [...]  # 获取失败的分镜ID
async for event in processor.process_stream(
    project_id='xxx',
    storyboard_ids=failed_storyboard_ids
):
    # 处理重试结果...
```

## 性能优化建议

### 1. 并发控制

当前是串行生成,可改为并发:

```python
# 在 process_stream() 中
import asyncio

# 分批并发生成
batch_size = 3
for i in range(0, len(storyboards), batch_size):
    batch = storyboards[i:i+batch_size]
    tasks = [
        self._generate_single_image(sb, session_id, model_name, provider)
        for sb in batch
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    # 处理结果...
```

### 2. 缓存机制

避免重复生成相同提示词的图片:

```python
# 检查是否已有相同prompt的图片
existing_image = await sync_to_async(
    GeneratedImage.objects.filter(
        storyboard__image_prompt=prompt,
        status='completed'
    ).first
)()

if existing_image:
    # 复用已有图片
    return existing_image
```

### 3. 超时控制

为 `generate_image()` 添加超时:

```python
import asyncio

response = await asyncio.wait_for(
    loop.run_in_executor(None, lambda: generate_image(...)),
    timeout=60.0  # 60秒超时
)
```

## 扩展开发

### 添加新的文生图提供商

1. 实现 `generate_image()` 兼容接口
2. 在 `ModelProvider` 中添加新的 `provider_type`
3. 更新 `_generate_single_image()` 方法以支持新提供商

### 自定义生成参数

修改 `_generate_single_image()` 方法:

```python
# 从分镜或项目配置读取参数
ratio = storyboard.custom_params.get('ratio', '16:9')
resolution = storyboard.custom_params.get('resolution', '2k')
negative_prompt = storyboard.negative_prompt

response = await loop.run_in_executor(
    None,
    lambda: generate_image(
        session_id=session_id,
        model=model_name,
        prompt=prompt,
        ratio=ratio,
        resolution=resolution,
        negative_prompt=negative_prompt
    )
)
```

## 测试示例

```python
import pytest
from apps.content.processors.text2image_stage import Text2ImageStageProcessor

@pytest.mark.asyncio
async def test_text2image_processor():
    processor = Text2ImageStageProcessor()

    # 创建测试项目和分镜
    project = await create_test_project()
    storyboard = await create_test_storyboard(project)

    # 执行处理
    context = PipelineContext(project_id=str(project.id))
    result = await processor.process(context)

    assert result.success
    assert result.data['success_count'] > 0

    # 验证图片已保存
    images = await sync_to_async(
        lambda: list(GeneratedImage.objects.filter(storyboard=storyboard))
    )()
    assert len(images) > 0
```

## 常见问题

### Q1: 图片生成失败返回空结果?

**A**: 检查:
1. `session_id` (API Key) 是否有效
2. API服务 (`http://localhost:5100`) 是否运行
3. `model_name` 是否正确 (如 "jimeng-4.0")
4. 提示词是否符合要求

### Q2: 如何修改图片比例和分辨率?

**A**: 修改 `_generate_single_image()` 方法的默认参数:

```python
async def _generate_single_image(
    self,
    storyboard: Storyboard,
    session_id: str,
    model_name: str,
    provider: ModelProvider,
    ratio: str = "1:1",      # 修改这里
    resolution: str = "4k"   # 修改这里
):
```

### Q3: 如何获取生成进度?

**A**: 使用流式接口 `process_stream()` 并监听 `progress` 事件:

```python
async for event in processor.process_stream(project_id='xxx'):
    if event['type'] == 'progress':
        progress = event['current'] / event['total'] * 100
        print(f"进度: {progress:.1f}%")
```

## 相关文件

- 处理器实现: `backend/apps/content/processors/text2image_stage.py`
- AI客户端: `backend/core/ai_client/text2image_client.py`
- 数据模型: `backend/apps/content/models.py`
- Pipeline基类: `backend/core/pipeline/base.py`

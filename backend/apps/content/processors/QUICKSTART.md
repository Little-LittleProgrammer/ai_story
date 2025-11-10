# 文生图处理器快速开始

## 📁 文件清单

创建的文件:
1. **处理器实现**: `backend/apps/content/processors/text2image_stage.py`
2. **使用指南**: `backend/apps/content/processors/README_text2image.md`
3. **测试脚本**: `backend/apps/content/processors/test_text2image_processor.py`
4. **本文档**: `backend/apps/content/processors/QUICKSTART.md`

## 🚀 快速开始

### 步骤 1: 准备数据

确保您已经有:
- ✅ 项目 (Project)
- ✅ 分镜数据 (Storyboard) - 包含 `image_prompt` 字段
- ✅ 文生图模型配置 (ModelProvider, provider_type='text2image')

### 步骤 2: 配置模型提供商

在 Django Admin 中配置文生图模型:

```python
# 通过 Django Admin 或代码创建
from apps.models.models import ModelProvider

provider = ModelProvider.objects.create(
    name="即梦AI",
    provider_type="text2image",
    api_url="http://localhost:5100/v1/images/generations",
    api_key="your_session_id_here",  # 作为session_id使用
    model_name="jimeng-4.0",
    is_active=True,
    rate_limit_rpm=60,
    priority=1
)
```

### 步骤 3: 使用处理器

#### 方式1: 非流式处理 (Pipeline集成)

```python
from core.pipeline.base import PipelineContext
from apps.content.processors.text2image_stage import Text2ImageStageProcessor

# 创建处理器
processor = Text2ImageStageProcessor()

# 创建上下文
context = PipelineContext(project_id='your-project-id')

# 执行处理
result = await processor.process(context)

if result.success:
    print(f"成功生成 {result.data['success_count']} 张图片")
```

#### 方式2: 流式处理 (SSE推送)

```python
from apps.content.processors.text2image_stage import Text2ImageStageProcessor

processor = Text2ImageStageProcessor()

async for event in processor.process_stream('your-project-id'):
    print(f"{event['type']}: {event}")
```

### 步骤 4: 测试

运行测试脚本:

```bash
cd backend

# 方式1: 直接运行
python manage.py shell < apps/content/processors/test_text2image_processor.py

# 方式2: 交互式
python manage.py shell
>>> exec(open('apps/content/processors/test_text2image_processor.py').read())
```

## 📊 数据流

```
1. 输入检查
   └─> 从 Storyboard 读取 image_prompt

2. 模型配置
   └─> 获取 ModelProvider (session_id, model_name)

3. 批量生成
   └─> 为每个分镜调用 generate_image()

4. 保存结果
   └─> 创建 GeneratedImage 记录

5. 更新阶段
   └─> 更新 ProjectStage.output_data
```

## 🔧 配置项

### 默认参数

在 `text2image_stage.py` 中可修改:

```python
class Text2ImageStageProcessor:
    def __init__(self):
        self.max_concurrent = 3  # 最大并发数

    async def _generate_single_image(
        self,
        storyboard,
        session_id,
        model_name,
        provider,
        ratio="16:9",      # 图片比例
        resolution="2k"    # 分辨率
    ):
```

### 支持的参数

| 参数 | 说明 | 可选值 | 默认值 |
|-----|------|--------|--------|
| `ratio` | 图片比例 | 1:1, 16:9, 4:3 等 | 16:9 |
| `resolution` | 分辨率 | 2k, 4k 等 | 2k |
| `negative_prompt` | 负面提示词 | 任意文本 | None |
| `sample_strength` | 采样强度 | 0.0-1.0 | None |

## 📝 Django View 集成示例

### 创建 View

在 `apps/projects/views.py` 中添加:

```python
from django.http import StreamingHttpResponse
from apps.content.processors.text2image_stage import Text2ImageStageProcessor
import json

class ProjectImageGenerationView(APIView):
    """项目图片生成接口"""

    async def post(self, request, project_id):
        """
        POST /api/v1/projects/{project_id}/generate-images/

        可选参数:
        - storyboard_ids: 指定要生成的分镜ID列表
        """
        storyboard_ids = request.data.get('storyboard_ids')

        async def event_stream():
            processor = Text2ImageStageProcessor()

            async for event in processor.process_stream(
                project_id=project_id,
                storyboard_ids=storyboard_ids
            ):
                # 转换为SSE格式
                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"

        response = StreamingHttpResponse(
            event_stream(),
            content_type='text/event-stream'
        )
        response['Cache-Control'] = 'no-cache'
        response['X-Accel-Buffering'] = 'no'
        return response
```

### 注册路由

在 `apps/projects/urls.py` 中:

```python
from django.urls import path
from .views import ProjectImageGenerationView

urlpatterns = [
    # ...其他路由
    path(
        '<uuid:project_id>/generate-images/',
        ProjectImageGenerationView.as_view(),
        name='project-generate-images'
    ),
]
```

## 🌐 前端集成示例

### Vue.js SSE客户端

```javascript
// services/imageGenerationService.js
export default {
  generateImages(projectId, storyboardIds = null) {
    return new Promise((resolve, reject) => {
      const url = `/api/v1/projects/${projectId}/generate-images/`
      const eventSource = new EventSource(url)

      const events = {
        progress: [],
        images: [],
        errors: []
      }

      eventSource.onmessage = (e) => {
        const event = JSON.parse(e.data)

        switch (event.type) {
          case 'progress':
            events.progress.push(event)
            this.onProgress?.(event)
            break

          case 'image_generated':
            events.images.push(event)
            this.onImageGenerated?.(event)
            break

          case 'error':
            events.errors.push(event)
            this.onError?.(event)
            break

          case 'done':
            eventSource.close()
            resolve({
              success: true,
              data: event.data,
              events
            })
            break
        }
      }

      eventSource.onerror = (e) => {
        eventSource.close()
        reject(new Error('SSE连接错误'))
      }
    })
  },

  // 回调函数
  onProgress: null,
  onImageGenerated: null,
  onError: null
}
```

### Vue组件使用

```vue
<template>
  <div>
    <button @click="startGeneration" :disabled="generating">
      {{ generating ? '生成中...' : '开始生成图片' }}
    </button>

    <div v-if="generating" class="progress">
      <div class="progress-bar" :style="{ width: progressPercent + '%' }">
        {{ currentIndex }}/{{ totalImages }}
      </div>
    </div>

    <div class="images-grid">
      <div v-for="image in generatedImages" :key="image.id" class="image-card">
        <img :src="image.url" :alt="'分镜 ' + image.sequence_number">
        <p>分镜 #{{ image.sequence_number }}</p>
      </div>
    </div>
  </div>
</template>

<script>
import imageGenerationService from '@/services/imageGenerationService'

export default {
  data() {
    return {
      generating: false,
      currentIndex: 0,
      totalImages: 0,
      generatedImages: []
    }
  },

  computed: {
    progressPercent() {
      return this.totalImages > 0
        ? (this.currentIndex / this.totalImages * 100)
        : 0
    }
  },

  methods: {
    async startGeneration() {
      this.generating = true
      this.generatedImages = []

      // 设置回调
      imageGenerationService.onProgress = (event) => {
        this.currentIndex = event.current
        this.totalImages = event.total
      }

      imageGenerationService.onImageGenerated = (event) => {
        this.generatedImages.push({
          id: event.image.id,
          url: event.image.url,
          sequence_number: event.sequence_number
        })
      }

      imageGenerationService.onError = (event) => {
        this.$message.error(event.error)
      }

      try {
        const result = await imageGenerationService.generateImages(
          this.$route.params.projectId
        )

        this.$message.success(`成功生成 ${result.data.success_count} 张图片`)
      } catch (error) {
        this.$message.error('图片生成失败: ' + error.message)
      } finally {
        this.generating = false
      }
    }
  }
}
</script>
```

## 🐛 故障排查

### 问题1: "未找到可用的文生图模型提供商"

**解决方案:**
```python
# 检查是否有配置
from apps.models.models import ModelProvider
providers = ModelProvider.objects.filter(provider_type='text2image', is_active=True)
print(providers)  # 应该至少有一个

# 如果没有，创建一个
ModelProvider.objects.create(...)  # 参考步骤2
```

### 问题2: "storyboard阶段未完成"

**解决方案:**
```python
# 检查阶段状态
from apps.projects.models import ProjectStage
stage = ProjectStage.objects.filter(
    project_id='your-project-id',
    stage_type='storyboard'
).first()
print(stage.status)  # 应该是 'completed'

# 如果不是，先完成storyboard阶段
```

### 问题3: "没有分镜数据"

**解决方案:**
```python
# 检查分镜
from apps.content.models import Storyboard
storyboards = Storyboard.objects.filter(project_id='your-project-id')
print(storyboards.count())  # 应该 > 0

# 如果没有，先生成分镜
```

### 问题4: 图片生成返回空结果

**解决方案:**
1. 检查API服务是否运行: `curl http://localhost:5100/v1/images/generations`
2. 检查session_id是否有效
3. 查看日志: `tail -f backend/logs/django.log`

## 📚 更多资源

- **详细文档**: [README_text2image.md](README_text2image.md)
- **架构设计**: [../../ARCHITECTURE.md](../../ARCHITECTURE.md)
- **Pipeline文档**: [../../../core/pipeline/README.md](../../../core/pipeline/README.md)
- **AI客户端文档**: [../../../core/ai_client/README.md](../../../core/ai_client/README.md)

## ✅ 检查清单

部署前检查:

- [ ] ModelProvider 已配置 (provider_type='text2image')
- [ ] API服务正常运行 (http://localhost:5100)
- [ ] 项目有分镜数据 (Storyboard)
- [ ] storyboard阶段已完成
- [ ] 测试脚本运行成功
- [ ] Django View 和路由已添加
- [ ] 前端SSE客户端已实现

## 🎯 下一步

1. **集成到Pipeline**: 将处理器添加到项目工作流
2. **添加重试机制**: 实现失败自动重试
3. **实现并发生成**: 提高批量生成性能
4. **添加缓存**: 避免重复生成相同图片
5. **监控和日志**: 添加详细的性能监控

---

**创建日期**: 2025-10-18
**版本**: 1.0.0
**作者**: Claude Code

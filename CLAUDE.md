# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

AI Story生成系统 - 基于Django + Vue的AI驱动的故事脚本到视频的自动化生成平台。

**核心工作流:** 文案改写 → 分镜生成 → 文生图 → 运镜生成 → 图生视频

**技术栈:**
- 后端: Django 3.2.15 + DRF + Celery + Redis + Channels
- 前端: Vue 2.7.14 + Vuex + daisyUI 4.12.23 + Tailwind CSS 3.4.17 ✅
- 包管理: uv (Python) + npm (Node.js)
- 数据库: SQLite (开发) / PostgreSQL (生产)
- AI集成: OpenAI/Claude API, Stable Diffusion, Runway
- 容器化: Docker + Docker Compose

## 常用命令

**访问地址:**
- 前端应用: http://localhost:3000
- 后端API: http://localhost:8000
- Django Admin: http://localhost:8000/admin
- WebSocket: ws://localhost:8000/ws/projects/{project_id}/

### 后端开发

```bash
cd backend

# 使用 uv 管理依赖
uv sync              # 同步所有依赖
uv sync --group dev  # 开发环境

# 运行Django命令
uv run python manage.py migrate

# ⚠️ 重要:启动服务器
# 选项1: 使用ASGI服务器(推荐 - 支持WebSocket和SSE流式输出)
./run_asgi.sh        # 或: daphne -b 0.0.0.0 -p 8000 config.asgi:application

# 选项2: 使用WSGI开发服务器(不支持WebSocket和真正的SSE流式)
uv run python manage.py runserver

# 或激活虚拟环境后直接使用
source .venv/bin/activate  # Linux/Mac
.venv\Scripts\activate     # Windows
python manage.py runserver
```

**流式生成架构说明:**
- **新架构 (Celery + Redis Pub/Sub + WebSocket)**:
  - 异步任务执行，不阻塞HTTP请求
  - 通过Redis Pub/Sub实时推送进度
  - 前端通过WebSocket订阅接收实时数据
  - 支持任务重试、超时控制、分布式部署
  - 详见: [CELERY_REDIS_STREAMING.md](backend/CELERY_REDIS_STREAMING.md)

- **旧架构 (SSE流式)**:
  - ASGI模式: 支持真正的实时流式输出
  - WSGI模式: 会缓冲完整响应后一次性返回
  - 已保留作为fallback

### 前端开发

```bash
cd frontend

# 安装依赖
npm install

# 启动开发服务器(热重载)
npm run dev

# 生产构建
npm run build

# 代码检查
npm run lint
npm run lint:fix
```

### 数据库操作

```bash
cd backend

# 使用 uv run 执行命令
# 创建迁移文件
uv run python manage.py makemigrations

# 执行迁移
uv run python manage.py migrate

# 创建超级用户
uv run python manage.py createsuperuser

# 进入Django Shell
uv run python manage.py shell

# 或激活虚拟环境后直接使用
source .venv/bin/activate
python manage.py makemigrations
python manage.py migrate
```

### 测试

```bash
cd backend

# 使用 uv run 运行测试
# 运行所有测试
uv run python manage.py test

# 运行指定app的测试
uv run python manage.py test apps.projects

# 运行单个测试文件
uv run python manage.py test apps.projects.tests.test_models

# 或激活虚拟环境后直接使用
source .venv/bin/activate
python manage.py test
```

### Celery 任务队列

```bash
cd backend

# ⚠️ 重要: 先启动Redis服务
# macOS: brew services start redis
# Docker: docker run -d -p 6379:6379 redis:latest

# 使用 uv run 启动 Celery Worker
# 启动默认队列Worker
uv run celery -A config worker -l info

# 启动多队列Worker (推荐 - 支持任务分类)
uv run celery -A config worker -Q llm,image,video -l info

# 后台运行
uv run celery -A config worker -Q llm,image,video -l info --detach

# 启动 Celery Beat (定时任务)
uv run celery -A config beat -l info

# 监控 Celery (需安装 flower)
uv run celery -A config flower
# 访问 http://localhost:5555

# 查看活跃任务
uv run celery -A config inspect active

# 查看已注册任务
uv run celery -A config inspect registered

# 或激活虚拟环境后直接使用
source .venv/bin/activate
celery -A config worker -Q llm,image,video -l info
```

**Celery队列说明:**
- `llm`: LLM类任务（文案改写、分镜生成、运镜生成）
- `image`: 文生图任务
- `video`: 图生视频任务

### 依赖管理 (uv)

```bash
cd backend

# 安装/同步所有依赖
uv sync

# 安装开发依赖
uv sync --group dev

# 添加新依赖
uv add django-rest-framework

# 添加开发依赖
uv add --group dev pytest

# 移除依赖
uv remove package-name

# 更新依赖
uv lock --upgrade

# 查看已安装的包
uv pip list

# 导出 requirements.txt (兼容性)
uv pip compile pyproject.toml -o requirements.txt
```

### Docker 部署

```bash
# 构建并启动所有服务
docker-compose up -d

# 查看服务状态
docker-compose ps

# 查看日志
docker-compose logs -f backend
docker-compose logs -f celery
docker-compose logs -f frontend

# 停止所有服务
docker-compose down

# 重启特定服务
docker-compose restart backend

# 进入容器执行命令
docker-compose exec backend python manage.py migrate
docker-compose exec backend python manage.py createsuperuser

# 清理并重建
docker-compose down -v  # -v 删除数据卷
docker-compose build --no-cache
docker-compose up -d
```

**Docker服务说明**:
- `db`: PostgreSQL 14数据库
- `redis`: Redis 7缓存和消息队列
- `backend`: Django应用（端口8000）
- `celery`: Celery Worker（3个队列）
- `celery-beat`: Celery定时任务调度器
- `frontend`: Vue开发服务器（端口3000）

## 快速导航

### 核心文件索引

**后端核心文件**:
- [apps/projects/models.py](backend/apps/projects/models.py) - 项目管理域模型
- [apps/projects/views.py](backend/apps/projects/views.py) - 项目API视图（704行，18个action）
- [apps/projects/tasks.py](backend/apps/projects/tasks.py) - Celery异步任务定义
- [apps/projects/consumers.py](backend/apps/projects/consumers.py) - WebSocket消费者
- [apps/content/processors/llm_stage.py](backend/apps/content/processors/llm_stage.py) - LLM处理器（510行）
- [apps/content/processors/text2image_stage.py](backend/apps/content/processors/text2image_stage.py) - 文生图处理器
- [core/pipeline/base.py](backend/core/pipeline/base.py) - Pipeline基类定义
- [core/pipeline/orchestrator.py](backend/core/pipeline/orchestrator.py) - 工作流编排器
- [core/ai_client/base.py](backend/core/ai_client/base.py) - AI客户端抽象基类
- [core/ai_client/openai_client.py](backend/core/ai_client/openai_client.py) - OpenAI客户端实现
- [core/redis/publisher.py](backend/core/redis/publisher.py) - Redis Pub/Sub发布器
- [config/settings/base.py](backend/config/settings/base.py) - 基础配置
- [config/celery.py](backend/config/celery.py) - Celery配置

**前端核心文件**:
- [frontend/src/views/projects/ProjectList.vue](frontend/src/views/projects/ProjectList.vue) - 项目列表页
- [frontend/src/store/modules/projects.js](frontend/src/store/modules/projects.js) - 项目状态管理
- [frontend/src/api/projects.js](frontend/src/api/projects.js) - 项目API封装
- [frontend/src/utils/wsClient.js](frontend/src/utils/wsClient.js) - WebSocket客户端
- [frontend/src/components/layout/Layout.vue](frontend/src/components/layout/Layout.vue) - 主布局组件
- [frontend/src/router/index.js](frontend/src/router/index.js) - 路由配置

**文档文件**:
- [backend/CELERY_REDIS_STREAMING.md](backend/CELERY_REDIS_STREAMING.md) - Celery+Redis流式架构详细文档（523行）
- [README.md](README.md) - 项目总体说明

## 架构设计

### 分层架构

```
API层 (DRF)
    ↓
业务逻辑层 (Service Layer)
    ↓
Pipeline工作流引擎 (责任链模式)
    ↓
AI客户端抽象层 (策略模式)
    ↓
领域模型层 (DDD)
    ↓
基础设施层 (PostgreSQL/Redis/Celery)
```

### 核心设计模式

1. **责任链模式 (Pipeline):**
   - `core/pipeline/` - 工作流阶段按顺序执行,每个阶段可决定是否继续
   - `apps/content/processors/` - 各阶段处理器实现

2. **策略模式 (AI客户端):**
   - `core/ai_client/base.py` - 统一的AI客户端接口
   - 支持动态切换不同的LLM/文生图/图生视频服务商

3. **工厂模式:**
   - 负载均衡器动态选择模型提供商
   - 支持轮询、随机、权重、最少负载策略

4. **领域驱动设计 (DDD):**
   - 项目管理域 (`apps/projects/`)
   - 提示词管理域 (`apps/prompts/`)
   - 模型管理域 (`apps/models/`)
   - 内容生成域 (`apps/content/`)

### 关键抽象

#### Pipeline 工作流 (`core/pipeline/`)

```python
# 执行完整工作流
from core.pipeline import ProjectPipeline
pipeline = ProjectPipeline()
context = await pipeline.execute(project_id='xxx')

# 单独执行某个阶段
result = await pipeline.execute_stage(project_id='xxx', stage_name='rewrite')
```

**核心类:**
- `PipelineContext` - 携带所有阶段数据的上下文对象
- `StageProcessor` - 阶段处理器抽象基类 (需实现: `validate()`, `process()`, `on_failure()`)
- `StageResult` - 阶段执行结果封装
- `ProjectPipeline` - 工作流编排器,自动处理阶段链和重试逻辑

#### AI客户端抽象 (`core/ai_client/`)

```python
# 所有AI客户端统一返回 AIResponse
@dataclass
class AIResponse:
    success: bool
    text: str
    data: Dict[str, Any]
    metadata: Dict[str, Any]
    error: Optional[str]
```

**客户端层次:**
- `BaseAIClient` - 所有AI客户端的基类
- `LLMClient` - 文本生成 (文案改写、分镜、运镜)
- `Text2ImageClient` - 图片生成
- `Image2VideoClient` - 视频生成

**具体实现:**
- `OpenAIClient` - OpenAI兼容接口
- `StableDiffusionClient` - Stable Diffusion API
- `RunwayClient` - Runway图生视频API

### 领域模型要点

#### 项目管理域 (`apps/projects/models.py`)

- **Project** - 项目聚合根
  - 状态流转: `draft → processing → completed/failed/paused`
  - 关联: PromptTemplateSet (提示词集)

- **ProjectStage** - 工作流阶段追踪
  - 5个阶段类型: rewrite, storyboard, image_generation, camera_movement, video_generation
  - 自动重试机制 (max_retries=3)
  - 存储: input_data, output_data (JSONField)

- **ProjectModelConfig** - 项目AI模型配置
  - 支持每个阶段配置多个模型 (ManyToMany)
  - 负载均衡策略: round_robin, random, weighted, least_loaded

#### 提示词管理域 (`apps/prompts/models.py`)

- **PromptTemplateSet** - 提示词集 (可复用)
- **PromptTemplate** - 提示词模板
  - 支持 Jinja2 模板语法
  - 存储变量定义: `variables: JSONField`
  - 版本控制: `version: IntegerField`

#### 模型管理域 (`apps/models/models.py`)

- **ModelProvider** - AI模型提供商
  - 类型: llm, text2image, image2video
  - 加密存储API Key
  - 限流配置: rate_limit_rpm, rate_limit_rpd
  - 权重: priority (用于负载均衡)

- **ModelUsageLog** - 使用日志和成本统计

#### 内容生成域 (`apps/content/models.py`)

- **ContentRewrite** - 文案改写结果 (1对1 with Project)
- **Storyboard** - 分镜 (1对多 with Project)
  - 字段: scene_description, narration_text, image_prompt, duration_seconds
  - 排序: sequence_number

- **GeneratedImage** - 生成图片 (多对1 with Storyboard)
  - 存储生成参数: generation_params (JSONField)
  - 支持重试: retry_count

- **CameraMovement** - 运镜参数 (1对1 with Storyboard)
  - 运镜类型: static, zoom_in, pan_left, tilt_up 等
  - 参数: movement_params (JSONField)

- **GeneratedVideo** - 生成视频 (多对1 with Storyboard)
  - 关联: image, camera_movement
  - 视频属性: duration, width, height, fps, file_size

## 开发规范

### SOLID 原则强制执行

代码库严格遵循SOLID原则,所有新代码必须符合:

1. **单一职责 (SRP):** 每个类/模块只负责一项功能
   - 示例: `RewriteProcessor` 只负责文案改写,不处理分镜生成

2. **开闭原则 (OCP):** 对扩展开放,对修改封闭
   - 示例: 添加新AI客户端只需继承 `BaseAIClient`,无需修改核心代码

3. **里氏替换 (LSP):** 子类必须可替换父类
   - 示例: 所有 `LLMClient` 实现可互换使用

4. **接口隔离 (ISP):** 接口专一,避免胖接口
   - 示例: LLM/Text2Image/Image2Video 接口分离

5. **依赖倒置 (DIP):** 依赖抽象而非具体实现
   - 示例: Pipeline依赖 `StageProcessor` 抽象,而非具体处理器

### 代码组织规范

**重要原则: 业务逻辑必须放在 `apps/` 目录下,而非 `core/` 目录**

1. **`core/` 目录职责:**
   - 存放通用的基础设施代码和抽象层
   - 例如: AI客户端抽象、Pipeline引擎、Redis工具类
   - 不应包含具体的业务逻辑或视图层代码

2. **`apps/` 目录职责:**
   - 存放所有业务逻辑代码
   - 包括: models, views, serializers, tasks, processors
   - 每个app代表一个领域边界

3. **视图层代码放置规则:**
   - ✅ 正确: `apps/projects/views.py` - 项目相关的视图
   - ✅ 正确: `apps/projects/sse_views.py` - 项目相关的SSE视图
   - ❌ 错误: `core/redis/sse_views.py` - 不应在core中放置业务视图
   - ❌ 错误: `core/views.py` - core不应包含视图层

4. **URL配置规则:**
   - 业务相关的URL应在对应app的 `urls.py` 中定义
   - 主 `config/urls.py` 只负责include各app的URL
   - 避免在主URL配置中直接导入app的视图

### 代码风格

- 遵循 PEP 8
- 使用类型注解 (`typing` 模块)
- Docstring格式: Google Style
- 异步操作使用 `async/await`

### 新增处理器流程

1. 继承 `StageProcessor` 基类
2. 实现 `validate()` - 验证阶段前置条件
3. 实现 `process()` - 执行核心业务逻辑
4. 实现 `on_failure()` - 处理失败场景
5. 注册到 `ProjectPipeline.stages` 列表

示例参考: `apps/content/processors/rewrite.py`

### 新增AI客户端流程

1. 选择合适的基类: `LLMClient` / `Text2ImageClient` / `Image2VideoClient`
2. 实现 `_generate_*()` 方法
3. 实现 `validate_config()` 方法
4. 返回标准 `AIResponse` 对象
5. 在 `ModelProvider.provider_type` 中添加类型

示例参考: `core/ai_client/openai_client.py`

## 关键配置

### 环境变量 (`.env`)

```bash
# Django
SECRET_KEY=your-secret-key
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# 数据库
DATABASE_URL=postgresql://user:pass@localhost:5432/ai_story

# Redis
REDIS_URL=redis://localhost:6379/0

# Celery
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0

# AI API (可选,可通过Admin后台配置)
OPENAI_API_KEY=sk-xxx
OPENAI_API_URL=https://api.openai.com/v1
```

### Settings 分层

- `config/settings/base.py` - 公共配置
- `config/settings/development.py` - 开发环境
- `config/settings/production.py` - 生产环境

使用 `DJANGO_SETTINGS_MODULE` 环境变量切换:
```bash
export DJANGO_SETTINGS_MODULE=config.settings.production
```

## 访问地址

- **前端应用:** http://localhost:3000 ✅
- **Django Admin:** http://localhost:8000/admin
- **API根路径:** http://localhost:8000/api/v1/
- **WebSocket:** ws://localhost:8000/ws/projects/{project_id}/

## 关键实现细节

### Redis 数据库分离策略

系统使用5个独立的Redis数据库，避免数据冲突：

```python
# config/settings/base.py
CELERY_BROKER_URL = 'redis://localhost:6379/0'      # 数据库0: Celery任务队列
CELERY_RESULT_BACKEND = 'redis://localhost:6379/1'  # 数据库1: Celery结果存储
REDIS_PUBSUB_URL = 'redis://localhost:6379/2'       # 数据库2: Pub/Sub专用
CHANNEL_LAYERS = {'hosts': ['redis://localhost:6379/3']}  # 数据库3: Channels专用
CACHES = {'LOCATION': 'redis://localhost:6379/4'}   # 数据库4: Django缓存
```

### WebSocket 消息格式规范

所有WebSocket消息遵循统一格式：

```javascript
// Token流式输出
{
  "type": "token",
  "content": "生成的文本片段",
  "full_text": "累积的完整文本"
}

// 阶段更新
{
  "type": "stage_update",
  "stage": "rewrite",
  "status": "processing",
  "message": "正在生成..."
}

// 进度更新（文生图/图生视频）
{
  "type": "progress",
  "current": 3,
  "total": 10,
  "message": "正在生成第3/10张图片"
}

// 完成
{
  "type": "done",
  "full_text": "完整的生成结果",
  "metadata": {...}
}

// 错误
{
  "type": "error",
  "error": "错误信息"
}
```

### 处理器数据流转规则

各阶段处理器的输入输出关系：

1. **rewrite (文案改写)**
   - 输入: `project.original_topic`
   - 输出: 保存到 `ContentRewrite.raw_text`
   - 下游: storyboard

2. **storyboard (分镜生成)**
   - 输入: `ContentRewrite.raw_text`
   - 输出: 保存到 `Storyboard` 模型（多条记录）
   - 下游: image_generation, camera_movement

3. **image_generation (文生图)**
   - 输入: `Storyboard.image_prompt`
   - 输出: 保存到 `GeneratedImage` 模型
   - 下游: video_generation

4. **camera_movement (运镜生成)**
   - 输入: `Storyboard.scene_description`
   - 输出: 保存到 `CameraMovement` 模型
   - 下游: video_generation

5. **video_generation (图生视频)**
   - 输入: `GeneratedImage` + `CameraMovement`
   - 输出: 保存到 `GeneratedVideo` 模型

### AI客户端工厂模式

动态创建AI客户端的流程：

```python
# core/ai_client/factory.py
def create_ai_client(provider: ModelProvider) -> BaseAIClient:
    """
    1. 从ModelProvider.executor_class获取类路径
    2. 如果为空，调用get_default_executor()获取默认执行器
    3. 动态导入并实例化客户端类
    4. 传入api_url, api_key, model_name等配置
    """
    executor_class_path = provider.executor_class or provider.get_default_executor()
    executor_class = get_executor_class(executor_class_path)
    return executor_class(
        api_url=provider.api_url,
        api_key=provider.api_key,
        model_name=provider.model_name
    )
```

### 前端WebSocket重连机制

```javascript
// frontend/src/utils/wsClient.js
// 指数退避重连策略
const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1)
// 第1次: 1秒, 第2次: 2秒, 第3次: 4秒, 第4次: 8秒, 第5次: 16秒
```

## 项目状态

### ✅ 后端已完成:
- Django项目结构和配置
- 12个领域模型 + Django Admin
- AI客户端抽象层 (基类 + 3个具体实现)
- Pipeline工作流引擎
- 4个阶段处理器 (LLMStageProcessor, Text2ImageStageProcessor, Image2VideoStageProcessor)
- Celery异步任务系统 (3个任务队列)
- WebSocket Consumer (ProjectStageConsumer, ProjectConsumer)
- Redis Pub/Sub 流式架构
- RESTful API (ProjectViewSet 18个action)

### ✅ 前端已完成:
- Vue 2 + Vuex + Vue Router 完整框架
- daisyUI 4.12.23 + Tailwind CSS 3.4.17 UI系统
- Layout布局组件(响应式侧边栏 + 导航栏)
- 3个公共组件(PageCard、StatusBadge、LoadingContainer)
- 项目列表页面(完整迁移到daisyUI)
- 4个Vuex模块(状态管理)
- 6个API服务层(封装后端接口)
- WebSocket实时通信客户端(支持自动重连)

### ⏳ 待开发:
- 负载均衡器实现 (已有接口，未实现具体策略)
- 前端剩余页面迁移到daisyUI
- 用户认证UI
- 图片/视频查看器组件
- 批量操作功能
- 单元测试和集成测试

## 特别注意

### 异步操作
- 所有Pipeline处理器必须是 `async` 方法
- AI客户端调用必须是 `async`
- Django ORM异步操作使用 `aget()`, `acreate()`, `aupdate()` 等方法

### 错误处理
- 使用自定义异常: `ValidationError`, `ProcessingError`
- 阶段失败自动重试 (指数退避: 1s, 2s, 4s)
- 在 `on_failure()` 中更新 ProjectStage 状态

### 安全
- ModelProvider.api_key 使用加密存储 (需实现 `EncryptedCharField`)
- API密钥不得硬编码在代码中
- CORS配置仅允许可信域名

### 性能优化
- 使用 `select_related()` / `prefetch_related()` 避免N+1查询
- 大数据量操作使用 `iterator()` 或批量操作
- Redis缓存热点数据
- 图片/视频生成使用Celery异步任务

## 调试和故障排查

### 常见问题

**1. WebSocket连接失败**
```bash
# 检查ASGI服务器是否运行
ps aux | grep daphne

# 检查WebSocket路由配置
cd backend && uv run python manage.py shell
>>> from apps.projects.routing import websocket_urlpatterns
>>> print(websocket_urlpatterns)

# 测试WebSocket连接
# 使用浏览器控制台或wscat工具
wscat -c ws://localhost:8000/ws/projects/{project_id}/stage/rewrite/
```

**2. Celery任务不执行**
```bash
# 检查Redis是否运行
redis-cli ping  # 应返回 PONG

# 检查Celery Worker是否运行
uv run celery -A config inspect active

# 查看Celery日志
uv run celery -A config worker -l debug

# 手动测试任务
cd backend && uv run python manage.py shell
>>> from apps.projects.tasks import execute_llm_stage
>>> result = execute_llm_stage.delay('project_id', 'rewrite', {}, 1)
>>> print(result.id)
```

**3. 流式输出不显示**
```bash
# 检查Redis Pub/Sub是否工作
redis-cli
> SUBSCRIBE ai_story:project:*
# 在另一个终端触发任务，观察是否有消息

# 检查RedisStreamPublisher配置
cd backend && uv run python manage.py shell
>>> from core.redis.publisher import RedisStreamPublisher
>>> publisher = RedisStreamPublisher('test-project', 'rewrite')
>>> publisher.publish_token('test', 'test')
```

**4. 前端API请求401错误**
```javascript
// 检查localStorage中的token
console.log(localStorage.getItem('access_token'))

// 检查token是否过期
// JWT配置: ACCESS_TOKEN_LIFETIME = 8小时
```

### 日志查看

**后端日志**:
```bash
# Django开发服务器日志（实时）
cd backend && uv run python manage.py runserver

# Celery Worker日志
uv run celery -A config worker -l info

# 查看特定模块日志
# 在代码中使用: logger = logging.getLogger(__name__)
```

**前端日志**:
```bash
# 开发服务器日志
cd frontend && npm run dev

# 浏览器控制台
# WebSocket消息: [WebSocket] 前缀
# API请求: Network标签
```

### 性能监控

**Celery监控 (Flower)**:
```bash
cd backend
uv add flower
uv run celery -A config flower
# 访问 http://localhost:5555
```

**Redis监控**:
```bash
# 实时监控所有命令
redis-cli monitor

# 查看内存使用
redis-cli info memory

# 查看连接数
redis-cli info clients

# 查看各数据库的key数量
redis-cli info keyspace
```

**Django调试工具栏**:
```bash
# 已安装在开发环境
# 访问任意API页面，右侧会显示调试面板
# 可查看SQL查询、缓存命中、信号等
```

### 数据库操作技巧

**查看模型关系**:
```bash
cd backend && uv run python manage.py shell
>>> from apps.projects.models import Project
>>> from apps.content.models import Storyboard

# 查看项目的所有分镜
>>> project = Project.objects.get(id='xxx')
>>> storyboards = project.storyboards.all().order_by('sequence_number')

# 查看分镜的所有生成图片
>>> storyboard = Storyboard.objects.first()
>>> images = storyboard.generated_images.all()

# 预加载关联数据（避免N+1查询）
>>> projects = Project.objects.select_related('template_set').prefetch_related('storyboards')
```

**重置数据库**:
```bash
cd backend

# 删除所有迁移文件（保留__init__.py）
find apps -path "*/migrations/*.py" -not -name "__init__.py" -delete

# 删除数据库
rm db.sqlite3

# 重新创建迁移
uv run python manage.py makemigrations

# 执行迁移
uv run python manage.py migrate

# 创建超级用户
uv run python manage.py createsuperuser
```


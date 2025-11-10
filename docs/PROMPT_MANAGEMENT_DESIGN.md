# 提示词管理功能设计文档

## 功能概述

提示词管理是AI Story生成系统的核心模块之一，负责管理和优化用于各个工作流阶段的AI提示词模板。该功能支持提示词集的创建、版本管理、实时预览和AI驱动的效果评估。

## 核心功能

### 1. 提示词集管理 (PromptTemplateSet)
- **CRUD操作**: 创建、查询、更新、删除提示词集
- **克隆功能**: 快速复制现有提示词集
- **默认设置**: 设置和获取默认提示词集
- **权限控制**: 非管理员只能管理自己创建的提示词集

### 2. 提示词模板管理 (PromptTemplate)
- **CRUD操作**: 管理五个阶段的提示词模板
  - 文案改写 (rewrite)
  - 分镜生成 (storyboard)
  - 文生图 (image_generation)
  - 运镜生成 (camera_movement)
  - 图生视频 (video_generation)
- **变量支持**: 使用Jinja2模板语法支持动态变量
- **变量验证**: 自动提取和验证模板中使用的变量

### 3. 版本管理
- **版本创建**: 创建提示词模板的新版本
- **版本历史**: 查看和对比历史版本
- **版本激活**: 旧版本自动停用，新版本自动激活

### 4. 模板验证与预览
- **语法验证**: 实时验证Jinja2模板语法
- **实时预览**: 使用实际变量值预览渲染结果
- **错误提示**: 详细的语法错误信息

### 5. AI驱动的效果评估
- **多维度评分**: 从清晰度、具体性、创造性三个维度评估
- **优化建议**: AI生成针对性的改进建议
- **优缺点分析**: 自动识别提示词的优点和缺点

## 技术架构

### 后端架构

#### 1. 数据模型层 ([models.py](../backend/apps/prompts/models.py))

```python
PromptTemplateSet:
├── id (UUID)
├── name (提示词集名称)
├── description (描述)
├── is_active (是否激活)
├── is_default (是否默认)
└── created_by (创建者)

PromptTemplate:
├── id (UUID)
├── template_set (关联提示词集)
├── stage_type (阶段类型)
├── template_content (模板内容 - 支持Jinja2)
├── variables (变量定义 - JSONField)
├── version (版本号)
└── is_active (是否激活)
```

#### 2. 序列化器层 ([serializers.py](../backend/apps/prompts/serializers.py))

**设计原则**: 遵循单一职责原则(SRP)，每个序列化器专注一项任务

- `PromptTemplateSetSerializer`: 完整的提示词集序列化
- `PromptTemplateSetListSerializer`: 列表视图的简化版本
- `PromptTemplateSerializer`: 完整的模板序列化，包含变量提取
- `PromptTemplateListSerializer`: 列表视图的简化版本
- `PromptTemplatePreviewSerializer`: 预览请求序列化
- `PromptTemplateValidateSerializer`: 验证请求序列化
- `PromptTemplateEvaluationSerializer`: 评估结果序列化

**核心验证逻辑**:
- 自动提取模板中使用的Jinja2变量
- 验证变量定义格式和类型
- 交叉验证模板和变量定义的一致性

#### 3. 视图层 ([views.py](../backend/apps/prompts/views.py))

**设计原则**: 遵循单一职责原则(SRP)和依赖倒置原则(DIP)

**PromptTemplateSetViewSet**:
- 标准CRUD操作
- `clone()`: 克隆提示词集及其所有模板
- `set_default()`: 设置默认提示词集(需管理员权限)
- `default()`: 获取默认提示词集

**PromptTemplateViewSet**:
- 标准CRUD操作
- `create_version()`: 创建新版本并自动停用旧版本
- `versions()`: 获取版本历史
- `validate()`: 验证模板语法
- `preview()`: 渲染预览结果
- `evaluate()`: AI评估提示词效果

#### 4. 业务逻辑层 ([services.py](../backend/apps/prompts/services.py))

**PromptEvaluationService**:

```python
职责: 使用AI模型评估提示词质量
方法:
├── evaluate_prompt(): 评估单个提示词
├── compare_prompts(): 对比两个提示词
└── suggest_improvements(): 生成改进建议

评估维度:
├── 清晰度 (Clarity): 0-10分
├── 具体性 (Specificity): 0-10分
├── 创造性 (Creativity): 0-10分
└── 总分 (Score): 0-10分

输出:
├── strengths: 优点列表
├── weaknesses: 缺点列表
└── suggestions: 改进建议列表
```

### 前端架构

#### 1. API服务层 ([api/prompts.js](../frontend/src/api/prompts.js))

**设计原则**: 遵循单一职责原则(SRP)，封装所有HTTP请求

**promptSetAPI** (提示词集API):
- `getList()`, `getDetail()`, `create()`, `update()`, `delete()`
- `clone()`, `setDefault()`, `getDefault()`

**promptTemplateAPI** (提示词模板API):
- `getList()`, `getDetail()`, `create()`, `update()`, `delete()`
- `createVersion()`, `getVersions()`
- `validate()`, `preview()`, `evaluate()`

**配置常量**:
- `STAGE_TYPES`: 阶段类型配置
- `VARIABLE_TYPES`: 变量类型配置

#### 2. 状态管理层 ([store/modules/prompts.js](../frontend/src/store/modules/prompts.js))

**State结构**:
```javascript
{
  // 提示词集
  promptSets: [],
  currentPromptSet: null,
  promptSetsTotal: 0,
  promptSetsLoading: false,

  // 提示词模板
  promptTemplates: [],
  currentPromptTemplate: null,
  promptTemplatesTotal: 0,
  promptTemplatesLoading: false,

  // 版本历史
  templateVersions: [],
  versionsLoading: false,

  // 评估结果
  evaluationResult: null,
  evaluationLoading: false,

  // 预览结果
  previewResult: null,
  previewLoading: false,
}
```

**Getters**:
- `activePromptSets`: 获取激活的提示词集
- `defaultPromptSet`: 获取默认提示词集
- `getTemplateByStageType`: 根据阶段类型获取模板
- `currentSetTemplates`: 获取当前提示词集的模板列表

**Actions** (26个异步操作):
- 提示词集: 8个操作 (fetchPromptSets, createPromptSet, ...)
- 提示词模板: 18个操作 (fetchPromptTemplates, updatePromptTemplate, ...)

#### 3. 路由配置 ([router/index.js](../frontend/src/router/index.js))

```javascript
/prompts                           # 提示词列表
/prompts/sets/create               # 创建提示词集
/prompts/sets/:id                  # 提示词集详情
/prompts/sets/:id/edit             # 编辑提示词集
/prompts/templates/:id/edit        # 编辑提示词模板
```

#### 4. 页面组件 (待实现)

**PromptList.vue** (提示词列表页):
- 提示词集卡片展示
- 搜索和过滤功能
- 克隆、删除、设为默认操作
- 使用daisyUI组件库

**PromptSetDetail.vue** (提示词集详情页):
- 提示词集基本信息
- 包含的5个阶段模板展示
- 每个模板的快捷编辑入口
- 版本历史查看

**PromptSetForm.vue** (提示词集表单):
- 创建/编辑提示词集
- 表单验证
- 响应式布局

**PromptTemplateEditor.vue** (提示词编辑器):
- Monaco Editor或CodeMirror集成
- Jinja2语法高亮
- 变量自动提取和高亮
- 实时语法验证
- 预览面板(split view)
- 变量输入区
- AI评估按钮和结果展示

**VersionHistory.vue** (版本历史组件):
- 版本列表
- Diff视图对比
- 版本回滚功能

## API接口文档

### 提示词集API

#### 1. 获取提示词集列表
```
GET /api/v1/prompts/sets/
Query: ?is_active=true&is_default=true&page=1&page_size=10

Response:
{
  "count": 100,
  "next": "...",
  "previous": "...",
  "results": [
    {
      "id": "uuid",
      "name": "默认提示词集",
      "description": "...",
      "is_active": true,
      "is_default": true,
      "created_by": {...},
      "templates_count": 5,
      "created_at": "...",
      "updated_at": "..."
    }
  ]
}
```

#### 2. 创建提示词集
```
POST /api/v1/prompts/sets/
Body:
{
  "name": "新提示词集",
  "description": "描述",
  "is_active": true
}

Response: 201 Created
{
  "id": "uuid",
  "name": "新提示词集",
  ...
}
```

#### 3. 克隆提示词集
```
POST /api/v1/prompts/sets/{id}/clone/
Body:
{
  "name": "克隆的提示词集"
}

Response: 201 Created
```

#### 4. 设置默认提示词集
```
POST /api/v1/prompts/sets/{id}/set_default/

Response: 200 OK
```

### 提示词模板API

#### 1. 获取模板列表
```
GET /api/v1/prompts/templates/
Query: ?template_set={set_id}&stage_type=rewrite&is_active=true

Response:
{
  "count": 50,
  "results": [
    {
      "id": "uuid",
      "stage_type": "rewrite",
      "stage_type_display": "文案改写",
      "version": 2,
      "is_active": true,
      "updated_at": "..."
    }
  ]
}
```

#### 2. 创建新版本
```
POST /api/v1/prompts/templates/{id}/create_version/
Body:
{
  "template_content": "新版本的模板内容 {{topic}}",
  "variables": {
    "topic": "string",
    "style": "string"
  }
}

Response: 201 Created
{
  "id": "new_uuid",
  "version": 3,
  "is_active": true,
  ...
}
```

#### 3. 验证模板语法
```
POST /api/v1/prompts/templates/{id}/validate/
Body:
{
  "template_content": "测试模板 {{variable}}"
}

Response: 200 OK
{
  "valid": true,
  "message": "模板语法正确"
}

或

Response: 400 Bad Request
{
  "template_content": ["模板语法错误: unexpected 'end of template'"]
}
```

#### 4. 预览模板
```
POST /api/v1/prompts/templates/{id}/preview/
Body:
{
  "variables": {
    "topic": "科幻故事",
    "style": "赛博朋克"
  }
}

Response: 200 OK
{
  "success": true,
  "rendered_content": "生成一个科幻故事,风格为赛博朋克...",
  "variables_used": {...}
}
```

#### 5. AI评估提示词
```
POST /api/v1/prompts/templates/{id}/evaluate/

Response: 200 OK
{
  "score": 8.5,
  "clarity": 9.0,
  "specificity": 8.5,
  "creativity": 8.0,
  "strengths": [
    "指令清晰明确",
    "提供了具体的风格要求"
  ],
  "weaknesses": [
    "缺少输出长度限制",
    "未指定目标受众"
  ],
  "suggestions": [
    "建议添加输出长度限制,如'500字以内'",
    "明确目标受众,如'适合成年读者'"
  ]
}
```

## 数据流

### 1. 创建提示词集流程
```
用户操作 → PromptSetForm.vue
    ↓
前端验证
    ↓
dispatch('prompts/createPromptSet', data)
    ↓
promptSetAPI.create(data)
    ↓
POST /api/v1/prompts/sets/
    ↓
PromptTemplateSetViewSet.create()
    ↓
PromptTemplateSetSerializer.validate()
    ↓
保存到数据库
    ↓
返回新创建的提示词集
    ↓
commit('ADD_PROMPT_SET', response)
    ↓
更新Vuex状态
    ↓
页面自动更新
```

### 2. AI评估流程
```
用户点击"评估"按钮
    ↓
dispatch('prompts/evaluateTemplate', templateId)
    ↓
promptTemplateAPI.evaluate(templateId)
    ↓
POST /api/v1/prompts/templates/{id}/evaluate/
    ↓
PromptTemplateViewSet.evaluate()
    ↓
PromptEvaluationService.evaluate_prompt()
    ↓
构建评估提示词
    ↓
调用AI模型 (OpenAI/Claude)
    ↓
解析评估结果 (JSON)
    ↓
返回评估数据
    ↓
commit('SET_EVALUATION_RESULT', response)
    ↓
显示评估结果卡片
```

## 设计原则应用

### SOLID原则

1. **单一职责原则 (SRP)**:
   - 每个序列化器只负责一个模型
   - 每个ViewSet只负责一个资源
   - 评估服务独立于ViewSet

2. **开闭原则 (OCP)**:
   - 提示词模板可扩展(添加新阶段类型无需修改现有代码)
   - AI客户端可扩展(支持不同的AI提供商)

3. **里氏替换原则 (LSP)**:
   - 所有序列化器可互换使用
   - 所有AI客户端实现可互换

4. **接口隔离原则 (ISP)**:
   - 列表序列化器和详情序列化器分离
   - 不同操作的序列化器独立(Preview, Validate, Evaluation)

5. **依赖倒置原则 (DIP)**:
   - ViewSet依赖序列化器抽象
   - 评估服务依赖AI客户端抽象

### KISS (简单至上)
- API设计直观易懂
- 状态管理结构清晰
- 避免过度封装

### DRY (杜绝重复)
- API服务层统一封装HTTP请求
- Vuex mutations复用逻辑
- 序列化器字段定义复用

### YAGNI (精益求精)
- 仅实现明确需要的功能
- 避免未来功能预留
- 版本控制采用简单实现(可后续扩展)

## 安全考虑

1. **权限控制**:
   - 非管理员只能管理自己创建的提示词集
   - 设置默认提示词集需要管理员权限
   - 查询自动过滤用户无权访问的数据

2. **输入验证**:
   - Jinja2模板语法验证
   - 变量定义格式验证
   - 防止模板注入攻击

3. **API限流**:
   - AI评估接口需要限流(成本考虑)
   - 使用ModelProvider的rate_limit配置

## 性能优化

1. **数据库查询优化**:
   - 使用`select_related('created_by')`减少查询
   - 使用`prefetch_related('templates')`预加载关联数据
   - 列表视图使用简化序列化器减少数据传输

2. **前端性能**:
   - 列表和详情使用不同的序列化器
   - Vuex状态缓存减少重复请求
   - 模板编辑器使用防抖(debounce)减少验证请求

3. **AI调用优化**:
   - 评估结果可缓存
   - 使用较低的temperature(0.3)获得一致性结果
   - 批量评估可异步处理

## 扩展性

### 未来可扩展功能

1. **完整版本控制**:
   - 集成django-simple-history
   - 支持任意版本回滚
   - 版本Diff可视化

2. **协作功能**:
   - 提示词集共享
   - 多人协作编辑
   - 评论和建议系统

3. **A/B测试**:
   - 同时测试多个提示词版本
   - 自动统计效果数据
   - 推荐最佳版本

4. **提示词市场**:
   - 公共提示词库
   - 用户上传和分享
   - 评分和评论系统

5. **智能优化**:
   - 基于历史数据的提示词优化
   - 自动A/B测试
   - 机器学习推荐

## 测试策略

### 后端测试
```python
# tests/test_prompts.py
- 测试提示词集CRUD
- 测试模板变量提取
- 测试模板语法验证
- 测试权限控制
- 测试版本管理
- 模拟AI评估服务
```

### 前端测试
```javascript
// tests/prompts.spec.js
- 测试Vuex actions
- 测试组件渲染
- 测试用户交互
- 测试表单验证
- 测试API调用
```

## 部署注意事项

1. **环境变量**:
   ```bash
   # AI评估需要配置LLM API
   OPENAI_API_KEY=sk-xxx
   ```

2. **数据库迁移**:
   ```bash
   uv run python manage.py makemigrations prompts
   uv run python manage.py migrate
   ```

3. **依赖安装**:
   ```bash
   # 后端: Jinja2已包含在Django中
   # 前端: 无额外依赖
   ```

4. **静态文件**:
   ```bash
   # 前端构建
   cd frontend && npm run build
   ```

## 已完成工作

### 后端 (100%完成)
- ✅ 数据模型 (models.py)
- ✅ 9个序列化器 (serializers.py)
- ✅ 2个ViewSet with 10个自定义action (views.py)
- ✅ 评估服务 (services.py)
- ✅ URL配置 (urls.py)
- ✅ 完整的API接口

### 前端 (50%完成)
- ✅ API服务层 (api/prompts.js)
- ✅ Vuex状态管理 (store/modules/prompts.js)
- ✅ 路由配置 (router/index.js)
- ⏳ 页面组件 (待实现)
- ⏳ 编辑器组件 (待实现)
- ⏳ 版本历史组件 (待实现)

## 下一步工作

1. **实现提示词列表页面** (PromptList.vue)
   - 使用daisyUI卡片组件
   - 搜索和过滤功能
   - 操作按钮(编辑、克隆、删除)

2. **实现提示词编辑器** (PromptTemplateEditor.vue)
   - Monaco Editor集成
   - Jinja2语法高亮
   - 实时预览面板
   - AI评估集成

3. **实现版本历史组件** (VersionHistory.vue)
   - 版本列表
   - Diff对比视图

4. **测试和优化**
   - 单元测试
   - 集成测试
   - 性能测试

---

**文档版本**: 1.0
**创建日期**: 2025-10-16
**作者**: AI Story生成系统开发团队
**状态**: 后端完成，前端进行中

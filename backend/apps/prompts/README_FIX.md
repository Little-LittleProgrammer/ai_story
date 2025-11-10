# 提示词模板重复问题修复指南

## 问题描述

由于数据库唯一约束 `unique_together = [('template_set', 'stage_type')]`，同一个提示词集中不能存在两个相同阶段类型的模板。如果数据库中已存在重复数据，会导致创建新模板时报错。

## 错误信息

```
字段 template_set, stage_type 必须能构成唯一集合。
```

## 修复方案

### 方案一：使用管理命令清理（推荐）

我们提供了一个 Django 管理命令来自动清理重复数据。

#### 1. 预览将要删除的记录（dry-run模式）

```bash
cd backend
python manage.py fix_duplicate_templates --dry-run
```

或使用 uv：

```bash
cd backend
uv run python manage.py fix_duplicate_templates --dry-run
```

这会显示哪些记录将被删除，但不会实际执行删除操作。

#### 2. 执行清理

```bash
cd backend
python manage.py fix_duplicate_templates
```

或使用 uv：

```bash
cd backend
uv run python manage.py fix_duplicate_templates
```

**清理策略：**
- 保留版本最高、创建时间最新的记录
- 删除其他重复记录

### 方案二：手动清理（高级用户）

如果你想手动清理，可以使用 Django Shell：

```bash
cd backend
python manage.py shell
```

或使用 uv：

```bash
cd backend
uv run python manage.py shell
```

然后执行以下代码：

```python
from apps.prompts.models import PromptTemplate
from django.db.models import Count

# 查找重复记录
duplicates = (
    PromptTemplate.objects
    .values('template_set', 'stage_type')
    .annotate(count=Count('id'))
    .filter(count__gt=1)
)

# 逐个处理
for dup in duplicates:
    templates = PromptTemplate.objects.filter(
        template_set_id=dup['template_set'],
        stage_type=dup['stage_type']
    ).order_by('-version', '-created_at')

    # 保留第一个，删除其他
    keep = templates.first()
    delete_list = templates[1:]

    print(f"保留: {keep.id}, 删除: {[t.id for t in delete_list]}")

    for template in delete_list:
        template.delete()
```

## 预防措施

修复已完成以下改进，防止未来再次出现此问题：

### 后端改进

1. **序列化器验证增强** (`backend/apps/prompts/serializers.py:142-155`)
   - 在创建/更新前验证 `template_set + stage_type` 唯一性
   - 提供友好的错误提示

2. **ViewSet 自动处理** (`backend/apps/prompts/views.py:183-206`)
   - 在 `perform_create` 中自动删除旧模板
   - 验证用户权限

### 前端改进

1. **模板列表正确显示** (`frontend/src/views/prompts/PromptSetDetail.vue`)
   - 直接从 API 返回的提示词集详情中获取模板列表
   - 修复了模板列表不显示的问题

2. **创建前友好提示** (`frontend/src/views/prompts/PromptTemplateEditor.vue:716-739`)
   - 创建前检查是否存在相同阶段的模板
   - 给用户确认提示，避免误操作

## 验证修复

修复后，你可以验证：

1. **查看提示词集详情页面**
   - 访问 http://localhost:3000/prompts
   - 点击某个提示词集
   - 应该能看到该提示词集的所有模板

2. **尝试创建重复模板**
   - 创建一个已存在阶段类型的模板
   - 应该会弹出确认对话框
   - 确认后，旧模板会被自动替换

3. **检查数据库**
   ```bash
   cd backend
   python manage.py shell
   ```

   ```python
   from apps.prompts.models import PromptTemplate
   from django.db.models import Count

   duplicates = (
       PromptTemplate.objects
       .values('template_set', 'stage_type')
       .annotate(count=Count('id'))
       .filter(count__gt=1)
   )

   print(f"重复记录数: {len(duplicates)}")
   # 应该输出: 重复记录数: 0
   ```

## 需要帮助？

如果遇到问题，请检查：

1. Django 和依赖包是否正确安装
2. 数据库迁移是否已执行：`python manage.py migrate`
3. 前端是否已重新构建：`npm run dev`

如果问题仍然存在，请查看：
- 后端日志：Django 控制台输出
- 前端日志：浏览器控制台（F12）
- 网络请求：浏览器开发者工具 Network 标签

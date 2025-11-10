# StoryboardViewer 组件使用文档

## 组件说明

`StoryboardViewer` 是一个用于展示分镜数据的可视化组件,支持卡片视图和JSON原始格式的切换展示。

## 功能特性

✅ **双视图模式**
- 卡片视图: 美观的网格布局,每个分镜一张卡片
- JSON视图: 格式化的原始JSON数据展示

✅ **响应式设计**
- 移动端: 单列布局
- 平板: 双列布局
- 桌面: 三列布局

✅ **交互功能**
- 复制单个分镜的提示词
- 复制完整JSON数据
- 折叠/展开视觉描述

✅ **数据格式兼容**
- 支持JSON字符串或对象
- 自动识别多种数据结构

## 使用方法

### 基础用法

```vue
<template>
  <StoryboardViewer :data="storyboardData" />
</template>

<script>
import StoryboardViewer from '@/components/content/StoryboardViewer.vue';

export default {
  components: {
    StoryboardViewer,
  },
  data() {
    return {
      storyboardData: {
        scenes: [
          {
            scene_number: 1,
            narration: "我是宝宝,我还不会说话。",
            visual_prompt: "温馨婴儿房内,婴儿坐在柔软米白色地毯上...",
            shot_type: "特写"
          }
        ]
      }
    };
  }
};
</script>
```

### 在StageContent中使用

组件已经集成到 `StageContent.vue` 中,当 `stageType === 'storyboard'` 且有输出数据时自动显示。

```vue
<!-- 会自动在分镜阶段显示可视化视图 -->
<StageContent
  stage-type="storyboard"
  :stage="currentStage"
  :all-stages="allStages"
  :project-id="projectId"
  @save="handleSave"
  @execute="handleExecute"
/>
```

## Props

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| data | String \| Object | null | 分镜数据,可以是JSON字符串或对象 |

## 支持的数据格式

### 格式1: 标准格式 (推荐)

```json
{
  "scenes": [
    {
      "scene_number": 1,
      "narration": "旁白文本",
      "visual_prompt": "视觉提示词",
      "shot_type": "镜头类型"
    }
  ]
}
```

### 格式2: 直接数组

```json
[
  {
    "scene_number": 1,
    "narration": "旁白文本",
    "visual_prompt": "视觉提示词",
    "shot_type": "镜头类型"
  }
]
```

### 格式3: 使用storyboards字段

```json
{
  "storyboards": [
    {
      "scene_number": 1,
      "narration": "旁白文本",
      "visual_prompt": "视觉提示词",
      "shot_type": "镜头类型"
    }
  ]
}
```

## 字段说明

每个分镜对象支持以下字段:

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| scene_number | Number | ✅ | 分镜序号 |
| narration | String | ✅ | 旁白文本 |
| visual_prompt | String | ✅ | 视觉提示词(用于图片生成) |
| shot_type | String | ❌ | 镜头类型(特写/中景/全景等),默认"标准镜头" |

## 样式定制

组件使用 daisyUI 主题系统,会自动适配当前主题颜色。

### 主要使用的daisyUI组件

- `tabs` / `tabs-boxed` - 视图切换选项卡
- `card` - 分镜卡片
- `badge` - 标签徽章
- `collapse` - 折叠面板
- `btn` - 按钮
- `mockup-code` - 代码展示框

## 示例数据

完整的示例数据:

```json
{
  "scenes": [
    {
      "scene_number": 1,
      "narration": "我是宝宝,我还不会说话。",
      "visual_prompt": "温馨婴儿房内,婴儿坐在柔软米白色地毯上,穿着浅黄色连体衣,衣服上有'小方圆'印花,大眼睛直视镜头,嘴角微笑,发出声音的样子,特写视角,3D渲染,皮克斯动画风格,软质材质,圆润轮廓,柔和阴影,暖色调,阳光感,低饱和度,奶油色背景,柔和高光",
      "shot_type": "特写"
    },
    {
      "scene_number": 2,
      "narration": "你们看到我头有点尖、有点肿。",
      "visual_prompt": "婴儿床内,宝宝躺着,穿着浅黄色连体衣,衣服上有'小方圆'印花,父母低头看着宝宝,表情担忧,中景视角,3D渲染,皮克斯动画风格,软质材质,圆润轮廓,柔和阴影,暖色调,阳光感,低饱和度,奶油色背景,柔和高光",
      "shot_type": "中景"
    }
  ]
}
```

## 常见问题

### Q: 数据无法显示?

A: 检查以下几点:
1. 数据格式是否正确(需要包含 `scenes` 字段或直接是数组)
2. 每个分镜对象是否包含必填字段 `scene_number`, `narration`, `visual_prompt`
3. 打开浏览器控制台查看是否有JSON解析错误

### Q: 如何添加更多字段?

A: 修改组件模板,在卡片中添加新的展示区域:

```vue
<!-- 在卡片中添加新字段 -->
<div class="mb-3">
  <div class="text-xs font-semibold text-base-content/60 mb-1">
    新字段名
  </div>
  <p class="text-sm">{{ scene.新字段 }}</p>
</div>
```

### Q: 能否修改卡片布局?

A: 可以修改 `grid-cols-*` 类来调整列数:

```vue
<!-- 修改为2列布局 -->
<div class="grid grid-cols-1 md:grid-cols-2 gap-4">

<!-- 修改为4列布局 -->
<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
```

## 技术实现

- **框架**: Vue 2.7
- **UI库**: daisyUI 4.12.23 + Tailwind CSS 3.4.17
- **依赖**:
  - Clipboard API (用于复制功能)
  - Element UI Message (可选,用于提示消息)

## 浏览器兼容性

- Chrome/Edge: 完全支持
- Firefox: 完全支持
- Safari: 完全支持
- IE11: 不支持 (需要 polyfill)

## 更新日志

### v1.0.0 (2025-10-17)
- ✅ 初始版本发布
- ✅ 支持卡片/JSON双视图切换
- ✅ 响应式布局
- ✅ 复制功能
- ✅ 多种数据格式兼容

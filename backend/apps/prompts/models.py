"""
提示词管理领域模型
遵循开闭原则(OCP): 提示词模板可扩展,无需修改核心代码
"""

import uuid
from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


class PromptTemplateSet(models.Model):
    """
    提示词集
    职责: 组织和管理提示词模板集合
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField('名称', max_length=255)
    description = models.TextField('描述', blank=True)
    is_active = models.BooleanField('是否激活', default=True)
    is_default = models.BooleanField('是否默认', default=False)

    created_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name='创建者',
        related_name='prompt_sets'
    )

    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        db_table = 'prompt_template_sets'
        verbose_name = '提示词集'
        verbose_name_plural = '提示词集'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['is_active', 'is_default']),
        ]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        """确保只有一个默认提示词集"""
        if self.is_default:
            PromptTemplateSet.objects.filter(is_default=True).update(is_default=False)
        super().save(*args, **kwargs)


class PromptTemplate(models.Model):
    """
    提示词模板
    职责: 存储和管理单个阶段的提示词模板
    支持Jinja2模板语法
    """

    STAGE_TYPES = [
        ('rewrite', '文案改写'),
        ('storyboard', '分镜生成'),
        ('image_generation', '文生图'),
        ('camera_movement', '运镜生成'),
        ('video_generation', '图生视频'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    template_set = models.ForeignKey(
        PromptTemplateSet,
        on_delete=models.CASCADE,
        related_name='templates',
        verbose_name='提示词集'
    )

    stage_type = models.CharField('阶段类型', max_length=20, choices=STAGE_TYPES)

    # 关联的模型提供商 (该阶段使用的默认模型)
    model_provider = models.ForeignKey(
        'models.ModelProvider',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='prompt_templates',
        verbose_name='模型提供商',
        help_text='该提示词模板默认使用的AI模型'
    )

    # 模板内容 (支持Jinja2语法)
    template_content = models.TextField('模板内容')

    # 变量定义 (JSON格式)
    # 示例: {"topic": "string", "style": "string", "length": "int"}
    variables = models.JSONField('变量定义', default=dict, blank=True)

    # 版本控制
    version = models.IntegerField('版本', default=1)
    is_active = models.BooleanField('是否激活', default=True)

    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        db_table = 'prompt_templates'
        verbose_name = '提示词模板'
        verbose_name_plural = '提示词模板'
        unique_together = [('template_set', 'stage_type')]
        indexes = [
            models.Index(fields=['template_set', 'stage_type', 'is_active']),
        ]

    def __str__(self):
        return f'{self.template_set.name} - {self.get_stage_type_display()}'

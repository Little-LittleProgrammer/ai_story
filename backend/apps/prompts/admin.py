"""提示词管理Admin配置"""
from django.contrib import admin
from .models import PromptTemplateSet, PromptTemplate


@admin.register(PromptTemplateSet)
class PromptTemplateSetAdmin(admin.ModelAdmin):
    list_display = ['name', 'is_active', 'is_default', 'created_by', 'created_at']
    list_filter = ['is_active', 'is_default']
    search_fields = ['name', 'description']


@admin.register(PromptTemplate)
class PromptTemplateAdmin(admin.ModelAdmin):
    list_display = ['template_set', 'stage_type', 'version', 'is_active', 'created_at']
    list_filter = ['stage_type', 'is_active']
    search_fields = ['template_content']

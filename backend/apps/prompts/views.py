"""
提示词管理视图
遵循单一职责原则(SRP): 每个ViewSet只负责一个模型的CRUD
遵循依赖倒置原则(DIP): 依赖抽象(序列化器)而非具体实现
"""

import asyncio

from django.db.models import Q
from django_filters.rest_framework import DjangoFilterBackend
from jinja2 import Template
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import PromptTemplate, PromptTemplateSet
from .serializers import (
    PromptTemplateEvaluationSerializer,
    PromptTemplateListSerializer,
    PromptTemplatePreviewSerializer,
    PromptTemplateSerializer,
    PromptTemplateSetListSerializer,
    PromptTemplateSetSerializer,
    PromptTemplateValidateSerializer,
)
from .services import PromptEvaluationService


class PromptTemplateSetViewSet(viewsets.ModelViewSet):
    """
    提示词集ViewSet
    职责: 提示词集的CRUD和特殊操作
    """

    queryset = PromptTemplateSet.objects.all()
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['is_active', 'is_default', 'created_by']
    search_fields = ['name', 'description']
    ordering_fields = ['created_at', 'updated_at', 'name']
    ordering = ['-created_at']

    def get_serializer_class(self):
        """根据操作类型选择序列化器"""
        if self.action == 'list':
            return PromptTemplateSetListSerializer
        return PromptTemplateSetSerializer

    def get_queryset(self):
        """
        过滤查询集
        非管理员只能看到自己创建的或默认的提示词集
        """
        queryset = super().get_queryset()
        user = self.request.user

        if not user.is_staff:
            queryset = queryset.filter(
                Q(created_by=user) | Q(is_default=True)
            )

        return queryset.prefetch_related('templates', 'created_by')

    @action(detail=True, methods=['post'])
    def clone(self, request, pk=None):
        """
        克隆提示词集
        POST /api/v1/prompts/sets/{id}/clone/
        Body: {"name": "新提示词集名称"}
        """
        original_set = self.get_object()
        new_name = request.data.get('name')

        if not new_name:
            return Response(
                {'error': '请提供新提示词集的名称'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 创建新提示词集
        new_set = PromptTemplateSet.objects.create(
            name=new_name,
            description=f'克隆自: {original_set.name}',
            is_active=True,
            is_default=False,
            created_by=request.user
        )

        # 复制所有模板
        for template in original_set.templates.all():
            PromptTemplate.objects.create(
                template_set=new_set,
                stage_type=template.stage_type,
                template_content=template.template_content,
                variables=template.variables,
                version=1,
                is_active=True
            )

        serializer = self.get_serializer(new_set)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'])
    def set_default(self, request, pk=None):
        """
        设置为默认提示词集
        POST /api/v1/prompts/sets/{id}/set_default/
        需要管理员权限
        """
        if not request.user.is_staff:
            return Response(
                {'error': '只有管理员可以设置默认提示词集'},
                status=status.HTTP_403_FORBIDDEN
            )

        prompt_set = self.get_object()

        # 取消其他默认提示词集
        PromptTemplateSet.objects.filter(is_default=True).update(is_default=False)

        # 设置当前为默认
        prompt_set.is_default = True
        prompt_set.save()

        serializer = self.get_serializer(prompt_set)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def default(self, request):
        """
        获取默认提示词集
        GET /api/v1/prompts/sets/default/
        """
        default_set = PromptTemplateSet.objects.filter(is_default=True).first()

        if not default_set:
            return Response(
                {'error': '未设置默认提示词集'},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = self.get_serializer(default_set)
        return Response(serializer.data)


class PromptTemplateViewSet(viewsets.ModelViewSet):
    """
    提示词模板ViewSet
    职责: 提示词模板的CRUD和特殊操作
    """

    queryset = PromptTemplate.objects.all()
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['template_set', 'stage_type', 'is_active']
    search_fields = ['template_content']
    ordering_fields = ['created_at', 'updated_at', 'version']
    ordering = ['-updated_at']

    def get_serializer_class(self):
        """根据操作类型选择序列化器"""
        if self.action == 'list':
            return PromptTemplateListSerializer
        return PromptTemplateSerializer

    def get_queryset(self):
        """
        过滤查询集
        非管理员只能看到自己创建的提示词集的模板
        """
        queryset = super().get_queryset()
        user = self.request.user

        if not user.is_staff:
            queryset = queryset.filter(
                Q(template_set__created_by=user) |
                Q(template_set__is_default=True)
            )

        return queryset.select_related('template_set', 'model_provider')

    def perform_create(self, serializer):
        """
        创建提示词模板时，检查是否已存在相同 template_set + stage_type 的模板
        如果存在，删除旧模板或提示用户更新
        """
        template_set = serializer.validated_data.get('template_set')
        stage_type = serializer.validated_data.get('stage_type')

        # 检查是否存在相同的模板
        existing_template = PromptTemplate.objects.filter(
            template_set=template_set,
            stage_type=stage_type
        ).first()

        if existing_template:
            # 验证权限
            if existing_template.template_set.created_by != self.request.user and not self.request.user.is_staff:
                from rest_framework.exceptions import PermissionDenied
                raise PermissionDenied('无权限修改此模板')

            # 删除旧模板（可选：改为更新旧模板）
            existing_template.delete()

        serializer.save()

    @action(detail=True, methods=['post'])
    def create_version(self, request, pk=None):
        """
        创建新版本
        POST /api/v1/prompts/templates/{id}/create_version/
        Body: {
            "template_content": "新模板内容",
            "variables": {"topic": "string"}
        }
        """
        original_template = self.get_object()

        # 验证权限
        if original_template.template_set.created_by != request.user and not request.user.is_staff:
            return Response(
                {'error': '无权限修改此模板'},
                status=status.HTTP_403_FORBIDDEN
            )

        # 创建新版本
        serializer = PromptTemplateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        new_template = PromptTemplate.objects.create(
            template_set=original_template.template_set,
            stage_type=original_template.stage_type,
            template_content=serializer.validated_data['template_content'],
            variables=serializer.validated_data.get('variables', {}),
            version=original_template.version + 1,
            is_active=True
        )

        # 停用旧版本
        original_template.is_active = False
        original_template.save()

        response_serializer = PromptTemplateSerializer(new_template)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['get'])
    def versions(self, request, pk=None):
        """
        获取版本历史
        GET /api/v1/prompts/templates/{id}/versions/

        注意: 当前实现返回同一stage_type的所有版本
        完整的版本控制需要使用django-simple-history
        """
        template = self.get_object()

        # 获取���一阶段类型的所有版本
        versions = PromptTemplate.objects.filter(
            template_set=template.template_set,
            stage_type=template.stage_type
        ).order_by('-version')

        serializer = PromptTemplateSerializer(versions, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def validate(self, request, pk=None):
        """
        验证模板语法
        POST /api/v1/prompts/templates/{id}/validate/
        Body: {"template_content": "要验证的模板内容"}
        """
        serializer = PromptTemplateValidateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        return Response({
            'valid': True,
            'message': '模板语法正确'
        })

    @action(detail=True, methods=['post'])
    def preview(self, request, pk=None):
        """
        预览模板渲染结果
        POST /api/v1/prompts/templates/{id}/preview/
        Body: {
            "variables": {
                "topic": "科幻故事",
                "style": "赛博朋克"
            }
        }
        """
        template = self.get_object()
        serializer = PromptTemplatePreviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        variables = serializer.validated_data['variables']

        try:
            # 渲染模板
            jinja_template = Template(template.template_content)
            rendered = jinja_template.render(**variables)

            return Response({
                'success': True,
                'rendered_content': rendered,
                'variables_used': variables
            })
        except Exception as e:
            return Response(
                {
                    'success': False,
                    'error': f'渲染失败: {str(e)}'
                },
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['post'])
    def evaluate(self, request, pk=None):
        """
        AI评估提示词效果
        POST /api/v1/prompts/templates/{id}/evaluate/

        使用AI分析提示词质量,提供优化建议
        """
        template = self.get_object()

        try:
            # 使用评估服务进行AI分析
            evaluation_service = PromptEvaluationService()
            evaluation_result = asyncio.run(
                evaluation_service.evaluate_prompt(template)
            )

            serializer = PromptTemplateEvaluationSerializer(data=evaluation_result)
            serializer.is_valid(raise_exception=True)

            return Response(serializer.data)
        except Exception as e:
            return Response(
                {
                    'error': f'评估失败: {str(e)}'
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

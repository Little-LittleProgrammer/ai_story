"""
内容管理视图
提供图片、视频等内容的访问接口
"""

import os
from pathlib import Path
from django.conf import settings
from django.http import FileResponse, Http404
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny


class StorageImageListView(APIView):
    """
    获取 storage/image 目录下的所有图片列表
    """
    permission_classes = [AllowAny]  # 允许未认证访问

    def get(self, request):
        """
        返回图片列表，包含文件名、大小、修改时间等信息
        """
        try:
            image_dir = Path(settings.STORAGE_ROOT) / 'image'

            # 确保目录存在
            if not image_dir.exists():
                return Response({
                    'success': False,
                    'message': '图片目录不存在',
                    'data': []
                }, status=status.HTTP_404_NOT_FOUND)

            # 支持的图片格式
            image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.svg'}

            images = []
            for file_path in image_dir.iterdir():
                if file_path.is_file() and file_path.suffix.lower() in image_extensions:
                    stat = file_path.stat()
                    images.append({
                        'name': file_path.name,
                        'size': stat.st_size,
                        'modified_time': stat.st_mtime,
                        'url': f'/api/v1/storage/image/{file_path.name}'
                    })

            # 按修改时间倒序排列
            images.sort(key=lambda x: x['modified_time'], reverse=True)

            return Response({
                'success': True,
                'message': '获取图片列表成功',
                'data': images,
                'total': len(images)
            })

        except Exception as e:
            return Response({
                'success': False,
                'message': f'获取图片列表失败: {str(e)}',
                'data': []
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class StorageImageDetailView(APIView):
    """
    访问 storage/image 目录下的单个图片文件
    """
    permission_classes = [AllowAny]  # 允许未认证访问

    def get(self, request, filename):
        """
        返回指定的图片文件
        """
        try:
            # 构建文件路径
            image_path = Path(settings.STORAGE_ROOT) / 'image' / filename

            # 安全检查：确保路径在允许的目录内（防止路径遍历攻击）
            storage_root = Path(settings.STORAGE_ROOT).resolve()
            resolved_path = image_path.resolve()

            if not str(resolved_path).startswith(str(storage_root)):
                raise Http404('非法的文件路径')

            # 检查文件是否存在
            if not image_path.exists() or not image_path.is_file():
                raise Http404('图片文件不存在')

            # 返回文件响应
            return FileResponse(
                open(image_path, 'rb'),
                content_type=self._get_content_type(image_path.suffix)
            )

        except Http404:
            raise
        except Exception as e:
            raise Http404(f'访问图片失败: {str(e)}')

    def _get_content_type(self, extension):
        """
        根据文件扩展名返回对应的 Content-Type
        """
        content_types = {
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.png': 'image/png',
            '.gif': 'image/gif',
            '.bmp': 'image/bmp',
            '.webp': 'image/webp',
            '.svg': 'image/svg+xml',
        }
        return content_types.get(extension.lower(), 'application/octet-stream')

class StorageVideoDetailView(APIView):
    """
    获取 storage/video 目录下的所有视频列表
    """
    permission_classes = [AllowAny]  # 允许未认证访问

    def get(self, request, filename):
        """
        返回指定的图片文件
        """
        try:
            # 构建文件路径
            video_path = Path(settings.STORAGE_ROOT) / 'video' / filename

            # 安全检查：确保路径在允许的目录内（防止路径遍历攻击）
            storage_root = Path(settings.STORAGE_ROOT).resolve()
            resolved_path = video_path.resolve()

            if not str(resolved_path).startswith(str(storage_root)):
                raise Http404('非法的文件路径')

            # 检查文件是否存在
            if not video_path.exists() or not video_path.is_file():
                raise Http404('图片文件不存在')

            # 返回文件响应
            return FileResponse(
                open(video_path, 'rb'),
                content_type='video/mp4'
            )

        except Http404:
            raise
        except Exception as e:
            raise Http404(f'访问图片失败: {str(e)}')
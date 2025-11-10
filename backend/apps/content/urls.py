"""内容生成URL路由"""
from django.urls import path
from .views import StorageImageListView, StorageImageDetailView, StorageVideoDetailView

urlpatterns = [
    # Storage图片API
    path('storage/image/', StorageImageListView.as_view(), name='storage-image-list'),
    path('storage/image/<str:filename>', StorageImageDetailView.as_view(), name='storage-image-detail'),
    path('storage/video/<str:filename>', StorageVideoDetailView.as_view(), name='storage-video-detail'),

    # 内容生成API
    # 待实现
]

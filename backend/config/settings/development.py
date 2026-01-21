"""
开发环境配置
"""

from .base import *
CELERY_ALWAYS_EAGER = True
CELERY_TASK_ALWAYS_EAGER = True

DEBUG = True
ALLOWED_HOSTS = ['*']

# CORS配置 - 开发环境允许所有源
CORS_ALLOW_ALL_ORIGINS = True

# 数据库配置 - 支持 Docker 环境中的 PostgreSQL
# 如果设置了 DATABASE_URL 环境变量，使用 PostgreSQL；否则使用 SQLite
import os
DATABASE_URL = os.getenv('DATABASE_URL')
if DATABASE_URL:
    # Docker 环境：使用 PostgreSQL
    # 解析 DATABASE_URL 格式: postgresql://user:password@host:port/dbname
    from urllib.parse import urlparse
    db_url = urlparse(DATABASE_URL)
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': db_url.path[1:],  # 去掉开头的 '/'
            'USER': db_url.username,
            'PASSWORD': db_url.password,
            'HOST': db_url.hostname,
            'PORT': db_url.port or 5432,
        }
    }
else:
    # 本地开发：使用 SQLite
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

# 日志配置
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'DEBUG',
    },
}
JIANYING_DRAFT_FOLDER = "D:\JianyingPro Drafts"
#!/usr/bin/env python
"""
Celery + Redis Pub/Sub 集成测试脚本

测试流程:
1. 测试Redis连接
2. 测试Redis Pub/Sub
3. 测试RedisStreamPublisher
4. 测试Celery任务 (需要先启动Celery Worker)

使用方法:
    python test_celery_redis.py
"""

import os
import sys
import time
import json
import django

# 设置Django环境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
django.setup()

import redis
from core.redis import RedisStreamPublisher


def test_redis_connection():
    """测试1: Redis连接"""
    print("\n" + "="*60)
    print("测试1: Redis连接")
    print("="*60)

    try:
        client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
        result = client.ping()
        print(f"✅ Redis连接成功: {result}")
        return True
    except Exception as e:
        print(f"❌ Redis连接失败: {e}")
        return False


def test_redis_pubsub():
    """测试2: Redis Pub/Sub"""
    print("\n" + "="*60)
    print("测试2: Redis Pub/Sub")
    print("="*60)

    try:
        client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)

        # 发布测试消息
        channel = "test:channel"
        message = json.dumps({"type": "test", "content": "Hello Redis!"})

        subscribers = client.publish(channel, message)
        print(f"✅ 消息已发布到频道 '{channel}'")
        print(f"   订阅者数量: {subscribers}")

        if subscribers == 0:
            print("   ⚠️  当前没有订阅者")

        return True
    except Exception as e:
        print(f"❌ Redis Pub/Sub测试失败: {e}")
        return False


def test_redis_stream_publisher():
    """测试3: RedisStreamPublisher"""
    print("\n" + "="*60)
    print("测试3: RedisStreamPublisher")
    print("="*60)

    try:
        # 创建发布器
        publisher = RedisStreamPublisher(
            project_id="test-project-123",
            stage_name="rewrite"
        )

        print(f"✅ 发布器已创建")
        print(f"   频道: {publisher.channel}")

        # 测试各种消息类型
        print("\n发布测试消息...")

        # 1. Token消息
        success = publisher.publish_token(
            content="这是一个测试",
            full_text="这是一个测试"
        )
        print(f"   Token消息: {'✅' if success else '❌'}")

        # 2. 阶段更新消息
        success = publisher.publish_stage_update(
            status="processing",
            progress=50,
            message="正在处理..."
        )
        print(f"   阶段更新消息: {'✅' if success else '❌'}")

        # 3. 进度消息
        success = publisher.publish_progress(
            current=5,
            total=10,
            item_name="测试项"
        )
        print(f"   进度消息: {'✅' if success else '❌'}")

        # 4. 完成消息
        success = publisher.publish_done(
            full_text="测试完成",
            metadata={"latency_ms": 1000}
        )
        print(f"   完成消息: {'✅' if success else '❌'}")

        # 5. 错误消息
        success = publisher.publish_error(
            error="这是一个测试错误",
            retry_count=0
        )
        print(f"   错误消息: {'✅' if success else '❌'}")

        publisher.close()
        print("\n✅ RedisStreamPublisher测试通过")
        return True

    except Exception as e:
        print(f"❌ RedisStreamPublisher测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_celery_task():
    """测试4: Celery任务 (需要先启动Worker)"""
    print("\n" + "="*60)
    print("测试4: Celery任务")
    print("="*60)
    print("⚠️  此测试需要先启动Celery Worker:")
    print("   celery -A config worker -l info")
    print()

    try:
        from apps.projects.tasks import execute_llm_stage
        from celery.result import AsyncResult

        # 检查是否有可用的Worker
        from config.celery import app
        inspect = app.control.inspect()
        active_workers = inspect.active()

        if not active_workers:
            print("❌ 没有检测到活跃的Celery Worker")
            print("   请先启动Worker: celery -A config worker -l info")
            return False

        print(f"✅ 检测到 {len(active_workers)} 个活跃的Worker")


        return True

    except Exception as e:
        print(f"❌ Celery任务测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """运行所有测试"""
    print("\n" + "🚀 " + "="*58)
    print("   Celery + Redis Pub/Sub 集成测试")
    print("="*60)

    results = []

    # 测试1: Redis连接
    results.append(("Redis连接", test_redis_connection()))

    # 测试2: Redis Pub/Sub
    results.append(("Redis Pub/Sub", test_redis_pubsub()))

    # 测试3: RedisStreamPublisher
    results.append(("RedisStreamPublisher", test_redis_stream_publisher()))

    # 测试4: Celery任务
    results.append(("Celery任务", test_celery_task()))

    # 汇总结果
    print("\n" + "="*60)
    print("测试结果汇总")
    print("="*60)

    passed = 0
    failed = 0

    for name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{name:30s} {status}")
        if result:
            passed += 1
        else:
            failed += 1

    print("="*60)
    print(f"总计: {passed} 通过, {failed} 失败")
    print("="*60)

    if failed == 0:
        print("\n🎉 所有测试通过！")
        return 0
    else:
        print(f"\n⚠️  有 {failed} 个测试失败")
        return 1


if __name__ == '__main__':
    sys.exit(main())

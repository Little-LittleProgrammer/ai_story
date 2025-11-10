"""
WebSocket消费者
职责: 订阅Redis Pub/Sub频道，将消息推送给前端
遵循单一职责原则(SRP)
"""

import json
import logging
import asyncio
import redis.asyncio as aioredis
from channels.generic.websocket import AsyncWebsocketConsumer
from django.conf import settings

logger = logging.getLogger(__name__)


class ProjectStageConsumer(AsyncWebsocketConsumer):
    """
    项目阶段WebSocket消费者

    订阅Redis Pub/Sub频道，实时推送AI生成进度给前端

    WebSocket URL: ws://localhost:8000/ws/projects/{project_id}/stage/{stage_name}/

    消息格式:
    {
        "type": "token|stage_update|done|error|progress",
        "content": "...",
        ...
    }
    """

    async def connect(self):
        """
        WebSocket连接建立
        """
        # 从URL获取参数
        self.project_id = self.scope['url_route']['kwargs']['project_id']
        self.stage_name = self.scope['url_route']['kwargs']['stage_name']

        # 构建Redis频道名称
        self.channel_name = f"ai_story:project:{self.project_id}:stage:{self.stage_name}"

        logger.info(f"WebSocket连接: {self.channel_name}")

        # 接受WebSocket连接
        await self.accept()

        # 启动Redis订阅任务
        self.redis_task = asyncio.create_task(self._subscribe_redis())

    async def disconnect(self, close_code):
        """
        WebSocket连接断开
        """
        logger.info(f"WebSocket断开: {self.channel_name}, code: {close_code}")

        # 取消Redis订阅任务
        if hasattr(self, 'redis_task'):
            self.redis_task.cancel()
            try:
                await self.redis_task
            except asyncio.CancelledError:
                pass

    async def receive(self, text_data=None, bytes_data=None):
        """
        接收来自前端的消息 (可选，用于心跳检测)
        """
        if text_data:
            try:
                data = json.loads(text_data)
                message_type = data.get('type')

                if message_type == 'ping':
                    # 心跳响应
                    await self.send(text_data=json.dumps({
                        'type': 'pong',
                        'timestamp': data.get('timestamp')
                    }))
            except json.JSONDecodeError:
                logger.warning(f"无效的JSON消息: {text_data}")

    async def _subscribe_redis(self):
        """
        订阅Redis Pub/Sub频道
        持续监听并转发消息到WebSocket
        """
        redis_url = getattr(settings, 'CELERY_BROKER_URL', 'redis://localhost:6379/5')

        try:
            # 创建Redis连接
            redis_client = await aioredis.from_url(
                redis_url,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5
            )

            # 创建Pub/Sub对象
            pubsub = redis_client.pubsub()

            # 订阅频道
            await pubsub.subscribe(self.channel_name)

            logger.info(f"已订阅Redis频道: {self.channel_name}")

            # 发送连接成功消息
            await self.send(text_data=json.dumps({
                'type': 'connected',
                'channel': self.channel_name,
                'message': '已连接到实时流'
            }))

            # 持续监听消息
            async for message in pubsub.listen():
                if message['type'] == 'message':
                    try:
                        # 解析消息
                        data = json.loads(message['data'])

                        # 转发到WebSocket
                        await self.send(text_data=json.dumps(data))

                        # 如果是完成或错误消息，可以选择关闭连接
                        if data.get('type') in ['done', 'error']:
                            logger.info(f"任务结束，准备关闭连接: {self.channel_name}")
                            # 等待1秒后关闭，确保消息已发送
                            await asyncio.sleep(1)
                            await self.close()
                            break

                    except json.JSONDecodeError as e:
                        logger.error(f"Redis消息解析失败: {e}")
                    except Exception as e:
                        logger.error(f"消息处理异常: {e}")

        except asyncio.CancelledError:
            logger.info(f"Redis订阅任务已取消: {self.channel_name}")
        except Exception as e:
            logger.error(f"Redis订阅失败: {e}")
            # 发送错误消息到前端
            await self.send(text_data=json.dumps({
                'type': 'error',
                'error': f'Redis连接失败: {str(e)}'
            }))
        finally:
            # 清理资源
            try:
                await pubsub.unsubscribe(self.channel_name)
                await redis_client.close()
                logger.info(f"已关闭Redis连接: {self.channel_name}")
            except Exception as e:
                logger.error(f"关闭Redis连接失败: {e}")


class ProjectConsumer(AsyncWebsocketConsumer):
    """
    项目级WebSocket消费者

    订阅整个项目的所有阶段更新

    WebSocket URL: ws://localhost:8000/ws/projects/{project_id}/

    可用于监控项目整体进度
    """

    async def connect(self):
        """
        WebSocket连接建立
        """
        self.project_id = self.scope['url_route']['kwargs']['project_id']

        # 订阅项目所有阶段的频道
        self.channels = [
            f"ai_story:project:{self.project_id}:stage:rewrite",
            f"ai_story:project:{self.project_id}:stage:storyboard",
            f"ai_story:project:{self.project_id}:stage:image_generation",
            f"ai_story:project:{self.project_id}:stage:camera_movement",
            f"ai_story:project:{self.project_id}:stage:video_generation",
        ]

        logger.info(f"WebSocket连接: 项目 {self.project_id}")

        await self.accept()

        # 启动Redis订阅任务
        self.redis_task = asyncio.create_task(self._subscribe_redis())

    async def disconnect(self, close_code):
        """
        WebSocket连接断开
        """
        logger.info(f"WebSocket断开: 项目 {self.project_id}, code: {close_code}")

        if hasattr(self, 'redis_task'):
            self.redis_task.cancel()
            try:
                await self.redis_task
            except asyncio.CancelledError:
                pass

    async def receive(self, text_data=None, bytes_data=None):
        """
        接收来自前端的消息
        """
        if text_data:
            try:
                data = json.loads(text_data)
                message_type = data.get('type')

                if message_type == 'ping':
                    await self.send(text_data=json.dumps({
                        'type': 'pong',
                        'timestamp': data.get('timestamp')
                    }))
            except json.JSONDecodeError:
                logger.warning(f"无效的JSON消息: {text_data}")

    async def _subscribe_redis(self):
        """
        订阅Redis Pub/Sub频道 (多个频道)
        """
        redis_url = getattr(settings, 'CELERY_BROKER_URL', 'redis://localhost:6379/5')

        try:
            redis_client = await aioredis.from_url(
                redis_url,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5
            )

            pubsub = redis_client.pubsub()

            # 订阅所有阶段频道
            await pubsub.subscribe(*self.channels)

            logger.info(f"已订阅项目 {self.project_id} 的所有阶段频道")

            # 发送连接成功消息
            await self.send(text_data=json.dumps({
                'type': 'connected',
                'project_id': self.project_id,
                'message': '已连接到项目实时流'
            }))

            # 持续监听消息
            async for message in pubsub.listen():
                if message['type'] == 'message':
                    try:
                        data = json.loads(message['data'])
                        await self.send(text_data=json.dumps(data))
                    except json.JSONDecodeError as e:
                        logger.error(f"Redis消息解析失败: {e}")
                    except Exception as e:
                        logger.error(f"消息处理异常: {e}")

        except asyncio.CancelledError:
            logger.info(f"Redis订阅任务已取消: 项目 {self.project_id}")
        except Exception as e:
            logger.error(f"Redis订阅失败: {e}")
            await self.send(text_data=json.dumps({
                'type': 'error',
                'error': f'Redis连接失败: {str(e)}'
            }))
        finally:
            try:
                await pubsub.unsubscribe(*self.channels)
                await redis_client.close()
                logger.info(f"已关闭Redis连接: 项目 {self.project_id}")
            except Exception as e:
                logger.error(f"关闭Redis连接失败: {e}")

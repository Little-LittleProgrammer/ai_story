"""
项目相关的Celery异步任务
职责: 执行耗时的AI生成任务，通过Redis Pub/Sub推送实时进度
遵循单一职责原则(SRP)
"""

from email import message
import logging
from typing import Dict, Any
from django.utils import timezone

from backend.apps.projects.utils import parse_json
from core.redis import RedisStreamPublisher
from apps.content.processors.llm_stage import LLMStageProcessor
from apps.content.processors.text2image_stage import Text2ImageStageProcessor
from apps.content.processors.image2video_stage import Image2VideoStageProcessor
from apps.projects.models import Project, ProjectStage
from config.celery import app

logger = logging.getLogger(__name__)


@app.task(
    bind=True,
    max_retries=0,
    default_retry_delay=60,
    acks_late=True,
    reject_on_worker_lost=True,
    soft_time_limit=600,  # 10分钟软超时
    time_limit=900  # 15分钟硬超时
)
def execute_llm_stage(
    self,
    project_id: str,
    stage_name: str,
    input_data: Dict[str, Any],
    user_id: int
) -> Dict[str, Any]:
    """
    执行LLM阶段任务 (文案改写/分镜生成/运镜生成)

    Args:
        self: Celery任务实例
        project_id: 项目ID
        stage_name: 阶段名称 (rewrite/storyboard/camera_movement)
        input_data: 输入数据
        user_id: 用户ID

    Returns:
        Dict包含: success, task_id, channel, result
    """

    task_id = self.request.id
    channel = f"ai_story:project:{project_id}:stage:{stage_name}"

    logger.info(f"开始执行LLM阶段任务: {stage_name}, 项目: {project_id}, 任务ID: {task_id}")

    # 初始化Redis发布器
    publisher = RedisStreamPublisher(project_id, stage_name)

    try:
        # 获取项目和阶段
        project = Project.objects.get(id=project_id, user_id=user_id)
        stage = ProjectStage.objects.get(project=project, stage_type=stage_name)

        # 更新阶段状态
        stage.status = 'processing'
        stage.started_at = timezone.now()
        stage.save()

        # 发布开始消息
        publisher.publish_stage_update(
            status='processing',
            progress=0,
            message=f'开始执行{stage.get_stage_type_display()}'
        )

        # 创建处理器
        processor = LLMStageProcessor(stage_type=stage_name)

        # 执行流式处理
        full_text = ""

        for chunk in processor.process_stream(
            project_id=project_id,
            input_data=input_data
        ):
            chunk_type = chunk.get('type')

            if chunk_type == 'token':
                # 发布token消息
                content = chunk.get('content', '')
                full_text = chunk.get('full_text', full_text)
                publisher.publish_token(content, full_text)

            elif chunk_type == 'stage_update':
                # 发布阶段更新
                publisher.publish_stage_update(
                    status=chunk.get('status', 'processing'),
                    progress=chunk.get('progress'),
                    message=chunk.get('message')
                )

            elif chunk_type == 'done':
                # 处理完成
                full_text = chunk.get('full_text', full_text)
                metadata = chunk.get('metadata', {})

                # 更新阶段状态
                ProjectStage.objects.filter(id=stage.id).update(
                    completed_at=timezone.now(),
                    status='completed'
                )
                # 发布完成消息
                publisher.publish_done(full_text, metadata)

            elif chunk_type == 'error':
                # 处理错误
                error_msg = chunk.get('error', '未知错误')
                raise Exception(error_msg)

        logger.info(f"LLM阶段任务完成: {stage_name}, 项目: {project_id}")

        return {
            'success': True,
            'task_id': task_id,
            'channel': channel,
            'result': full_text
        }

    except Project.DoesNotExist:
        error_msg = f'项目不存在: {project_id}'
        logger.error(error_msg)
        publisher.publish_error(error_msg)
        return {'success': False, 'error': error_msg}

    except ProjectStage.DoesNotExist:
        error_msg = f'阶段不存在: {stage_name}'
        logger.error(error_msg)
        publisher.publish_error(error_msg)
        return {'success': False, 'error': error_msg}

    except Exception as e:
        error_msg = f'任务执行失败: {str(e)}'
        logger.exception(error_msg)

        # 更新阶段状态
        try:
            stage = ProjectStage.objects.get(
                project_id=project_id,
                stage_type=stage_name
            )
            stage.status = 'failed'
            stage.error_message = error_msg
            stage.retry_count += 1
            stage.save()
        except Exception:
            pass

        # 发布错误消息
        publisher.publish_error(error_msg, retry_count=self.request.retries)

        # 重试
        if self.request.retries < self.max_retries:
            logger.info(f"任务将在60秒后重试 (第{self.request.retries + 1}次)")
            raise self.retry(exc=e, countdown=60)

        return {'success': False, 'error': error_msg}

    finally:
        publisher.close()


@app.task(
    bind=True,
    max_retries=0,
    default_retry_delay=60,
    acks_late=True,
    reject_on_worker_lost=True,
    soft_time_limit=600,
    time_limit=900
)
def execute_text2image_stage(
    self,
    project_id: str,
    storyboard_ids: list = None,
    user_id: int = None
) -> Dict[str, Any]:
    """
    执行文生图阶段任务

    Args:
        self: Celery任务实例
        project_id: 项目ID
        storyboard_ids: 分镜ID列表 (可选，为空则处理所有分镜)
        user_id: 用户ID

    Returns:
        Dict包含: success, task_id, channel, result
    """
    task_id = self.request.id
    stage_name = 'image_generation'
    channel = f"ai_story:project:{project_id}:stage:{stage_name}"

    logger.info(f"开始执行文生图任务, 项目: {project_id}, 任务ID: {task_id}")

    publisher = RedisStreamPublisher(project_id, stage_name)

    try:
        # 获取项目和阶段
        project = Project.objects.get(id=project_id)
        stage = ProjectStage.objects.get(project=project, stage_type=stage_name)

        # 更新阶段状态
        stage.status = 'processing'
        stage.started_at = timezone.now()
        stage.save()

        # 发布开始消息
        publisher.publish_stage_update(
            status='processing',
            progress=0,
            message='开始生成图片'
        )

        # 创建处理器
        processor = Text2ImageStageProcessor()

        # 执行流式处理
        for chunk in processor.process_stream(
            project_id=project_id,
            storyboard_ids=storyboard_ids
        ):
            chunk_type = chunk.get('type')

            if chunk_type == 'progress':
                # 发布进度消息
                publisher.publish_progress(
                    current=chunk.get('current', 0),
                    total=chunk.get('total', 0),
                    item_name=chunk.get('item_name', ''),
                )

            elif chunk_type == 'stage_update':
                # 发布阶段更新
                publisher.publish_stage_update(
                    status=chunk.get('status', 'processing'),
                    progress=chunk.get('progress'),
                    message=chunk.get('message')
                )

            elif chunk_type == 'done':
                # 处理完成
                metadata = chunk.get('metadata', {})

                # 更新阶段状态
                ProjectStage.objects.filter(id=stage.id).update(
                    status='completed',
                    completed_at=timezone.now()
                )
                # 发布完成消息
                publisher.publish_done(metadata=metadata)

            elif chunk_type == 'error':
                # 处理错误
                error_msg = chunk.get('error', '未知错误')
                raise Exception(error_msg)

        logger.info(f"文生图任务完成, 项目: {project_id}")

        return {
            'success': True,
            'task_id': task_id,
            'channel': channel
        }

    except Exception as e:
        error_msg = f'文生图任务失败: {str(e)}'
        logger.exception(error_msg)

        # 更新阶段状态
        try:
            stage = ProjectStage.objects.get(
                project_id=project_id,
                stage_type=stage_name
            )
            stage.status = 'failed'
            stage.error_message = error_msg
            stage.retry_count += 1
            stage.save()
        except Exception:
            pass

        # 发布错误消息
        publisher.publish_error(error_msg, retry_count=self.request.retries)

        # 重试
        if self.request.retries < self.max_retries:
            raise self.retry(exc=e, countdown=60)

        return {'success': False, 'error': error_msg}

    finally:
        publisher.close()


@app.task(
    bind=True,
    max_retries=0,
    default_retry_delay=60,
    acks_late=True,
    reject_on_worker_lost=True,
    soft_time_limit=1200,  # 20分钟软超时 (视频生成较慢)
    time_limit=1500  # 25分钟硬超时
)
def execute_image2video_stage(
    self,
    project_id: str,
    storyboard_ids: list = None,
    user_id: int = None
) -> Dict[str, Any]:
    """
    执行图生视频阶段任务

    Args:
        self: Celery任务实例
        project_id: 项目ID
        storyboard_ids: 分镜ID列表 (可选，为空则处理所有分镜)
        user_id: 用户ID

    Returns:
        Dict包含: success, task_id, channel, result
    """
    task_id = self.request.id
    stage_name = 'video_generation'
    channel = f"ai_story:project:{project_id}:stage:{stage_name}"

    logger.info(f"开始执行图生视频任务, 项目: {project_id}, 任务ID: {task_id}")

    publisher = RedisStreamPublisher(project_id, stage_name)

    try:
        # 获取项目和阶段
        project = Project.objects.get(id=project_id)
        stage = ProjectStage.objects.get(project=project, stage_type=stage_name)

        # 更新阶段状态
        stage.status = 'processing'
        stage.started_at = timezone.now()
        stage.save()

        # 发布开始消息
        publisher.publish_stage_update(
            status='processing',
            progress=0,
            message='开始生成视频'
        )

        # 创建处理器
        processor = Image2VideoStageProcessor()

        # 执行流式处理
        for chunk in processor.process_stream(
            project_id=project_id,
            storyboard_ids=storyboard_ids
        ):
            chunk_type = chunk.get('type')

            if chunk_type == 'progress':
                # 发布进度消息
                publisher.publish_progress(
                    current=chunk.get('current', 0),
                    total=chunk.get('total', 0),
                    item_name=chunk.get('item_name', '')
                )

            elif chunk_type == 'stage_update':
                # 发布阶段更新
                publisher.publish_stage_update(
                    status=chunk.get('status', 'processing'),
                    progress=chunk.get('progress'),
                    message=chunk.get('message')
                )

            elif chunk_type == 'done':
                # 处理完成
                metadata = chunk.get('metadata', {})
                # 发布完成消息
                publisher.publish_done(metadata=metadata)

            elif chunk_type == 'error':
                # 处理错误
                error_msg = chunk.get('error', '未知错误')
                raise Exception(error_msg)

        logger.info(f"图生视频任务完成, 项目: {project_id}")

        return {
            'success': True,
            'task_id': task_id,
            'channel': channel
        }

    except Exception as e:
        error_msg = f'图生视频任务失败: {str(e)}'
        logger.exception(error_msg)

        # 更新阶段状态
        try:
            stage = ProjectStage.objects.get(
                project_id=project_id,
                stage_type=stage_name
            )
            stage.status = 'failed'
            stage.error_message = error_msg
            stage.retry_count += 1
            stage.save()
        except Exception:
            pass

        # 发布错误消息
        publisher.publish_error(error_msg, retry_count=self.request.retries)

        # 重试
        if self.request.retries < self.max_retries:
            raise self.retry(exc=e, countdown=60)

        return {'success': False, 'error': error_msg}

    finally:
        publisher.close()

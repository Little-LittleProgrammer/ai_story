"""
图生视频阶段处理器
职责: 为每个已生成的图片调用Image2VideoClient生成视频
遵循单一职责原则(SRP) + 开闭原则(OCP)
"""

import copy
import logging
import os
import asyncio
from typing import Any, Dict, Generator, List, Optional

from django.conf import settings
from core.ai_client.factory import create_ai_client
from core.pipeline.base import PipelineContext, StageProcessor, StageResult
from django.utils import timezone
from jinja2 import Template, TemplateError
import base64
from pathlib import Path

from apps.models.models import ModelProvider
from apps.projects.models import Project, ProjectStage
from apps.projects.utils import parse_json

logger = logging.getLogger(__name__)


class Image2VideoStageProcessor(StageProcessor):
    """
    图生视频阶段处理器

    职责:
    - 读取image_generation阶段的图片数据
    - 读取camera_movement阶段的运镜参数
    - 为每个图片调用Image2VideoClient生成视频
    - 保存生成的视频到GeneratedVideo模型
    - 支持批量生成和流式进度推送

    特性:
    - 异步轮询任务状态
    - 失败自动重试机制
    - 支持流式进度更新
    - 超时控制和错误处理
    """

    def __init__(self):
        """初始化处理器"""
        super().__init__("video_generation")
        self.stage_type = "video_generation"
        self.max_concurrent = 2  # 最大并发生成数(视频生成较慢,建议并发数小一些)
        self.poll_interval = 10  # 轮询间隔(秒)
        self.max_wait_time = 600  # 最大等待时间(秒)

    def validate(self, context: PipelineContext) -> bool:
        """
        验证是否可以执行图生视频阶段

        检查:
        1. 项目是否存在
        2. image_generation阶段是否已完成
        3. camera_movement阶段是否已完成
        4. 是否有图片数据
        5. 是否配置了图生视频模型
        """
        try:
            project = Project.objects.get(id=context.project_id)

            # 检查image_generation阶段是否完成
            image_stage = ProjectStage.objects.filter(
                project=project, stage_type="image_generation", status="completed"
            ).first()

            if not image_stage:
                logger.error(f"项目 {context.project_id} 的image_generation阶段未完成")
                return False

            # 检查camera_movement阶段是否完成
            camera_stage = ProjectStage.objects.filter(
                project=project, stage_type="camera_movement", status="completed"
            ).first()

            if not camera_stage:
                logger.error(f"项目 {context.project_id} 的camera_movement阶段未完成")
                return False

            # 检查是否有图片数据(从output_data验证)
            if image_stage.output_data:
                scenes = image_stage.output_data.get("human_text", {}).get("scenes", [])
                has_images = any(scene.get("urls") for scene in scenes)

                if not has_images:
                    logger.error(f"项目 {context.project_id} 没有图片数据")
                    return False
            else:
                logger.error(
                    f"项目 {context.project_id} 的image_generation阶段没有输出数据"
                )
                return False

            # 检查是否有可用的图生视频模型
            provider = self._get_image2video_provider(project)
            if not provider:
                logger.error(f"项目 {context.project_id} 未配置图生视频模型")
                return False

            return True

        except Project.DoesNotExist:
            logger.error(f"项目 {context.project_id} 不存在")
            return False
        except Exception as e:
            logger.error(f"验证失败: {str(e)}", exc_info=True)
            return False

    def process(self, context: PipelineContext) -> StageResult:
        """
        非流式执行图生视频生成
        用于Pipeline自动执行
        """
        try:
            # 获取项目和阶段
            project = Project.objects.get(id=context.project_id)
            stage, created = ProjectStage.objects.get_or_create(project=project, stage_type=self.stage_type)

            # 更新阶段状态
            stage.status = "processing"
            stage.started_at = timezone.now()
            stage.save()

            # 获取分镜数据(从ProjectStage.output_data读取)
            storyboards = stage.output_data.get("human_text", {}).get("scenes", [])

            if not storyboards:
                return StageResult(
                    success=False, error="没有找到分镜数据", can_retry=False
                )

            # 获取AI客户端提供商
            provider = self._get_image2video_provider(project)
            if not provider:
                return StageResult(
                    success=False, error="未找到可用的图生视频模型提供商", can_retry=False
                )

            # 批量生成视频（使用流式方法）
            generated_videos = []
            failed_count = 0

            for index, storyboard in enumerate(storyboards, 1):
                try:
                    # 检查是否有图片URL
                    image_urls = storyboard.get("urls", [])
                    if not image_urls:
                        logger.warning(f"分镜 {index} 没有图片URL，跳过")
                        failed_count += 1
                        continue

                    # 使用流式方法生成视频（同步调用）
                    video_url = None
                    for result in self._generate_single_video_stream(
                        project=project,
                        storyboard=storyboard,
                        scene_number=index,
                        provider=provider,
                    ):
                        if result.get("type") == "success":
                            video_url = result.get("video_url")
                        elif result.get("type") == "error":
                            logger.error(f"分镜 {index} 视频生成失败: {result.get('error')}")
                            break

                    if video_url:
                        generated_videos.append(
                            {"scene_number": index, "video_url": video_url}
                        )
                        # 更新output_data
                        storyboard["video_url"] = video_url
                    else:
                        failed_count += 1

                except Exception as e:
                    logger.error(f"分镜 {index} 视频生成失败: {str(e)}")
                    failed_count += 1

            # 保存最终结果
            success_count = len(generated_videos)
            total = len(storyboards)

            output_data = {
                "human_text": {"scenes": storyboards},
                "total_storyboards": total,
                "success_count": success_count,
                "failed_count": failed_count,
                "generated_videos": generated_videos,
            }

            stage.output_data = output_data
            stage.status = "completed" if failed_count == 0 else "partially_completed"
            stage.completed_at = timezone.now()
            stage.save()

            # 添加到上下文
            context.add_result(self.stage_type, output_data)

            return StageResult(success=True, data=output_data)

        except Exception as e:
            logger.error(f"{self.stage_type} 阶段处理失败: {str(e)}", exc_info=True)
            return StageResult(success=False, error=str(e), can_retry=True)

    def process_stream(
        self, project_id: str, storyboard_ids: List[int] = None
    ) -> Generator[Dict[str, Any], None, None]:
        """
        流式执行图生视频生成
        用于SSE实时推送进度

        Args:
            project_id: 项目ID
            storyboard_ids: 指定要生成的分镜ID列表(可选,默认生成所有)

        Yields:
            Dict包含: type (progress/task_created/task_status/video_generated/done/error), content, data
        """
        stage = None
        try:
            # 获取项目和阶段
            project = Project.objects.get(id=project_id)
            stage, created = ProjectStage.objects.get_or_create(project=project, stage_type=self.stage_type)

            # 更新阶段状态
            stage.status = "processing"
            stage.started_at = timezone.now()
            stage.save()

            yield {
                "type": "stage_update",
                "stage": {
                    "id": str(stage.id),
                    "status": "processing",
                    "stage_type": self.stage_type,
                    "started_at": stage.started_at.isoformat(),
                },
            }

            # 获取分镜列表(从image_generation阶段的output_data读取)
            image_stage = ProjectStage.objects.filter(
                project=project, stage_type="image_generation", status="completed"
            ).first()
            
            if not image_stage or not image_stage.output_data:
                yield {"type": "error", "error": "没有找到图片生成阶段的数据"}
                return

            # 从image_generation阶段的output_data读取分镜数据
            if storyboard_ids:
                storyboards = image_stage.output_data.get("human_text", {}).get("scenes", [])
                storyboards = [
                    i for i in storyboards if i.get("scene_number") in storyboard_ids
                ]
            else:
                storyboards = image_stage.output_data.get("human_text", {}).get("scenes", [])

            if not storyboards:
                yield {"type": "error", "error": "没有找到分镜数据"}
                return

            total = len(storyboards)
            yield {"type": "info", "message": f"开始生成视频，共 {total} 个分镜..."}

            # 获取AI客户端配置
            provider = self._get_image2video_provider(project)

            # 批量生成视频
            generated_videos = []
            failed_count = 0

            for index, storyboard in enumerate(storyboards, 1):
                try:
                    # 进度更新
                    yield {
                        "type": "progress",
                        "current": index,
                        "total": total,
                        "message": f"正在生成第 {index}/{total} 个视频...",
                        "scene_number": index,
                    }

                    # 检查是否有图片URL
                    image_urls = storyboard.get("urls", [])
                    if not image_urls:
                        failed_count += 1
                        yield {
                            "type": "warning",
                            "message": f"分镜 {index} 没有图片URL，跳过",
                        }
                        continue

                    # 生成视频 (流式推送状态更新)
                    video_url = None
                    for event in self._generate_single_video_stream(
                        project=project,
                        storyboard=storyboard,
                        scene_number=storyboard["scene_number"],
                        provider=provider,
                    ):
                        # 转发所有事件
                        yield event

                        # 保存最终生成的视频URL
                        if event["type"] == "video_generated":
                            video_urls = event.get("video_urls", {}).get("data", [])

                    if video_urls:
                        generated_videos.append(
                            {"scene_number": storyboard["scene_number"], "video_urls": video_urls}
                        )
                        # 更新storyboard数据
                        storyboard["video_urls"] = video_urls

                        # 保存到当前阶段(video_generation)
                        # 从image_stage复制分镜数据，然后添加视频URL
                        scenes = image_stage.output_data.get("human_text", {}).get("scenes", [])
                        for each in scenes:
                            if each.get("scene_number") == storyboard.get("scene_number"):
                                each["video_urls"] = video_urls

                        # 确保stage.output_data存在并更新
                        if not stage.output_data:
                            stage.output_data = {}
                        stage.output_data["human_text"] = {"scenes": scenes}
                        stage.save()
                    else:
                        failed_count += 1
                        yield {
                            "type": "warning",
                            "message": f"分镜 {index} 视频生成失败",
                        }

                except Exception as e:
                    failed_count += 1
                    logger.error(f"分镜 {index} 生成失败: {str(e)}")
                    yield {
                        "type": "error",
                        "error": f"分镜 {index} 生成失败: {str(e)}",
                        "scene_number": index,
                    }

            # 保存最终结果
            success_count = len(generated_videos)
            
            # 更新阶段状态为完成
            if success_count > 0:
                # 确保所有视频URL都已保存到stage.output_data
                # 从image_stage复制完整的分镜数据（包含视频URL）
                scenes = image_stage.output_data.get("human_text", {}).get("scenes", [])
                # 更新每个分镜的视频URL
                for generated_video in generated_videos:
                    scene_number = generated_video.get("scene_number")
                    video_urls = generated_video.get("video_urls", [])
                    for scene in scenes:
                        if scene.get("scene_number") == scene_number:
                            scene["video_urls"] = video_urls
                
                # 保存到video_generation阶段
                if not stage.output_data:
                    stage.output_data = {}
                stage.output_data["human_text"] = {"scenes": scenes}
                stage.status = "completed"
                stage.completed_at = timezone.now()
                stage.save()
            
            yield {
                "type": "done",
                "message": f"视频生成完成: 成功 {success_count}/{total}",
                "stage": {
                    "id": str(stage.id),
                    "status": stage.status,
                },
            }

        except Exception as e:
            logger.error(f"流式图生视频处理失败: {str(e)}", exc_info=True)

            # 更新阶段状态
            if stage:
                try:
                    stage.status = "failed"
                    stage.error_message = str(e)
                    stage.save()
                except Exception:
                    pass

            yield {"type": "error", "error": str(e)}

    def on_failure(self, context: PipelineContext, error: Exception):
        """失败处理"""
        try:
            project = Project.objects.get(id=context.project_id)
            stage = ProjectStage.objects.filter(
                    project=project, stage_type=self.stage_type
                ).first()

            if stage:
                stage.status = "failed"
                stage.error_message = str(error)
                stage.save()

        except Exception as e:
            logger.error(f"更新失败状态失败: {str(e)}")

    # ===== 私有辅助方法 =====

    def _get_image2video_provider(
        self, project: Project
    ) -> Optional[ModelProvider]:
        """获取图生视频模型提供商"""
        # 1. 优先从项目模型配置获取
        config = getattr(project, "model_config", None)

        if config:
            providers = list(config.video_providers.all())

            if providers:
                # 简化版: 使用第一个提供商
                # TODO: 实现负载均衡策略
                return providers[0]

        # 2. 获取系统默认提供商
        provider = ModelProvider.objects.filter(
            provider_type="image2video", is_active=True
        ).first()

        if not provider:
            raise Exception("未找到可用的图生视频模型提供商，请在后台配置")

        return provider

    def _generate_single_video(
        self,
        project: Project,
        storyboard: Dict[str, Any],
        scene_number: int,
        provider: ModelProvider,
    ) -> Optional[str]:
        """
        为单个分镜生成视频 (非流式版本，已废弃，请使用 _generate_single_video_stream)

        Args:
            project: 项目对象
            storyboard: 分镜数据字典
            scene_number: 分镜序号
            provider: 模型提供商

        Returns:
            视频URL或None(失败时)
        """
        # 使用流式方法，收集最后一个结果
        video_url = None
        for result in self._generate_single_video_stream(
            project=project,
            storyboard=storyboard,
            scene_number=scene_number,
            provider=provider,
        ):
            if result.get("type") == "success":
                video_url = result.get("video_url")
            elif result.get("type") == "error":
                logger.error(f"分镜 {scene_number} 视频生成失败: {result.get('error')}")
                return None
        return video_url

    def image_to_base64(self, image_path):
        """将本地图片转换为 Base64 字符串（带格式前缀）"""
        image = Path(image_path)
        with open(image, "rb") as f:
            base64_str = base64.b64encode(f.read()).decode("utf-8")
        # 自动识别图片格式（根据文件后缀）
        ext = image.suffix.lstrip(".").lower()
        if ext == "jpg":
            ext = "jpeg"  # 标准 MIME 类型是 image/jpeg
        return f"{base64_str}"

    def _generate_single_video_stream(
        self,
        project: Project,
        storyboard: Dict[str, Any],
        scene_number: int,
        provider: ModelProvider,
    ) -> Generator[Dict[str, Any], None, None]:
        """
        为单个分镜生成视频 (流式版本,推送状态更新)

        Args:
            storyboard: 分镜数据字典
            scene_number: 分镜序号
            provider: 模型提供商

        Yields:
            Dict包含: type (task_created/task_status/video_generated/error), data
        """
        try:
            # 准备生成参数
            prompt = self._build_prompt(project, storyboard)
            image_urls = storyboard.get("urls", [])

            if not image_urls:
                yield {
                    "type": "error",
                    "error": f"分镜 {scene_number} 没有图片URL",
                    "scene_number": scene_number,
                }
                return

            # 获取图片URL
            # MiniMax API 支持公网 URL 或 Base64 Data URL
            # 如果是本地路径，需要转换为 Base64 Data URL
            image_url = image_urls[0].get("url", "")
            
            # 如果 image_url 是本地路径（不是 http/https/data URL），转换为Base64 Data URL
            if image_url and not image_url.startswith(("http://", "https://", "data:")):
                image_dir = Path(settings.STORAGE_ROOT) / 'image'
                path_list = image_url.split("/")[-2:]
                image_path = Path(image_dir, *path_list)
                if image_path.exists():
                    base64_image = self.image_to_base64(image_path)
                    image_url = f"data:image/jpeg;base64,{base64_image}"
                else:
                    logger.warning(f"图片文件不存在: {image_path}")
                    yield {
                        "type": "error",
                        "error": f"分镜 {scene_number} 图片文件不存在: {image_path}",
                        "scene_number": scene_number,
                    }
                    return

            # 获取运镜参数
            camera_movement = storyboard.get("camera_movement", {})
            
            # 如果 camera_movement 是字符串（JSON格式），先格式化再解析为字典
            if isinstance(camera_movement, str):
                try:
                    # 使用 parse_json 函数进行格式化和解析
                    parsed_data = parse_json(camera_movement)
                    if isinstance(parsed_data, dict):
                        camera_movement = parsed_data
                    else:
                        logger.warning(f"camera_movement 解析后不是字典类型: {type(parsed_data)}")
                        camera_movement = {}
                except Exception as e:
                    logger.warning(f"无法解析camera_movement JSON: {camera_movement}, 错误: {str(e)}")
                    camera_movement = {}

            # 如果没有camera_movement，使用默认值
            if not camera_movement:
                camera_movement = {
                    "movement_type": "static",
                    "movement_params": {}
                }

            # 获取视频时长（从storyboard或使用默认值）
            # 优先从duration_seconds获取，如果没有则从duration字段解析
            duration = storyboard.get("duration_seconds")
            if duration is None:
                duration_str = storyboard.get("duration", "3秒")
                # 解析字符串格式的时长（如"5秒"、"4秒"）
                import re
                match = re.search(r'(\d+(?:\.\d+)?)', str(duration_str))
                if match:
                    duration = float(match.group(1))
                else:
                    duration = 3.0
            else:
                # 确保duration是数字类型
                duration = float(duration) if not isinstance(duration, (int, float)) else duration
            
            fps = storyboard.get("fps", 24)

            # 创建AI客户端
            client = create_ai_client(provider)

            # 调用 generate 方法（使用标准接口）
            # 在同步生成器中运行异步代码
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # 如果事件循环正在运行，创建新任务
                    task = asyncio.create_task(
                        client.generate(
                            image_url=image_url,
                            camera_movement=camera_movement,
                            duration=duration,
                            fps=fps,
                            prompt=prompt,  # 传递构建好的prompt
                            resolution=storyboard.get("resolution", "720P"),  # 可选分辨率
                        )
                    )
                    response = loop.run_until_complete(task)
                else:
                    response = loop.run_until_complete(
                        client.generate(
                            image_url=image_url,
                            camera_movement=camera_movement,
                            duration=duration,
                            fps=fps,
                            prompt=prompt,
                            resolution=storyboard.get("resolution", "720P"),
                        )
                    )
            except RuntimeError:
                # 没有事件循环，创建新的
                response = asyncio.run(
                    client.generate(
                        image_url=image_url,
                        camera_movement=camera_movement,
                        duration=duration,
                        fps=fps,
                        prompt=prompt,
                        resolution=storyboard.get("resolution", "720P"),
                    )
                )

            # 检查响应
            if not response.success:
                yield {
                    "type": "error",
                    "error": response.error or "视频生成失败",
                    "scene_number": scene_number,
                }
                return

            # 提取视频URL
            video_data = response.data or {}
            video_urls = video_data.get("urls", [])
            
            # 如果没有urls，尝试从url字段获取
            if not video_urls and video_data.get("url"):
                video_urls = [video_data["url"]]

            yield {
                "type": "video_generated",
                "scene_number": scene_number,
                "video_urls": {
                    "data": video_urls,
                    "metadata": response.metadata
                },
            }

        except Exception as e:
            logger.error(
                f"分镜 {scene_number} 流式视频生成异常: {str(e)}", exc_info=True
            )

            yield {"type": "error", "error": str(e), "scene_number": scene_number}
    def _get_prompt_template(self, project: Project):
        """获取提示词模板"""
        # 从项目的prompt_template_set中获取
        template_set = getattr(project, 'prompt_template_set', None)
        from apps.prompts.models import PromptTemplateSet, PromptTemplate

        if not template_set:
            # 尝试获取默认提示词集
            template_set = PromptTemplateSet.objects.filter(is_default=True).first()

        if not template_set:
            return None
        # 获取对应阶段的模板 - 使用select_related预加载model_provider
        template = PromptTemplate.objects.select_related('model_provider').filter(
            template_set=template_set,
            stage_type=self.stage_type,
            is_active=True
        ).first()

        return template
    
    def _build_prompt(self, project: Project, storyboard: dict) -> str:
        """
        构建提示词
        从PromptTemplate获取模板并使用Jinja2渲染
        
        注意：此方法只负责构建 prompt 文本，不处理图片转换
        图片处理应在 _generate_single_video_stream 中完成
        """
        template = self._get_prompt_template(project)

        if not template:
            raise ValueError(f"未找到 {self.stage_type} 阶段的提示词模板")
        
        # 复制 storyboard 数据，避免修改原始数据
        storyboard_copy = copy.deepcopy(storyboard)
        
        # 处理 camera_movement：如果是字符串（JSON格式），解析为字典
        camera_movement = storyboard_copy.get("camera_movement", {})
        if isinstance(camera_movement, str):
            try:
                import json
                camera_movement = json.loads(camera_movement)
                storyboard_copy["camera_movement"] = camera_movement
            except json.JSONDecodeError:
                logger.warning(f"无法解析camera_movement JSON: {camera_movement}")
                storyboard_copy["camera_movement"] = {
                    "movement_type": "static",
                    "movement_params": {}
                }
        elif not camera_movement:
            # 如果没有camera_movement，使用默认值
            storyboard_copy["camera_movement"] = {
                "movement_type": "static",
                "movement_params": {}
            }
        
        try:
            # 准备模板变量
            template_vars = {
                'project': {
                    'name': project.name,
                    'description': project.description,
                    'original_topic': project.original_topic,
                },
                **storyboard_copy  # 合并输入数据作为变量
            }

            # 渲染Jinja2模板
            jinja_template = Template(template.template_content)
            rendered_prompt = jinja_template.render(**template_vars)

            return rendered_prompt

        except TemplateError as e:
            logger.error(f"提示词模板渲染失败: {str(e)}")
            raise ValueError(f"提示词模板渲染失败: {str(e)}")
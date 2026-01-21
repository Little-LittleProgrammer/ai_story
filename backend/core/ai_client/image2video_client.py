"""
图生视频客户端实现
支持 MiniMax 图生视频 API
"""

import requests
import json
import time
import logging
import asyncio
from typing import Dict, Any, Optional
from .base import Image2VideoClient as BaseImage2VideoClient, AIResponse

logger = logging.getLogger(__name__)


class Image2VideoClient(BaseImage2VideoClient):
    """
    图生视频客户端实现（MiniMax API）
    """

    def __init__(self, api_url: str, api_key: str, model_name: str, **kwargs):
        """
        初始化图生视频客户端

        Args:
            api_url: API地址（如 https://api.minimaxi.com）
            api_key: API密钥
            model_name: 模型名称
            **kwargs: 其他配置参数
        """
        super().__init__(api_url, api_key, model_name, **kwargs)
        # 确保 API URL 以 /v1/video_generation 结尾或包含基础路径
        if not self.api_url.endswith('/v1/video_generation'):
            # 如果 URL 是基础域名，添加路径
            if self.api_url.endswith('/'):
                self.api_url = self.api_url.rstrip('/')
            self.api_url = f"{self.api_url}/v1/video_generation"

    async def validate_config(self) -> bool:
        """
        验证配置是否有效

        Returns:
            bool: 配置是否有效
        """
        if not self.api_url or not self.api_key or not self.model_name:
            return False

        # 简单的配置验证
        return True

    def _validate_and_adjust_duration(self, duration: float, resolution: str) -> int:
        """
        验证并调整视频时长，使其符合模型和分辨率的要求

        根据MiniMax API文档：
        - MiniMax-Hailuo-2.3/2.3-Fast/02: 768P支持6s或10s，1080P只支持6s
        - 其他模型: 720P支持6s

        Args:
            duration: 请求的时长（秒）
            resolution: 视频分辨率（如 "720P", "768P", "1080P"）

        Returns:
            int: 调整后的时长（秒）
        """
        duration_int = int(duration)
        
        # MiniMax-Hailuo系列模型
        hailiuo_models = ['MiniMax-Hailuo-2.3', 'MiniMax-Hailuo-2.3-Fast', 'MiniMax-Hailuo-02']
        
        if self.model_name in hailiuo_models:
            if resolution == '1080P':
                # 1080P只支持6s
                if duration_int != 6:
                    logger.warning(f"模型 {self.model_name} 在 {resolution} 分辨率下只支持6s，已自动调整")
                    return 6
            elif resolution == '768P':
                # 768P支持6s或10s
                if duration_int not in [6, 10]:
                    # 自动调整到最接近的支持时长
                    adjusted = 6 if duration_int < 8 else 10
                    logger.warning(
                        f"模型 {self.model_name} 在 {resolution} 分辨率下只支持6s或10s，"
                        f"已从 {duration_int}s 调整为 {adjusted}s"
                    )
                    return adjusted
            else:
                # 其他分辨率不支持，默认使用6s
                logger.warning(
                    f"模型 {self.model_name} 不支持 {resolution} 分辨率，"
                    f"已自动调整为6s"
                )
                return 6
        else:
            # 其他模型：720P支持6s
            if resolution == '720P':
                if duration_int != 6:
                    logger.warning(f"模型 {self.model_name} 在 {resolution} 分辨率下只支持6s，已自动调整")
                    return 6
            else:
                # 其他分辨率不支持，默认使用6s
                logger.warning(
                    f"模型 {self.model_name} 不支持 {resolution} 分辨率，"
                    f"已自动调整为6s"
                )
                return 6
        
        return duration_int

    def _validate_and_adjust_resolution(self, resolution: str, duration: float) -> str:
        """
        验证并调整视频分辨率，使其符合模型的要求

        根据MiniMax API文档：
        - MiniMax-Hailuo-2.3/2.3-Fast/02: 只支持768P和1080P，不支持720P
        - 其他模型: 支持720P

        Args:
            resolution: 请求的分辨率（如 "720P", "768P", "1080P"）
            duration: 视频时长（秒），用于确定默认分辨率

        Returns:
            str: 调整后的分辨率
        """
        # MiniMax-Hailuo系列模型
        hailiuo_models = ['MiniMax-Hailuo-2.3', 'MiniMax-Hailuo-2.3-Fast', 'MiniMax-Hailuo-02']
        
        if self.model_name in hailiuo_models:
            # Hailuo系列不支持720P，需要调整为768P或1080P
            if resolution == '720P':
                # 根据时长选择合适的分辨率：如果时长是6s，优先使用1080P；否则使用768P
                adjusted = '1080P' if int(duration) == 6 else '768P'
                logger.warning(
                    f"模型 {self.model_name} 不支持 {resolution} 分辨率，"
                    f"已自动调整为 {adjusted}"
                )
                return adjusted
            elif resolution not in ['768P', '1080P']:
                # 其他不支持的分辨率，默认使用768P
                logger.warning(
                    f"模型 {self.model_name} 不支持 {resolution} 分辨率，"
                    f"已自动调整为 768P"
                )
                return '768P'
        
        return resolution

    async def _retrieve_file_url(self, file_id: str, headers: Dict[str, str]) -> Optional[str]:
        """
        通过 file_id 获取文件下载 URL

        Args:
            file_id: 文件ID
            headers: 请求头（包含认证信息）

        Returns:
            Optional[str]: 下载URL，失败返回None
        """
        try:
            # 构建文件检索接口URL
            base_url = self.api_url.replace('/v1/video_generation', '')
            retrieve_url = f"{base_url}/v1/files/retrieve"
            
            # 调用文件检索接口
            response = requests.get(
                retrieve_url,
                params={'file_id': file_id},
                headers=headers,
                timeout=30
            )
            response.raise_for_status()
            
            result = response.json()
            
            # 检查业务状态码
            base_resp = result.get('base_resp', {})
            status_code = base_resp.get('status_code', -1)
            
            if status_code != 0:
                status_msg = base_resp.get('status_msg', '未知错误')
                logger.error(
                    f"获取文件下载URL失败: file_id={file_id}, "
                    f"status_code={status_code}, status_msg={status_msg}"
                )
                return None
            
            # 提取下载URL
            file_obj = result.get('file', {})
            download_url = file_obj.get('download_url')
            
            if download_url:
                logger.info(
                    f"成功获取文件下载URL: file_id={file_id}, "
                    f"filename={file_obj.get('filename', 'unknown')}, "
                    f"bytes={file_obj.get('bytes', 0)}"
                )
                return download_url
            else:
                logger.error(f"文件检索成功但缺少download_url: file_id={file_id}")
                return None
                
        except requests.exceptions.RequestException as e:
            logger.error(f"获取文件下载URL请求失败: file_id={file_id}, error={str(e)}")
            return None
        except Exception as e:
            logger.error(f"获取文件下载URL异常: file_id={file_id}, error={str(e)}", exc_info=True)
            return None

    async def _generate_video(
        self,
        image_url: str,
        camera_movement: Dict[str, Any],
        duration: float = 3.0,
        fps: int = 24,
        **kwargs
    ) -> AIResponse:
        """
        生成视频（适配 MiniMax API 格式）

        Args:
            image_url: 源图片URL或Base64 Data URL（如 data:image/jpeg;base64,...）
            camera_movement: 运镜参数
            duration: 视频时长（秒），默认3.0
            fps: 帧率（MiniMax API不支持此参数，仅保留兼容性）
            **kwargs: 其他参数
                - prompt: 视频文本描述（可选，如果不提供则从camera_movement构建）
                - resolution: 视频分辨率（可选，如 "720P", "768P", "1080P"）
                - prompt_optimizer: 是否自动优化prompt（默认True）
                - fast_pretreatment: 是否缩短优化耗时（默认False）

        Returns:
            AIResponse: 包含视频URL的响应对象
        """
        start_time = time.time()

        # 构建请求头
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }

        # 从 kwargs 获取参数
        prompt = kwargs.get('prompt', '')
        resolution = kwargs.get('resolution', '720P')  # 默认720P
        prompt_optimizer = kwargs.get('prompt_optimizer', True)
        fast_pretreatment = kwargs.get('fast_pretreatment', False)

        # 如果没有提供 prompt，尝试从 camera_movement 构建
        if not prompt and camera_movement:
            prompt = self._build_prompt_from_camera_movement(camera_movement)

        # 验证并调整分辨率（根据模型）
        resolution = self._validate_and_adjust_resolution(resolution, duration)
        
        # 验证并调整视频时长（根据模型和分辨率）
        duration_int = self._validate_and_adjust_duration(duration, resolution)
        
        if duration_int != int(duration):
            logger.warning(
                f"视频时长已自动调整: {int(duration)}s -> {duration_int}s "
                f"(model={self.model_name}, resolution={resolution})"
            )

        # 构建请求体（符合 MiniMax API 格式）
        payload = {
            "model": self.model_name,
            "first_frame_image": image_url,  # 支持 URL 或 Base64 Data URL
            "duration": duration_int,
            "resolution": resolution,
            "prompt_optimizer": prompt_optimizer,
        }

        # 添加 prompt（如果提供）
        if prompt:
            payload["prompt"] = prompt

        # 添加可选参数
        if fast_pretreatment:
            payload["fast_pretreatment"] = True

        try:
            timeout = self.config.get('timeout', 300)  # 视频生成可能需要更长时间

            # 发送POST请求创建任务
            logger.info(f"创建视频生成任务: model={self.model_name}, duration={duration_int}s, resolution={resolution}")
            response = requests.post(
                self.api_url,
                headers=headers,
                data=json.dumps(payload),
                timeout=timeout
            )

            # 检查HTTP响应状态
            response.raise_for_status()

            # 解析响应数据（MiniMax API 格式）
            result = response.json()
            latency_ms = int((time.time() - start_time) * 1000)

            # 检查业务状态码（MiniMax 使用 base_resp.status_code）
            base_resp = result.get('base_resp', {})
            status_code = base_resp.get('status_code', -1)

            if status_code != 0:
                status_msg = base_resp.get('status_msg', '未知错误')
                error_msg = f'API返回错误: status_code={status_code}, status_msg={status_msg}'
                logger.error(error_msg)
                return AIResponse(
                    success=False,
                    error=error_msg
                )

            # 提取任务ID
            task_id = result.get('task_id')
            if not task_id:
                return AIResponse(
                    success=False,
                    error='响应格式错误: 缺少task_id字段'
                )

            logger.info(f"视频生成任务已创建: task_id={task_id}")

            # 轮询等待任务完成
            video_url = await self._wait_for_task_completion(task_id, headers, timeout)

            if not video_url:
                return AIResponse(
                    success=False,
                    error='视频生成失败或超时'
                )

            total_latency_ms = int((time.time() - start_time) * 1000)

            return AIResponse(
                success=True,
                data={
                    'url': video_url,
                    'urls': [video_url],  # 兼容原有格式
                    'task_id': task_id
                },
                metadata={
                    'latency_ms': total_latency_ms,
                    'model': self.model_name,
                    'duration': duration_int,
                    'resolution': resolution,
                    'task_id': task_id
                }
            )

        except requests.exceptions.Timeout:
            error_msg = f'请求超时: 超过 {timeout} 秒'
            logger.error(error_msg)
            return AIResponse(
                success=False,
                error=error_msg
            )
        except requests.exceptions.RequestException as e:
            error_msg = f'HTTP请求失败: {str(e)}'
            logger.error(error_msg, exc_info=True)
            return AIResponse(
                success=False,
                error=error_msg
            )
        except Exception as e:
            error_msg = f'视频生成失败: {str(e)}'
            logger.error(error_msg, exc_info=True)
            return AIResponse(
                success=False,
                error=error_msg
            )

    def _build_prompt_from_camera_movement(self, camera_movement: Dict[str, Any]) -> str:
        """
        从运镜参数构建提示词

        Args:
            camera_movement: 运镜参数字典

        Returns:
            str: 构建的提示词
        """
        movement_type = camera_movement.get('movement_type', 'static')
        movement_params = camera_movement.get('movement_params', {})

        # MiniMax 支持的运镜指令映射
        movement_map = {
            'static': '固定',
            'zoom_in': '[推进]',
            'zoom_out': '[拉远]',
            'pan_left': '[左移]',
            'pan_right': '[右移]',
            'tilt_up': '[上摇]',
            'tilt_down': '[下摇]',
            'pan_left_continuous': '[左摇]',
            'pan_right_continuous': '[右摇]',
            'crane_up': '[上升]',
            'crane_down': '[下降]',
            'shake': '[晃动]',
            'follow': '[跟随]',
        }

        # 获取运镜指令
        movement_instruction = movement_map.get(movement_type, '')

        # 构建基础提示词
        prompt_parts = []
        if movement_instruction:
            prompt_parts.append(movement_instruction)

        # 添加其他描述信息
        if movement_params:
            speed = movement_params.get('speed', '')
            if speed:
                prompt_parts.append(f"速度: {speed}")

        # 如果没有有效的运镜指令，返回默认提示
        if not prompt_parts:
            return "根据图片内容生成视频"

        return " ".join(prompt_parts)

    async def _wait_for_task_completion(
        self,
        task_id: str,
        headers: Dict[str, str],
        timeout: int = 600,
        poll_interval: int = 5
    ) -> Optional[str]:
        """
        轮询等待任务完成

        Args:
            task_id: 任务ID
            headers: 请求头
            timeout: 总超时时间（秒）
            poll_interval: 轮询间隔（秒）

        Returns:
            Optional[str]: 视频URL，失败返回None
        """
        start_time = time.time()
        query_url = self.api_url.replace('/v1/video_generation', '/v1/query/video_generation')

        while True:
            elapsed_time = time.time() - start_time

            if elapsed_time > timeout:
                logger.error(f"视频生成任务超时: task_id={task_id}, 等待时间超过 {timeout} 秒")
                return None

            try:
                # 查询任务状态
                response = requests.get(
                    f"{query_url}?task_id={task_id}",
                    headers=headers,
                    timeout=30
                )
                response.raise_for_status()

                result = response.json()

                # 检查业务状态码
                base_resp = result.get('base_resp', {})
                status_code = base_resp.get('status_code', -1)

                if status_code != 0:
                    status_msg = base_resp.get('status_msg', '未知错误')
                    logger.error(f"查询任务状态失败: status_code={status_code}, status_msg={status_msg}")
                    return None

                # 获取任务状态（转换为小写以确保大小写一致性）
                status = result.get('status', '').lower()
                logger.debug(f"任务状态: task_id={task_id}, status={status}")

                if status == 'success':
                    # 任务成功，提取 file_id 并获取下载URL
                    file_id = result.get('file_id')
                    video_width = result.get('video_width', 0)
                    video_height = result.get('video_height', 0)
                    
                    if file_id:
                        # 通过 file_id 获取实际的下载URL
                        download_url = await self._retrieve_file_url(file_id, headers)
                        
                        if download_url:
                            logger.info(
                                f"视频生成成功: task_id={task_id}, file_id={file_id}, "
                                f"resolution={video_width}x{video_height}, "
                                f"download_url={download_url}"
                            )
                            return download_url
                        else:
                            # 如果获取下载URL失败，返回 file_id 作为fallback
                            logger.warning(
                                f"无法获取下载URL，返回file_id: task_id={task_id}, file_id={file_id}"
                            )
                            return f"file_id:{file_id}"
                    else:
                        logger.error(f"任务成功但缺少file_id: task_id={task_id}")
                        return None

                elif status == 'failed':
                    error_msg = result.get('error', '未知错误')
                    logger.error(f"视频生成任务失败: task_id={task_id}, error={error_msg}")
                    return None

                elif status == 'processing':
                    # 任务进行中，继续等待
                    logger.debug(f"任务进行中，等待 {poll_interval} 秒后重试: task_id={task_id}")
                    await asyncio.sleep(poll_interval)
                    continue

                else:
                    # 未知状态，继续等待
                    logger.warning(f"未知任务状态: task_id={task_id}, status={status}")
                    await asyncio.sleep(poll_interval)
                    continue

            except requests.exceptions.RequestException as e:
                logger.warning(f"查询任务状态失败，等待 {poll_interval} 秒后重试: {str(e)}")
                await asyncio.sleep(poll_interval)
                continue
            except Exception as e:
                logger.error(f"查询任务状态异常: {str(e)}", exc_info=True)
                await asyncio.sleep(poll_interval)
                continue


# 保留原有的 VideoGenerator 类以兼容旧代码（已废弃）
class VideoGenerator:
    """视频生成客户端（已废弃，请使用 Image2VideoClient）"""
    
    BASE_URL = "https://openai.qiniu.com"
    BASE_URL_BACKUP = "https://api.qnaigc.com"

    def __init__(self, api_url: str, api_token: str, model: str):
        """初始化视频生成客户端（已废弃）"""
        logger.warning("VideoGenerator 类已废弃，请使用 Image2VideoClient")
        self.api_token = api_token
        self.base_url = api_url
        self.model = model
        self.headers = {
            "Authorization": f"Bearer {api_token}",
            "Content-Type": "application/json"
        }

    def create_video_task(self, **kwargs) -> str:
        """创建视频任务（已废弃）"""
        raise NotImplementedError("VideoGenerator 已废弃，请使用 Image2VideoClient")

"""
文生图客户端实现
支持通用的文生图API接口
"""

import requests
import json
import time
import logging
from typing import Dict, Any
from .base import Text2ImageClient as BaseText2ImageClient, AIResponse

logger = logging.getLogger(__name__)


class Text2ImageClient(BaseText2ImageClient):
    """
    文生图客户端实现
    支持通用的文生图API接口
    """

    def _generate_image(
        self,
        prompt: str,
        negative_prompt: str = "",
        width: int = 1024,
        height: int = 1024,
        steps: int = 20,
        **kwargs
    ) -> AIResponse:
        """
        生成图片（适配 minimaxi API 格式）

        Args:
            prompt: 图片提示词
            negative_prompt: 负面提示词（minimaxi 暂不支持）
            width: 宽度（minimaxi 通过 aspect_ratio 控制）
            height: 高度（minimaxi 通过 aspect_ratio 控制）
            steps: 生成步数（minimaxi 暂不支持）
            **kwargs: 其他参数
                - ratio: 图片比例，如 "16:9", "9:16", "1:1"（会转换为 aspect_ratio）
                - aspect_ratio: 图片比例（优先使用）
                - n: 生成图片数量，默认1
                - prompt_optimizer: 是否启用提示词优化器，默认False
                - response_format: 响应格式，默认"url"

        Returns:
            AIResponse: 包含图片URL的响应对象
        """
        start_time = time.time()

        # 构建请求头
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }

        # 从kwargs获取参数，优先使用 aspect_ratio，如果没有则使用 ratio
        aspect_ratio = kwargs.get('aspect_ratio') or kwargs.get('ratio', '1:1')
        n = kwargs.get('n', 1)  # 生成图片数量，默认1
        prompt_optimizer = kwargs.get('prompt_optimizer', False)  # 提示词优化器
        response_format = kwargs.get('response_format', 'url')  # 响应格式

        # 构建请求体（符合 minimaxi API 格式）
        payload = {
            "model": self.model_name,
            "prompt": prompt,
            "aspect_ratio": aspect_ratio,
            "response_format": response_format,
            "n": n
        }

        # 添加可选参数
        if prompt_optimizer:
            payload["prompt_optimizer"] = True

        # 注意：minimaxi API 暂不支持 negative_prompt、resolution 等参数

        # 打印请求参数
        logger.info(f"文生图请求参数:")
        logger.info(f"  URL: {self.api_url}")
        logger.info(f"  Headers: {json.dumps({k: v if k != 'Authorization' else 'Bearer ***' for k, v in headers.items()}, indent=2, ensure_ascii=False)}")
        logger.info(f"  Payload: {json.dumps(payload, indent=2, ensure_ascii=False)}")

        try:
            timeout = self.config.get('timeout', 60)

            # 发送POST请求
            response = requests.post(
                self.api_url,
                headers=headers,
                data=json.dumps(payload),
                timeout=timeout
            )

            # 检查HTTP响应状态
            response.raise_for_status()

            # 解析响应数据（minimaxi API 格式）
            result = response.json()
            latency_ms = int((time.time() - start_time) * 1000)

            # 检查业务状态码（minimaxi 使用 base_resp.status_code）
            base_resp = result.get('base_resp', {})
            status_code = base_resp.get('status_code', -1)
            
            if status_code != 0:
                status_msg = base_resp.get('status_msg', '未知错误')
                return AIResponse(
                    success=False,
                    error=f'API返回错误: status_code={status_code}, status_msg={status_msg}'
                )

            # 提取图片URL列表（minimaxi 格式: data.image_urls）
            data = result.get('data', {})
            image_urls = data.get('image_urls', [])
            
            if not image_urls:
                return AIResponse(
                    success=False,
                    error='响应格式错误: 缺少image_urls字段或image_urls为空'
                )

            # 构建标准格式的图片数据列表（兼容原有格式）
            images_data = [{"url": url} for url in image_urls]

            return AIResponse(
                success=True,
                data={
                    'urls': image_urls,
                    'images': images_data  # 包含完整的图片信息，格式: [{"url": "xxx"}]
                },
                metadata={
                    'latency_ms': latency_ms,
                    'model': self.model_name,
                    'aspect_ratio': aspect_ratio,
                    'n': n,
                    'prompt_optimizer': prompt_optimizer,
                    'minimaxi_metadata': result.get('metadata', {}),  # minimaxi 的元数据
                    'minimaxi_id': result.get('id', '')  # minimaxi 返回的任务ID
                }
            )

        except requests.exceptions.RequestException as e:
            return AIResponse(
                success=False,
                error=f'网络请求错误: {str(e)}'
            )
        except Exception as e:
            return AIResponse(
                success=False,
                error=f'未知错误: {str(e)}'
            )

    def validate_config(self) -> bool:
        """验证配置"""
        if not self.api_url or not self.api_key or not self.model_name:
            return False

        # 简单的连通性测试（可选实现）
        return True


# 保留旧的函数接口以保持向后兼容
def generate_image(
    api_url,
    session_id,
    model,
    prompt,
    ratio="1:1",
    resolution="2k",
    negative_prompt=None,
    sample_strength=None,
    response_format=None,
    n=1,
    prompt_optimizer=False
):
    """
    调用图像生成API（向后兼容的函数接口，适配 minimaxi API 格式）

    参数:
        api_url (str): API地址
        session_id (str): 会话ID，用于Authorization（JWT token）
        model (str): 使用的模型名称，如"image-01"
        prompt (str): 图像描述文本
        ratio (str, 可选): 图像比例，默认"1:1"（会转换为 aspect_ratio）
        resolution (str, 可选): 分辨率级别（minimaxi 不支持，保留参数以兼容）
        negative_prompt (str, 可选): 负面提示词（minimaxi 不支持，保留参数以兼容）
        sample_strength (float, 可选): 采样强度（minimaxi 不支持，保留参数以兼容）
        response_format (str, 可选): 响应格式，默认"url"
        n (int, 可选): 生成图片数量，默认1
        prompt_optimizer (bool, 可选): 是否启用提示词优化器，默认False

    返回:
        dict: 接口响应数据（minimaxi 格式）
    """
    # 构建请求头
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {session_id}"
    }

    # 构建请求体（符合 minimaxi API 格式）
    payload = {
        "model": model,
        "prompt": prompt,
        "aspect_ratio": ratio,  # 使用 ratio 作为 aspect_ratio
        "response_format": response_format or "url",
        "n": n
    }

    # 添加可选参数
    if prompt_optimizer:
        payload["prompt_optimizer"] = True

    # 注意：minimaxi API 不支持 negative_prompt、resolution、sample_strength 等参数

    try:
        # 发送POST请求
        response = requests.post(
            api_url,
            headers=headers,
            data=json.dumps(payload)
        )

        # 检查响应状态
        response.raise_for_status()

        # 返回解析后的JSON数据（minimaxi 格式）
        return response.json()

    except requests.exceptions.RequestException as e:
        print(f"请求出错: {e}")
        # 可根据需要处理异常，如返回None或重新抛出
        return None

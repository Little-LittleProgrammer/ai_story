import json
import re


def _extract_json_from_text(text: str) -> str:
        """从文本中提取JSON内容,处理可能包含markdown代码块的情况"""
        # 尝试移除 markdown 代码块标记
        text = text.strip()

        # 如果有 ```json 或 ``` 标记,提取其中的内容
        if '```' in text:
            # 匹配 ```json ... ``` 或 ``` ... ```
            match = re.search(r'```(?:json)?\s*\n?(.*?)\n?```', text, re.DOTALL)
            if match:
                text = match.group(1).strip()

        return text


def _fix_json_format(text: str) -> str:
    """修复常见的JSON格式错误"""
    # 修复缺少字符串值前引号的情况
    # 例如: "description":兔子..." -> "description": "兔子..."
    
    # 匹配 "key":值 模式，其中值不是以引号开头
    def fix_missing_quote(match):
        key = match.group(1)  # 键名（带引号）
        colon_ws = match.group(2)  # 冒号和空白
        value = match.group(3)  # 值部分（可能包含结尾引号）
        
        value_stripped = value.strip()
        
        # 如果值已经以引号开头，不需要修复
        if value_stripped.startswith('"'):
            return match.group(0)
        
        # 如果值是数字、布尔值、null、对象或数组，不需要修复
        if (value_stripped.startswith(('{', '[', '-')) or
            value_stripped.lower() in ('true', 'false', 'null') or
            (value_stripped and value_stripped[0].isdigit())):
            return match.group(0)
        
        # 如果值以引号结尾但没有开头引号，添加开头引号
        if value_stripped.endswith('"'):
            return f'{key}{colon_ws}"{value_stripped}'
        
        # 否则，为整个值添加引号
        return f'{key}{colon_ws}"{value_stripped}"'
    
    # 匹配 "key": 值 模式，值到下一个逗号、}、]之前
    # 值不能以引号、数字、{、[开头（这些已经是正确格式）
    # 值可能包含中文字符，也可能以引号结尾（缺少开头引号的情况）
    # 使用更宽松的匹配：匹配从冒号后到下一个逗号、}、]之前的所有内容（包括可能的引号）
    pattern = r'("(?:[^"\\]|\\.)*")\s*(:\s*)([^",\[\]{}\s].*?)(?=\s*[,}\]])'
    
    fixed_text = re.sub(pattern, fix_missing_quote, text, flags=re.MULTILINE | re.DOTALL)
    return fixed_text

def parse_storyboard_json(json_text: str) -> dict:
    """解析分镜JSON数据"""
    import logging
    logger = logging.getLogger(__name__)
    try:
        # 如果输入为空或None，返回空字典
        if not json_text or not json_text.strip():
            logger.debug("json_text 为空，返回空字典")
            return {}
        
        # 提取纯JSON内容
        clean_json = _extract_json_from_text(json_text)
        logger.debug(f"clean_json: {clean_json[:200] if clean_json else '(空)'}")
        
        # 如果提取后仍为空，返回空字典
        if not clean_json or not clean_json.strip():
            logger.debug("clean_json 为空，返回空字典")
            return {}
        
        # 先尝试直接解析
        try:
            storyboard_data = json.loads(clean_json)
        except json.JSONDecodeError as e:
            # 如果解析失败，尝试修复格式后再次解析
            logger.debug(f"首次解析失败: {str(e)}, 尝试修复JSON格式")
            fixed_json = _fix_json_format(clean_json)
            logger.debug(f"修复后的JSON: {fixed_json[:500]}...")
            storyboard_data = json.loads(fixed_json)
        
       
        # 验证数据结构
        if 'scenes' not in storyboard_data:
            raise ValueError("JSON数据中缺少 'scenes' 字段")

        if not isinstance(storyboard_data['scenes'], list):
            raise ValueError("'scenes' 必须是数组类型")

        # 验证每个场景的必需字段
        for i, scene in enumerate(storyboard_data['scenes']):
            required_fields = ['scene_number', 'narration', 'visual_prompt', 'shot_type']
            for field in required_fields:
                if field not in scene:
                    raise ValueError(f"场景 {i+1} 缺少必需字段: {field}")
        logger.debug(f"storyboard_data: {storyboard_data}")
        return storyboard_data

    except json.JSONDecodeError as e:
        raise ValueError(f"JSON解析失败: {str(e)}\n原始内容:\n{json_text[:200]}...")
    except Exception as e:
        raise ValueError(f"分镜数据解析失败: {str(e)}")


def parse_json(json_text: str) -> dict:
    """解析JSON数据"""
    try:
        # 提取纯JSON内容
        clean_json = _extract_json_from_text(json_text)

        # 先尝试直接解析
        try:
            data = json.loads(clean_json)
        except json.JSONDecodeError:
            # 如果解析失败，尝试修复格式后再次解析
            fixed_json = _fix_json_format(clean_json)
            data = json.loads(fixed_json)

        return data

    except json.JSONDecodeError:
        return ""
    except Exception:
        return ""
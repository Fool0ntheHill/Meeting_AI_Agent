# -*- coding: utf-8 -*-
"""
数据格式转换工具

用于在 snake_case (Python/后端) 和 camelCase (JavaScript/前端) 之间转换
"""

import re
from typing import Any, Dict, List, Union


def to_camel_case(snake_str: str) -> str:
    """
    将 snake_case 字符串转换为 camelCase
    
    Args:
        snake_str: snake_case 字符串，如 "user_name"
        
    Returns:
        str: camelCase 字符串，如 "userName"
        
    Examples:
        >>> to_camel_case("user_name")
        'userName'
        >>> to_camel_case("task_id")
        'taskId'
        >>> to_camel_case("audio_file_path")
        'audioFilePath'
    """
    components = snake_str.split('_')
    # 第一个单词保持小写，其余单词首字母大写
    return components[0] + ''.join(x.title() for x in components[1:])


def to_snake_case(camel_str: str) -> str:
    """
    将 camelCase 字符串转换为 snake_case
    
    Args:
        camel_str: camelCase 字符串，如 "userName"
        
    Returns:
        str: snake_case 字符串，如 "user_name"
        
    Examples:
        >>> to_snake_case("userName")
        'user_name'
        >>> to_snake_case("taskId")
        'task_id'
        >>> to_snake_case("audioFilePath")
        'audio_file_path'
    """
    # 在大写字母前插入下划线，然后转小写
    snake_str = re.sub(r'(?<!^)(?=[A-Z])', '_', camel_str).lower()
    return snake_str


def convert_keys_to_camel_case(obj: Any) -> Any:
    """
    递归地将对象的所有键从 snake_case 转换为 camelCase
    
    用于将后端数据转换为前端格式
    
    Args:
        obj: 要转换的对象（dict, list, 或其他类型）
        
    Returns:
        Any: 转换后的对象
        
    Examples:
        >>> data = {"user_id": 1, "user_name": "张三"}
        >>> convert_keys_to_camel_case(data)
        {'userId': 1, 'userName': '张三'}
        
        >>> data = [{"task_id": "123", "task_name": "会议"}]
        >>> convert_keys_to_camel_case(data)
        [{'taskId': '123', 'taskName': '会议'}]
    """
    if obj is None:
        return None
    
    if isinstance(obj, dict):
        return {
            to_camel_case(key): convert_keys_to_camel_case(value)
            for key, value in obj.items()
        }
    
    if isinstance(obj, list):
        return [convert_keys_to_camel_case(item) for item in obj]
    
    return obj


def convert_keys_to_snake_case(obj: Any) -> Any:
    """
    递归地将对象的所有键从 camelCase 转换为 snake_case
    
    用于将前端数据转换为后端格式
    
    Args:
        obj: 要转换的对象（dict, list, 或其他类型）
        
    Returns:
        Any: 转换后的对象
        
    Examples:
        >>> data = {"userId": 1, "userName": "张三"}
        >>> convert_keys_to_snake_case(data)
        {'user_id': 1, 'user_name': '张三'}
        
        >>> data = [{"taskId": "123", "taskName": "会议"}]
        >>> convert_keys_to_snake_case(data)
        [{'task_id': '123', 'task_name': '会议'}]
    """
    if obj is None:
        return None
    
    if isinstance(obj, dict):
        return {
            to_snake_case(key): convert_keys_to_snake_case(value)
            for key, value in obj.items()
        }
    
    if isinstance(obj, list):
        return [convert_keys_to_snake_case(item) for item in obj]
    
    return obj


# 别名，与前端命名保持一致
convertKeysToCamelCase = convert_keys_to_camel_case
convertKeysToSnakeCase = convert_keys_to_snake_case

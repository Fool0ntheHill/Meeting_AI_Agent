#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试可用的模型
"""

import requests
import json

# API 配置
BASE_URL = "http://llm-api.gs.com:4000"
API_KEY = "sk-WTmUUql26vw3fBa2rwpxXQ"

# 根据错误信息，这个 team 可以访问的模型前缀
AVAILABLE_PREFIXES = ['one/*', 'dashscope/*', 'ollama/*', 'deepseek/*', 'openai/*']

# 常见的模型名称
TEST_MODELS = [
    "deepseek/deepseek-chat",
    "deepseek/deepseek-coder",
    "openai/gpt-4o",
    "openai/gpt-4o-mini",
    "openai/gpt-3.5-turbo",
    "dashscope/qwen-plus",
    "dashscope/qwen-turbo",
    "one/yi-large",
]

def test_model(model_name):
    """测试单个模型"""
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
    }
    
    payload = {
        "model": model_name,
        "messages": [
            {
                "role": "user",
                "content": "你好"
            }
        ],
        "max_tokens": 10
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            if "choices" in result and len(result["choices"]) > 0:
                content = result["choices"][0].get("message", {}).get("content", "")
                return True, content[:50]
            return True, "响应格式异常"
        else:
            error_msg = response.json().get("error", {}).get("message", response.text)
            return False, error_msg[:100]
    except Exception as e:
        return False, str(e)[:100]


def main():
    print("=" * 80)
    print("  测试可用模型")
    print("=" * 80)
    print()
    print(f"Base URL: {BASE_URL}")
    print(f"API Key: {API_KEY[:20]}...")
    print()
    print(f"可访问的模型前缀: {', '.join(AVAILABLE_PREFIXES)}")
    print()
    print("=" * 80)
    print()
    
    available_models = []
    
    for model in TEST_MODELS:
        print(f"测试模型: {model}")
        success, message = test_model(model)
        
        if success:
            print(f"  ✅ 可用")
            print(f"  回复: {message}")
            available_models.append(model)
        else:
            print(f"  ❌ 不可用")
            if len(message) < 80:
                print(f"  原因: {message}")
        print()
    
    print("=" * 80)
    print(f"  可用模型总数: {len(available_models)}")
    print("=" * 80)
    
    if available_models:
        print()
        print("可用模型列表:")
        for model in available_models:
            print(f"  - {model}")


if __name__ == "__main__":
    main()

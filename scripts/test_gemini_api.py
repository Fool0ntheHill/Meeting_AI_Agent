#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试 Gemini API 接口
"""

import requests
import json

# API 配置
BASE_URL = "http://llm-api.gs.com:4000"
API_KEY = "sk-WTmUUql26vw3fBa2rwpxXQ"
MODEL = "gemini/gemini-3-pro"  # 添加 gemini/ 前缀

def test_gemini_api():
    """测试 Gemini API"""
    print("=" * 80)
    print("  测试 Gemini API 接口")
    print("=" * 80)
    print()
    print(f"Base URL: {BASE_URL}")
    print(f"API Key: {API_KEY[:20]}...")
    print()
    
    # 准备请求
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
    }
    
    # 测试消息
    payload = {
        "model": MODEL,
        "messages": [
            {
                "role": "user",
                "content": "你好，请用一句话介绍一下你自己。"
            }
        ],
        "temperature": 0.7,
        "max_tokens": 100
    }
    
    print("1. 测试基本对话...")
    print(f"   请求: {payload['messages'][0]['content']}")
    print()
    
    try:
        # 发送请求
        response = requests.post(
            f"{BASE_URL}/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=30
        )
        
        print(f"   状态码: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"   ✅ 请求成功")
            print()
            
            # 解析响应
            if "choices" in result and len(result["choices"]) > 0:
                message = result["choices"][0].get("message", {})
                content = message.get("content", "")
                print(f"   回复: {content}")
                print()
                
                # 显示使用情况
                if "usage" in result:
                    usage = result["usage"]
                    print(f"   Token 使用:")
                    print(f"   - 输入: {usage.get('prompt_tokens', 0)}")
                    print(f"   - 输出: {usage.get('completion_tokens', 0)}")
                    print(f"   - 总计: {usage.get('total_tokens', 0)}")
            else:
                print(f"   ⚠️  响应格式异常")
                print(f"   响应: {json.dumps(result, indent=2, ensure_ascii=False)}")
        else:
            print(f"   ❌ 请求失败")
            print(f"   响应: {response.text}")
    
    except requests.exceptions.Timeout:
        print(f"   ❌ 请求超时")
    except requests.exceptions.ConnectionError as e:
        print(f"   ❌ 连接失败: {e}")
    except Exception as e:
        print(f"   ❌ 发生错误: {e}")
        import traceback
        traceback.print_exc()
    
    print()
    
    # 测试结构化输出
    print("2. 测试结构化输出...")
    
    structured_payload = {
        "model": MODEL,
        "messages": [
            {
                "role": "user",
                "content": "请分析这段会议内容并生成结构化的会议纪要：'大家好，今天我们讨论了项目进度。张三负责前端开发，李四负责后端开发。下周五之前需要完成第一版。'"
            }
        ],
        "response_format": {
            "type": "json_schema",
            "json_schema": {
                "name": "meeting_minutes",
                "strict": True,
                "schema": {
                    "type": "object",
                    "properties": {
                        "summary": {
                            "type": "string",
                            "description": "会议摘要"
                        },
                        "participants": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "参与者列表"
                        },
                        "action_items": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "task": {"type": "string"},
                                    "assignee": {"type": "string"},
                                    "deadline": {"type": "string"}
                                },
                                "required": ["task", "assignee"],
                                "additionalProperties": False
                            }
                        }
                    },
                    "required": ["summary", "participants", "action_items"],
                    "additionalProperties": False
                }
            }
        }
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/v1/chat/completions",
            headers=headers,
            json=structured_payload,
            timeout=30
        )
        
        print(f"   状态码: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"   ✅ 请求成功")
            print()
            
            if "choices" in result and len(result["choices"]) > 0:
                message = result["choices"][0].get("message", {})
                content = message.get("content", "")
                
                # 尝试解析 JSON
                try:
                    structured_data = json.loads(content)
                    print(f"   结构化输出:")
                    print(json.dumps(structured_data, indent=2, ensure_ascii=False))
                except json.JSONDecodeError:
                    print(f"   回复: {content}")
        else:
            print(f"   ❌ 请求失败")
            print(f"   响应: {response.text}")
    
    except Exception as e:
        print(f"   ❌ 发生错误: {e}")
    
    print()
    print("=" * 80)
    print("  测试完成")
    print("=" * 80)


if __name__ == "__main__":
    test_gemini_api()

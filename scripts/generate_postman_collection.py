#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""生成 Postman 集合文件"""

import json
from pathlib import Path

def generate_postman_collection():
    """生成 Postman 集合"""
    collection = {
        "info": {
            "name": "Meeting Minutes Agent API",
            "description": "会议纪要 Agent API 完整集合",
            "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json",
            "version": "1.0.0"
        },
        "variable": [
            {"key": "base_url", "value": "http://localhost:8000/api/v1", "type": "string"},
            {"key": "api_key", "value": "test-api-key", "type": "string"},
            {"key": "task_id", "value": "", "type": "string"}
        ],
        "item": [
            {
                "name": "Health",
                "item": [
                    {
                        "name": "Health Check",
                        "request": {
                            "method": "GET",
                            "header": [],
                            "url": {
                                "raw": "{{base_url}}/health",
                                "host": ["{{base_url}}"],
                                "path": ["health"]
                            }
                        }
                    },
                    {
                        "name": "Root",
                        "request": {
                            "method": "GET",
                            "header": [],
                            "url": {
                                "raw": "{{base_url}}/",
                                "host": ["{{base_url}}"],
                                "path": [""]
                            }
                        }
                    }
                ]
            },
            {
                "name": "Tasks",
                "item": [
                    {
                        "name": "Create Task",
                        "event": [
                            {
                                "listen": "test",
                                "script": {
                                    "exec": [
                                        "if (pm.response.code === 201) {",
                                        "    var jsonData = pm.response.json();",
                                        "    pm.collectionVariables.set('task_id', jsonData.task_id);",
                                        "}"
                                    ]
                                }
                            }
                        ],
                        "request": {
                            "method": "POST",
                            "header": [{"key": "Authorization", "value": "{{api_key}}"}],
                            "body": {
                                "mode": "raw",
                                "raw": json.dumps({
                                    "audio_files": [{"file_path": "test_data/meeting_sample.wav", "speaker_id": "speaker_001"}],
                                    "prompt_instance": {"template_id": "global_meeting_minutes_v1", "parameters": {}},
                                    "asr_language": "zh-CN+en-US",
                                    "output_language": "zh-CN"
                                }, indent=2, ensure_ascii=False),
                                "options": {"raw": {"language": "json"}}
                            },
                            "url": {
                                "raw": "{{base_url}}/tasks",
                                "host": ["{{base_url}}"],
                                "path": ["tasks"]
                            }
                        }
                    },
                    {
                        "name": "Get Task Status",
                        "request": {
                            "method": "GET",
                            "header": [{"key": "Authorization", "value": "{{api_key}}"}],
                            "url": {
                                "raw": "{{base_url}}/tasks/{{task_id}}/status",
                                "host": ["{{base_url}}"],
                                "path": ["tasks", "{{task_id}}", "status"]
                            }
                        }
                    },
                    {
                        "name": "List Tasks",
                        "request": {
                            "method": "GET",
                            "header": [{"key": "Authorization", "value": "{{api_key}}"}],
                            "url": {
                                "raw": "{{base_url}}/tasks?limit=10&offset=0",
                                "host": ["{{base_url}}"],
                                "path": ["tasks"],
                                "query": [
                                    {"key": "limit", "value": "10"},
                                    {"key": "offset", "value": "0"}
                                ]
                            }
                        }
                    },
                    {
                        "name": "Estimate Cost",
                        "request": {
                            "method": "POST",
                            "header": [{"key": "Authorization", "value": "{{api_key}}"}],
                            "body": {
                                "mode": "raw",
                                "raw": json.dumps({"audio_duration": 3600, "num_speakers": 5}, indent=2),
                                "options": {"raw": {"language": "json"}}
                            },
                            "url": {
                                "raw": "{{base_url}}/tasks/estimate",
                                "host": ["{{base_url}}"],
                                "path": ["tasks", "estimate"]
                            }
                        }
                    }
                ]
            }
        ]
    }
    
    # 保存文件
    output_path = Path("docs/api_references/postman_collection.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(collection, f, indent=2, ensure_ascii=False)
    
    print(f"✅ Generated: {output_path}")
    print(f"📊 Requests: {sum(len(group['item']) for group in collection['item'])}")

if __name__ == "__main__":
    generate_postman_collection()

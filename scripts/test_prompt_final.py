"""
最终提示词测试 - 使用最简单的提示词来验证
"""

import asyncio
import sys
import json
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import httpx
from scripts.auth_helper import get_jwt_token


async def test_prompt_final():
    """最终提示词测试"""
    
    base_url = "http://localhost:8000"
    token = get_jwt_token("user_test_user", "tenant_test_user")
    headers = {"Authorization": f"Bearer {token}"}
    
    print("=" * 80)
    print("最终提示词测试")
    print("=" * 80)
    
    # 1. 上传音频文件
    print("\n【步骤 1】上传音频文件...")
    audio_file = project_root / "test_data" / "meeting.ogg"
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        with open(audio_file, "rb") as f:
            files = {"file": ("meeting.ogg", f, "audio/ogg")}
            response = await client.post(
                f"{base_url}/api/v1/upload",
                headers=headers,
                files=files,
            )
        
        if response.status_code not in [200, 201]:
            print(f"✗ 上传失败: {response.status_code}")
            print(response.text)
            return
        
        upload_data = response.json()
        file_path = upload_data["file_path"]
        audio_duration = upload_data.get("duration", 0)
        print(f"✓ 上传成功: {file_path}")
    
    # 2. 创建任务，使用极简的自定义提示词
    print("\n【步骤 2】创建任务...")
    
    # 极简的自定义提示词 - 只要求输出固定文本
    custom_prompt = """请输出以下JSON：
{"content": "TEST_SUCCESS"}

转写内容：
{transcript}"""
    
    task_data = {
        "meeting_type": "最终提示词测试",
        "audio_files": [file_path],
        "file_order": [0],
        "original_filenames": ["meeting.ogg"],
        "audio_duration": audio_duration,
        "asr_language": "zh-CN+en-US",
        "output_language": "zh-CN",
        "skip_speaker_recognition": True,
        "prompt_instance": {
            "template_id": "__blank__",
            "language": "zh-CN",
            "parameters": {},
            "prompt_text": custom_prompt,
        },
    }
    
    print(f"\n提示词内容:")
    print(custom_prompt)
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            f"{base_url}/api/v1/tasks",
            headers=headers,
            json=task_data,
        )
        
        if response.status_code != 201:
            print(f"✗ 创建任务失败: {response.status_code}")
            print(response.text)
            return
        
        task_response = response.json()
        task_id = task_response["task_id"]
        print(f"\n✓ 任务创建成功: {task_id}")
        print(f"\n请查看 Worker 日志中的:")
        print(f"  '=== ACTUAL PROMPT SENT TO GEMINI API ==='")
        print(f"\n完成后运行: python scripts/check_artifact_prompts.py {task_id}")


if __name__ == "__main__":
    asyncio.run(test_prompt_final())

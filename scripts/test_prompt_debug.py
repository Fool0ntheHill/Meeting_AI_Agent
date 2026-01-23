"""
测试提示词调试 - 创建一个简单的任务来追踪提示词传递
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


async def test_prompt_debug():
    """测试提示词调试"""
    
    base_url = "http://localhost:8000"
    token = get_jwt_token("user_test_user", "tenant_test_user")
    headers = {"Authorization": f"Bearer {token}"}
    
    print("=" * 80)
    print("测试提示词调试")
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
        print(f"  音频时长: {audio_duration:.2f} 秒")
    
    # 2. 创建任务，使用空白模板和简单的自定义提示词
    print("\n【步骤 2】创建任务（空白模板 + 简单提示词）...")
    
    # 简单的自定义提示词
    custom_prompt = """【测试提示词】
请只输出以下内容，不要添加任何其他内容：

这是一个测试。如果你看到这段文字，说明提示词被正确使用了。

转写内容：
{transcript}"""
    
    task_data = {
        "meeting_type": "提示词调试测试",
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
    
    print(f"\n发送的 prompt_instance:")
    print(json.dumps(task_data["prompt_instance"], indent=2, ensure_ascii=False))
    
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
    
    # 3. 等待任务完成
    print("\n【步骤 3】等待任务完成...")
    print("请查看 Worker 日志，查找以下关键信息：")
    print("  - 'Converting dict to PromptInstance'")
    print("  - 'Has prompt_text: True'")
    print("  - 'Using user-edited prompt_text'")
    print("  - '=== PROMPT SENT TO GEMINI ==='")
    print()
    
    max_wait = 180
    wait_time = 0
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        while wait_time < max_wait:
            response = await client.get(
                f"{base_url}/api/v1/tasks/{task_id}/status",
                headers=headers,
            )
            
            if response.status_code != 200:
                print(f"✗ 获取状态失败: {response.status_code}")
                break
            
            status_data = response.json()
            state = status_data["state"]
            progress = status_data["progress"]
            
            print(f"  状态: {state}, 进度: {progress}%")
            
            if state in ["success", "failed", "partial_success"]:
                print(f"\n✓ 任务完成: {state}")
                break
            
            await asyncio.sleep(5)
            wait_time += 5
        
        if wait_time >= max_wait:
            print(f"\n✗ 任务超时")
            return
    
    # 4. 检查生成的 artifact
    print(f"\n【步骤 4】检查生成的 artifact...")
    print(f"运行: python scripts/check_artifact_prompts.py {task_id}")


if __name__ == "__main__":
    asyncio.run(test_prompt_debug())

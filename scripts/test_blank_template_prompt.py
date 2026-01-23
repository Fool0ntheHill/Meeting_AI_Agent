"""
测试空白模板的提示词是否正确使用

创建一个任务，使用空白模板和自定义提示词，验证生成的内容是否符合预期
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


async def test_blank_template_prompt():
    """测试空白模板提示词"""
    
    base_url = "http://localhost:8000"
    token = get_jwt_token("user_test_user", "tenant_test_user")
    headers = {"Authorization": f"Bearer {token}"}
    
    print("=" * 80)
    print("测试空白模板提示词")
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
    
    # 2. 创建任务，使用空白模板和自定义提示词
    print("\n【步骤 2】创建任务（空白模板 + 自定义提示词）...")
    
    # 自定义提示词：要求只输出特定内容
    custom_prompt = """请严格按照以下格式输出，不要添加任何其他内容：

## 测试结果
这是一个测试提示词，用于验证空白模板功能是否正常工作。

## 转写内容
{transcript}

## 结论
如果你看到这段文字，说明空白模板的 prompt_text 字段已经被正确使用。"""
    
    task_data = {
        "meeting_type": "测试空白模板提示词",
        "audio_files": [file_path],
        "file_order": [0],
        "original_filenames": ["meeting.ogg"],
        "audio_duration": audio_duration,
        "asr_language": "zh-CN+en-US",
        "output_language": "zh-CN",
        "skip_speaker_recognition": True,
        "prompt_instance": {  # 单数，不是复数
            "template_id": "__blank__",  # 空白模板
            "language": "zh-CN",
            "parameters": {},
            "prompt_text": custom_prompt,  # 自定义提示词
        },
    }
    
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
        print(f"✓ 任务创建成功: {task_id}")
    
    # 3. 等待任务完成
    print("\n【步骤 3】等待任务完成...")
    max_wait = 180  # 最多等待 3 分钟
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
            print(f"\n✗ 任务超时（等待 {max_wait} 秒）")
            return
    
    # 4. 获取生成的 artifact
    print("\n【步骤 4】获取生成的 artifact...")
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(
            f"{base_url}/api/v1/tasks/{task_id}/artifacts",
            headers=headers,
        )
        
        if response.status_code != 200:
            print(f"✗ 获取 artifacts 失败: {response.status_code}")
            return
        
        artifacts = response.json()
        
        if not artifacts or not isinstance(artifacts, list):
            print(f"✗ 没有找到 artifacts 或格式错误: {artifacts}")
            return
        
        print(f"✓ 找到 {len(artifacts)} 个 artifacts\n")
        
        for artifact in artifacts:
            artifact_id = artifact["artifact_id"]
            artifact_type = artifact["artifact_type"]
            version = artifact["version"]
            
            print(f"--- Artifact {artifact_id} ---")
            print(f"  类型: {artifact_type}")
            print(f"  版本: {version}")
            
            # 获取详细内容
            response = await client.get(
                f"{base_url}/api/v1/artifacts/{artifact_id}",
                headers=headers,
            )
            
            if response.status_code != 200:
                print(f"  ✗ 获取详情失败: {response.status_code}")
                continue
            
            artifact_detail = response.json()
            content = artifact_detail.get("content", {})
            metadata = artifact_detail.get("metadata", {})
            
            # 检查 metadata 中的 prompt 信息
            prompt_info = metadata.get("prompt", {})
            
            print(f"\n  【提示词信息】")
            print(f"    模板 ID: {prompt_info.get('template_id', 'N/A')}")
            print(f"    是否用户编辑: {prompt_info.get('is_user_edited', 'N/A')}")
            
            prompt_text = prompt_info.get('prompt_text', '')
            if prompt_text:
                print(f"    提示词文本（前200字符）:")
                print(f"      {prompt_text[:200]}")
            
            # 检查生成的内容
            print(f"\n  【生成内容】")
            if isinstance(content, dict):
                content_text = content.get("content", "")
            else:
                content_text = str(content)
            
            print(f"    内容长度: {len(content_text)} 字符")
            print(f"    内容预览（前500字符）:")
            print(f"      {content_text[:500]}")
            
            # 验证结果
            print(f"\n  【验证结果】")
            if "测试结果" in content_text and "空白模板的 prompt_text 字段已经被正确使用" in content_text:
                print(f"    ✓ 提示词被正确使用！")
            else:
                print(f"    ✗ 提示词未被正确使用，生成的内容不符合预期")
                print(f"    预期关键词: '测试结果', '空白模板的 prompt_text 字段已经被正确使用'")
            
            print()


if __name__ == "__main__":
    asyncio.run(test_blank_template_prompt())

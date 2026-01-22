#!/usr/bin/env python3
"""
创建任务并实时监控进度

一键创建测试任务并监控其进度变化
"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import requests
from scripts.auth_helper import get_auth_headers


def create_and_monitor():
    """创建任务并监控进度"""
    base_url = "http://localhost:8000"
    headers = get_auth_headers()
    
    print("=" * 80)
    print("创建测试任务并监控进度")
    print("=" * 80)
    
    # 1. 创建任务
    print("\n1. 创建任务...")
    
    create_data = {
        "audio_files": [
            "https://meeting-agent-test.tos-cn-beijing.volces.com/test_audio.ogg"
        ],
        "file_order": [0],
        "original_filenames": ["test_audio.ogg"],
        "meeting_type": "weekly_sync",
        "asr_language": "zh-CN+en-US",
        "output_language": "zh-CN",
        "skip_speaker_recognition": True,
        "prompt_instance": {
            "template_id": "default",
            "language": "zh-CN",
            "parameters": {}
        }
    }
    
    response = requests.post(
        f"{base_url}/api/workspaces/default/tasks",
        headers=headers,
        json=create_data,
    )
    
    if response.status_code != 201:
        print(f"❌ 创建任务失败: {response.status_code}")
        print(response.text)
        return
    
    result = response.json()
    task_id = result["task_id"]
    
    print(f"✅ 任务已创建: {task_id}")
    print(f"\n2. 开始监控进度（每2秒刷新）...")
    print("=" * 80)
    
    # 2. 监控进度
    last_progress = -1
    last_state = None
    start_time = time.time()
    
    while True:
        try:
            response = requests.get(
                f"{base_url}/api/workspaces/default/tasks/{task_id}/status",
                headers=headers,
            )
            
            if response.status_code != 200:
                print(f"❌ 查询失败: {response.status_code}")
                break
            
            data = response.json()
            
            # 检查是否有变化
            if data["progress"] != last_progress or data["state"] != last_state:
                elapsed = time.time() - start_time
                
                # 进度条
                progress_bar_length = 50
                filled = int(progress_bar_length * data["progress"] / 100)
                bar = "█" * filled + "░" * (progress_bar_length - filled)
                
                print(f"\n[{elapsed:6.1f}s] {bar} {data['progress']:5.1f}%")
                print(f"         阶段: {data['state']}", end="")
                
                if data.get("estimated_time"):
                    est_min = data["estimated_time"] // 60
                    est_sec = data["estimated_time"] % 60
                    print(f" | 预估剩余: {est_min}分{est_sec}秒", end="")
                
                print()  # 换行
                
                last_progress = data["progress"]
                last_state = data["state"]
            
            # 检查是否完成
            if data["state"] in ["success", "failed"]:
                print("\n" + "=" * 80)
                if data["state"] == "success":
                    print(f"✅ 任务完成！总耗时: {elapsed:.1f}秒")
                    print(f"\n查看结果:")
                    print(f"  python scripts/check_task_artifact.py {task_id}")
                else:
                    print(f"❌ 任务失败！")
                    if data.get("error_details"):
                        print(f"   错误: {data['error_details']}")
                break
            
            time.sleep(2)
            
        except KeyboardInterrupt:
            print("\n\n⚠️  监控已中断")
            print(f"任务 ID: {task_id}")
            break
        except Exception as e:
            print(f"\n❌ 查询出错: {e}")
            time.sleep(2)


if __name__ == "__main__":
    create_and_monitor()

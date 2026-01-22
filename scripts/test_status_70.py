#!/usr/bin/env python3
"""测试能否看到 status 70（correcting 阶段）"""

import time
import requests
from datetime import datetime
from auth_helper import get_auth_headers

BASE_URL = "http://localhost:8000/api/v1"


def create_and_monitor_task():
    """创建任务并监控状态变化"""
    headers = get_auth_headers()
    
    # 1. 创建任务
    print("=" * 80)
    print("创建测试任务...")
    print("=" * 80)
    
    create_data = {
        "meeting_type": "internal",
        "audio_files": ["uploads/user_test_user/meeting.ogg"],
        "file_order": [0],
        "original_filenames": ["meeting.ogg"],
        "asr_language": "zh-CN+en-US",
        "output_language": "zh-CN",
        "skip_speaker_recognition": False,  # 启用声纹识别，才会有 correcting 阶段
        "prompt_instance": {
            "template_id": "template_meeting_minutes_v1",
            "parameters": {}
        }
    }
    
    response = requests.post(
        f"{BASE_URL}/tasks",
        headers=headers,
        json=create_data,
        timeout=30,
    )
    
    if response.status_code != 201:
        print(f"❌ 创建任务失败: {response.status_code}")
        print(response.text)
        return
    
    task_id = response.json()["task_id"]
    print(f"✅ 任务已创建: {task_id}\n")
    
    # 2. 监控任务状态
    print("=" * 80)
    print("监控任务状态变化...")
    print("=" * 80)
    print()
    
    last_state = None
    last_progress = None
    status_history = []
    
    while True:
        try:
            response = requests.get(
                f"{BASE_URL}/tasks/{task_id}/status",
                headers=headers,
                timeout=10,
            )
            
            if response.status_code == 200:
                data = response.json()
                state = data.get("state")
                progress = data.get("progress", 0)
                estimated_time = data.get("estimated_time")
                
                # 记录所有状态变化
                if state != last_state or progress != last_progress:
                    timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
                    status_line = f"[{timestamp}] state={state}, progress={progress}%"
                    
                    if estimated_time:
                        status_line += f", estimated_time={estimated_time}s"
                    
                    print(status_line)
                    status_history.append({
                        "timestamp": timestamp,
                        "state": state,
                        "progress": progress,
                        "estimated_time": estimated_time,
                    })
                    
                    last_state = state
                    last_progress = progress
                
                # 任务完成
                if state in ["success", "failed", "partial_success"]:
                    print(f"\n✅ 任务完成: {state}")
                    break
            
            else:
                print(f"❌ 查询失败: {response.status_code}")
                print(response.text)
                break
        
        except KeyboardInterrupt:
            print("\n\n⚠️  监控已停止")
            break
        
        except Exception as e:
            print(f"❌ 错误: {e}")
            break
        
        time.sleep(0.5)  # 更频繁的轮询，捕捉所有状态变化
    
    # 3. 分析状态历史
    print("\n" + "=" * 80)
    print("状态变化历史:")
    print("=" * 80)
    
    for i, status in enumerate(status_history, 1):
        print(f"{i}. [{status['timestamp']}] {status['state']} - {status['progress']}%")
    
    # 检查是否有 correcting 阶段和 70% 进度
    has_correcting = any(s["state"] == "correcting" for s in status_history)
    has_70_progress = any(s["progress"] == 70.0 for s in status_history)
    
    print("\n" + "=" * 80)
    print("分析结果:")
    print("=" * 80)
    print(f"是否有 correcting 状态: {'✅ 是' if has_correcting else '❌ 否'}")
    print(f"是否有 70% 进度: {'✅ 是' if has_70_progress else '❌ 否'}")
    
    if has_correcting and has_70_progress:
        print("\n✅ 前端应该能够读到 status 70!")
    else:
        print("\n⚠️  前端可能读不到 status 70")
        if not has_correcting:
            print("   原因: 没有 correcting 状态（可能跳过了声纹识别）")
        if not has_70_progress:
            print("   原因: 没有 70% 进度记录")


if __name__ == "__main__":
    create_and_monitor_task()

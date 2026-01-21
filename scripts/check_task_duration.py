"""检查任务列表接口返回的时长字段"""

import requests
import json
from auth_helper import get_jwt_token

# 配置
BASE_URL = "http://localhost:8000/api/v1"

def check_task_duration():
    """检查任务列表中的时长字段"""
    
    # 获取 token
    token = get_jwt_token()
    headers = {"Authorization": f"Bearer {token}"}
    
    # 获取任务列表
    print("=" * 60)
    print("获取任务列表...")
    print("=" * 60)
    
    response = requests.get(
        f"{BASE_URL}/tasks",
        headers=headers,
        params={"limit": 5}
    )
    
    if response.status_code != 200:
        print(f"❌ 请求失败: {response.status_code}")
        print(response.text)
        return
    
    tasks = response.json()
    print(f"✅ 获取到 {len(tasks)} 个任务\n")
    
    # 检查每个任务的时长字段
    for i, task in enumerate(tasks, 1):
        print(f"任务 {i}: {task.get('task_id')}")
        print(f"  名称: {task.get('name', '未命名')}")
        print(f"  状态: {task.get('state')}")
        print(f"  创建时间: {task.get('created_at')}")
        
        # 检查时长相关字段
        duration = task.get('duration')
        audio_duration = task.get('audio_duration')
        
        print(f"  duration 字段: {duration} {'(存在)' if duration is not None else '(不存在)'}")
        print(f"  audio_duration 字段: {audio_duration} {'(存在)' if audio_duration is not None else '(不存在)'}")
        
        if duration is not None:
            print(f"    → duration 值: {duration} 秒 = {duration/60:.2f} 分钟")
        
        if audio_duration is not None:
            print(f"    → audio_duration 值: {audio_duration} 秒 = {audio_duration/60:.2f} 分钟")
        
        print()
    
    # 总结
    print("=" * 60)
    print("字段总结:")
    print("=" * 60)
    print("后端返回的字段名: duration")
    print("字段单位: 秒 (float)")
    print("字段说明: 从转写记录中获取的音频总时长")
    print("\n前端处理建议:")
    print("1. 使用 'duration' 字段（不是 'audio_duration'）")
    print("2. 单位是秒，不需要除以 1000")
    print("3. 如果 duration 为 null，说明任务还未完成转写")

if __name__ == "__main__":
    check_task_duration()

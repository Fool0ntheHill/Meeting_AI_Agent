#!/usr/bin/env python3
"""
测试任务进度跟踪

监控任务的实时进度和预估时间
"""

import sys
import time
import asyncio
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import requests
from scripts.auth_helper import get_auth_headers


def test_progress_tracking(task_id: str):
    """
    测试进度跟踪
    
    Args:
        task_id: 任务 ID
    """
    base_url = "http://localhost:8000"
    headers = get_auth_headers()
    
    print(f"开始监控任务: {task_id}")
    print("=" * 80)
    
    last_progress = -1
    last_state = None
    start_time = time.time()
    
    while True:
        try:
            # 查询任务状态
            response = requests.get(
                f"{base_url}/api/workspaces/default/tasks/{task_id}/status",
                headers=headers,
            )
            
            if response.status_code == 404:
                print(f"❌ 任务不存在: {task_id}")
                break
            
            if response.status_code != 200:
                print(f"❌ 查询失败: {response.status_code} - {response.text}")
                break
            
            data = response.json()
            
            # 检查是否有变化
            if data["progress"] != last_progress or data["state"] != last_state:
                elapsed = time.time() - start_time
                
                print(f"\n[{elapsed:6.1f}s] 状态更新:")
                print(f"  阶段: {data['state']}")
                print(f"  进度: {data['progress']:.1f}%")
                
                if data.get("estimated_time"):
                    est_min = data["estimated_time"] // 60
                    est_sec = data["estimated_time"] % 60
                    print(f"  预估剩余: {est_min}分{est_sec}秒")
                else:
                    print(f"  预估剩余: 计算中...")
                
                if data.get("error_details"):
                    print(f"  错误: {data['error_details']}")
                
                last_progress = data["progress"]
                last_state = data["state"]
            
            # 检查是否完成
            if data["state"] in ["success", "failed"]:
                print("\n" + "=" * 80)
                if data["state"] == "success":
                    print(f"✅ 任务完成！总耗时: {elapsed:.1f}秒")
                else:
                    print(f"❌ 任务失败！")
                    if data.get("error_details"):
                        print(f"   错误: {data['error_details']}")
                break
            
            # 等待 2 秒后再次查询
            time.sleep(2)
            
        except KeyboardInterrupt:
            print("\n\n⚠️  监控已中断")
            break
        except Exception as e:
            print(f"\n❌ 查询出错: {e}")
            time.sleep(2)
    
    print("\n监控结束")


def get_latest_task():
    """获取最新的任务 ID"""
    base_url = "http://localhost:8000"
    headers = get_auth_headers()
    
    response = requests.get(
        f"{base_url}/api/workspaces/default/tasks",
        headers=headers,
        params={"limit": 1},
    )
    
    if response.status_code == 200:
        data = response.json()
        if data["tasks"]:
            return data["tasks"][0]["task_id"]
    
    return None


if __name__ == "__main__":
    if len(sys.argv) > 1:
        task_id = sys.argv[1]
    else:
        # 获取最新任务
        task_id = get_latest_task()
        if not task_id:
            print("❌ 没有找到任务，请提供任务 ID")
            print("用法: python scripts/test_progress_tracking.py <task_id>")
            sys.exit(1)
        print(f"使用最新任务: {task_id}\n")
    
    test_progress_tracking(task_id)

#!/usr/bin/env python3
"""监控已存在任务的进度"""

import sys
import time
import requests
from datetime import datetime

# 从 auth_helper 导入认证函数
from auth_helper import get_auth_headers

BASE_URL = "http://localhost:8000/api/v1"


def monitor_task(task_id: str, interval: int = 2):
    """
    监控任务进度
    
    Args:
        task_id: 任务 ID
        interval: 轮询间隔(秒)
    """
    print(f"\n{'='*80}")
    print(f"监控任务: {task_id}")
    print(f"{'='*80}\n")
    
    try:
        headers = get_auth_headers()
    except Exception as e:
        print(f"❌ 认证失败: {e}")
        print("提示: 请确保后端服务正在运行")
        return
    
    last_state = None
    last_progress = None
    status_history = []
    
    while True:
        try:
            # 查询任务状态
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
                error_details = data.get("error_details")
                
                # 每次都打印，即使没有变化（用于调试）
                timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
                
                # 只在状态或进度变化时打印详细信息
                if state != last_state or progress != last_progress:
                    print(f"[{timestamp}] 状态: {state} | 进度: {progress}%", end="")
                    
                    if estimated_time:
                        print(f" | 预估剩余: {estimated_time}秒", end="")
                    
                    if error_details:
                        print(f" | 错误: {error_details}", end="")
                    
                    print()
                    
                    # 记录历史
                    status_history.append({
                        "timestamp": timestamp,
                        "state": state,
                        "progress": progress,
                    })
                    
                    last_state = state
                    last_progress = progress
                else:
                    # 没有变化时也打印一个点，表示正在轮询
                    print(".", end="", flush=True)
                
                # 任务完成
                if state in ["success", "failed", "partial_success"]:
                    print(f"\n✅ 任务完成: {state}")
                    
                    # 显示历史记录
                    print(f"\n{'='*80}")
                    print("状态变化历史:")
                    print(f"{'='*80}")
                    for i, s in enumerate(status_history, 1):
                        print(f"{i}. [{s['timestamp']}] {s['state']} - {s['progress']}%")
                    
                    # 检查是否有 70% 进度
                    has_70 = any(s["progress"] == 70.0 for s in status_history)
                    has_correcting = any(s["state"] == "correcting" for s in status_history)
                    print(f"\n是否捕捉到 70% 进度: {'✅ 是' if has_70 else '❌ 否'}")
                    print(f"是否有 correcting 状态: {'✅ 是' if has_correcting else '❌ 否'}")
                    break
            
            elif response.status_code == 404:
                print(f"❌ 任务不存在: {task_id}")
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
        
        time.sleep(0.1)  # 更快的轮询频率，捕捉所有状态变化


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python scripts/monitor_existing_task.py <task_id>")
        sys.exit(1)
    
    task_id = sys.argv[1]
    monitor_task(task_id)

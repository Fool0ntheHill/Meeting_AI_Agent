"""模拟前端轮询，创建新任务并实时监控进度"""
import sys
import os
import time
import requests
import json
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.auth_helper import get_jwt_token

def simulate_polling(task_id: str, interval: float = 2.0, max_duration: int = 300):
    """
    模拟前端轮询
    
    Args:
        task_id: 任务 ID
        interval: 轮询间隔（秒）
        max_duration: 最大监控时长（秒）
    """
    print("=" * 80)
    print(f"模拟前端轮询 - 任务 {task_id}")
    print(f"轮询间隔: {interval}秒")
    print("=" * 80)
    
    # 获取 token
    token = get_jwt_token("test_user")
    headers = {"Authorization": f"Bearer {token}"}
    
    base_url = "http://localhost:8000"
    status_url = f"{base_url}/api/v1/tasks/{task_id}/status"
    
    start_time = time.time()
    last_state = None
    last_progress = None
    state_history = []
    
    poll_count = 0
    
    while True:
        poll_count += 1
        elapsed = time.time() - start_time
        
        if elapsed > max_duration:
            print(f"\n⏱️  达到最大监控时长 {max_duration}秒，停止轮询")
            break
        
        try:
            # 发起请求
            response = requests.get(status_url, headers=headers, timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                state = data.get("state")
                progress = data.get("progress", 0)
                estimated_time = data.get("estimated_time")
                updated_at = data.get("updated_at")
                
                # 检测状态变化
                state_changed = (state != last_state or progress != last_progress)
                
                if state_changed:
                    timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
                    print(f"\n[{timestamp}] 第 {poll_count} 次轮询 (耗时 {elapsed:.1f}s)")
                    print(f"  state: {state}")
                    print(f"  progress: {progress}%")
                    print(f"  estimated_time: {estimated_time}s")
                    print(f"  updated_at: {updated_at}")
                    
                    # 记录历史
                    state_history.append({
                        "poll_count": poll_count,
                        "elapsed": round(elapsed, 2),
                        "state": state,
                        "progress": progress,
                        "estimated_time": estimated_time,
                    })
                    
                    last_state = state
                    last_progress = progress
                
                # 任务完成
                if state in ["success", "failed", "partial_success"]:
                    print(f"\n✓ 任务完成: {state}")
                    break
                    
            elif response.status_code == 404:
                print(f"\n✗ 任务不存在: {task_id}")
                break
            else:
                print(f"\n✗ API 错误: {response.status_code}")
                print(response.text)
                
        except requests.exceptions.RequestException as e:
            print(f"\n✗ 请求失败: {e}")
        
        # 等待下一次轮询
        time.sleep(interval)
    
    # 打印汇总
    print("\n" + "=" * 80)
    print("轮询汇总")
    print("=" * 80)
    print(f"总轮询次数: {poll_count}")
    print(f"捕获到的状态变化: {len(state_history)} 次")
    print(f"总耗时: {elapsed:.1f}秒")
    
    if state_history:
        print("\n状态变化历史:")
        for i, record in enumerate(state_history, 1):
            print(f"  {i}. [{record['elapsed']}s] {record['state']} {record['progress']}% (第 {record['poll_count']} 次轮询)")
        
        # 分析是否错过了状态
        print("\n分析:")
        captured_states = set(r['state'] for r in state_history)
        expected_states = {"running", "transcribing", "identifying", "correcting", "summarizing", "success"}
        missed_states = expected_states - captured_states
        
        if missed_states:
            print(f"  ⚠️  可能错过的状态: {', '.join(missed_states)}")
            print(f"  原因: 这些状态持续时间 < {interval}秒，前端轮询间隔太长")
        else:
            print(f"  ✓ 捕获了所有预期状态")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/simulate_frontend_polling.py <task_id> [interval]")
        print("\nExample:")
        print("  python scripts/simulate_frontend_polling.py task_abc123 2.0")
        sys.exit(1)
    
    task_id = sys.argv[1]
    interval = float(sys.argv[2]) if len(sys.argv) > 2 else 2.0
    
    simulate_polling(task_id, interval)

"""对比 SSE 和轮询的效果"""
import sys
import os
import time
import threading
import requests
import json
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.auth_helper import get_jwt_token

def test_polling(task_id: str, interval: float = 2.0):
    """轮询方式"""
    print("\n" + "=" * 80)
    print("方式 1: 轮询 (每 2 秒)")
    print("=" * 80)
    
    token = get_jwt_token("test_user")
    headers = {"Authorization": f"Bearer {token}"}
    url = f"http://localhost:8000/api/v1/tasks/{task_id}/status"
    
    states_captured = []
    start_time = time.time()
    
    while True:
        try:
            response = requests.get(url, headers=headers, timeout=5)
            if response.status_code == 200:
                data = response.json()
                state = data.get("state")
                progress = data.get("progress", 0)
                
                timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
                elapsed = time.time() - start_time
                
                print(f"[{timestamp}] {state} {progress}% (耗时 {elapsed:.1f}s)")
                states_captured.append((elapsed, state, progress))
                
                if state in ["success", "failed", "partial_success"]:
                    break
            
            time.sleep(interval)
        except Exception as e:
            print(f"Error: {e}")
            break
    
    print(f"\n✓ 轮询完成，捕获 {len(states_captured)} 次状态变化")
    return states_captured


def test_sse(task_id: str):
    """SSE 方式"""
    print("\n" + "=" * 80)
    print("方式 2: SSE (实时推送)")
    print("=" * 80)
    
    token = get_jwt_token("test_user")
    headers = {"Authorization": f"Bearer {token}"}
    url = f"http://localhost:8000/api/v1/sse/tasks/{task_id}/progress"
    
    states_captured = []
    start_time = time.time()
    
    try:
        response = requests.get(url, headers=headers, stream=True, timeout=300)
        
        if response.status_code != 200:
            print(f"✗ 连接失败: {response.status_code}")
            return states_captured
        
        event_type = None
        for line in response.iter_lines(decode_unicode=True):
            if not line:
                continue
            
            if line.startswith("event:"):
                event_type = line.split(":", 1)[1].strip()
            elif line.startswith("data:"):
                data_str = line.split(":", 1)[1].strip()
                try:
                    data = json.loads(data_str)
                    
                    if event_type == "progress":
                        state = data.get('state')
                        progress = data.get('progress', 0)
                        
                        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
                        elapsed = time.time() - start_time
                        
                        print(f"[{timestamp}] {state} {progress}% (耗时 {elapsed:.1f}s)")
                        states_captured.append((elapsed, state, progress))
                    
                    elif event_type == "complete":
                        print(f"\n✓ 任务完成")
                        break
                    
                except json.JSONDecodeError:
                    pass
                
                event_type = None
    
    except Exception as e:
        print(f"Error: {e}")
    
    print(f"\n✓ SSE 完成，捕获 {len(states_captured)} 次状态变化")
    return states_captured


def compare_results(polling_states, sse_states):
    """对比结果"""
    print("\n" + "=" * 80)
    print("对比结果")
    print("=" * 80)
    
    print(f"\n轮询捕获: {len(polling_states)} 次状态变化")
    print(f"SSE 捕获: {len(sse_states)} 次状态变化")
    
    # 提取唯一状态
    polling_unique = set(s[1] for s in polling_states)
    sse_unique = set(s[1] for s in sse_states)
    
    print(f"\n轮询捕获的状态: {', '.join(sorted(polling_unique))}")
    print(f"SSE 捕获的状态: {', '.join(sorted(sse_unique))}")
    
    missed_by_polling = sse_unique - polling_unique
    if missed_by_polling:
        print(f"\n⚠️  轮询错过的状态: {', '.join(missed_by_polling)}")
    else:
        print(f"\n✓ 轮询没有错过任何状态")
    
    # 计算平均延迟
    if sse_states:
        avg_sse_delay = sum(s[0] for s in sse_states) / len(sse_states)
        print(f"\nSSE 平均延迟: {avg_sse_delay:.2f}秒")
    
    if polling_states:
        avg_polling_delay = sum(s[0] for s in polling_states) / len(polling_states)
        print(f"轮询平均延迟: {avg_polling_delay:.2f}秒")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/demo_sse_vs_polling.py <task_id>")
        print("\n说明:")
        print("  需要两个相同的任务来对比效果")
        print("  建议先创建一个任务，然后分别用轮询和 SSE 监控")
        sys.exit(1)
    
    task_id = sys.argv[1]
    
    print("=" * 80)
    print("SSE vs 轮询 对比测试")
    print("=" * 80)
    print(f"\n任务 ID: {task_id}")
    print("\n注意: 这个脚本会先用轮询测试，然后用 SSE 测试")
    print("      如果任务已完成，请创建新任务测试")
    
    # 先测试轮询
    polling_states = test_polling(task_id)
    
    # 等待一下
    time.sleep(2)
    
    # 再测试 SSE（需要新任务）
    print("\n提示: 如果要测试 SSE，请创建新任务并运行:")
    print(f"  python scripts/test_sse.py <new_task_id>")

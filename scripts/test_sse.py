"""测试 SSE 实时进度推送"""
import sys
import os
import requests
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.auth_helper import get_jwt_token

def test_sse_stream(task_id: str):
    """
    测试 SSE 流
    
    Args:
        task_id: 任务 ID
    """
    print("=" * 80)
    print(f"测试 SSE 实时进度推送 - 任务 {task_id}")
    print("=" * 80)
    
    # 获取 token - 使用 test_user_001 匹配任务的 user_id
    token = get_jwt_token("test_user_001")
    print(f"\n使用 Token: {token[:50]}...")
    
    headers = {"Authorization": f"Bearer {token}"}
    
    url = f"http://localhost:8000/api/v1/sse/tasks/{task_id}/progress"
    
    print(f"\n连接到: {url}")
    print("等待进度更新...\n")
    
    # 先测试普通 API 是否工作
    print("测试认证...")
    test_url = f"http://localhost:8000/api/v1/tasks/{task_id}/status"
    try:
        test_response = requests.get(test_url, headers=headers, timeout=5)
        if test_response.status_code == 200:
            print(f"✓ 认证成功 (status API)")
        else:
            print(f"✗ 认证失败: {test_response.status_code}")
            print(f"   响应: {test_response.text}")
            return
    except Exception as e:
        print(f"✗ 测试请求失败: {e}")
        return
    
    print("\n开始 SSE 连接...")
    
    try:
        # 使用 stream=True 接收 SSE
        # 注意：需要在 URL 中传递 token 或使用 Session
        session = requests.Session()
        session.headers.update(headers)
        response = session.get(url, stream=True, timeout=300)
        
        if response.status_code != 200:
            print(f"✗ 连接失败: {response.status_code}")
            print(response.text)
            return
        
        print("✓ SSE 连接成功\n")
        
        # 逐行读取 SSE 消息
        event_type = None
        for line in response.iter_lines(decode_unicode=True):
            if not line:
                continue
            
            # 解析 SSE 格式
            if line.startswith("event:"):
                event_type = line.split(":", 1)[1].strip()
            elif line.startswith("data:"):
                data_str = line.split(":", 1)[1].strip()
                try:
                    data = json.loads(data_str)
                    
                    if event_type == "progress":
                        print(f"📊 进度更新:")
                        print(f"   state: {data.get('state')}")
                        print(f"   progress: {data.get('progress')}%")
                        print(f"   estimated_time: {data.get('estimated_time')}s")
                        print(f"   updated_at: {data.get('updated_at')}")
                        print()
                    elif event_type == "complete":
                        print(f"✓ 任务完成: {data.get('state')}")
                        break
                    elif event_type == "error":
                        print(f"✗ 错误: {data.get('error')}")
                        break
                    elif event_type == "timeout":
                        print(f"⏱️  超时: {data.get('message')}")
                        break
                    
                except json.JSONDecodeError as e:
                    print(f"✗ JSON 解析失败: {e}")
                    print(f"   原始数据: {data_str}")
                
                event_type = None  # 重置事件类型
    
    except requests.exceptions.Timeout:
        print("✗ 连接超时")
    except requests.exceptions.RequestException as e:
        print(f"✗ 请求失败: {e}")
    except KeyboardInterrupt:
        print("\n\n⚠️  用户中断")
    
    print("\n" + "=" * 80)
    print("SSE 测试结束")
    print("=" * 80)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/test_sse.py <task_id>")
        print("\nExample:")
        print("  python scripts/test_sse.py task_abc123")
        sys.exit(1)
    
    task_id = sys.argv[1]
    test_sse_stream(task_id)

# -*- coding: utf-8 -*-
"""Test script for API endpoints."""

import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from fastapi.testclient import TestClient

from src.api.app import create_app
from src.database.session import init_db
from auth_helper import get_jwt_token

# 初始化数据库
print("Initializing database...")
init_db()
print("Database initialized\n")

# 创建测试客户端
app = create_app()
client = TestClient(app)

# 获取测试 token
USERNAME = "test_user"


def get_test_headers():
    """获取测试用的认证 headers"""
    token = get_jwt_token(USERNAME)
    return {"Authorization": f"Bearer {token}"}


def test_health_check():
    """测试健康检查端点"""
    print("=" * 60)
    print("Testing Health Check Endpoint")
    print("=" * 60)
    
    response = client.get("/api/v1/health")
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.json()}")
    print()
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "database" in data["dependencies"]
    
    print("✅ Health check test passed\n")


def test_root_endpoint():
    """测试根端点"""
    print("=" * 60)
    print("Testing Root Endpoint")
    print("=" * 60)
    
    response = client.get("/api/v1/")
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.json()}")
    print()
    
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    
    print("✅ Root endpoint test passed\n")


def test_create_task():
    """测试创建任务"""
    print("=" * 60)
    print("Testing Create Task Endpoint")
    print("=" * 60)
    
    # 准备请求数据
    request_data = {
        "audio_files": ["https://example.com/meeting.wav"],
        "file_order": [0],
        "meeting_type": "weekly_sync",
        "asr_language": "zh-CN+en-US",
        "output_language": "zh-CN",
        "skip_speaker_recognition": False,
    }
    
    # 发送请求 (使用 JWT 认证)
    response = client.post(
        "/api/v1/tasks",
        json=request_data,
        headers=get_test_headers(),
    )
    
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.json()}")
    print()
    
    assert response.status_code == 201
    data = response.json()
    assert data["success"] is True
    assert "task_id" in data
    
    task_id = data["task_id"]
    print(f"✅ Task created successfully: {task_id}\n")
    
    return task_id


def test_get_task_status(task_id: str):
    """测试查询任务状态"""
    print("=" * 60)
    print("Testing Get Task Status Endpoint")
    print("=" * 60)
    
    response = client.get(
        f"/api/v1/tasks/{task_id}/status",
        headers=get_test_headers(),
    )
    
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.json()}")
    print()
    
    assert response.status_code == 200
    data = response.json()
    assert data["task_id"] == task_id
    assert "state" in data
    assert "progress" in data
    
    print("✅ Task status retrieved successfully\n")


def test_get_task_detail(task_id: str):
    """测试获取任务详情"""
    print("=" * 60)
    print("Testing Get Task Detail Endpoint")
    print("=" * 60)
    
    response = client.get(
        f"/api/v1/tasks/{task_id}",
        headers=get_test_headers(),
    )
    
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.json()}")
    print()
    
    assert response.status_code == 200
    data = response.json()
    assert data["task_id"] == task_id
    assert "audio_files" in data
    assert "meeting_type" in data
    
    print("✅ Task detail retrieved successfully\n")


def test_list_tasks():
    """测试列出任务"""
    print("=" * 60)
    print("Testing List Tasks Endpoint")
    print("=" * 60)
    
    response = client.get(
        "/api/v1/tasks",
        headers=get_test_headers(),
    )
    
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.json()}")
    print()
    
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    
    print(f"✅ Found {len(data)} tasks\n")


def test_estimate_cost():
    """测试成本预估"""
    print("=" * 60)
    print("Testing Estimate Cost Endpoint")
    print("=" * 60)
    
    request_data = {
        "audio_duration": 600.0,  # 10 分钟
        "meeting_type": "weekly_sync",
        "enable_speaker_recognition": True,
    }
    
    response = client.post(
        "/api/v1/tasks/estimate",
        json=request_data,
        headers=get_test_headers(),
    )
    
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.json()}")
    print()
    
    assert response.status_code == 200
    data = response.json()
    assert "total_cost" in data
    assert "cost_breakdown" in data
    
    print("✅ Cost estimation successful\n")


def test_authentication():
    """测试认证"""
    print("=" * 60)
    print("Testing Authentication")
    print("=" * 60)
    
    # 测试缺少 Authorization 头
    response = client.get("/api/v1/tasks")
    print(f"Without auth - Status Code: {response.status_code}")
    assert response.status_code == 401
    
    # 测试无效的 Authorization 格式
    response = client.get(
        "/api/v1/tasks",
        headers={"Authorization": "InvalidFormat"},
    )
    print(f"Invalid format - Status Code: {response.status_code}")
    assert response.status_code == 401
    
    print("✅ Authentication tests passed\n")


def main():
    """运行所有测试"""
    print("\n" + "=" * 60)
    print("Meeting Minutes Agent API Tests")
    print("=" * 60 + "\n")
    
    try:
        # 基础端点测试
        test_health_check()
        test_root_endpoint()
        
        # 认证测试
        test_authentication()
        
        # 任务管理测试
        task_id = test_create_task()
        test_get_task_status(task_id)
        test_get_task_detail(task_id)
        test_list_tasks()
        
        # 成本预估测试
        test_estimate_cost()
        
        print("=" * 60)
        print("✅ All tests passed!")
        print("=" * 60)
        
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

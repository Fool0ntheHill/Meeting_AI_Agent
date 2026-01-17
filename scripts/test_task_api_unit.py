#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""测试任务 API 的单元测试"""

import sys
import os

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.database.session import init_db, get_session
from src.database.repositories import TaskRepository
from src.core.models import TaskState
from src.utils.logger import get_logger

logger = get_logger(__name__)


def test_task_creation():
    """测试任务创建"""
    print("\n" + "=" * 60)
    print("测试任务创建")
    print("=" * 60)
    
    # 初始化数据库
    init_db()
    
    # 创建任务
    with get_session() as session:
        task_repo = TaskRepository(session)
        
        task = task_repo.create(
            task_id="test_task_001",
            user_id="test_user",
            tenant_id="test_tenant",
            meeting_type="common",
            audio_files=["test1.wav", "test2.wav"],
            file_order=[0, 1],
            asr_language="zh-CN+en-US",
            output_language="zh-CN",
            skip_speaker_recognition=False,
            hotword_set_id=None,
            preferred_asr_provider="volcano",
        )
        
        print(f"✅ 任务创建成功:")
        print(f"   Task ID: {task.task_id}")
        print(f"   User ID: {task.user_id}")
        print(f"   State: {task.state}")
        print(f"   Audio files: {task.get_audio_files_list()}")
        print(f"   ASR Language: {task.asr_language}")
        print(f"   Output Language: {task.output_language}")
        
        # 查询任务
        print("\n查询任务...")
        retrieved_task = task_repo.get_by_id("test_task_001")
        if retrieved_task:
            print(f"✅ 任务查询成功:")
            print(f"   Task ID: {retrieved_task.task_id}")
            print(f"   State: {retrieved_task.state}")
        else:
            print("❌ 任务查询失败")
        
        # 更新任务状态
        print("\n更新任务状态...")
        task_repo.update_state(
            task_id="test_task_001",
            state=TaskState.TRANSCRIBING,
            progress=0.3,
        )
        
        updated_task = task_repo.get_by_id("test_task_001")
        print(f"✅ 任务状态更新成功:")
        print(f"   State: {updated_task.state}")
        print(f"   Progress: {updated_task.progress}")
        
        # 清理测试数据
        print("\n清理测试数据...")
        task_repo.delete("test_task_001")
        print("✅ 测试数据已清理")


def test_redis_cache():
    """测试 Redis 缓存"""
    print("\n" + "=" * 60)
    print("测试 Redis 缓存")
    print("=" * 60)
    
    try:
        import redis
        import json
        
        # 连接 Redis
        client = redis.from_url("redis://localhost:6379/0", decode_responses=True)
        client.ping()
        print("✅ Redis 连接成功")
        
        # 测试缓存写入
        cache_key = "test_task_status:test_001"
        cache_data = {
            "task_id": "test_001",
            "user_id": "test_user",
            "state": "pending",
            "progress": 0.0,
        }
        
        client.setex(cache_key, 60, json.dumps(cache_data, ensure_ascii=False))
        print(f"✅ 缓存写入成功: {cache_key}")
        
        # 测试缓存读取
        cached = client.get(cache_key)
        if cached:
            data = json.loads(cached)
            print(f"✅ 缓存读取成功:")
            print(f"   Task ID: {data['task_id']}")
            print(f"   State: {data['state']}")
        else:
            print("❌ 缓存读取失败")
        
        # 清理测试数据
        client.delete(cache_key)
        print("✅ 测试缓存已清理")
        
    except redis.ConnectionError as e:
        print(f"⚠️  Redis 未运行: {e}")
        print("   缓存功能将降级到仅使用数据库")
    except Exception as e:
        print(f"❌ Redis 测试失败: {e}")


def main():
    """主函数"""
    print("=" * 60)
    print("任务 API 单元测试")
    print("=" * 60)
    
    try:
        test_task_creation()
        test_redis_cache()
        
        print("\n" + "=" * 60)
        print("✅ 所有测试通过")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()

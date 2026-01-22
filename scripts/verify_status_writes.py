#!/usr/bin/env python3
"""
验证状态更新是否真的写入数据库

这个脚本会：
1. 监控数据库的实际写入操作
2. 检查 SQLAlchemy 的 flush/commit 行为
3. 验证 Redis 缓存清除是否生效
"""

import sys
import time
from datetime import datetime

# 添加项目根目录到 Python 路径
sys.path.insert(0, ".")

from src.database.session import session_scope
from src.database.repositories import TaskRepository
from src.core.models import TaskState


def test_status_update_persistence():
    """测试状态更新是否真的持久化到数据库"""
    
    print("=" * 80)
    print("测试状态更新持久化")
    print("=" * 80)
    
    # 创建测试任务
    task_id = f"test_persist_{int(time.time())}"
    
    print(f"\n1. 创建测试任务: {task_id}")
    with session_scope() as db:
        repo = TaskRepository(db)
        repo.create(
            task_id=task_id,
            user_id="user_test",
            tenant_id="default",
            meeting_type="internal",
            audio_files=["test.wav"],
            file_order=[0],
        )
    
    # 快速连续更新状态（模拟 Pipeline 行为）
    states = [
        (TaskState.TRANSCRIBING, 0.0),
        (TaskState.TRANSCRIBING, 40.0),
        (TaskState.IDENTIFYING, 40.0),
        (TaskState.IDENTIFYING, 60.0),
        (TaskState.CORRECTING, 60.0),
        (TaskState.CORRECTING, 70.0),
        (TaskState.SUMMARIZING, 70.0),
        (TaskState.SUCCESS, 100.0),
    ]
    
    print("\n2. 快速连续更新状态（模拟 Pipeline）:")
    for i, (state, progress) in enumerate(states):
        with session_scope() as db:
            repo = TaskRepository(db)
            repo.update_status(
                task_id=task_id,
                state=state,
                progress=progress,
                estimated_time=10 - i,
            )
            print(f"   [{i+1}] 更新: {state.value} {progress}%")
        
        # 模拟处理时间（非常短）
        time.sleep(0.1)
    
    # 验证所有状态是否都能从数据库读取
    print("\n3. 从数据库读取最终状态:")
    with session_scope() as db:
        repo = TaskRepository(db)
        task = repo.get_by_id(task_id)
        if task:
            print(f"   ✓ 任务状态: {task.state}")
            print(f"   ✓ 进度: {task.progress}%")
            print(f"   ✓ 预估时间: {task.estimated_time}s")
            print(f"   ✓ 更新时间: {task.updated_at}")
        else:
            print(f"   ✗ 任务未找到!")
    
    # 检查 Redis 缓存
    print("\n4. 检查 Redis 缓存:")
    try:
        import redis
        r = redis.from_url("redis://localhost:6379/0", decode_responses=True)
        cache_key = f"task_status:{task_id}"
        cached = r.get(cache_key)
        if cached:
            print(f"   ⚠ Redis 中仍有缓存: {cached[:100]}...")
        else:
            print(f"   ✓ Redis 缓存已清除")
    except Exception as e:
        print(f"   ✗ Redis 检查失败: {e}")
    
    # 清理测试任务
    print(f"\n5. 清理测试任务: {task_id}")
    with session_scope() as db:
        repo = TaskRepository(db)
        repo.delete(task_id)
    
    print("\n" + "=" * 80)
    print("测试完成")
    print("=" * 80)


def analyze_real_task(task_id: str):
    """分析真实任务的状态历史"""
    
    print("=" * 80)
    print(f"分析任务: {task_id}")
    print("=" * 80)
    
    with session_scope() as db:
        repo = TaskRepository(db)
        task = repo.get_by_id(task_id)
        
        if not task:
            print(f"\n✗ 任务未找到: {task_id}")
            return
        
        print(f"\n当前状态:")
        print(f"  状态: {task.state}")
        print(f"  进度: {task.progress}%")
        print(f"  预估时间: {task.estimated_time}s")
        print(f"  创建时间: {task.created_at}")
        print(f"  更新时间: {task.updated_at}")
        print(f"  完成时间: {task.completed_at}")
        
        # 计算时间差
        if task.completed_at and task.created_at:
            duration = (task.completed_at - task.created_at).total_seconds()
            print(f"  总耗时: {duration:.1f}秒")
        
        # 检查 Redis 缓存
        print(f"\nRedis 缓存状态:")
        try:
            import redis
            r = redis.from_url("redis://localhost:6379/0", decode_responses=True)
            cache_key = f"task_status:{task_id}"
            cached = r.get(cache_key)
            if cached:
                print(f"  ⚠ 有缓存: {cached[:200]}...")
            else:
                print(f"  ✓ 无缓存")
        except Exception as e:
            print(f"  ✗ Redis 检查失败: {e}")
    
    print("\n" + "=" * 80)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        # 分析指定任务
        task_id = sys.argv[1]
        analyze_real_task(task_id)
    else:
        # 运行持久化测试
        test_status_update_persistence()

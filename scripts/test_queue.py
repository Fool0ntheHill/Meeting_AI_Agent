"""
测试队列和 Worker

测试消息队列的推送、拉取和 Worker 处理。
"""

import sys
import time
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.queue.manager import QueueManager, QueueBackend
from src.utils.logger import setup_logger

# 设置日志
setup_logger()


def test_redis_queue():
    """测试 Redis 队列"""
    print("\n" + "=" * 60)
    print("测试 Redis 队列")
    print("=" * 60)
    
    try:
        # 创建队列管理器
        queue = QueueManager(
            backend=QueueBackend.REDIS,
            redis_url="redis://localhost:6379/0",
            queue_name="test_queue",
        )
        
        # 清空队列
        queue.clear_queue()
        print("✅ 队列已清空")
        
        # 推送任务
        print("\n推送任务...")
        for i in range(5):
            task_id = f"task_{i}"
            task_data = {
                "audio_files": [f"audio_{i}.wav"],
                "meeting_type": "test",
            }
            priority = i % 3  # 优先级 0, 1, 2
            
            success = queue.push(task_id, task_data, priority)
            if success:
                print(f"  ✅ 推送任务 {task_id} (priority={priority})")
            else:
                print(f"  ❌ 推送任务 {task_id} 失败")
        
        # 查询队列长度
        length = queue.get_queue_length()
        print(f"\n队列长度: {length}")
        
        # 拉取任务
        print("\n拉取任务...")
        while True:
            message = queue.pull(timeout=1)
            if message:
                task_id = message["task_id"]
                priority = message["priority"]
                print(f"  ✅ 拉取任务 {task_id} (priority={priority})")
            else:
                print("  队列为空")
                break
        
        # 关闭连接
        queue.close()
        print("\n✅ Redis 队列测试完成")
        
    except Exception as e:
        print(f"\n❌ Redis 队列测试失败: {e}")
        import traceback
        traceback.print_exc()


def test_priority_queue():
    """测试优先级队列"""
    print("\n" + "=" * 60)
    print("测试优先级队列")
    print("=" * 60)
    
    try:
        queue = QueueManager(
            backend=QueueBackend.REDIS,
            redis_url="redis://localhost:6379/0",
            queue_name="test_priority_queue",
        )
        
        # 清空队列
        queue.clear_queue()
        
        # 推送不同优先级的任务
        print("\n推送任务 (优先级: 低 → 高)...")
        tasks = [
            ("task_low", {"type": "low"}, 0),
            ("task_medium", {"type": "medium"}, 5),
            ("task_high", {"type": "high"}, 10),
        ]
        
        for task_id, task_data, priority in tasks:
            queue.push(task_id, task_data, priority)
            print(f"  推送 {task_id} (priority={priority})")
        
        # 拉取任务 (应该按优先级顺序)
        print("\n拉取任务 (应该按优先级: 高 → 低)...")
        expected_order = ["task_high", "task_medium", "task_low"]
        actual_order = []
        
        for _ in range(3):
            message = queue.pull(timeout=1)
            if message:
                task_id = message["task_id"]
                priority = message["priority"]
                actual_order.append(task_id)
                print(f"  拉取 {task_id} (priority={priority})")
        
        # 验证顺序
        if actual_order == expected_order:
            print("\n✅ 优先级队列测试通过")
        else:
            print(f"\n❌ 优先级队列测试失败")
            print(f"  期望顺序: {expected_order}")
            print(f"  实际顺序: {actual_order}")
        
        queue.close()
        
    except Exception as e:
        print(f"\n❌ 优先级队列测试失败: {e}")
        import traceback
        traceback.print_exc()


def main():
    """主函数"""
    print("\n" + "=" * 60)
    print("队列测试")
    print("=" * 60)
    print("\n注意: 此测试需要 Redis 服务运行在 localhost:6379")
    print("启动 Redis: docker run -d -p 6379:6379 redis:latest")
    print()
    
    # 测试 Redis 队列
    test_redis_queue()
    
    # 测试优先级队列
    test_priority_queue()
    
    print("\n" + "=" * 60)
    print("所有测试完成")
    print("=" * 60)


if __name__ == "__main__":
    main()

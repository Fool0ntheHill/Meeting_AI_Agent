"""检查 Redis 缓存状态"""
import sys
import redis

def check_redis_cache(task_id: str):
    print(f"检查任务 {task_id} 的 Redis 缓存...")
    print("=" * 80)
    
    try:
        r = redis.from_url("redis://localhost:6379/0", decode_responses=True)
        
        # 检查缓存键
        cache_key = f"task_status:{task_id}"
        
        # 检查是否存在
        exists = r.exists(cache_key)
        print(f"\n缓存键: {cache_key}")
        print(f"是否存在: {'是' if exists else '否'}")
        
        if exists:
            # 获取缓存值
            cached_value = r.get(cache_key)
            print(f"\n缓存内容:")
            print(cached_value)
            
            # 获取 TTL
            ttl = r.ttl(cache_key)
            print(f"\nTTL (剩余时间): {ttl}秒")
        else:
            print("\n✓ 缓存已清除或不存在（这是正常的，说明缓存清除工作正常）")
        
        # 检查 Redis 中所有的 task_status 键
        print("\n" + "=" * 80)
        print("所有任务状态缓存:")
        print("=" * 80)
        
        all_keys = r.keys("task_status:*")
        if all_keys:
            print(f"\n找到 {len(all_keys)} 个缓存键:")
            for key in all_keys:
                ttl = r.ttl(key)
                print(f"  {key} (TTL: {ttl}s)")
        else:
            print("\n✓ 没有任何任务状态缓存（说明缓存清除工作正常）")
            
    except Exception as e:
        print(f"✗ 检查失败: {e}")
        print("\n请确认:")
        print("1. Redis 是否正在运行")
        print("2. Redis 地址是否正确: redis://localhost:6379/0")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/check_redis_cache.py <task_id>")
        sys.exit(1)
    
    task_id = sys.argv[1]
    check_redis_cache(task_id)

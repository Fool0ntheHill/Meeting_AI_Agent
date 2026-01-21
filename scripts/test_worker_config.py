"""
测试 worker 配置加载
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.config.loader import get_config

def test_config():
    """测试配置加载"""
    config = get_config()
    
    print("=" * 60)
    print("Worker 配置检查")
    print("=" * 60)
    print()
    
    print("1. Volcano ASR 配置:")
    print(f"   access_key: {config.volcano.access_key[:20]}...")
    print(f"   app_id: {config.volcano.app_id}")
    print(f"   tos_bucket: {config.volcano.tos_bucket}")
    print(f"   tos_region: {config.volcano.tos_region}")
    print()
    
    print("2. Storage 配置:")
    print(f"   bucket: {config.storage.bucket}")
    print(f"   region: {config.storage.region}")
    print(f"   access_key: {config.storage.access_key[:20]}...")
    print()
    
    print("3. 配置验证:")
    if config.volcano.tos_bucket == config.storage.bucket:
        print("   ✓ TOS bucket 一致")
    else:
        print(f"   ✗ TOS bucket 不一致: {config.volcano.tos_bucket} vs {config.storage.bucket}")
    
    if config.volcano.tos_region == config.storage.region:
        print("   ✓ TOS region 一致")
    else:
        print(f"   ✗ TOS region 不一致: {config.volcano.tos_region} vs {config.storage.region}")
    
    if config.volcano.access_key == config.storage.access_key:
        print("   ⚠ ASR 和 Storage 使用相同的 access_key (可能不正确)")
    else:
        print("   ✓ ASR 和 Storage 使用不同的 access_key")

if __name__ == "__main__":
    test_config()

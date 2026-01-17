#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""直接测试火山引擎热词 API"""

import sys
import os

# 设置测试环境
os.environ["APP_ENV"] = "test"

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.config.loader import get_config
from src.providers.volcano_hotword import VolcanoHotwordClient
from src.utils.logger import get_logger

logger = get_logger(__name__)


def test_list_boosting_tables():
    """测试列出热词库（不需要创建权限）"""
    print("\n" + "=" * 60)
    print("测试列出热词库")
    print("=" * 60)
    
    try:
        config = get_config()
        client = VolcanoHotwordClient(
            app_id=str(config.volcano.app_id),
            access_key=config.volcano.access_key,
            secret_key=config.volcano.secret_key,
        )
        
        print(f"App ID: {client.app_id}")
        print(f"Access Key: {client.access_key[:10]}...")
        
        # 尝试列出热词库
        result = client.list_boosting_tables(page_number=1, page_size=10)
        
        print(f"✅ 列出热词库成功:")
        print(f"   热词库数量: {result.get('BoostingTableCount', 0)}")
        
        if result.get('BoostingTables'):
            for table in result['BoostingTables']:
                print(f"   - {table.get('BoostingTableName')} (ID: {table.get('BoostingTableID')})")
        else:
            print("   (当前没有热词库)")
        
        return True
        
    except Exception as e:
        print(f"❌ 列出热词库失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_create_boosting_table():
    """测试创建热词库"""
    print("\n" + "=" * 60)
    print("测试创建热词库")
    print("=" * 60)
    
    try:
        config = get_config()
        client = VolcanoHotwordClient(
            app_id=str(config.volcano.app_id),
            access_key=config.volcano.access_key,
            secret_key=config.volcano.secret_key,
        )
        
        # 准备测试热词
        hotwords_content = "测试词1|10\n测试词2|10\n测试词3|10"
        
        # 尝试创建热词库
        result = client.create_boosting_table(
            name="测试热词库_API测试",
            hotwords_content=hotwords_content,
        )
        
        print(f"✅ 创建热词库成功:")
        print(f"   BoostingTableID: {result.get('BoostingTableID')}")
        print(f"   词数: {result.get('WordCount')}")
        print(f"   字符数: {result.get('WordSize')}")
        
        return result.get('BoostingTableID')
        
    except Exception as e:
        print(f"❌ 创建热词库失败: {e}")
        import traceback
        traceback.print_exc()
        return None


def main():
    """主函数"""
    print("=" * 60)
    print("火山引擎热词 API 直接测试")
    print("=" * 60)
    print("\n⚠️  注意: 此测试会直接调用火山引擎 API")
    print("⚠️  注意: 可能产生少量费用")
    
    # 测试列出热词库（只读操作）
    list_success = test_list_boosting_tables()
    
    if not list_success:
        print("\n❌ 列出热词库失败，可能是:")
        print("   1. Access Key 或 Secret Key 错误")
        print("   2. App ID 错误")
        print("   3. 网络连接问题")
        return
    
    print("\n✅ 列出热词库成功，说明认证正常")
    
    # 测试创建热词库（需要写权限）
    input("\n按 Enter 继续测试创建热词库...")
    
    boosting_table_id = test_create_boosting_table()
    
    if boosting_table_id:
        print(f"\n✅ 创建成功! BoostingTableID: {boosting_table_id}")
        print("\n⚠️  请手动删除测试热词库:")
        print(f"   BoostingTableID: {boosting_table_id}")
    else:
        print("\n❌ 创建失败，可能是:")
        print("   1. Access Key 没有创建热词库的权限")
        print("   2. 热词库数量已达上限")
        print("   3. 热词格式不正确")


if __name__ == "__main__":
    main()

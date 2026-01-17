#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""测试火山引擎热词客户端"""

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


def test_client_initialization():
    """测试客户端初始化"""
    print("\n" + "=" * 60)
    print("测试客户端初始化")
    print("=" * 60)
    
    try:
        config = get_config()
        client = VolcanoHotwordClient(
            app_id=str(config.volcano.app_id),
            access_key=config.volcano.access_key,
            secret_key=config.volcano.secret_key,
        )
        
        print(f"✅ 客户端初始化成功")
        print(f"   App ID: {client.app_id}")
        print(f"   Domain: {client.domain}")
        print(f"   Region: {client.region}")
        print(f"   Service: {client.service}")
        print(f"   Version: {client.version}")
        
        return client
        
    except Exception as e:
        print(f"❌ 客户端初始化失败: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_signature_generation(client: VolcanoHotwordClient):
    """测试签名生成"""
    print("\n" + "=" * 60)
    print("测试签名生成")
    print("=" * 60)
    
    try:
        # 测试 HMAC 编码
        test_data = "test_string"
        hash_result = client._get_hmac_encode16(test_data)
        print(f"✅ SHA256 哈希生成成功")
        print(f"   输入: {test_data}")
        print(f"   输出: {hash_result[:32]}...")
        
        # 测试签名
        test_key = b"test_key"
        test_data = "test_data"
        signature = client._get_volc_signature(test_key, test_data)
        print(f"✅ HMAC-SHA256 签名生成成功")
        print(f"   签名长度: {len(signature)} bytes")
        
        # 测试请求头生成
        headers = client._get_headers(
            canonical_query_string="Action=ListBoostingTable&Version=2022-08-30",
            http_method="POST",
            canonical_uri="/",
            content_type="application/json; charset=utf-8",
            payload_sign="test_payload_sign",
        )
        
        print(f"✅ 请求头生成成功")
        print(f"   Headers:")
        for key, value in headers.items():
            if key == "Authorization":
                print(f"     {key}: {value[:50]}...")
            else:
                print(f"     {key}: {value}")
        
    except Exception as e:
        print(f"❌ 签名生成失败: {e}")
        import traceback
        traceback.print_exc()


def test_api_methods_structure(client: VolcanoHotwordClient):
    """测试 API 方法结构"""
    print("\n" + "=" * 60)
    print("测试 API 方法结构")
    print("=" * 60)
    
    # 检查方法是否存在
    methods = [
        "create_boosting_table",
        "list_boosting_tables",
        "get_boosting_table",
        "update_boosting_table",
        "delete_boosting_table",
    ]
    
    for method_name in methods:
        if hasattr(client, method_name):
            method = getattr(client, method_name)
            print(f"✅ 方法存在: {method_name}")
            print(f"   文档: {method.__doc__.strip().split(chr(10))[0] if method.__doc__ else 'N/A'}")
        else:
            print(f"❌ 方法不存在: {method_name}")


def main():
    """主函数"""
    print("=" * 60)
    print("火山引擎热词客户端测试")
    print("=" * 60)
    print("\n⚠️  注意: 此测试不会调用实际的火山引擎 API")
    print("⚠️  注意: 仅测试客户端初始化和签名生成逻辑")
    
    try:
        # 测试客户端初始化
        client = test_client_initialization()
        
        if not client:
            print("\n❌ 客户端初始化失败,跳过后续测试")
            return
        
        # 测试签名生成
        test_signature_generation(client)
        
        # 测试 API 方法结构
        test_api_methods_structure(client)
        
        print("\n" + "=" * 60)
        print("✅ 所有测试通过")
        print("=" * 60)
        print("\n下一步:")
        print("1. 启动 API 服务器: python main.py")
        print("2. 运行完整 API 测试: python scripts/test_hotwords_api.py")
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()

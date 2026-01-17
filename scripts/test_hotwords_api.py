#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""测试热词管理 API"""

import sys
import os
import requests
from pathlib import Path

# 设置测试环境
os.environ["APP_ENV"] = "test"

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.utils.logger import get_logger
from auth_helper import get_auth_headers, BASE_URL as API_BASE_URL

logger = get_logger(__name__)

# API 配置
BASE_URL = API_BASE_URL
USERNAME = "test_user"

# 测试数据目录
TEST_DATA_DIR = Path(__file__).parent.parent / "test_data"


def get_headers():
    """获取认证 headers"""
    return get_auth_headers(USERNAME)


def test_create_hotword_set():
    """测试创建热词集"""
    print("\n" + "=" * 60)
    print("测试创建热词集")
    print("=" * 60)
    
    # 准备测试文件
    hotwords_file = TEST_DATA_DIR / "hotwords_medical.txt"
    
    if not hotwords_file.exists():
        print(f"❌ 测试文件不存在: {hotwords_file}")
        return None
    
    # 准备表单数据
    data = {
        "name": "医疗术语热词库",
        "scope": "global",
        "asr_language": "zh-CN",
        "description": "包含常用医疗术语",
    }
    
    # 准备文件
    with open(hotwords_file, "rb") as f:
        files = {"hotwords_file": ("hotwords_medical.txt", f, "text/plain")}
        
        # 发送请求
        response = requests.post(
            f"{BASE_URL}/hotword-sets",
            headers=get_headers(),
            data=data,
            files=files,
        )
    
    print(f"状态码: {response.status_code}")
    print(f"响应: {response.json()}")
    
    if response.status_code == 201:
        result = response.json()
        print(f"✅ 热词集创建成功:")
        print(f"   ID: {result['hotword_set_id']}")
        print(f"   BoostingTableID: {result['boosting_table_id']}")
        print(f"   词数: {result['word_count']}")
        return result["hotword_set_id"]
    else:
        print(f"❌ 创建失败: {response.text}")
        return None


def test_create_tenant_hotword_set():
    """测试创建租户热词集"""
    print("\n" + "=" * 60)
    print("测试创建租户热词集")
    print("=" * 60)
    
    # 准备测试文件
    hotwords_file = TEST_DATA_DIR / "hotwords_tech.txt"
    
    if not hotwords_file.exists():
        print(f"❌ 测试文件不存在: {hotwords_file}")
        return None
    
    # 准备表单数据
    data = {
        "name": "技术术语热词库",
        "scope": "tenant",
        "scope_id": "tenant_001",
        "asr_language": "zh-CN+en-US",
        "description": "包含技术相关术语",
    }
    
    # 准备文件
    with open(hotwords_file, "rb") as f:
        files = {"hotwords_file": ("hotwords_tech.txt", f, "text/plain")}
        
        # 发送请求
        response = requests.post(
            f"{BASE_URL}/hotword-sets",
            headers=get_headers(),
            data=data,
            files=files,
        )
    
    print(f"状态码: {response.status_code}")
    print(f"响应: {response.json()}")
    
    if response.status_code == 201:
        result = response.json()
        print(f"✅ 租户热词集创建成功:")
        print(f"   ID: {result['hotword_set_id']}")
        print(f"   BoostingTableID: {result['boosting_table_id']}")
        print(f"   词数: {result['word_count']}")
        return result["hotword_set_id"]
    else:
        print(f"❌ 创建失败: {response.text}")
        return None


def test_list_hotword_sets():
    """测试列出热词集"""
    print("\n" + "=" * 60)
    print("测试列出热词集")
    print("=" * 60)
    
    # 发送请求
    response = requests.get(
        f"{BASE_URL}/hotword-sets",
        headers=get_headers(),
    )
    
    print(f"状态码: {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        print(f"✅ 查询到 {result['total']} 个热词集:")
        for hs in result["hotword_sets"]:
            print(f"   - {hs['name']} ({hs['scope']}, {hs['provider']})")
            print(f"     ID: {hs['hotword_set_id']}")
            print(f"     词数: {hs.get('word_count', 'N/A')}")
    else:
        print(f"❌ 查询失败: {response.text}")


def test_get_hotword_set(hotword_set_id: str):
    """测试获取热词集详情"""
    print("\n" + "=" * 60)
    print("测试获取热词集详情")
    print("=" * 60)
    
    # 不包含预览
    response = requests.get(
        f"{BASE_URL}/hotword-sets/{hotword_set_id}",
        headers=get_headers(),
    )
    
    print(f"状态码: {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        print(f"✅ 热词集详情:")
        print(f"   ID: {result['hotword_set_id']}")
        print(f"   名称: {result['name']}")
        print(f"   提供商: {result['provider']}")
        print(f"   资源 ID: {result['provider_resource_id']}")
        print(f"   作用域: {result['scope']}")
        print(f"   词数: {result.get('word_count', 'N/A')}")
        print(f"   字符数: {result.get('word_size', 'N/A')}")
    else:
        print(f"❌ 查询失败: {response.text}")
    
    # 包含预览
    print("\n测试获取热词集详情(包含预览):")
    response = requests.get(
        f"{BASE_URL}/hotword-sets/{hotword_set_id}",
        headers=get_headers(),
        params={"include_preview": True},
    )
    
    if response.status_code == 200:
        result = response.json()
        if result.get("preview"):
            print(f"✅ 热词预览 (前 {len(result['preview'])} 个):")
            for word in result["preview"][:5]:
                print(f"   - {word}")
        else:
            print("ℹ️ 无预览数据")
    else:
        print(f"❌ 查询失败: {response.text}")


def test_update_hotword_set(hotword_set_id: str):
    """测试更新热词集"""
    print("\n" + "=" * 60)
    print("测试更新热词集")
    print("=" * 60)
    
    # 1. 只更新名称和描述
    print("\n1. 更新名称和描述:")
    data = {
        "name": "医疗术语热词库(更新版)",
        "description": "更新后的描述",
    }
    
    response = requests.put(
        f"{BASE_URL}/hotword-sets/{hotword_set_id}",
        headers=get_headers(),
        data=data,
    )
    
    print(f"状态码: {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        print(f"✅ 热词集已更新:")
        print(f"   词数: {result['word_count']}")
    else:
        print(f"❌ 更新失败: {response.text}")
    
    # 2. 更新热词文件
    print("\n2. 更新热词文件:")
    hotwords_file = TEST_DATA_DIR / "hotwords_tech.txt"
    
    if hotwords_file.exists():
        data = {
            "name": "医疗术语热词库(再次更新)",
        }
        
        with open(hotwords_file, "rb") as f:
            files = {"hotwords_file": ("hotwords_tech.txt", f, "text/plain")}
            
            response = requests.put(
                f"{BASE_URL}/hotword-sets/{hotword_set_id}",
                headers=get_headers(),
                data=data,
                files=files,
            )
        
        print(f"状态码: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ 热词集文件已更新:")
            print(f"   词数: {result['word_count']}")
        else:
            print(f"❌ 更新失败: {response.text}")


def test_delete_hotword_set(hotword_set_id: str):
    """测试删除热词集"""
    print("\n" + "=" * 60)
    print("测试删除热词集")
    print("=" * 60)
    
    # 发送请求
    response = requests.delete(
        f"{BASE_URL}/hotword-sets/{hotword_set_id}",
        headers=get_headers(),
    )
    
    print(f"状态码: {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        print(f"✅ 热词集已删除: {hotword_set_id}")
    else:
        print(f"❌ 删除失败: {response.text}")
    
    # 验证删除
    response = requests.get(
        f"{BASE_URL}/hotword-sets/{hotword_set_id}",
        headers=get_headers(),
    )
    
    if response.status_code == 404:
        print("✅ 验证: 热词集已不存在")
    else:
        print("❌ 验证失败: 热词集仍然存在")


def main():
    """主函数"""
    print("=" * 60)
    print("热词管理 API 测试")
    print("=" * 60)
    print("\n⚠️  注意: 此测试需要 API 服务器运行在 http://localhost:8000")
    print("⚠️  注意: 此测试会调用火山引擎 API,可能产生费用")
    print("\n请确保:")
    print("1. API 服务器已启动: python main.py")
    print("2. 配置文件中已填写火山引擎凭证")
    print("3. 测试热词文件存在于 test_data/ 目录")
    
    input("\n按 Enter 继续测试...")
    
    try:
        # 测试创建
        hotword_set_id1 = test_create_hotword_set()
        hotword_set_id2 = test_create_tenant_hotword_set()
        
        if not hotword_set_id1:
            print("\n❌ 创建热词集失败,跳过后续测试")
            return
        
        # 测试列出
        test_list_hotword_sets()
        
        # 测试获取详情
        test_get_hotword_set(hotword_set_id1)
        
        # 测试更新
        test_update_hotword_set(hotword_set_id1)
        
        # 测试删除
        if hotword_set_id1:
            test_delete_hotword_set(hotword_set_id1)
        if hotword_set_id2:
            test_delete_hotword_set(hotword_set_id2)
        
        print("\n" + "=" * 60)
        print("✅ 所有测试完成")
        print("=" * 60)
        
    except requests.exceptions.ConnectionError:
        print("\n❌ 无法连接到 API 服务器")
        print("请确保 API 服务器已启动: python main.py")
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""测试文件夹重名检测"""

import requests
import sys
from auth_helper import get_auth_headers

BASE_URL = "http://127.0.0.1:51008"


def test_duplicate_folder_name():
    """测试创建重名文件夹"""
    print("=" * 60)
    print("测试文件夹重名检测")
    print("=" * 60)
    
    headers = get_auth_headers()
    
    # 1. 创建第一个文件夹
    folder_name = "测试重名文件夹"
    print(f"\n1. 创建文件夹: {folder_name}")
    
    response = requests.post(
        f"{BASE_URL}/api/v1/folders",
        json={"name": folder_name},
        headers=headers
    )
    
    if response.status_code == 201:
        data = response.json()
        folder_id = data.get("folder_id")
        print(f"✓ 文件夹创建成功: {folder_id}")
    else:
        print(f"✗ 创建失败: {response.status_code}")
        print(response.text)
        return False
    
    # 2. 尝试创建同名文件夹
    print(f"\n2. 尝试创建同名文件夹: {folder_name}")
    
    response = requests.post(
        f"{BASE_URL}/api/v1/folders",
        json={"name": folder_name},
        headers=headers
    )
    
    if response.status_code == 409:
        print(f"✓ 正确返回 409 Conflict")
        print(f"  错误信息: {response.json().get('detail')}")
        duplicate_detected = True
    else:
        print(f"✗ 应该返回 409，实际返回: {response.status_code}")
        print(response.text)
        duplicate_detected = False
    
    # 3. 清理：删除测试文件夹
    print(f"\n3. 清理测试数据")
    response = requests.delete(
        f"{BASE_URL}/api/v1/folders/{folder_id}",
        headers=headers
    )
    
    if response.status_code == 200:
        print(f"✓ 文件夹已删除")
    else:
        print(f"✗ 删除失败: {response.status_code}")
    
    # 4. 验证删除后可以重新创建同名文件夹
    print(f"\n4. 验证删除后可以重新创建同名文件夹")
    
    response = requests.post(
        f"{BASE_URL}/api/v1/folders",
        json={"name": folder_name},
        headers=headers
    )
    
    if response.status_code == 201:
        data = response.json()
        new_folder_id = data.get("folder_id")
        print(f"✓ 文件夹重新创建成功: {new_folder_id}")
        
        # 清理
        requests.delete(
            f"{BASE_URL}/api/v1/folders/{new_folder_id}",
            headers=headers
        )
    else:
        print(f"✗ 重新创建失败: {response.status_code}")
        print(response.text)
    
    print("\n" + "=" * 60)
    if duplicate_detected:
        print("✓ 测试通过：重名检测正常工作")
        return True
    else:
        print("✗ 测试失败：重名检测未生效")
        return False


if __name__ == "__main__":
    try:
        success = test_duplicate_folder_name()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n✗ 测试出错: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

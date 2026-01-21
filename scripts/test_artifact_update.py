#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试 artifact 直接修改接口（原地更新）

验证：
1. PUT /artifacts/{artifact_id} 直接更新现有 artifact
2. artifact_id 和 version 不变
3. content 被更新
4. metadata 添加 manually_edited 标记
"""

import requests
from auth_helper import get_jwt_token

task_id = "task_ab07a64f9e8d4f69"

print("=" * 60)
print("测试 Artifact 直接修改接口")
print("=" * 60)

# 1. 登录
print("\n1. 登录...")
token = get_jwt_token("test_user")
headers = {
    "Authorization": f"Bearer {token}",
    "Content-Type": "application/json"
}

# 2. 获取现有 artifact
print(f"\n2. 获取现有 artifact...")
response = requests.get(
    f"http://localhost:8000/api/v1/tasks/{task_id}/artifacts",
    headers=headers
)

if response.status_code != 200:
    print(f"   ❌ 错误: {response.status_code}")
    exit(1)

data = response.json()
artifacts = data["artifacts_by_type"].get("meeting_minutes", [])

if not artifacts:
    print("   ❌ 没有找到 meeting_minutes")
    exit(1)

artifact_id = artifacts[0]["artifact_id"]
version = artifacts[0]["version"]
print(f"   ✓ 找到 artifact: {artifact_id} (v{version})")

# 3. 获取 artifact 详情
print(f"\n3. 获取 artifact 详情...")
response = requests.get(
    f"http://localhost:8000/api/v1/artifacts/{artifact_id}",
    headers=headers
)

if response.status_code != 200:
    print(f"   ❌ 错误: {response.status_code}")
    exit(1)

data = response.json()
content = data["artifact"]["content"]
print(f"   ✓ 获取成功，content 类型: {type(content)}")

# 4. 修改 content
print(f"\n4. 修改 content...")
modified_content = content.copy()
modified_content["会议概要"] = "【已修改】" + modified_content.get("会议概要", "")
modified_content["其他"] = "这是通过 API 手动修改的测试"

print(f"   修改内容：")
print(f"   - 会议概要: 添加【已修改】前缀")
print(f"   - 其他: 添加测试说明")

# 5. 调用 PUT 接口更新（原地更新，不创建新版本）
print(f"\n5. 调用 PUT /artifacts/{artifact_id}...")
response = requests.put(
    f"http://localhost:8000/api/v1/artifacts/{artifact_id}",
    headers=headers,
    json=modified_content
)

print(f"   Status: {response.status_code}")

if response.status_code == 200:
    result = response.json()
    print(f"\n   ✅ 更新成功！")
    print(f"   - artifact_id: {result['artifact_id']} (应该与原 ID 相同)")
    print(f"   - 消息: {result['message']}")
    
    # 验证 artifact_id 没有变化（原地更新）
    if result['artifact_id'] == artifact_id:
        print(f"   ✓ 确认：artifact_id 未变化（原地更新）")
    else:
        print(f"   ⚠️  警告：artifact_id 发生了变化！")
    
    # 6. 验证更新后的内容
    print(f"\n6. 验证更新后的内容...")
    response = requests.get(
        f"http://localhost:8000/api/v1/artifacts/{artifact_id}",
        headers=headers
    )
    
    if response.status_code == 200:
        data = response.json()
        updated_content = data["artifact"]["content"]
        metadata = data["artifact"]["metadata"]
        updated_version = data["artifact"]["version"]
        
        print(f"   ✓ 内容获取成功")
        print(f"   - 版本号: v{updated_version} (应该与原版本相同: v{version})")
        print(f"   - 会议概要: {updated_content.get('会议概要', '')[:80]}...")
        print(f"   - 其他: {updated_content.get('其他', '')}")
        
        # 验证版本号没有变化
        if updated_version == version:
            print(f"   ✓ 确认：版本号未变化（原地更新）")
        else:
            print(f"   ⚠️  警告：版本号发生了变化！")
        
        # 验证内容已更新
        if "【已修改】" in updated_content.get('会议概要', ''):
            print(f"   ✓ 确认：内容已成功更新")
        else:
            print(f"   ❌ 错误：内容未更新")
        
        # 验证元数据
        if metadata:
            print(f"   - 元数据: manually_edited={metadata.get('manually_edited')}")
            print(f"   - 元数据: last_edited_at={metadata.get('last_edited_at')}")
            print(f"   - 元数据: last_edited_by={metadata.get('last_edited_by')}")
            
            if metadata.get('manually_edited') == True:
                print(f"   ✓ 确认：已标记为手动编辑")
            else:
                print(f"   ❌ 错误：未标记为手动编辑")
        else:
            print(f"   ❌ 错误：元数据为空")
    else:
        print(f"   ❌ 获取更新后内容失败: {response.status_code}")
else:
    print(f"   ❌ 更新失败")
    print(f"   错误: {response.text}")

print("\n" + "=" * 60)
print("测试完成")
print("=" * 60)

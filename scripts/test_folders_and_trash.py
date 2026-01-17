#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""测试文件夹和回收站功能"""

import sys
import requests
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from scripts.auth_helper import get_jwt_token

BASE_URL = "http://localhost:8000/api/v1"


def test_folders_and_trash():
    """测试文件夹和回收站功能"""
    
    # 获取测试 Token
    print("1. 获取测试 Token...")
    token = get_jwt_token("test_user")
    headers = {"Authorization": f"Bearer {token}"}
    print(f"   ✅ Token: {token[:20]}...")
    
    # 测试创建文件夹
    print("\n2. 创建文件夹...")
    response = requests.post(
        f"{BASE_URL}/folders",
        json={"name": "2024年会议"},
        headers=headers,
    )
    print(f"   状态码: {response.status_code}")
    if response.status_code == 201:
        folder_data = response.json()
        folder_id = folder_data["folder_id"]
        print(f"   ✅ 文件夹已创建: {folder_id}")
    else:
        print(f"   ❌ 创建失败: {response.text}")
        return
    
    # 测试创建第二个文件夹（扁平结构）
    print("\n3. 创建第二个文件夹...")
    response = requests.post(
        f"{BASE_URL}/folders",
        json={"name": "产品规划"},
        headers=headers,
    )
    print(f"   状态码: {response.status_code}")
    if response.status_code == 201:
        folder2_data = response.json()
        folder2_id = folder2_data["folder_id"]
        print(f"   ✅ 第二个文件夹已创建: {folder2_id}")
    else:
        print(f"   ❌ 创建失败: {response.text}")
        return
    
    # 测试列出文件夹
    print("\n4. 列出所有文件夹...")
    response = requests.get(f"{BASE_URL}/folders", headers=headers)
    print(f"   状态码: {response.status_code}")
    if response.status_code == 200:
        folders = response.json()
        print(f"   ✅ 找到 {folders['total']} 个文件夹（扁平结构）")
        for folder in folders["items"]:
            print(f"      - {folder['name']} (ID: {folder['folder_id']})")
    else:
        print(f"   ❌ 获取失败: {response.text}")
    
    # 测试重命名文件夹
    print("\n5. 重命名文件夹...")
    response = requests.patch(
        f"{BASE_URL}/folders/{folder_id}",
        json={"name": "2024年重要会议"},
        headers=headers,
    )
    print(f"   状态码: {response.status_code}")
    if response.status_code == 200:
        print(f"   ✅ 文件夹已重命名")
    else:
        print(f"   ❌ 重命名失败: {response.text}")
    
    # 测试创建任务（用于测试移动和删除）
    print("\n6. 创建测试任务...")
    response = requests.post(
        f"{BASE_URL}/tasks",
        json={
            "audio_files": ["test_audio.wav"],
            "meeting_type": "weekly_sync",
            "asr_language": "zh-CN",
            "output_language": "zh-CN",
        },
        headers=headers,
    )
    print(f"   状态码: {response.status_code}")
    if response.status_code == 201:
        task_data = response.json()
        task_id = task_data["task_id"]
        print(f"   ✅ 任务已创建: {task_id}")
    else:
        print(f"   ❌ 创建失败: {response.text}")
        return
    
    # 测试移动任务到文件夹
    print("\n7. 移动任务到文件夹...")
    response = requests.patch(
        f"{BASE_URL}/sessions/{task_id}/move",
        json={"folder_id": folder_id},
        headers=headers,
    )
    print(f"   状态码: {response.status_code}")
    if response.status_code == 200:
        print(f"   ✅ 任务已移动到文件夹")
    else:
        print(f"   ❌ 移动失败: {response.text}")
    
    # 测试软删除任务
    print("\n8. 软删除任务（移入回收站）...")
    response = requests.patch(
        f"{BASE_URL}/sessions/{task_id}/delete",
        headers=headers,
    )
    print(f"   状态码: {response.status_code}")
    if response.status_code == 200:
        print(f"   ✅ 任务已移至回收站")
    else:
        print(f"   ❌ 删除失败: {response.text}")
    
    # 测试列出回收站
    print("\n9. 列出回收站...")
    response = requests.get(f"{BASE_URL}/trash/sessions", headers=headers)
    print(f"   状态码: {response.status_code}")
    if response.status_code == 200:
        trash = response.json()
        print(f"   ✅ 回收站中有 {trash['total']} 个会话")
        for item in trash["items"]:
            print(f"      - {item['task_id']} (删除时间: {item['deleted_at']})")
    else:
        print(f"   ❌ 获取失败: {response.text}")
    
    # 测试还原任务
    print("\n10. 还原任务...")
    response = requests.patch(
        f"{BASE_URL}/sessions/{task_id}/restore",
        headers=headers,
    )
    print(f"   状态码: {response.status_code}")
    if response.status_code == 200:
        print(f"   ✅ 任务已还原")
    else:
        print(f"   ❌ 还原失败: {response.text}")
    
    # 测试再次软删除
    print("\n11. 再次软删除任务...")
    response = requests.patch(
        f"{BASE_URL}/sessions/{task_id}/delete",
        headers=headers,
    )
    print(f"   状态码: {response.status_code}")
    if response.status_code == 200:
        print(f"   ✅ 任务已移至回收站")
    else:
        print(f"   ❌ 删除失败: {response.text}")
    
    # 测试彻底删除任务
    print("\n12. 彻底删除任务...")
    response = requests.delete(
        f"{BASE_URL}/sessions/{task_id}",
        headers=headers,
    )
    print(f"   状态码: {response.status_code}")
    if response.status_code == 200:
        print(f"   ✅ 任务已彻底删除")
    else:
        print(f"   ❌ 删除失败: {response.text}")
    
    # 测试批量操作
    print("\n13. 创建多个测试任务用于批量操作...")
    task_ids = []
    for i in range(3):
        response = requests.post(
            f"{BASE_URL}/tasks",
            json={
                "audio_files": [f"test_audio_{i}.wav"],
                "meeting_type": "weekly_sync",
                "asr_language": "zh-CN",
                "output_language": "zh-CN",
            },
            headers=headers,
        )
        if response.status_code == 201:
            task_ids.append(response.json()["task_id"])
    print(f"   ✅ 创建了 {len(task_ids)} 个任务")
    
    # 测试批量移动
    print("\n14. 批量移动任务...")
    response = requests.post(
        f"{BASE_URL}/sessions/batch-move",
        json={"task_ids": task_ids, "folder_id": folder_id},
        headers=headers,
    )
    print(f"   状态码: {response.status_code}")
    if response.status_code == 200:
        result = response.json()
        print(f"   ✅ 批量移动完成: {result['moved_count']} 个任务")
    else:
        print(f"   ❌ 批量移动失败: {response.text}")
    
    # 测试批量删除
    print("\n15. 批量删除任务...")
    response = requests.post(
        f"{BASE_URL}/sessions/batch-delete",
        json={"task_ids": task_ids},
        headers=headers,
    )
    print(f"   状态码: {response.status_code}")
    if response.status_code == 200:
        result = response.json()
        print(f"   ✅ 批量删除完成: {result['deleted_count']} 个任务")
    else:
        print(f"   ❌ 批量删除失败: {response.text}")
    
    # 测试批量还原
    print("\n16. 批量还原任务...")
    response = requests.post(
        f"{BASE_URL}/sessions/batch-restore",
        json={"task_ids": task_ids},
        headers=headers,
    )
    print(f"   状态码: {response.status_code}")
    if response.status_code == 200:
        result = response.json()
        print(f"   ✅ 批量还原完成: {result['restored_count']} 个任务")
    else:
        print(f"   ❌ 批量还原失败: {response.text}")
    
    # 清理：删除测试数据
    print("\n17. 清理测试数据...")
    # 删除任务
    for tid in task_ids:
        requests.patch(f"{BASE_URL}/sessions/{tid}/delete", headers=headers)
        requests.delete(f"{BASE_URL}/sessions/{tid}", headers=headers)
    # 删除文件夹（会话会自动移到根目录）
    requests.delete(f"{BASE_URL}/folders/{folder_id}", headers=headers)
    requests.delete(f"{BASE_URL}/folders/{folder2_id}", headers=headers)
    print(f"   ✅ 清理完成")
    
    print("\n" + "="*60)
    print("✅ 所有测试完成！")
    print("="*60)


if __name__ == "__main__":
    print("="*60)
    print("文件夹和回收站功能测试")
    print("="*60)
    print("\n⚠️  请确保 API 服务器正在运行: python main.py")
    print()
    
    try:
        test_folders_and_trash()
    except requests.exceptions.ConnectionError:
        print("\n❌ 无法连接到 API 服务器")
        print("   请先启动服务器: python main.py")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

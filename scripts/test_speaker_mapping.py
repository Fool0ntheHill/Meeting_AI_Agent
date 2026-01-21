#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试 speaker mapping 功能

验证：
1. speakers 表中的数据
2. speaker_mappings 表中的数据
3. GET /api/v1/tasks/{task_id}/transcript 返回的 speaker_mapping
"""

import sys
import requests
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.database.session import session_scope
from src.database.repositories import SpeakerRepository, SpeakerMappingRepository
from auth_helper import get_jwt_token

def test_database():
    """测试数据库中的数据"""
    print("=" * 60)
    print("1. 检查 speakers 表")
    print("=" * 60)
    
    with session_scope() as session:
        speaker_repo = SpeakerRepository(session)
        
        # 获取所有 speakers
        speakers = speaker_repo.get_by_tenant("default")
        print(f"\n找到 {len(speakers)} 个说话人：")
        for speaker in speakers:
            print(f"  - {speaker.speaker_id} -> {speaker.display_name}")
        
        # 测试批量获取
        speaker_ids = ["speaker_linyudong", "speaker_lanweiyi"]
        display_names = speaker_repo.get_display_names_batch(speaker_ids)
        print(f"\n批量获取结果：")
        for speaker_id, display_name in display_names.items():
            print(f"  - {speaker_id} -> {display_name}")
    
    print("\n" + "=" * 60)
    print("2. 检查 speaker_mappings 表")
    print("=" * 60)
    
    # 使用测试任务 ID
    task_id = "task_07cb88970c3848c4"
    
    with session_scope() as session:
        mapping_repo = SpeakerMappingRepository(session)
        
        # 获取任务的 speaker mappings
        mappings = mapping_repo.get_by_task_id(task_id)
        print(f"\n任务 {task_id} 的 speaker mappings：")
        if mappings:
            for mapping in mappings:
                print(f"  - {mapping.speaker_label} -> {mapping.speaker_name} (ID: {mapping.speaker_id})")
        else:
            print("  (无数据 - 需要重新运行任务)")

def test_api():
    """测试 API 返回"""
    print("\n" + "=" * 60)
    print("3. 测试 GET /api/v1/tasks/{task_id}/transcript API")
    print("=" * 60)
    
    # 获取 JWT token（使用正确的用户名）
    token = get_jwt_token("user_test_user")
    
    # 使用测试任务 ID
    task_id = "task_07cb88970c3848c4"
    
    # 调用 API
    url = f"http://localhost:8000/api/v1/tasks/{task_id}/transcript"
    headers = {"Authorization": f"Bearer {token}"}
    
    print(f"\nGET {url}")
    response = requests.get(url, headers=headers)
    
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        
        # 检查 speaker_mapping 字段
        speaker_mapping = data.get("speaker_mapping")
        print(f"\nspeaker_mapping 字段：")
        if speaker_mapping:
            print(f"  类型: {type(speaker_mapping)}")
            print(f"  内容:")
            for label, name in speaker_mapping.items():
                print(f"    - {label} -> {name}")
        else:
            print("  (无数据)")
        
        # 检查 segments 中的 speaker
        segments = data.get("segments", [])
        print(f"\n前 3 个 segments 的 speaker：")
        for i, seg in enumerate(segments[:3]):
            print(f"  [{i}] speaker: {seg.get('speaker')}")
        
        print("\n✓ API 测试完成")
        print("\n前端应该：")
        print("  1. 从 API 响应中获取 speaker_mapping")
        print("  2. 使用 speaker_mapping 替换 segments 中的 speaker 显示")
        print("  3. 例如：'Speaker 1' -> '林煜东'")
    else:
        print(f"Error: {response.text}")

if __name__ == "__main__":
    test_database()
    test_api()

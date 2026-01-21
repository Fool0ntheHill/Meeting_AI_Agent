#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""检查特定任务的 speaker mapping 数据"""

import sys
import requests
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.database.session import session_scope
from src.database.repositories import SpeakerMappingRepository, SpeakerRepository
from src.database.models import Task
from auth_helper import get_jwt_token

task_id = "task_ab07a64f9e8d4f69"

print("=" * 60)
print(f"检查任务: {task_id}")
print("=" * 60)

# 1. 检查任务基本信息
print("\n1. 任务基本信息")
with session_scope() as session:
    task = session.query(Task).filter(Task.task_id == task_id).first()
    if task:
        print(f"  Task ID: {task.task_id}")
        print(f"  User ID: {task.user_id}")
        print(f"  Tenant ID: {task.tenant_id}")
        print(f"  State: {task.state}")
    else:
        print("  ❌ 任务不存在")
        sys.exit(1)

# 2. 检查 speaker_mappings 表
print("\n2. speaker_mappings 表数据")
with session_scope() as session:
    mapping_repo = SpeakerMappingRepository(session)
    mappings = mapping_repo.get_by_task_id(task_id)
    
    # 提取数据到列表（避免 session 关闭后访问）
    mapping_data = []
    if mappings:
        print(f"  找到 {len(mappings)} 条映射：")
        for m in mappings:
            mapping_data.append({
                'speaker_label': m.speaker_label,
                'speaker_name': m.speaker_name,
                'speaker_id': m.speaker_id
            })
            print(f"    - {m.speaker_label} -> {m.speaker_name} (speaker_id: {m.speaker_id})")
    else:
        print("  ❌ 无映射数据")

# 3. 检查 speakers 表
print("\n3. speakers 表数据")
with session_scope() as session:
    speaker_repo = SpeakerRepository(session)
    
    if mapping_data:
        speaker_ids = [m['speaker_id'] for m in mapping_data if m['speaker_id']]
        if speaker_ids:
            display_names = speaker_repo.get_display_names_batch(speaker_ids)
            print(f"  找到 {len(display_names)} 个真实姓名：")
            for speaker_id, display_name in display_names.items():
                print(f"    - {speaker_id} -> {display_name}")
        else:
            print("  ⚠️ 映射中没有 speaker_id")
    else:
        print("  (跳过，因为没有映射数据)")

# 4. 测试 API 响应
print("\n4. API 响应测试")
token = get_jwt_token("user_test_user")
url = f"http://localhost:8000/api/v1/tasks/{task_id}/transcript"
headers = {"Authorization": f"Bearer {token}"}

print(f"  GET {url}")
response = requests.get(url, headers=headers)
print(f"  Status: {response.status_code}")

if response.status_code == 200:
    data = response.json()
    
    # 检查 speaker_mapping 字段
    speaker_mapping = data.get("speaker_mapping")
    print(f"\n  speaker_mapping 字段:")
    if speaker_mapping:
        print(f"    类型: {type(speaker_mapping)}")
        print(f"    内容:")
        for label, name in speaker_mapping.items():
            print(f"      {label} -> {name}")
    else:
        print(f"    ❌ 字段为空或不存在")
        print(f"    响应中的所有字段: {list(data.keys())}")
    
    # 检查前几个 segments
    segments = data.get("segments", [])
    if segments:
        print(f"\n  前 3 个 segments:")
        for i, seg in enumerate(segments[:3]):
            print(f"    [{i}] speaker: {seg.get('speaker')}, text: {seg.get('text', '')[:30]}...")
else:
    print(f"  ❌ 错误: {response.text}")

print("\n" + "=" * 60)
print("诊断结果")
print("=" * 60)

with session_scope() as session:
    mapping_repo = SpeakerMappingRepository(session)
    mappings = mapping_repo.get_by_task_id(task_id)
    
    # 提取数据
    mapping_data = []
    if mappings:
        for m in mappings:
            mapping_data.append({
                'speaker_id': m.speaker_id
            })
    
    if not mapping_data:
        print("❌ 问题：speaker_mappings 表中没有数据")
        print("   原因：可能是旧任务，或者 worker 没有保存映射")
        print("   解决：重新运行任务")
    else:
        speaker_repo = SpeakerRepository(session)
        speaker_ids = [m['speaker_id'] for m in mapping_data if m['speaker_id']]
        
        if not speaker_ids:
            print("❌ 问题：映射中没有 speaker_id")
            print("   原因：数据不完整")
        else:
            display_names = speaker_repo.get_display_names_batch(speaker_ids)
            
            if not display_names:
                print("❌ 问题：speakers 表中没有对应的真实姓名")
                print("   原因：speakers 表缺少数据")
                print("   解决：运行 python scripts/migrate_add_speakers_table.py")
            else:
                print("✅ 数据完整，应该能正常显示")
                print("   如果前端还是不显示，检查：")
                print("   1. Backend 是否重启（加载新代码）")
                print("   2. 前端是否正确读取 speaker_mapping 字段")
                print("   3. 浏览器控制台是否有错误")

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试 Pipeline 是否正确保存真实姓名到 segments

验证点：
1. SpeakerMapping 表中存储的是真实姓名（如 "林煜东"），不是声纹 ID（如 "speaker_linyudong"）
2. Transcript segments 中存储的是真实姓名
3. 生成新笔记时，LLM 看到的是真实姓名
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.database.session import session_scope
from src.database.repositories import (
    TaskRepository,
    TranscriptRepository,
    SpeakerMappingRepository,
    SpeakerRepository,
)
import json


def test_speaker_names_in_database():
    """测试数据库中的说话人名称"""
    print("=" * 80)
    print("测试：数据库中的说话人名称")
    print("=" * 80)
    
    # 使用最近的任务进行测试
    with session_scope() as db:
        task_repo = TaskRepository(db)
        transcript_repo = TranscriptRepository(db)
        speaker_mapping_repo = SpeakerMappingRepository(db)
        speaker_repo = SpeakerRepository(db)
        
        # 获取最近的任务
        tasks = task_repo.get_by_user("test_user", limit=5)
        
        if not tasks:
            print("❌ 没有找到任务")
            return
        
        for task in tasks:
            print(f"\n{'=' * 80}")
            print(f"任务 ID: {task.task_id}")
            print(f"状态: {task.state}")
            print(f"创建时间: {task.created_at}")
            
            # 1. 检查 SpeakerMapping 表
            print(f"\n{'─' * 80}")
            print("1. SpeakerMapping 表中的数据：")
            mappings = speaker_mapping_repo.get_by_task_id(task.task_id)
            
            if not mappings:
                print("   ⚠️  没有找到 speaker mapping")
                continue
            
            for mapping in mappings:
                print(f"   - {mapping.speaker_label} -> {mapping.speaker_name} (speaker_id={mapping.speaker_id})")
                
                # 检查是否是真实姓名
                if mapping.speaker_id and mapping.speaker_id.startswith("speaker_"):
                    # 查询 Speaker 表获取真实姓名
                    real_name = speaker_repo.get_display_name(mapping.speaker_id)
                    if real_name and real_name != mapping.speaker_name:
                        print(f"      ❌ 错误：存储的是声纹 ID，应该是真实姓名 '{real_name}'")
                    elif real_name and real_name == mapping.speaker_name:
                        print(f"      ✅ 正确：存储的是真实姓名")
                    else:
                        print(f"      ⚠️  警告：Speaker 表中没有找到该声纹 ID 的真实姓名")
            
            # 2. 检查 Transcript segments
            print(f"\n{'─' * 80}")
            print("2. Transcript segments 中的说话人：")
            transcript_record = transcript_repo.get_by_task_id(task.task_id)
            
            if not transcript_record:
                print("   ⚠️  没有找到 transcript")
                continue
            
            segments = transcript_record.get_segments_list()
            
            # 统计说话人
            speakers_in_segments = set()
            for seg in segments[:10]:  # 只显示前 10 条
                speakers_in_segments.add(seg.get("speaker", "Unknown"))
            
            print(f"   前 10 条 segments 中的说话人: {speakers_in_segments}")
            
            # 检查是否是真实姓名
            for speaker in speakers_in_segments:
                if speaker and speaker.startswith("speaker_"):
                    print(f"      ❌ 错误：segments 中存储的是声纹 ID '{speaker}'")
                elif speaker and not speaker.startswith("Speaker "):
                    print(f"      ✅ 正确：segments 中存储的是真实姓名 '{speaker}'")
                else:
                    print(f"      ⚠️  警告：segments 中存储的是原始 ASR 标签 '{speaker}'")
            
            # 3. 显示完整的 segment 示例
            print(f"\n{'─' * 80}")
            print("3. Segment 示例（前 3 条）：")
            for i, seg in enumerate(segments[:3], 1):
                print(f"   [{i}] {seg.get('speaker', 'Unknown')}: {seg.get('text', '')[:50]}...")


def test_speaker_table():
    """测试 Speaker 表中的数据"""
    print("\n" + "=" * 80)
    print("测试：Speaker 表中的数据")
    print("=" * 80)
    
    with session_scope() as db:
        speaker_repo = SpeakerRepository(db)
        
        # 获取所有说话人
        speakers = speaker_repo.get_by_tenant("default")
        
        if not speakers:
            print("❌ Speaker 表中没有数据")
            return
        
        print(f"\n找到 {len(speakers)} 个说话人：")
        for speaker in speakers:
            print(f"   - {speaker.speaker_id} -> {speaker.display_name}")


if __name__ == "__main__":
    print("\n" + "=" * 80)
    print("测试：Pipeline 是否正确保存真实姓名到 segments")
    print("=" * 80)
    
    # 测试 Speaker 表
    test_speaker_table()
    
    # 测试数据库中的说话人名称
    test_speaker_names_in_database()
    
    print("\n" + "=" * 80)
    print("测试完成")
    print("=" * 80)
    print("\n预期结果：")
    print("1. SpeakerMapping.speaker_name 应该是真实姓名（如 '林煜东'），不是声纹 ID")
    print("2. Transcript segments 中的 speaker 字段应该是真实姓名")
    print("3. 如果 Speaker 表中没有该声纹 ID，则使用声纹 ID 作为临时名称")
    print("\n注意：")
    print("- 历史数据（如 task_295eb9a492a54181）可能仍然是声纹 ID")
    print("- 新创建的任务应该直接存储真实姓名")

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""测试说话人名称替换逻辑"""

import asyncio
from src.database.session import session_scope
from src.database.repositories import SpeakerRepository
from src.services.correction import CorrectionService
from src.core.models import TranscriptionResult, Segment

async def test_speaker_replacement():
    print("=" * 60)
    print("测试说话人名称替换")
    print("=" * 60)
    
    # 1. 创建测试 transcript
    segments = [
        Segment(
            start_time=0.0,
            end_time=5.0,
            speaker="Speaker 1",
            text="大家好，我是林煜东"
        ),
        Segment(
            start_time=5.0,
            end_time=10.0,
            speaker="Speaker 2",
            text="你好，我是蓝为一"
        ),
    ]
    
    transcript = TranscriptionResult(
        segments=segments,
        full_text="大家好，我是林煜东 你好，我是蓝为一",
        duration=10.0,
        language="zh-CN",
        provider="test"
    )
    
    print("\n1. 原始 transcript:")
    for seg in transcript.segments:
        print(f"   {seg.speaker}: {seg.text}")
    
    # 2. 第一次修正：Speaker 1 -> speaker_linyudong
    correction_service = CorrectionService()
    speaker_mapping_1 = {
        "Speaker 1": "speaker_linyudong",
        "Speaker 2": "speaker_lanweiyi"
    }
    
    transcript = await correction_service.correct_speakers(transcript, speaker_mapping_1)
    
    print("\n2. 第一次修正后 (Speaker -> speaker_id):")
    for seg in transcript.segments:
        print(f"   {seg.speaker}: {seg.text}")
    
    # 3. 从数据库获取真实姓名
    with session_scope() as session:
        speaker_repo = SpeakerRepository(session)
        speaker_ids = list(speaker_mapping_1.values())
        display_names = speaker_repo.get_display_names_batch(speaker_ids)
        
        print(f"\n3. 从数据库查询到的真实姓名:")
        for speaker_id, display_name in display_names.items():
            print(f"   {speaker_id} -> {display_name}")
        
        # 4. 第二次修正：speaker_id -> 真实姓名
        # 注意：第一次修正后，transcript 中的 speaker 已经是 speaker_id 了
        real_name_mapping = {}
        for speaker_id, display_name in display_names.items():
            real_name_mapping[speaker_id] = display_name
        
        print(f"\n4. 真实姓名映射 (修正后):")
        for k, v in real_name_mapping.items():
            print(f"   {k} -> {v}")
        
        transcript = await correction_service.correct_speakers(transcript, real_name_mapping)
        
        print("\n5. 第二次修正后 (speaker_id -> 真实姓名):")
        for seg in transcript.segments:
            print(f"   {seg.speaker}: {seg.text}")
        
        print("\n6. Full text:")
        print(f"   {transcript.full_text}")

if __name__ == "__main__":
    asyncio.run(test_speaker_replacement())

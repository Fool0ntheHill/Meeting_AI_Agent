"""
测试完整的说话人映射流程

验证:
1. 数据库中 transcript.segments 的原始状态
2. SpeakerMapping 表的映射
3. API 生成时应用映射后的结果
4. 用户修改说话人后的效果
"""

import asyncio
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy.orm import Session
from src.database.session import session_scope
from src.database.repositories import (
    TaskRepository,
    TranscriptRepository,
    SpeakerMappingRepository,
)
from src.services.correction import CorrectionService


async def test_complete_flow():
    """测试完整流程"""
    
    print("=" * 80)
    print("测试完整的说话人映射流程")
    print("=" * 80)
    
    with session_scope() as db:
        task_repo = TaskRepository(db)
        transcript_repo = TranscriptRepository(db)
        speaker_mapping_repo = SpeakerMappingRepository(db)
        
        # 1. 找一个成功的任务
        tasks = task_repo.get_by_user("user_test_user", limit=10)
        success_task = None
        for task in tasks:
            if task.state == "success":
                success_task = task
                break
        
        if not success_task:
            print("❌ 没有找到成功的任务")
            return
        
        print(f"\n✅ 找到任务: {success_task.task_id}")
        
        # 2. 查看数据库中的原始 transcript.segments
        transcript = transcript_repo.get_by_task_id(success_task.task_id)
        if not transcript:
            print("❌ 没有找到转写记录")
            return
        
        import json
        segments = json.loads(transcript.segments)
        print(f"\n📊 数据库中的原始 transcript.segments (前3个):")
        for i, seg in enumerate(segments[:3]):
            print(f"   [{i+1}] speaker='{seg['speaker']}' - {seg['text'][:50]}...")
        
        # 3. 查看 SpeakerMapping 表
        speaker_mapping = speaker_mapping_repo.get_mapping_dict(success_task.task_id)
        print(f"\n📊 SpeakerMapping 表:")
        for label, name in speaker_mapping.items():
            print(f"   {label} -> {name}")
        
        # 4. 模拟 API 生成时的流程：应用映射
        print(f"\n🔄 模拟 API 生成流程：应用说话人映射")
        transcript_result = transcript_repo.to_transcription_result(transcript)
        
        print(f"\n   应用映射前 (前3个片段):")
        for i, seg in enumerate(transcript_result.segments[:3]):
            print(f"   [{i+1}] speaker='{seg.speaker}' - {seg.text[:50]}...")
        
        if speaker_mapping:
            correction_service = CorrectionService()
            transcript_result = await correction_service.correct_speakers(
                transcript_result, speaker_mapping
            )
            
            print(f"\n   应用映射后 (前3个片段):")
            for i, seg in enumerate(transcript_result.segments[:3]):
                print(f"   [{i+1}] speaker='{seg.speaker}' - {seg.text[:50]}...")
        
        # 5. 总结
        print(f"\n" + "=" * 80)
        print("流程总结")
        print("=" * 80)
        
        # 检查数据库中的 segments 是否包含原始标签
        has_raw_labels_in_db = any(
            seg['speaker'] in ['Speaker 1', 'Speaker 2', 'Speaker 0']
            for seg in segments[:10]
        )
        
        # 检查应用映射后是否包含真实姓名
        has_real_names_after_mapping = any(
            name in seg.speaker
            for seg in transcript_result.segments[:10]
            for name in speaker_mapping.values()
        )
        
        print(f"\n✓ 数据库中存储的是原始标签: {has_raw_labels_in_db}")
        print(f"✓ 应用映射后包含真实姓名: {has_real_names_after_mapping}")
        
        if has_raw_labels_in_db and has_real_names_after_mapping:
            print(f"\n✅ 流程正确:")
            print(f"   1. 数据库存储原始标签 (Speaker 1, Speaker 2)")
            print(f"   2. SpeakerMapping 表存储映射关系")
            print(f"   3. API 生成时动态应用映射")
            print(f"   4. LLM 看到的是真实姓名")
        else:
            print(f"\n❌ 流程有问题")


if __name__ == "__main__":
    asyncio.run(test_complete_flow())

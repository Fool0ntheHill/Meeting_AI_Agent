"""
测试说话人映射和会议时间是否正确传递到 LLM 提示词

验证:
1. 说话人映射是否从数据库正确获取
2. 说话人映射是否应用到转写文本格式化
3. 会议时间是否包含在提示词中
4. LLM 看到的是真实姓名而不是 speaker1/speaker2
"""

import asyncio
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy.orm import Session
from src.database.session import session_scope
from src.database.repositories import (
    TaskRepository,
    TranscriptRepository,
    SpeakerMappingRepository,
)
from src.providers.gemini_llm import GeminiLLM
from src.config.loader import get_config


async def test_speaker_mapping_in_prompt():
    """测试说话人映射和会议时间传递"""
    
    print("=" * 80)
    print("测试说话人映射和会议时间传递到 LLM 提示词")
    print("=" * 80)
    
    # 1. 查找一个已完成的任务
    with session_scope() as db:
        task_repo = TaskRepository(db)
        transcript_repo = TranscriptRepository(db)
        speaker_mapping_repo = SpeakerMappingRepository(db)
        
        # 获取最近的一个成功任务
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
        print(f"   任务名称: {success_task.name}")
        print(f"   会议日期: {success_task.meeting_date}")
        print(f"   会议时间: {success_task.meeting_time}")
        
        # 2. 获取转写结果
        transcript = transcript_repo.get_by_task_id(success_task.task_id)
        if not transcript:
            print("❌ 没有找到转写记录")
            return
        
        transcript_result = transcript_repo.to_transcription_result(transcript)
        print(f"\n✅ 转写记录:")
        print(f"   片段数: {len(transcript_result.segments)}")
        print(f"   时长: {transcript_result.duration:.2f}秒")
        
        # 显示前3个片段的原始说话人标签
        print(f"\n   前3个片段的原始说话人标签:")
        for i, seg in enumerate(transcript_result.segments[:3]):
            print(f"   [{i+1}] {seg.speaker}: {seg.text[:50]}...")
        
        # 3. 获取说话人映射
        speaker_mapping = speaker_mapping_repo.get_mapping_dict(success_task.task_id)
        print(f"\n✅ 说话人映射:")
        for label, name in speaker_mapping.items():
            print(f"   {label} -> {name}")
        
        if not speaker_mapping:
            print("   ⚠️  没有说话人映射")
        
        # 4. 测试格式化转写文本（不带映射）
        config = get_config()
        llm = GeminiLLM(config.gemini)
        
        print(f"\n" + "=" * 80)
        print("测试 1: 格式化转写文本（不带说话人映射）")
        print("=" * 80)
        formatted_without_mapping = llm.format_transcript(transcript_result)
        print(f"\n前500个字符:")
        print(formatted_without_mapping[:500])
        
        # 5. 测试格式化转写文本（带映射）
        print(f"\n" + "=" * 80)
        print("测试 2: 格式化转写文本（带说话人映射）")
        print("=" * 80)
        formatted_with_mapping = llm.format_transcript(transcript_result, speaker_mapping)
        print(f"\n前500个字符:")
        print(formatted_with_mapping[:500])
        
        # 6. 对比差异
        print(f"\n" + "=" * 80)
        print("对比分析")
        print("=" * 80)
        
        # 检查是否包含原始标签
        has_raw_labels = any(label in formatted_with_mapping for label in speaker_mapping.keys())
        print(f"\n✓ 是否包含原始标签 (speaker1, speaker2): {has_raw_labels}")
        if has_raw_labels:
            print("   ❌ 错误: 格式化后的文本仍包含原始标签")
        else:
            print("   ✅ 正确: 原始标签已被替换")
        
        # 检查是否包含真实姓名
        has_real_names = any(name in formatted_with_mapping for name in speaker_mapping.values())
        print(f"\n✓ 是否包含真实姓名: {has_real_names}")
        if has_real_names:
            print("   ✅ 正确: 包含真实姓名")
            for name in speaker_mapping.values():
                if name in formatted_with_mapping:
                    count = formatted_with_mapping.count(f"[{name}]")
                    print(f"   - {name}: 出现 {count} 次")
        else:
            print("   ❌ 错误: 没有找到真实姓名")
        
        # 7. 测试会议时间格式化
        print(f"\n" + "=" * 80)
        print("测试 3: 会议时间格式化")
        print("=" * 80)
        
        from src.utils.meeting_metadata import format_meeting_datetime
        datetime_str = format_meeting_datetime(success_task.meeting_date, success_task.meeting_time)
        print(f"\n会议时间字符串: {datetime_str}")
        
        if datetime_str:
            print("   ✅ 会议时间格式化成功")
        else:
            print("   ⚠️  会议时间为空")
        
        # 8. 总结
        print(f"\n" + "=" * 80)
        print("测试总结")
        print("=" * 80)
        
        issues = []
        
        if not speaker_mapping:
            issues.append("没有说话人映射数据")
        
        if has_raw_labels:
            issues.append("格式化后仍包含原始标签 (speaker1, speaker2)")
        
        if not has_real_names:
            issues.append("格式化后没有真实姓名")
        
        if not datetime_str:
            issues.append("会议时间为空")
        
        if issues:
            print("\n❌ 发现问题:")
            for issue in issues:
                print(f"   - {issue}")
        else:
            print("\n✅ 所有检查通过!")
            print("   - 说话人映射正确应用")
            print("   - 会议时间正确格式化")
            print("   - LLM 将看到真实姓名而不是 speaker1/speaker2")


if __name__ == "__main__":
    asyncio.run(test_speaker_mapping_in_prompt())

"""检查任务配置和进度历史"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.database.session import session_scope
from src.database.repositories import TaskRepository


def check_task(task_id: str):
    print("=" * 80)
    print(f"任务配置检查: {task_id}")
    print("=" * 80)
    
    with session_scope() as db:
        repo = TaskRepository(db)
        task = repo.get_by_id(task_id)
        
        if not task:
            print(f"✗ 任务不存在: {task_id}")
            return
        
        print(f"\n任务配置:")
        print(f"  meeting_type: {task.meeting_type}")
        print(f"  skip_speaker_recognition: {task.skip_speaker_recognition}")
        print(f"  asr_language: {task.asr_language}")
        print(f"  output_language: {task.output_language}")
        print(f"  hotword_set_id: {task.hotword_set_id}")
        
        print(f"\n当前状态:")
        print(f"  state: {task.state}")
        print(f"  progress: {task.progress}%")
        print(f"  estimated_time: {task.estimated_time}s")
        print(f"  created_at: {task.created_at}")
        print(f"  updated_at: {task.updated_at}")
        if task.completed_at:
            print(f"  completed_at: {task.completed_at}")
            duration = (task.completed_at - task.created_at).total_seconds()
            print(f"  总耗时: {duration:.1f}秒")
        
        # 分析跳过的阶段
        print(f"\n预期进度:")
        if task.skip_speaker_recognition:
            print("  ⚠️  跳过说话人识别")
            print("  0% → 40% (转写) → 70% (生成) → 100% (完成)")
        else:
            print("  0% → 40% (转写) → 60% (识别) → 70% (修正/生成) → 100% (完成)")
        
        # 检查说话人映射
        from src.database.repositories import SpeakerMappingRepository
        mapping_repo = SpeakerMappingRepository(db)
        mappings = mapping_repo.get_by_task_id(task_id)
        
        if mappings:
            print(f"\n说话人映射: ({len(mappings)} 个)")
            for m in mappings:
                print(f"  {m.speaker_label} → {m.speaker_name}")
        else:
            print(f"\n说话人映射: 无")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("使用方法: python scripts/check_task_config.py <task_id>")
        sys.exit(1)
    
    check_task(sys.argv[1])

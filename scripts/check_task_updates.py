"""检查任务的所有状态更新记录"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.database.session import session_scope
from src.database.repositories import TaskRepository

def check_task_updates(task_id: str):
    print(f"检查任务 {task_id} 的状态更新...")
    print("=" * 80)
    
    with session_scope() as db:
        task_repo = TaskRepository(db)
        task = task_repo.get_by_id(task_id)
        
        if not task:
            print(f"❌ 任务不存在: {task_id}")
            return
        
        print(f"\n任务信息:")
        print(f"  task_id: {task.task_id}")
        print(f"  state: {task.state}")
        print(f"  progress: {task.progress}%")
        print(f"  estimated_time: {task.estimated_time}s")
        print(f"  skip_speaker_recognition: {task.skip_speaker_recognition}")
        print(f"  created_at: {task.created_at}")
        print(f"  updated_at: {task.updated_at}")
        print(f"  completed_at: {task.completed_at}")
        
        # 计算总耗时
        if task.completed_at and task.created_at:
            duration = (task.completed_at - task.created_at).total_seconds()
            print(f"  总耗时: {duration:.1f}秒")
        
        # 检查说话人映射
        from src.database.repositories import SpeakerMappingRepository
        mapping_repo = SpeakerMappingRepository(db)
        mappings = mapping_repo.get_by_task_id(task_id)
        
        print(f"\n说话人映射: ({len(mappings)} 个)")
        for m in mappings:
            print(f"  {m.speaker_label} → {m.speaker_name} (speaker_id={m.speaker_id})")
        
        # 检查转写记录
        from src.database.repositories import TranscriptRepository
        transcript_repo = TranscriptRepository(db)
        transcript = transcript_repo.get_by_task_id(task_id)
        
        if transcript:
            print(f"\n转写记录:")
            print(f"  duration: {transcript.duration}s")
            print(f"  segments: {len(transcript.get_segments_list())} 个")
            print(f"  provider: {transcript.provider}")
        
        # 检查生成的 artifact
        from src.database.repositories import ArtifactRepository
        artifact_repo = ArtifactRepository(db)
        artifacts = artifact_repo.get_by_task_id(task_id)
        
        print(f"\n生成的 Artifacts: ({len(artifacts)} 个)")
        for a in artifacts:
            print(f"  {a.artifact_id} - version {a.version} - {a.artifact_type}")
            print(f"    created_at: {a.created_at}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/check_task_updates.py <task_id>")
        sys.exit(1)
    
    task_id = sys.argv[1]
    check_task_updates(task_id)

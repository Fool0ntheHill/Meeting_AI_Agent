#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
检查数据库中的任务
"""

import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.api.dependencies import get_db
from src.database.repositories import TaskRepository, TranscriptRepository, ArtifactRepository


def check_task(task_id: str):
    """检查任务是否存在"""
    print("=" * 80)
    print(f"  检查任务: {task_id}")
    print("=" * 80)
    print()
    
    db = next(get_db())
    
    try:
        task_repo = TaskRepository(db)
        transcript_repo = TranscriptRepository(db)
        artifact_repo = ArtifactRepository(db)
        
        # 1. 检查任务
        print("1. 检查任务...")
        task = task_repo.get_by_id(task_id)
        if task:
            print(f"   ✅ 任务存在")
            print(f"   - 任务 ID: {task.task_id}")
            print(f"   - 用户 ID: {task.user_id}")
            print(f"   - 租户 ID: {task.tenant_id}")
            print(f"   - 状态: {task.state}")
            print(f"   - 会议类型: {task.meeting_type}")
            print(f"   - 创建时间: {task.created_at}")
            print(f"   - 更新时间: {task.updated_at}")
            if task.completed_at:
                print(f"   - 完成时间: {task.completed_at}")
        else:
            print(f"   ❌ 任务不存在")
            return False
        
        print()
        
        # 2. 检查转写记录
        print("2. 检查转写记录...")
        transcript = transcript_repo.get_by_task_id(task_id)
        if transcript:
            print(f"   ✅ 找到转写记录")
            print(f"   - ID: {transcript.transcript_id}")
            print(f"   - 时长: {transcript.duration} 秒")
            print(f"   - 语言: {transcript.language}")
            print(f"   - 提供商: {transcript.provider}")
            
            # segments 可能是字符串或列表
            if isinstance(transcript.segments, str):
                import json
                segments = json.loads(transcript.segments)
                print(f"   - 片段数: {len(segments)}")
                if segments:
                    print(f"   - 第一个片段: {segments[0].get('text', '')[:50]}...")
            elif isinstance(transcript.segments, list):
                print(f"   - 片段数: {len(transcript.segments)}")
                if transcript.segments:
                    seg = transcript.segments[0]
                    text = seg.text if hasattr(seg, 'text') else seg.get('text', '')
                    print(f"   - 第一个片段: {text[:50]}...")
            else:
                print(f"   - 片段数: 未知格式")
        else:
            print(f"   ⚠️  未找到转写记录")
        
        print()
        
        # 3. 检查衍生内容
        print("3. 检查衍生内容...")
        artifacts = artifact_repo.get_by_task_id(task_id)
        if artifacts:
            artifact_count = len(artifacts) if isinstance(artifacts, list) else 1
            print(f"   ✅ 找到 {artifact_count} 个衍生内容")
            
            artifacts_list = artifacts if isinstance(artifacts, list) else [artifacts]
            for i, artifact in enumerate(artifacts_list, 1):
                print(f"   衍生内容 {i}:")
                print(f"   - ID: {artifact.artifact_id}")
                print(f"   - 类型: {artifact.artifact_type}")
                print(f"   - 版本: {artifact.version}")
                print(f"   - 创建者: {artifact.created_by}")
                print(f"   - 创建时间: {artifact.created_at}")
        else:
            print(f"   ⚠️  未找到衍生内容")
        
        print()
        print("=" * 80)
        print("  ✅ 检查完成")
        print("=" * 80)
        
        return True
        
    except Exception as e:
        print(f"\n❌ 检查失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()


if __name__ == "__main__":
    if len(sys.argv) > 1:
        task_id = sys.argv[1]
    else:
        task_id = "task_completed_a8232248"  # 默认使用最近创建的任务 ID
    
    check_task(task_id)

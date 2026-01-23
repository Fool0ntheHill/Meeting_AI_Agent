"""
检查任务的提示词和 artifact

查看任务使用的 prompt_instance 和生成的 artifact 内容
"""

import asyncio
import sys
import json
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.database.session import get_session
from src.database.repositories import TaskRepository, ArtifactRepository
from sqlalchemy import text


async def check_task_prompt(task_id: str):
    """检查任务的提示词"""
    
    print("=" * 80)
    print(f"检查任务: {task_id}")
    print("=" * 80)
    
    with get_session() as session:
        task_repo = TaskRepository(session)
        artifact_repo = ArtifactRepository(session)
        
        # 获取任务
        task = task_repo.get_by_id(task_id)
        if not task:
            print(f"✗ 任务不存在: {task_id}")
            return
        
        print(f"\n【任务基本信息】")
        print(f"  任务 ID: {task.task_id}")
        print(f"  状态: {task.state}")
        print(f"  用户 ID: {task.user_id}")
        print(f"  创建时间: {task.created_at}")
        print(f"  会议类型: {task.meeting_type}")
        
        # 获取 artifacts
        print(f"\n【Artifacts】")
        artifacts = artifact_repo.get_by_task_id(task_id)
        
        if not artifacts:
            print(f"  (无 artifacts)")
            return
        
        print(f"  找到 {len(artifacts)} 个 artifacts:")
        
        for artifact in artifacts:
            print(f"\n  --- Artifact {artifact.artifact_id} ---")
            print(f"  类型: {artifact.artifact_type}")
            print(f"  版本: {artifact.version}")
            print(f"  创建时间: {artifact.created_at}")
            print(f"  内容长度: {len(artifact.content)} 字符")
            
            # 显示内容预览
            print(f"\n  【内容预览】")
            print("  " + "-" * 76)
            content_lines = artifact.content.split('\n')
            for i, line in enumerate(content_lines[:30]):  # 显示前30行
                print(f"  {line}")
            if len(content_lines) > 30:
                print(f"  ... (还有 {len(content_lines) - 30} 行)")
            print("  " + "-" * 76)
            
            # 检查是否包含默认提示词的特征
            print(f"\n  【提示词分析】")
            default_keywords = [
                "会议纪要",
                "会议主题",
                "参会人员",
                "讨论要点",
                "决策事项",
                "待办事项",
                "行动计划"
            ]
            
            found_keywords = []
            for keyword in default_keywords:
                if keyword in artifact.content:
                    found_keywords.append(keyword)
            
            if found_keywords:
                print(f"  包含默认提示词关键词: {', '.join(found_keywords)}")
            else:
                print(f"  未检测到默认提示词关键词")
            
            # 检查是否有自定义内容的特征
            if "产品" in artifact.content or "业务规则" in artifact.content:
                print(f"  ✓ 包含会议特定内容（产品、业务规则等）")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("用法: python scripts/check_task_prompt.py <task_id>")
        print("示例: python scripts/check_task_prompt.py task_710ea9f754f046c3")
        sys.exit(1)
    
    task_id = sys.argv[1]
    asyncio.run(check_task_prompt(task_id))

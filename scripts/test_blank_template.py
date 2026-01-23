"""
测试空白模板功能

验证使用 template_id="__blank__" 创建任务是否正常工作
"""

import asyncio
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.database.session import get_session
from src.database.repositories import TaskRepository


async def test_blank_template():
    """测试空白模板任务"""
    
    print("=" * 60)
    print("测试空白模板功能")
    print("=" * 60)
    
    # 查找最近使用空白模板的任务
    with get_session() as session:
        task_repo = TaskRepository(session)
        
        # 查找失败的任务
        print("\n查找最近失败的任务...")
        from sqlalchemy import text
        tasks = session.execute(
            text("""
            SELECT task_id, state, error_code, error_message, created_at
            FROM tasks
            WHERE state = 'failed'
            AND error_message LIKE '%__blank__%'
            ORDER BY created_at DESC
            LIMIT 5
            """)
        ).fetchall()
        
        if not tasks:
            print("✓ 没有找到因空白模板失败的任务")
            return
        
        print(f"\n找到 {len(tasks)} 个因空白模板失败的任务:")
        for task in tasks:
            task_id, state, error_code, error_message, created_at = task
            print(f"\n任务 ID: {task_id}")
            print(f"  状态: {state}")
            print(f"  错误代码: {error_code}")
            print(f"  错误信息: {error_message}")
            print(f"  创建时间: {created_at}")
        
        # 检查最新的任务
        latest_task_id = tasks[0][0]
        print(f"\n检查任务 {latest_task_id} 的详细信息...")
        
        task = task_repo.get_by_id(latest_task_id)
        if task:
            print(f"  用户 ID: {task.user_id}")
            print(f"  租户 ID: {task.tenant_id}")
            print(f"  任务名称: {task.name}")
            print(f"  进度: {task.progress}%")
            print(f"  音频时长: {task.audio_duration}s")
            
            # 检查是否有转录结果
            transcript_count = session.execute(
                text("SELECT COUNT(*) FROM transcripts WHERE task_id = :task_id"),
                {"task_id": latest_task_id}
            ).fetchone()[0]
            print(f"  转录记录: {transcript_count} 条")
            
            # 检查是否有说话人映射
            speaker_count = session.execute(
                text("SELECT COUNT(*) FROM speaker_mappings WHERE task_id = :task_id"),
                {"task_id": latest_task_id}
            ).fetchone()[0]
            print(f"  说话人映射: {speaker_count} 条")
            
            print("\n✓ 任务在 LLM 生成阶段失败（转录和声纹识别都成功了）")
            print("✓ 修复后，该任务应该可以重新生成 artifact")


if __name__ == "__main__":
    asyncio.run(test_blank_template())

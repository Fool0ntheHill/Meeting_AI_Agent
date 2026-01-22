"""重新生成指定任务的 artifact"""

import sys
import sqlite3
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def regenerate_artifact(task_id: str):
    """删除任务的 artifact，让系统重新生成"""
    db_path = project_root / "meeting_agent.db"
    
    if not db_path.exists():
        print(f"❌ 数据库文件不存在: {db_path}")
        return
    
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    # 检查任务是否存在
    cursor.execute("SELECT task_id, state FROM tasks WHERE task_id = ?", (task_id,))
    row = cursor.fetchone()
    
    if not row:
        print(f"❌ 任务不存在: {task_id}")
        conn.close()
        return
    
    task_id, state = row
    print(f"任务 ID: {task_id}")
    print(f"任务状态: {state}")
    
    # 查询现有的 artifacts
    cursor.execute("""
        SELECT artifact_id, artifact_type, created_at
        FROM generated_artifacts
        WHERE task_id = ?
        ORDER BY created_at DESC
    """, (task_id,))
    
    artifacts = cursor.fetchall()
    
    if not artifacts:
        print(f"\n⚠ 该任务没有 artifacts")
        conn.close()
        return
    
    print(f"\n找到 {len(artifacts)} 个 artifacts:")
    for artifact_id, artifact_type, created_at in artifacts:
        print(f"  - {artifact_id} ({artifact_type}) - {created_at}")
    
    # 确认删除
    print(f"\n⚠ 警告：这将删除所有 artifacts，需要重新运行 worker 来生成")
    confirm = input("确认删除？(yes/no): ").strip().lower()
    
    if confirm != "yes":
        print("\n已取消操作")
        conn.close()
        return
    
    # 删除 artifacts
    cursor.execute("DELETE FROM generated_artifacts WHERE task_id = ?", (task_id,))
    deleted_count = cursor.rowcount
    
    # 将任务状态改回 processing，让 worker 重新生成
    cursor.execute("""
        UPDATE tasks
        SET state = 'processing', progress = 0.5
        WHERE task_id = ?
    """, (task_id,))
    
    conn.commit()
    conn.close()
    
    print(f"\n✓ 已删除 {deleted_count} 个 artifacts")
    print(f"✓ 任务状态已改为 'processing'")
    print(f"\n请确保 worker 正在运行，它会自动重新生成 artifacts")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        task_id = sys.argv[1]
    else:
        task_id = input("请输入任务 ID: ").strip()
    
    if task_id:
        regenerate_artifact(task_id)
    else:
        print("❌ 请提供任务 ID")

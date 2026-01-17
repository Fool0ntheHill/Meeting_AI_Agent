# -*- coding: utf-8 -*-
"""更新数据库中的文件路径为 TOS URL

使用方法:
    python scripts/update_file_paths_in_db.py \
        --db postgresql://user:pass@host:5432/dbname \
        --tos-base https://your-bucket.tos-cn-beijing.volces.com \
        --dry-run

注意:
    1. 确保数据库已备份
    2. 建议先使用 --dry-run 演练
    3. 只更新以 "uploads/" 开头的本地路径
"""

import argparse
import sys
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.database.models import Task
from src.utils.logger import get_logger

logger = get_logger(__name__)


def update_task_file_paths(
    session,
    tos_base_url: str,
    dry_run: bool = False,
) -> int:
    """
    更新任务表中的文件路径
    
    Args:
        session: 数据库会话
        tos_base_url: TOS 基础 URL
        dry_run: 是否为演练模式
    
    Returns:
        更新的任务数
    """
    tasks = session.query(Task).all()
    updated_count = 0
    
    for task in tasks:
        # 解析 audio_files JSON
        audio_files = task.get_audio_files_list()
        
        # 检查是否需要更新
        needs_update = False
        updated_files = []
        
        for file_path in audio_files:
            # 只更新本地路径
            if file_path.startswith("uploads/"):
                # 转换为 TOS URL
                tos_url = f"{tos_base_url}/{file_path}"
                updated_files.append(tos_url)
                needs_update = True
                
                if dry_run:
                    print(f"  [演练] {task.task_id}: {file_path} -> {tos_url}")
                else:
                    print(f"  ✅ {task.task_id}: {file_path} -> {tos_url}")
            else:
                # 保持原样（可能已经是 URL）
                updated_files.append(file_path)
        
        # 更新
        if needs_update:
            if not dry_run:
                task.set_audio_files_list(updated_files)
            updated_count += 1
    
    if not dry_run:
        session.commit()
    
    return updated_count


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="更新数据库文件路径工具")
    parser.add_argument(
        "--db",
        required=True,
        help="数据库连接字符串（如: postgresql://user:pass@host:5432/dbname）",
    )
    parser.add_argument(
        "--tos-base",
        required=True,
        help="TOS 基础 URL（如: https://your-bucket.tos-cn-beijing.volces.com）",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="演练模式，不实际更新",
    )
    
    args = parser.parse_args()
    
    # 移除末尾的斜杠
    tos_base_url = args.tos_base.rstrip("/")
    
    print("=" * 60)
    print("更新数据库文件路径工具")
    print("=" * 60)
    print(f"数据库: {args.db}")
    print(f"TOS 基础 URL: {tos_base_url}")
    print(f"演练模式: {'是' if args.dry_run else '否'}")
    print("=" * 60)
    
    # 确认
    if not args.dry_run:
        confirm = input("\n⚠️  确认开始更新？这将修改数据库！(yes/no): ")
        if confirm.lower() != "yes":
            print("已取消")
            sys.exit(0)
    
    try:
        # 连接数据库
        print("\n📡 连接数据库...")
        engine = create_engine(args.db)
        Session = sessionmaker(bind=engine)
        session = Session()
        
        print("✅ 数据库连接成功")
        
        # 更新路径
        print("\n📦 开始更新文件路径...")
        updated_count = update_task_file_paths(session, tos_base_url, args.dry_run)
        
        # 完成
        print("\n" + "=" * 60)
        if args.dry_run:
            print(f"✅ 演练完成！共 {updated_count} 个任务需要更新")
            print("   使用 --dry-run=false 执行实际更新")
        else:
            print(f"✅ 更新完成！共更新 {updated_count} 个任务")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ 更新失败: {e}")
        logger.exception("Update failed")
        sys.exit(1)
    
    finally:
        # 关闭连接
        try:
            session.close()
        except:
            pass


if __name__ == "__main__":
    main()

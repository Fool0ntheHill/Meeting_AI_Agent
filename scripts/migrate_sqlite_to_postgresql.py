#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""将 SQLite 数据迁移到 PostgreSQL"""

import sys
from pathlib import Path
from datetime import datetime

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import create_engine, text, inspect
from sqlalchemy.orm import sessionmaker
from src.database.models import Base, Task, TranscriptRecord, SpeakerMapping, PromptTemplate, Folder
from src.utils.logger import get_logger

logger = get_logger(__name__)


def migrate_data(sqlite_url: str, postgresql_url: str, skip_existing: bool = True):
    """
    迁移数据从 SQLite 到 PostgreSQL
    
    Args:
        sqlite_url: SQLite 数据库 URL
        postgresql_url: PostgreSQL 数据库 URL
        skip_existing: 是否跳过已存在的记录
    """
    print("=" * 80)
    print("SQLite → PostgreSQL 数据迁移")
    print("=" * 80)
    print()
    
    # 创建引擎
    print("[1/7] 连接数据库...")
    try:
        sqlite_engine = create_engine(sqlite_url, echo=False)
        postgresql_engine = create_engine(postgresql_url, echo=False)
        print("✓ 数据库连接成功")
        print(f"  - 源数据库: {sqlite_url}")
        print(f"  - 目标数据库: {postgresql_url.split('@')[-1]}")
    except Exception as e:
        print(f"✗ 数据库连接失败: {e}")
        return False
    print()
    
    # 创建会话
    SQLiteSession = sessionmaker(bind=sqlite_engine)
    PostgreSQLSession = sessionmaker(bind=postgresql_engine)
    
    sqlite_session = SQLiteSession()
    postgresql_session = PostgreSQLSession()
    
    try:
        # 检查源数据库表
        print("[2/7] 检查源数据库...")
        inspector = inspect(sqlite_engine)
        tables = inspector.get_table_names()
        print(f"✓ 找到 {len(tables)} 个表: {', '.join(tables)}")
        print()
        
        # 创建目标数据库表结构
        print("[3/7] 创建目标数据库表结构...")
        Base.metadata.create_all(bind=postgresql_engine)
        print("✓ 表结构创建成功")
        print()
        
        # 迁移 folders 表
        if "folders" in tables:
            print("[4/7] 迁移 folders 表...")
            folders = sqlite_session.query(Folder).all()
            migrated = 0
            skipped = 0
            
            for folder in folders:
                if skip_existing:
                    existing = postgresql_session.query(Folder).filter_by(folder_id=folder.folder_id).first()
                    if existing:
                        skipped += 1
                        continue
                
                # 创建新对象（避免 session 冲突）
                new_folder = Folder(
                    folder_id=folder.folder_id,
                    user_id=folder.user_id,
                    tenant_id=folder.tenant_id,
                    name=folder.name,
                    parent_id=folder.parent_id,
                    created_at=folder.created_at,
                    updated_at=folder.updated_at,
                )
                postgresql_session.add(new_folder)
                migrated += 1
            
            postgresql_session.commit()
            print(f"✓ 迁移 {migrated} 个文件夹 (跳过 {skipped} 个)")
        else:
            print("[4/7] 跳过 folders 表 (不存在)")
        print()
        
        # 迁移 tasks 表
        print("[5/7] 迁移 tasks 表...")
        tasks = sqlite_session.query(Task).all()
        migrated = 0
        skipped = 0
        
        for task in tasks:
            if skip_existing:
                existing = postgresql_session.query(Task).filter_by(task_id=task.task_id).first()
                if existing:
                    skipped += 1
                    continue
            
            # 创建新对象
            new_task = Task(
                task_id=task.task_id,
                user_id=task.user_id,
                tenant_id=task.tenant_id,
                task_name=task.task_name,
                audio_file_path=task.audio_file_path,
                audio_duration=task.audio_duration,
                asr_provider=task.asr_provider,
                asr_language=task.asr_language,
                enable_speaker_recognition=task.enable_speaker_recognition,
                state=task.state,
                progress=task.progress,
                created_at=task.created_at,
                updated_at=task.updated_at,
                started_at=task.started_at,
                completed_at=task.completed_at,
                error_code=task.error_code,
                error_message=task.error_message,
                error_details=task.error_details,
                retryable=task.retryable,
                folder_id=task.folder_id,
                is_deleted=task.is_deleted,
                deleted_at=task.deleted_at,
                meeting_date=task.meeting_date,
                meeting_location=task.meeting_location,
                meeting_participants=task.meeting_participants,
                content_modified_at=task.content_modified_at,
            )
            postgresql_session.add(new_task)
            migrated += 1
        
        postgresql_session.commit()
        print(f"✓ 迁移 {migrated} 个任务 (跳过 {skipped} 个)")
        print()
        
        # 迁移 transcript_records 表
        if "transcript_records" in tables:
            print("[6/7] 迁移 transcript_records 表...")
            records = sqlite_session.query(TranscriptRecord).all()
            migrated = 0
            skipped = 0
            
            for record in records:
                if skip_existing:
                    existing = postgresql_session.query(TranscriptRecord).filter_by(
                        task_id=record.task_id,
                        segment_index=record.segment_index
                    ).first()
                    if existing:
                        skipped += 1
                        continue
                
                new_record = TranscriptRecord(
                    task_id=record.task_id,
                    segment_index=record.segment_index,
                    start_time=record.start_time,
                    end_time=record.end_time,
                    text=record.text,
                    speaker_id=record.speaker_id,
                    confidence=record.confidence,
                )
                postgresql_session.add(new_record)
                migrated += 1
            
            postgresql_session.commit()
            print(f"✓ 迁移 {migrated} 个转写记录 (跳过 {skipped} 个)")
        else:
            print("[6/7] 跳过 transcript_records 表 (不存在)")
        print()
        
        # 迁移 speaker_mappings 表
        if "speaker_mappings" in tables:
            print("[7/7] 迁移 speaker_mappings 表...")
            mappings = sqlite_session.query(SpeakerMapping).all()
            migrated = 0
            skipped = 0
            
            for mapping in mappings:
                if skip_existing:
                    existing = postgresql_session.query(SpeakerMapping).filter_by(
                        task_id=mapping.task_id,
                        speaker_id=mapping.speaker_id
                    ).first()
                    if existing:
                        skipped += 1
                        continue
                
                new_mapping = SpeakerMapping(
                    task_id=mapping.task_id,
                    speaker_id=mapping.speaker_id,
                    speaker_name=mapping.speaker_name,
                    created_at=mapping.created_at,
                    updated_at=mapping.updated_at,
                )
                postgresql_session.add(new_mapping)
                migrated += 1
            
            postgresql_session.commit()
            print(f"✓ 迁移 {migrated} 个说话人映射 (跳过 {skipped} 个)")
        else:
            print("[7/7] 跳过 speaker_mappings 表 (不存在)")
        print()
        
        # 验证迁移结果
        print("=" * 80)
        print("迁移结果验证:")
        print("=" * 80)
        
        if "folders" in tables:
            sqlite_folder_count = sqlite_session.query(Folder).count()
            postgresql_folder_count = postgresql_session.query(Folder).count()
            print(f"Folders: {sqlite_folder_count} (源) → {postgresql_folder_count} (目标)")
        
        sqlite_task_count = sqlite_session.query(Task).count()
        postgresql_task_count = postgresql_session.query(Task).count()
        print(f"Tasks: {sqlite_task_count} (源) → {postgresql_task_count} (目标)")
        
        if "transcript_records" in tables:
            sqlite_record_count = sqlite_session.query(TranscriptRecord).count()
            postgresql_record_count = postgresql_session.query(TranscriptRecord).count()
            print(f"Transcript Records: {sqlite_record_count} (源) → {postgresql_record_count} (目标)")
        
        if "speaker_mappings" in tables:
            sqlite_mapping_count = sqlite_session.query(SpeakerMapping).count()
            postgresql_mapping_count = postgresql_session.query(SpeakerMapping).count()
            print(f"Speaker Mappings: {sqlite_mapping_count} (源) → {postgresql_mapping_count} (目标)")
        
        print()
        print("=" * 80)
        print("✓ 数据迁移完成！")
        print("=" * 80)
        
        return True
        
    except Exception as e:
        print(f"✗ 迁移失败: {e}")
        postgresql_session.rollback()
        return False
        
    finally:
        sqlite_session.close()
        postgresql_session.close()


def main():
    """主函数"""
    import os
    import argparse
    
    parser = argparse.ArgumentParser(description="迁移 SQLite 数据到 PostgreSQL")
    parser.add_argument(
        "--sqlite",
        default="sqlite:///./meeting_agent.db",
        help="SQLite 数据库 URL (默认: sqlite:///./meeting_agent.db)"
    )
    parser.add_argument(
        "--postgresql",
        help="PostgreSQL 数据库 URL (例如: postgresql://user:pass@localhost/dbname)"
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="覆盖已存在的记录 (默认: 跳过)"
    )
    
    args = parser.parse_args()
    
    # 如果没有指定 PostgreSQL URL，从环境变量读取
    if not args.postgresql:
        db_host = os.getenv("DB_HOST", "localhost")
        db_port = os.getenv("DB_PORT", "5432")
        db_name = os.getenv("DB_NAME", "meeting_agent")
        db_user = os.getenv("DB_USER", "meeting_user")
        db_password = os.getenv("DB_PASSWORD", "")
        
        if not db_password:
            print("错误: 请指定 --postgresql 参数或设置 DB_PASSWORD 环境变量")
            print()
            print("示例 1 (使用参数):")
            print("  python scripts/migrate_sqlite_to_postgresql.py \\")
            print("    --postgresql postgresql://user:pass@localhost/meeting_agent")
            print()
            print("示例 2 (使用环境变量):")
            print("  export DB_PASSWORD=your_password")
            print("  python scripts/migrate_sqlite_to_postgresql.py")
            sys.exit(1)
        
        args.postgresql = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
    
    print()
    print("警告: 此操作将把 SQLite 数据迁移到 PostgreSQL")
    print(f"源数据库: {args.sqlite}")
    print(f"目标数据库: {args.postgresql.split('@')[-1]}")
    print()
    
    response = input("确认继续? (yes/no): ")
    if response.lower() != "yes":
        print("已取消")
        sys.exit(0)
    
    print()
    
    # 执行迁移
    success = migrate_data(
        args.sqlite,
        args.postgresql,
        skip_existing=not args.overwrite
    )
    
    if not success:
        print()
        print("迁移失败，请检查错误信息")
        sys.exit(1)
    
    print()
    print("下一步:")
    print("1. 更新 config/development.yaml 中的数据库配置")
    print("2. 重启后端服务: python main.py")
    print("3. 重启 Worker: python worker.py")
    print("4. 验证系统功能正常")


if __name__ == "__main__":
    main()

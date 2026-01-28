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
from sqlalchemy.inspection import inspect as sa_inspect
from sqlalchemy.orm import sessionmaker
from src.database.models import (
    Base,
    AuditLogRecord,
    Folder,
    GeneratedArtifactRecord,
    HotwordSetRecord,
    PromptTemplateRecord,
    Speaker,
    SpeakerMapping,
    Task,
    TranscriptRecord,
    User,
)
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
        print("[OK] 数据库连接成功")
        print(f"  - 源数据库: {sqlite_url}")
        print(f"  - 目标数据库: {postgresql_url.split('@')[-1]}")
    except Exception as e:
        print(f"[FAIL] 数据库连接失败: {e}")
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
        print(f"[OK] 找到 {len(tables)} 个表: {', '.join(tables)}")
        print()
        
        # 创建目标数据库表结构
        print("[3/7] 创建目标数据库表结构...")
        Base.metadata.create_all(bind=postgresql_engine)
        print("[OK] 表结构创建成功")
        print()
        
        migrations = [
            ("users", User),
            ("folders", Folder),
            ("speakers", Speaker),
            ("tasks", Task),
            ("transcripts", TranscriptRecord),
            ("speaker_mappings", SpeakerMapping),
            ("prompt_templates", PromptTemplateRecord),
            ("generated_artifacts", GeneratedArtifactRecord),
            ("hotword_sets", HotwordSetRecord),
            ("audit_logs", AuditLogRecord),
        ]
        total_steps = 3 + len(migrations)
        step_offset = 3
        
        for index, (table_name, model_cls) in enumerate(migrations, start=1):
            step_number = step_offset + index
            if table_name not in tables:
                print(f"[{step_number}/{total_steps}] 跳过 {table_name} 表 (不存在)")
                print()
                continue
            
            print(f"[{step_number}/{total_steps}] 迁移 {table_name} 表...")
            records = sqlite_session.query(model_cls).all()
            migrated = 0
            skipped = 0
            
            pk_columns = sa_inspect(model_cls).primary_key
            column_attrs = sa_inspect(model_cls).mapper.column_attrs
            
            for record in records:
                if skip_existing:
                    pk_filter = {col.key: getattr(record, col.key) for col in pk_columns}
                    existing = postgresql_session.query(model_cls).filter_by(**pk_filter).first()
                    if existing:
                        skipped += 1
                        continue
                
                data = {col.key: getattr(record, col.key) for col in column_attrs}
                new_record = model_cls(**data)
                postgresql_session.add(new_record)
                migrated += 1
            
            postgresql_session.commit()
            print(f"[OK] 迁移 {migrated} 条记录 (跳过 {skipped} 条)")
            print()
        
        # 验证迁移结果
        print("=" * 80)
        print("迁移结果验证:")
        print("=" * 80)
        
        for table_name, model_cls in migrations:
            if table_name not in tables:
                continue
            sqlite_count = sqlite_session.query(model_cls).count()
            postgresql_count = postgresql_session.query(model_cls).count()
            print(f"{table_name}: {sqlite_count} (源) → {postgresql_count} (目标)")
        
        print()
        print("=" * 80)
        print("[OK] 数据迁移完成！")
        print("=" * 80)
        
        return True
        
    except Exception as e:
        print(f"[FAIL] 迁移失败: {e}")
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

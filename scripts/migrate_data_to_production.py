# -*- coding: utf-8 -*-
"""将开发环境数据迁移到生产环境

使用方法:
    python scripts/migrate_data_to_production.py \
        --source sqlite:///./meeting_agent.db \
        --target postgresql://user:pass@host:5432/dbname

注意:
    1. 确保目标数据库已创建表结构
    2. 建议先在测试环境验证
    3. 迁移前备份数据
"""

import argparse
import sys
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.database.models import (
    Base,
    User,
    Task,
    TranscriptRecord,
    SpeakerMapping,
    GeneratedArtifactRecord,
    PromptTemplateRecord,
    HotwordSetRecord,
    AuditLogRecord,
)


def migrate_table(model_class, source_session, target_session, dry_run=False):
    """
    迁移单个表
    
    Args:
        model_class: 模型类
        source_session: 源数据库会话
        target_session: 目标数据库会话
        dry_run: 是否为演练模式
    
    Returns:
        int: 迁移的记录数
    """
    table_name = model_class.__tablename__
    
    try:
        # 查询所有记录
        records = source_session.query(model_class).all()
        count = len(records)
        
        if count == 0:
            print(f"  ⚠️  {table_name}: 无数据")
            return 0
        
        if dry_run:
            print(f"  📋 {table_name}: {count} 条记录（演练模式，不实际迁移）")
            return count
        
        # 迁移记录
        for record in records:
            # 使用 merge 避免主键冲突
            target_session.merge(record)
        
        target_session.commit()
        print(f"  ✅ {table_name}: {count} 条记录")
        return count
        
    except Exception as e:
        target_session.rollback()
        print(f"  ❌ {table_name}: 迁移失败 - {e}")
        raise


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="数据库迁移工具")
    parser.add_argument(
        "--source",
        required=True,
        help="源数据库连接字符串（如: sqlite:///./meeting_agent.db）",
    )
    parser.add_argument(
        "--target",
        required=True,
        help="目标数据库连接字符串（如: postgresql://user:pass@host:5432/dbname）",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="演练模式，不实际迁移数据",
    )
    parser.add_argument(
        "--skip-tables",
        nargs="*",
        default=[],
        help="跳过的表名列表",
    )
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("数据库迁移工具")
    print("=" * 60)
    print(f"源数据库: {args.source}")
    print(f"目标数据库: {args.target}")
    print(f"演练模式: {'是' if args.dry_run else '否'}")
    if args.skip_tables:
        print(f"跳过的表: {', '.join(args.skip_tables)}")
    print("=" * 60)
    
    # 确认
    if not args.dry_run:
        confirm = input("\n⚠️  确认开始迁移？这将修改目标数据库！(yes/no): ")
        if confirm.lower() != "yes":
            print("已取消")
            sys.exit(0)
    
    try:
        # 连接数据库
        print("\n📡 连接数据库...")
        source_engine = create_engine(args.source)
        target_engine = create_engine(args.target)
        
        SourceSession = sessionmaker(bind=source_engine)
        TargetSession = sessionmaker(bind=target_engine)
        
        source_session = SourceSession()
        target_session = TargetSession()
        
        print("✅ 数据库连接成功")
        
        # 定义迁移顺序（按依赖关系）
        migration_order = [
            ("users", User),
            ("prompt_templates", PromptTemplateRecord),
            ("hotword_sets", HotwordSetRecord),
            ("tasks", Task),
            ("transcripts", TranscriptRecord),
            ("speaker_mappings", SpeakerMapping),
            ("generated_artifacts", GeneratedArtifactRecord),
            ("audit_logs", AuditLogRecord),
        ]
        
        # 迁移数据
        print("\n📦 开始迁移数据...")
        total_records = 0
        
        for table_name, model_class in migration_order:
            if table_name in args.skip_tables:
                print(f"  ⏭️  {table_name}: 已跳过")
                continue
            
            count = migrate_table(model_class, source_session, target_session, args.dry_run)
            total_records += count
        
        # 完成
        print("\n" + "=" * 60)
        if args.dry_run:
            print(f"✅ 演练完成！共 {total_records} 条记录")
            print("   使用 --dry-run=false 执行实际迁移")
        else:
            print(f"✅ 迁移完成！共迁移 {total_records} 条记录")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ 迁移失败: {e}")
        sys.exit(1)
    
    finally:
        # 关闭连接
        try:
            source_session.close()
            target_session.close()
        except:
            pass


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""测试 PostgreSQL 数据库连接"""

import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import text
from src.database.session import get_engine, session_scope
from src.utils.logger import get_logger

logger = get_logger(__name__)


def test_connection(database_url: str):
    """
    测试数据库连接
    
    Args:
        database_url: 数据库连接 URL
    """
    print("=" * 80)
    print("PostgreSQL 连接测试")
    print("=" * 80)
    print()
    
    # 测试 1: 创建引擎
    print("[1/5] 创建数据库引擎...")
    try:
        engine = get_engine(database_url, echo=False)
        print("✓ 引擎创建成功")
        print(f"  - 数据库: {database_url.split('@')[-1] if '@' in database_url else database_url}")
        print(f"  - 连接池大小: {engine.pool.size()}")
    except Exception as e:
        print(f"✗ 引擎创建失败: {e}")
        return False
    print()
    
    # 测试 2: 测试连接
    print("[2/5] 测试数据库连接...")
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version()"))
            version = result.scalar()
            print("✓ 连接成功")
            print(f"  - PostgreSQL 版本: {version}")
    except Exception as e:
        print(f"✗ 连接失败: {e}")
        return False
    print()
    
    # 测试 3: 测试会话
    print("[3/5] 测试会话管理...")
    try:
        with session_scope() as session:
            result = session.execute(text("SELECT current_database()"))
            db_name = result.scalar()
            print("✓ 会话创建成功")
            print(f"  - 当前数据库: {db_name}")
    except Exception as e:
        print(f"✗ 会话创建失败: {e}")
        return False
    print()
    
    # 测试 4: 测试事务
    print("[4/5] 测试事务管理...")
    try:
        with session_scope() as session:
            # 创建临时表
            session.execute(text("""
                CREATE TEMP TABLE test_table (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(100)
                )
            """))
            
            # 插入数据
            session.execute(text("INSERT INTO test_table (name) VALUES ('test')"))
            
            # 查询数据
            result = session.execute(text("SELECT COUNT(*) FROM test_table"))
            count = result.scalar()
            
            print("✓ 事务测试成功")
            print(f"  - 插入记录数: {count}")
    except Exception as e:
        print(f"✗ 事务测试失败: {e}")
        return False
    print()
    
    # 测试 5: 测试连接池
    print("[5/5] 测试连接池...")
    try:
        pool = engine.pool
        print("✓ 连接池信息:")
        print(f"  - 连接池大小: {pool.size()}")
        print(f"  - 已签出连接: {pool.checkedout()}")
        print(f"  - 溢出连接: {pool.overflow()}")
    except Exception as e:
        print(f"✗ 连接池测试失败: {e}")
        return False
    print()
    
    print("=" * 80)
    print("✓ 所有测试通过！PostgreSQL 连接正常")
    print("=" * 80)
    return True


def main():
    """主函数"""
    import os
    
    # 从环境变量读取数据库配置
    db_host = os.getenv("DB_HOST", "localhost")
    db_port = os.getenv("DB_PORT", "5432")
    db_name = os.getenv("DB_NAME", "meeting_agent")
    db_user = os.getenv("DB_USER", "meeting_user")
    db_password = os.getenv("DB_PASSWORD", "")
    
    if not db_password:
        print("错误: 请设置 DB_PASSWORD 环境变量")
        print()
        print("示例:")
        print("  export DB_PASSWORD=your_password")
        print("  python scripts/test_postgresql_connection.py")
        sys.exit(1)
    
    # 构建数据库 URL
    database_url = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
    
    # 运行测试
    success = test_connection(database_url)
    
    if not success:
        print()
        print("提示:")
        print("1. 确保 PostgreSQL 服务正在运行")
        print("2. 确保数据库和用户已创建")
        print("3. 确保用户有足够的权限")
        print("4. 检查防火墙设置")
        sys.exit(1)


if __name__ == "__main__":
    main()

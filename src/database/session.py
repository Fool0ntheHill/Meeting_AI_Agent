# -*- coding: utf-8 -*-
"""Database session management."""

from contextlib import contextmanager
from typing import Generator, Optional

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

from src.database.models import Base
from src.utils.logger import get_logger

logger = get_logger(__name__)

# 全局引擎和会话工厂
_engine: Optional[Engine] = None
_SessionLocal: Optional[sessionmaker] = None


def get_engine(database_url: str = "sqlite:///./meeting_agent.db", echo: bool = False) -> Engine:
    """
    获取或创建数据库引擎
    
    Args:
        database_url: 数据库连接 URL
            - SQLite: "sqlite:///./meeting_agent.db"
            - PostgreSQL: "postgresql://user:password@localhost/dbname"
            - MySQL: "mysql+pymysql://user:password@localhost/dbname"
        echo: 是否打印 SQL 语句
    
    Returns:
        Engine: SQLAlchemy 引擎
    """
    global _engine

    if _engine is None:
        # SQLite 特殊配置
        if database_url.startswith("sqlite"):
            _engine = create_engine(
                database_url,
                echo=echo,
                connect_args={"check_same_thread": False},  # SQLite 多线程支持
                poolclass=StaticPool,  # 使用静态连接池
            )
            
            # 启用 SQLite 外键约束
            @event.listens_for(_engine, "connect")
            def set_sqlite_pragma(dbapi_conn, connection_record):
                cursor = dbapi_conn.cursor()
                cursor.execute("PRAGMA foreign_keys=ON")
                cursor.close()
        else:
            # PostgreSQL/MySQL 配置
            _engine = create_engine(
                database_url,
                echo=echo,
                pool_size=10,  # 连接池大小
                max_overflow=20,  # 最大溢出连接数
                pool_pre_ping=True,  # 连接前检查
                pool_recycle=3600,  # 连接回收时间(秒)
            )

        logger.info(f"Database engine created: {database_url}")

    return _engine


def get_session_factory(engine: Optional[Engine] = None) -> sessionmaker:
    """
    获取或创建会话工厂
    
    Args:
        engine: 数据库引擎(可选,默认使用全局引擎)
    
    Returns:
        sessionmaker: 会话工厂
    """
    global _SessionLocal

    if _SessionLocal is None:
        if engine is None:
            engine = get_engine()

        _SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=engine,
        )

        logger.info("Session factory created")

    return _SessionLocal


def get_session(engine: Optional[Engine] = None) -> Session:
    """
    获取数据库会话
    
    Args:
        engine: 数据库引擎(可选)
    
    Returns:
        Session: 数据库会话
    
    Usage:
        session = get_session()
        try:
            # 使用 session
            pass
        finally:
            session.close()
    """
    factory = get_session_factory(engine)
    return factory()


@contextmanager
def session_scope(engine: Optional[Engine] = None) -> Generator[Session, None, None]:
    """
    提供事务性会话上下文管理器
    
    Args:
        engine: 数据库引擎(可选)
    
    Yields:
        Session: 数据库会话
    
    Usage:
        with session_scope() as session:
            task = Task(task_id="task_123", ...)
            session.add(task)
            # 自动提交或回滚
    """
    session = get_session(engine)
    try:
        yield session
        session.commit()
    except Exception as e:
        session.rollback()
        logger.error(f"Session rollback due to error: {e}")
        raise
    finally:
        session.close()


def init_db(database_url: str = "sqlite:///./meeting_agent.db", echo: bool = False) -> None:
    """
    初始化数据库(创建所有表)
    
    Args:
        database_url: 数据库连接 URL
        echo: 是否打印 SQL 语句
    """
    engine = get_engine(database_url, echo)
    Base.metadata.create_all(bind=engine)
    logger.info("Database initialized successfully")


def close_db() -> None:
    """关闭数据库连接"""
    global _engine, _SessionLocal

    if _engine is not None:
        _engine.dispose()
        _engine = None
        logger.info("Database engine disposed")

    _SessionLocal = None

# -*- coding: utf-8 -*-
"""文件夹和回收站相关的数据库模型

这个文件包含新增的 Folder 模型和 Task 模型需要添加的字段
"""

from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship
from src.database.models import Base


class Folder(Base):
    """文件夹表"""

    __tablename__ = "folders"

    # 主键
    folder_id = Column(String(64), primary_key=True, index=True)

    # 文件夹信息
    name = Column(String(256), nullable=False)
    parent_id = Column(String(64), ForeignKey("folders.folder_id", ondelete="CASCADE"), nullable=True, index=True)

    # 所有者信息
    owner_user_id = Column(String(64), nullable=False, index=True)
    owner_tenant_id = Column(String(64), nullable=False, index=True)

    # 时间戳
    created_at = Column(DateTime, nullable=False, default=datetime.now, index=True)
    updated_at = Column(DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)

    # 关系
    parent = relationship("Folder", remote_side="Folder.folder_id", backref="children")
    tasks = relationship("Task", back_populates="folder")

    # 索引
    __table_args__ = (
        Index("idx_folder_owner_user", "owner_user_id"),
        Index("idx_folder_owner_tenant", "owner_tenant_id"),
        Index("idx_folder_parent", "parent_id"),
    )


# Task 模型需要添加的字段（在 src/database/models.py 中的 Task 类添加）:
"""
    # 文件夹和回收站
    folder_id = Column(String(64), ForeignKey("folders.folder_id", ondelete="SET NULL"), nullable=True, index=True)
    is_deleted = Column(Boolean, nullable=False, default=False, index=True)
    deleted_at = Column(DateTime, nullable=True)
    
    # 关系
    folder = relationship("Folder", back_populates="tasks")
    
    # 在 __table_args__ 中添加索引:
    Index("idx_task_folder", "folder_id"),
    Index("idx_task_deleted", "is_deleted", "deleted_at"),
"""

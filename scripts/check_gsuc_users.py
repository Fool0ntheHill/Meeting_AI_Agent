#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""查看数据库中的 GSUC 用户"""

import sys
from pathlib import Path
from datetime import datetime

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.database.session import get_session
from src.database.models import User, Task

print("=" * 60)
print("数据库用户查询")
print("=" * 60)

db = get_session()

# 查询所有用户
users = db.query(User).all()

print(f"\n总用户数: {len(users)}")
print("\n用户列表:")
print("-" * 60)

for user in users:
    print(f"\nUser ID: {user.user_id}")
    print(f"  Username: {user.username}")
    print(f"  Tenant ID: {user.tenant_id}")
    print(f"  Active: {user.is_active}")
    print(f"  Created: {user.created_at}")
    print(f"  Last Login: {user.last_login_at or 'Never'}")
    
    # 查询该用户的任务数
    task_count = db.query(Task).filter(Task.user_id == user.user_id).count()
    print(f"  Tasks: {task_count}")
    
    # 判断登录方式
    if user.user_id.startswith("user_gsuc_"):
        gsuc_uid = user.user_id.replace("user_gsuc_", "")
        print(f"  Login Type: GSUC (uid={gsuc_uid})")
    elif user.user_id.startswith("user_"):
        print(f"  Login Type: Development")
    else:
        print(f"  Login Type: Unknown")

print("\n" + "=" * 60)

# 统计
gsuc_users = [u for u in users if u.user_id.startswith("user_gsuc_")]
dev_users = [u for u in users if u.user_id.startswith("user_") and not u.user_id.startswith("user_gsuc_")]

print(f"\n统计:")
print(f"  GSUC 用户: {len(gsuc_users)}")
print(f"  开发用户: {len(dev_users)}")
print(f"  其他用户: {len(users) - len(gsuc_users) - len(dev_users)}")

db.close()

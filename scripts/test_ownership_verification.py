#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试所有权验证依赖

测试场景:
1. 正常访问 - 用户访问自己的任务
2. 越权访问 - 用户尝试访问其他用户的任务
3. 任务不存在 - 访问不存在的任务
"""

import sys
import os
import uuid
from datetime import datetime, timedelta

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.database.session import get_session
from src.database.repositories import TaskRepository, UserRepository
from src.api.dependencies import verify_task_ownership, get_current_user_id
from src.config.loader import get_config
from jose import jwt
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials


def create_test_jwt(user_id: str, tenant_id: str) -> str:
    """创建测试 JWT Token"""
    config = get_config()
    
    payload = {
        "sub": user_id,
        "tenant_id": tenant_id,
        "exp": datetime.utcnow() + timedelta(hours=1),
        "iat": datetime.utcnow(),
    }
    
    token = jwt.encode(
        payload,
        config.jwt_secret_key,
        algorithm=config.jwt_algorithm
    )
    
    return token


async def test_ownership_verification():
    """测试所有权验证"""
    print("=" * 80)
    print("测试所有权验证依赖")
    print("=" * 80)
    
    session = get_session()
    
    try:
        # 创建测试用户
        user_repo = UserRepository(session)
        task_repo = TaskRepository(session)
        
        user1_id = f"test_user_{uuid.uuid4().hex[:8]}"
        user2_id = f"test_user_{uuid.uuid4().hex[:8]}"
        tenant_id = f"test_tenant_{uuid.uuid4().hex[:8]}"
        
        print(f"\n创建测试用户:")
        print(f"  User 1: {user1_id}")
        print(f"  User 2: {user2_id}")
        print(f"  Tenant: {tenant_id}")
        
        user1 = user_repo.create(
            user_id=user1_id,
            username=f"testuser1_{uuid.uuid4().hex[:4]}",
            tenant_id=tenant_id,
        )
        
        user2 = user_repo.create(
            user_id=user2_id,
            username=f"testuser2_{uuid.uuid4().hex[:4]}",
            tenant_id=tenant_id,
        )
        
        session.commit()
        
        # 创建测试任务 (属于 user1)
        task_id = f"task_{uuid.uuid4().hex[:16]}"
        print(f"\n创建测试任务: {task_id} (owned by {user1_id})")
        
        task = task_repo.create(
            task_id=task_id,
            user_id=user1_id,
            tenant_id=tenant_id,
            meeting_type="internal",
            audio_files=["test.wav"],
            file_order=[0],
        )
        
        session.commit()
        
        # 测试 1: 正常访问 - user1 访问自己的任务
        print("\n" + "=" * 80)
        print("测试 1: 正常访问 - 用户访问自己的任务")
        print("=" * 80)
        
        try:
            # 模拟依赖注入
            class MockCredentials:
                def __init__(self, token):
                    self.credentials = token
            
            token1 = create_test_jwt(user1_id, tenant_id)
            print(f"User 1 Token: {token1[:50]}...")
            
            # 直接调用验证函数
            from src.api.dependencies import verify_jwt_token
            
            credentials = MockCredentials(token1)
            auth_result = await verify_jwt_token(credentials, session)
            verified_user_id, verified_tenant_id = auth_result
            
            print(f"✅ JWT 验证成功: user_id={verified_user_id}, tenant_id={verified_tenant_id}")
            
            # 验证任务所有权
            verified_task = await verify_task_ownership(task_id, verified_user_id, session)
            print(f"✅ 所有权验证成功: task_id={verified_task.task_id}, owner={verified_task.user_id}")
            
        except HTTPException as e:
            print(f"❌ 测试失败: {e.status_code} - {e.detail}")
            return False
        
        # 测试 2: 越权访问 - user2 尝试访问 user1 的任务
        print("\n" + "=" * 80)
        print("测试 2: 越权访问 - 用户尝试访问其他用户的任务")
        print("=" * 80)
        
        try:
            token2 = create_test_jwt(user2_id, tenant_id)
            print(f"User 2 Token: {token2[:50]}...")
            
            credentials = MockCredentials(token2)
            auth_result = await verify_jwt_token(credentials, session)
            verified_user_id, verified_tenant_id = auth_result
            
            print(f"✅ JWT 验证成功: user_id={verified_user_id}, tenant_id={verified_tenant_id}")
            
            # 尝试访问 user1 的任务 (应该失败)
            verified_task = await verify_task_ownership(task_id, verified_user_id, session)
            print(f"❌ 测试失败: 越权访问应该被拒绝，但成功了")
            return False
            
        except HTTPException as e:
            if e.status_code == 403:
                print(f"✅ 越权访问被正确拒绝: {e.status_code} - {e.detail}")
            else:
                print(f"❌ 错误的状态码: 期望 403, 实际 {e.status_code}")
                return False
        
        # 测试 3: 任务不存在
        print("\n" + "=" * 80)
        print("测试 3: 访问不存在的任务")
        print("=" * 80)
        
        try:
            fake_task_id = f"task_{uuid.uuid4().hex[:16]}"
            print(f"尝试访问不存在的任务: {fake_task_id}")
            
            verified_task = await verify_task_ownership(fake_task_id, user1_id, session)
            print(f"❌ 测试失败: 访问不存在的任务应该返回 404，但成功了")
            return False
            
        except HTTPException as e:
            if e.status_code == 404:
                print(f"✅ 不存在的任务被正确拒绝: {e.status_code} - {e.detail}")
            else:
                print(f"❌ 错误的状态码: 期望 404, 实际 {e.status_code}")
                return False
        
        print("\n" + "=" * 80)
        print("✅ 所有测试通过!")
        print("=" * 80)
        
        # 清理测试数据
        print("\n清理测试数据...")
        task_repo.delete(task_id)
        session.delete(user1)
        session.delete(user2)
        session.commit()
        
        return True
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        session.rollback()
        return False
        
    finally:
        session.close()


if __name__ == "__main__":
    import asyncio
    
    success = asyncio.run(test_ownership_verification())
    sys.exit(0 if success else 1)

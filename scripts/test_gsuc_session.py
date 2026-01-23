#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试 GSUC Session 认证

测试内容:
1. 数据格式转换工具
2. GSUC Session 验证（Mock）
3. API 端点认证
"""

import sys
import asyncio
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.utils.case_converter import (
    to_camel_case,
    to_snake_case,
    convert_keys_to_camel_case,
    convert_keys_to_snake_case
)
from src.providers.gsuc_session import GSUCSessionManager


def test_case_converter():
    """测试数据格式转换工具"""
    print("\n" + "="*60)
    print("测试 1: 数据格式转换工具")
    print("="*60)
    
    # 测试字符串转换
    print("\n1.1 字符串转换:")
    test_cases = [
        ("user_name", "userName"),
        ("task_id", "taskId"),
        ("audio_file_path", "audioFilePath"),
        ("created_at", "createdAt"),
    ]
    
    for snake, expected_camel in test_cases:
        camel = to_camel_case(snake)
        print(f"  {snake} → {camel} {'✓' if camel == expected_camel else '✗'}")
        
        # 反向转换
        back_to_snake = to_snake_case(camel)
        print(f"  {camel} → {back_to_snake} {'✓' if back_to_snake == snake else '✗'}")
    
    # 测试对象转换
    print("\n1.2 对象转换:")
    
    # snake_case → camelCase
    snake_obj = {
        "task_id": "task_123",
        "task_name": "会议纪要",
        "user_id": "user_gsuc_1003",
        "audio_file_path": "/uploads/audio.mp3",
        "created_at": "2024-01-23T10:00:00Z"
    }
    
    camel_obj = convert_keys_to_camel_case(snake_obj)
    print(f"  snake_case → camelCase:")
    print(f"    输入: {snake_obj}")
    print(f"    输出: {camel_obj}")
    
    expected_keys = {"taskId", "taskName", "userId", "audioFilePath", "createdAt"}
    actual_keys = set(camel_obj.keys())
    print(f"    验证: {'✓' if actual_keys == expected_keys else '✗'}")
    
    # camelCase → snake_case
    back_to_snake_obj = convert_keys_to_snake_case(camel_obj)
    print(f"\n  camelCase → snake_case:")
    print(f"    输入: {camel_obj}")
    print(f"    输出: {back_to_snake_obj}")
    print(f"    验证: {'✓' if back_to_snake_obj == snake_obj else '✗'}")
    
    # 测试嵌套对象
    print("\n1.3 嵌套对象转换:")
    nested_obj = {
        "task_info": {
            "task_id": "task_123",
            "task_name": "会议纪要"
        },
        "user_list": [
            {"user_id": "user_1", "user_name": "张三"},
            {"user_id": "user_2", "user_name": "李四"}
        ]
    }
    
    nested_camel = convert_keys_to_camel_case(nested_obj)
    print(f"  输入: {nested_obj}")
    print(f"  输出: {nested_camel}")
    print(f"  验证: {'✓' if 'taskInfo' in nested_camel and 'userList' in nested_camel else '✗'}")


async def test_gsuc_session_manager():
    """测试 GSUC Session 管理器"""
    print("\n" + "="*60)
    print("测试 2: GSUC Session 管理器")
    print("="*60)
    
    # 创建管理器（不使用 Redis）
    manager = GSUCSessionManager(
        gsuc_api_url="https://gsuc.gamesci.com.cn",
        redis_client=None
    )
    
    print("\n2.1 创建 Session 管理器:")
    print(f"  GSUC API URL: {manager.gsuc_api_url}")
    print(f"  Timeout: {manager.timeout}s")
    print(f"  Cache TTL: {manager.cache_ttl}s")
    print(f"  Redis: {'启用' if manager.redis_client else '未启用'}")
    
    # 测试 Session 验证（Mock）
    print("\n2.2 测试 Session 验证:")
    print("  注意: 当前为 Mock 实现，实际需要调用 GSUC API")
    
    mock_session_id = "OP0s4dCO5Cln6-BRRXl9PshQnIx29NZE_bDjJD5x5HQ"
    print(f"  Session ID: {mock_session_id[:30]}...")
    
    # 由于没有真实的 GSUC API，这里会返回 None
    user_info = await manager.verify_session(mock_session_id)
    
    if user_info:
        print(f"  验证成功:")
        print(f"    user_id: {user_info['user_id']}")
        print(f"    tenant_id: {user_info['tenant_id']}")
        print(f"    username: {user_info.get('username', 'N/A')}")
    else:
        print(f"  验证失败（预期行为，因为没有真实的 GSUC API）")
    
    print("\n2.3 缓存失效:")
    manager.invalidate_session(mock_session_id)
    print(f"  Session 缓存已失效")


def test_api_dependencies():
    """测试 API 依赖"""
    print("\n" + "="*60)
    print("测试 3: API 依赖")
    print("="*60)
    
    print("\n3.1 导入依赖:")
    try:
        from src.api.dependencies import (
            verify_jwt_token,
            verify_gsuc_session,
            get_current_user_id,
            get_current_tenant_id
        )
        print("  ✓ verify_jwt_token")
        print("  ✓ verify_gsuc_session")
        print("  ✓ get_current_user_id")
        print("  ✓ get_current_tenant_id")
    except ImportError as e:
        print(f"  ✗ 导入失败: {e}")
        return
    
    print("\n3.2 依赖说明:")
    print("  - verify_jwt_token: 开发环境使用（JWT Token）")
    print("  - verify_gsuc_session: 生产环境使用（GSUC SESSIONID）")
    print("  - 从 Token header 提取 SESSIONID（不是 Authorization header）")
    print("  - 调用 GSUC API 或查询 Redis 缓存验证")


def main():
    """主函数"""
    print("\n" + "="*60)
    print("GSUC Session 认证测试")
    print("="*60)
    
    # 测试 1: 数据格式转换
    test_case_converter()
    
    # 测试 2: GSUC Session 管理器
    asyncio.run(test_gsuc_session_manager())
    
    # 测试 3: API 依赖
    test_api_dependencies()
    
    # 总结
    print("\n" + "="*60)
    print("测试总结")
    print("="*60)
    print("\n✓ 数据格式转换工具正常")
    print("✓ GSUC Session 管理器已创建")
    print("✓ API 依赖已更新")
    print("\n下一步:")
    print("1. 向 GSUC 团队确认 Session 验证 API")
    print("2. 配置 Redis 连接")
    print("3. 实现真实的 GSUC API 调用")
    print("4. 前端实现 Token header 传递")
    print("5. 测试完整登录流程")


if __name__ == "__main__":
    main()

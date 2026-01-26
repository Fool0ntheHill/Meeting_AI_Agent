#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
验证 GSUC 回调代码是否包含 account 字段

直接检查代码逻辑，不运行实际测试
"""

import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def verify_callback_code():
    """验证回调代码"""
    
    print("="*60)
    print("验证 GSUC 回调代码")
    print("="*60)
    
    # 读取 auth.py 文件
    auth_file = project_root / "src" / "api" / "routes" / "auth.py"
    
    with open(auth_file, "r", encoding="utf-8") as f:
        content = f.read()
    
    # 查找兼容路由的 params 定义
    print("\n1. 检查兼容路由 /api/v1/auth/callback")
    print("-" * 60)
    
    # 查找 gsuc_callback_compat 函数
    if "def gsuc_callback_compat" in content:
        print("✅ 找到兼容路由函数")
        
        # 查找 params 定义
        start_idx = content.find("def gsuc_callback_compat")
        end_idx = content.find("def ", start_idx + 1)
        if end_idx == -1:
            end_idx = len(content)
        
        func_content = content[start_idx:end_idx]
        
        # 检查 params 字典
        if 'params = {' in func_content:
            params_start = func_content.find('params = {')
            params_end = func_content.find('}', params_start)
            params_block = func_content[params_start:params_end + 1]
            
            print("\n回调参数定义:")
            print(params_block)
            
            # 验证必需字段
            print("\n字段验证:")
            required_fields = [
                ("access_token", "JWT Token"),
                ("user_id", "用户 ID"),
                ("tenant_id", "租户 ID"),
                ("username", "中文名"),
                ("account", "英文账号"),
                ("avatar", "头像 URL"),
                ("expires_in", "过期时间")
            ]
            
            for field, desc in required_fields:
                if f'"{field}"' in params_block:
                    print(f"  ✅ {field}: {desc}")
                else:
                    print(f"  ❌ {field}: {desc} (缺失)")
        else:
            print("❌ 未找到 params 定义")
    else:
        print("❌ 未找到兼容路由函数")
    
    # 查找标准路由的 params 定义
    print("\n2. 检查标准路由 /api/v1/auth/gsuc/callback")
    print("-" * 60)
    
    if "def gsuc_callback" in content:
        print("✅ 找到标准路由函数")
        
        # 查找第一个 gsuc_callback 函数 (不是 compat)
        start_idx = content.find("async def gsuc_callback(")
        if start_idx != -1:
            end_idx = content.find("async def gsuc_callback_compat", start_idx)
            if end_idx == -1:
                end_idx = content.find("# ============", start_idx + 1000)
            
            func_content = content[start_idx:end_idx]
            
            # 检查 params 字典
            if 'params = {' in func_content:
                params_start = func_content.find('params = {')
                params_end = func_content.find('}', params_start)
                params_block = func_content[params_start:params_end + 1]
                
                print("\n回调参数定义:")
                print(params_block)
                
                # 验证必需字段
                print("\n字段验证:")
                for field, desc in required_fields:
                    if f'"{field}"' in params_block:
                        print(f"  ✅ {field}: {desc}")
                    else:
                        print(f"  ❌ {field}: {desc} (缺失)")
            else:
                print("❌ 未找到 params 定义")
    else:
        print("❌ 未找到标准路由函数")
    
    print("\n" + "="*60)
    print("✅ 代码验证完成")
    print("="*60)
    
    print("\n前端期待的回调 URL 格式:")
    print("http://localhost:5173/login?")
    print("  access_token=<jwt_token>&")
    print("  user_id=user_gsuc_1231&")
    print("  tenant_id=tenant_gsuc_1231&")
    print("  username=林晋辉&")
    print("  account=lorenzolin&")
    print("  avatar=https://...&")
    print("  expires_in=86400")
    
    print("\n前端使用建议:")
    print("  - 显示用户名: 使用 username 参数 (林晋辉)")
    print("  - 显示 ID: 使用 account 参数 (lorenzolin)")
    print("  - 用户标识: 使用 user_id 参数 (user_gsuc_1231)")


if __name__ == "__main__":
    try:
        verify_callback_code()
    except Exception as e:
        print(f"\n❌ 验证出错: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

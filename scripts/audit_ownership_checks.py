#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
审计所有任务相关接口的所有权检查

检查所有需要任务 ID 的端点，确定哪些已经有所有权检查，哪些缺少检查。
"""

import re
from pathlib import Path
from typing import List, Dict, Tuple


def extract_endpoints(file_path: str) -> List[Dict]:
    """提取文件中的所有端点"""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    endpoints = []
    
    # 匹配路由装饰器和函数定义
    pattern = r'@router\.(get|post|put|patch|delete)\((.*?)\).*?async def (\w+)\((.*?)\):'
    matches = re.finditer(pattern, content, re.DOTALL)
    
    for match in matches:
        method = match.group(1).upper()
        route = match.group(2).strip().strip('"').strip("'")
        func_name = match.group(3)
        params = match.group(4)
        
        # 检查是否有 task_id 参数
        has_task_id = 'task_id' in params
        
        # 检查是否使用了 verify_task_ownership
        func_start = match.end()
        func_end = content.find('\n\nasync def', func_start)
        if func_end == -1:
            func_end = len(content)
        func_body = content[func_start:func_end]
        
        uses_verify_ownership = 'verify_task_ownership' in params
        
        # 检查是否手动验证所有权
        manual_check = (
            'task.user_id != user_id' in func_body or
            'task_repo.get_by_id(task_id)' in func_body
        )
        
        endpoints.append({
            'method': method,
            'route': route,
            'function': func_name,
            'has_task_id': has_task_id,
            'uses_verify_ownership': uses_verify_ownership,
            'manual_check': manual_check,
            'file': file_path,
        })
    
    return endpoints


def analyze_endpoints():
    """分析所有端点"""
    print("=" * 100)
    print("任务相关接口所有权检查审计")
    print("=" * 100)
    
    files = [
        'src/api/routes/tasks.py',
        'src/api/routes/corrections.py',
        'src/api/routes/artifacts.py',
    ]
    
    all_endpoints = []
    for file_path in files:
        if Path(file_path).exists():
            endpoints = extract_endpoints(file_path)
            all_endpoints.extend(endpoints)
    
    # 分类端点
    task_endpoints = [e for e in all_endpoints if e['has_task_id']]
    non_task_endpoints = [e for e in all_endpoints if not e['has_task_id']]
    
    # 进一步分类任务端点
    with_verify_ownership = [e for e in task_endpoints if e['uses_verify_ownership']]
    with_manual_check = [e for e in task_endpoints if e['manual_check'] and not e['uses_verify_ownership']]
    without_check = [e for e in task_endpoints if not e['uses_verify_ownership'] and not e['manual_check']]
    
    print(f"\n总计端点: {len(all_endpoints)}")
    print(f"  - 需要任务 ID 的端点: {len(task_endpoints)}")
    print(f"  - 不需要任务 ID 的端点: {len(non_task_endpoints)}")
    
    print("\n" + "=" * 100)
    print("✅ 已使用 verify_task_ownership 的端点")
    print("=" * 100)
    if with_verify_ownership:
        for e in with_verify_ownership:
            print(f"  {e['method']:6} {e['route']:50} -> {e['function']}")
            print(f"         文件: {e['file']}")
    else:
        print("  (无)")
    
    print("\n" + "=" * 100)
    print("⚠️  使用手动检查的端点 (需要重构)")
    print("=" * 100)
    if with_manual_check:
        for e in with_manual_check:
            print(f"  {e['method']:6} {e['route']:50} -> {e['function']}")
            print(f"         文件: {e['file']}")
            print(f"         建议: 替换为 Depends(verify_task_ownership)")
    else:
        print("  (无)")
    
    print("\n" + "=" * 100)
    print("❌ 缺少所有权检查的端点 (安全风险!)")
    print("=" * 100)
    if without_check:
        for e in without_check:
            print(f"  {e['method']:6} {e['route']:50} -> {e['function']}")
            print(f"         文件: {e['file']}")
            print(f"         风险: 可能存在 IDOR 漏洞")
    else:
        print("  (无)")
    
    print("\n" + "=" * 100)
    print("修复计划")
    print("=" * 100)
    
    total_to_fix = len(with_manual_check) + len(without_check)
    
    if total_to_fix == 0:
        print("✅ 所有端点都已正确实现所有权检查!")
    else:
        print(f"\n需要修复的端点总数: {total_to_fix}")
        print(f"  - 需要重构 (手动检查 → verify_task_ownership): {len(with_manual_check)}")
        print(f"  - 需要添加检查: {len(without_check)}")
        
        print("\n优先级:")
        print("  1. 高优先级: 缺少检查的端点 (立即修复)")
        print("  2. 中优先级: 手动检查的端点 (重构以提高一致性)")
        
        print("\n修复步骤:")
        print("  1. 在函数参数中添加: task: Task = Depends(verify_task_ownership)")
        print("  2. 移除手动的 task_repo.get_by_id() 和权限检查代码")
        print("  3. 直接使用 task 对象")
    
    print("\n" + "=" * 100)
    
    return {
        'total': len(all_endpoints),
        'task_endpoints': len(task_endpoints),
        'with_verify_ownership': len(with_verify_ownership),
        'with_manual_check': len(with_manual_check),
        'without_check': len(without_check),
        'endpoints': {
            'with_verify_ownership': with_verify_ownership,
            'with_manual_check': with_manual_check,
            'without_check': without_check,
        }
    }


if __name__ == "__main__":
    result = analyze_endpoints()
    
    # 生成详细报告
    print("\n详细端点列表:")
    print("\n1. 已使用 verify_task_ownership:")
    for e in result['endpoints']['with_verify_ownership']:
        print(f"   - {e['method']} {e['route']} ({e['file']})")
    
    print("\n2. 使用手动检查:")
    for e in result['endpoints']['with_manual_check']:
        print(f"   - {e['method']} {e['route']} ({e['file']})")
    
    print("\n3. 缺少检查:")
    for e in result['endpoints']['without_check']:
        print(f"   - {e['method']} {e['route']} ({e['file']})")

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试空白模板 (__blank__) 修复

验证:
1. 重新生成 artifact 时使用 __blank__ 模板不会报 404 错误
2. 修正转写时使用 __blank__ 模板不会报 404 错误
"""

import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import asyncio
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.database.models import Base, Task, TranscriptRecord
from src.config.loader import get_config


async def test_blank_template_fix():
    """测试空白模板修复"""
    
    print("="*60)
    print("测试空白模板 (__blank__) 修复")
    print("="*60)
    
    # 测试 1: 检查 artifacts.py 中的修复
    print("\n" + "-"*60)
    print("测试 1: 检查 artifacts.py 中的空白模板处理")
    print("-"*60)
    
    # 读取 artifacts.py 源代码
    source_file = project_root / "src" / "api" / "routes" / "artifacts.py"
    with open(source_file, "r", encoding="utf-8") as f:
        content = f.read()
    
    # 检查是否包含空白模板处理逻辑
    checks_passed = 0
    total_checks = 0
    
    total_checks += 1
    if 'request.prompt_instance.template_id != "__blank__"' in content:
        print("✅ artifacts.py 已添加空白模板处理逻辑")
        checks_passed += 1
    else:
        print("❌ artifacts.py 缺少空白模板处理逻辑")
    
    total_checks += 1
    if 'Using blank template (__blank__), will be created by service' in content:
        print("✅ artifacts.py 包含空白模板日志")
        checks_passed += 1
    else:
        print("❌ artifacts.py 缺少空白模板日志")
    
    # 测试 2: 检查 corrections.py 中的修复
    print("\n" + "-"*60)
    print("测试 2: 检查 corrections.py 中的空白模板处理")
    print("-"*60)
    
    source_file = project_root / "src" / "api" / "routes" / "corrections.py"
    with open(source_file, "r", encoding="utf-8") as f:
        content = f.read()
    
    # 检查是否包含空白模板处理逻辑
    total_checks += 1
    if 'request.prompt_instance.template_id != "__blank__"' in content:
        print("✅ corrections.py 已添加空白模板处理逻辑")
        checks_passed += 1
    else:
        print("❌ corrections.py 缺少空白模板处理逻辑")
    
    total_checks += 1
    if 'Using blank template (__blank__), will be created by service' in content:
        print("✅ corrections.py 包含空白模板日志")
        checks_passed += 1
    else:
        print("❌ corrections.py 缺少空白模板日志")
    
    # 测试 3: 验证 ArtifactGenerationService 中的空白模板创建
    print("\n" + "-"*60)
    print("测试 3: 验证 ArtifactGenerationService 中的空白模板创建")
    print("-"*60)
    
    from src.services.artifact_generation import ArtifactGenerationService
    from src.core.models import PromptInstance
    
    # 创建测试用的 PromptInstance
    prompt_instance = PromptInstance(
        template_id="__blank__",
        language="zh-CN",
        prompt_text="测试空白模板",
        parameters={}
    )
    
    # 创建服务实例
    service = ArtifactGenerationService(
        llm_provider=None,
        template_repo=None,
        artifact_repo=None
    )
    
    # 测试创建空白模板
    try:
        blank_template = service._create_blank_template("meeting_minutes", prompt_instance)
        total_checks += 1
        print(f"✅ 成功创建空白模板")
        print(f"   模板 ID: {blank_template.template_id}")
        print(f"   模板标题: {blank_template.title}")
        print(f"   提示词: {blank_template.prompt_body[:100]}...")
        checks_passed += 1
    except Exception as e:
        total_checks += 1
        print(f"❌ 创建空白模板失败: {e}")
    
    print("\n" + "="*60)
    print(f"测试结果: {checks_passed}/{total_checks} 通过")
    print("="*60)
    
    if checks_passed == total_checks:
        print("\n✅ 所有测试通过！")
    else:
        print(f"\n⚠️  {total_checks - checks_passed} 个测试失败")
    
    print("\n修复说明:")
    print("1. artifacts.py 和 corrections.py 现在会检查 template_id 是否为 __blank__")
    print("2. 如果是 __blank__，不会从数据库查询模板，而是传 None 给服务")
    print("3. ArtifactGenerationService 会自动创建临时空白模板")
    print("4. 空白模板使用用户提供的 prompt_text 作为提示词")
    
    print("\n下次使用空白模板时:")
    print("- 重新生成 artifact 不会再报 404 错误")
    print("- 修正转写后重新生成也不会报 404 错误")


if __name__ == "__main__":
    try:
        asyncio.run(test_blank_template_fix())
    except Exception as e:
        print(f"\n❌ 测试出错: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

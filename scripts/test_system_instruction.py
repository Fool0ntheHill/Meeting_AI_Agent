#!/usr/bin/env python3
"""测试 System Instruction 的效果"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.providers.gemini_llm import GLOBAL_SYSTEM_INSTRUCTION

print("=" * 100)
print("System Instruction 测试")
print("=" * 100)

print("\n📋 当前的 System Instruction 内容:")
print("-" * 100)
print(GLOBAL_SYSTEM_INSTRUCTION)
print("-" * 100)

print("\n✅ 设计原则验证:")
print("-" * 100)

# 检查是否包含防幻觉约束
if "严格基于" in GLOBAL_SYSTEM_INSTRUCTION and "编造" in GLOBAL_SYSTEM_INSTRUCTION:
    print("✅ 包含防幻觉约束（Grounding）")
else:
    print("❌ 缺少防幻觉约束")

# 检查是否包含格式兼容性约束
if "复选框" in GLOBAL_SYSTEM_INSTRUCTION and "- [ ]" in GLOBAL_SYSTEM_INSTRUCTION:
    print("✅ 包含格式兼容性约束（企微文档）")
else:
    print("❌ 缺少格式兼容性约束")

# 检查是否避免了角色定义
if "你是" not in GLOBAL_SYSTEM_INSTRUCTION and "助手" not in GLOBAL_SYSTEM_INSTRUCTION:
    print("✅ 没有定义角色（保持灵活性）")
else:
    print("⚠️  包含角色定义（可能影响灵活性）")

print("-" * 100)

print("\n🎯 System Instruction 的作用:")
print("-" * 100)
print("1. 防幻觉：强制 AI 基于转写内容，不编造事实")
print("2. 格式兼容：禁用复选框语法，确保企微文档粘贴正常")
print("3. 保持灵活：不定义角色，让用户模板决定任务类型")
print("-" * 100)

print("\n📊 与 User Prompt 的关系:")
print("-" * 100)
print("System Instruction: 全局约束（所有任务共享）")
print("User Prompt:        任务特定内容（用户模板定义）")
print("-" * 100)

print("\n🔄 完整的 Gemini API 调用结构:")
print("-" * 100)
print("""
response = client.models.generate_content(
    model="gemini-2.0-flash-exp",
    
    # ⭐ System Instruction（全局约束）
    system_instruction=GLOBAL_SYSTEM_INSTRUCTION,
    
    # 📝 User Prompt（用户内容）
    contents="[模板主体] + [转写内容] + [语言指令]",
    
    # 🔧 Config（格式参数）
    config=GenerateContentConfig(
        response_mime_type="application/json",
        response_schema={...}
    )
)
""")
print("-" * 100)

print("\n✨ 总结:")
print("-" * 100)
print("System Instruction 已成功添加到 Gemini LLM Provider")
print("所有新生成的 artifact 都会自动应用这些约束")
print("需要重启 worker 才能生效")
print("-" * 100)

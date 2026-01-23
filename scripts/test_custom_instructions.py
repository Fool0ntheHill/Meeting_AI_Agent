"""
测试 custom_instructions 功能

验证用户自定义指令是否正确应用到提示词中
"""

import asyncio
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.core.models import PromptInstance, PromptTemplate, OutputLanguage
from src.providers.gemini_llm import GeminiLLM
from src.config.loader import get_config


async def test_custom_instructions():
    """测试自定义指令"""
    
    print("=" * 80)
    print("测试 custom_instructions 功能")
    print("=" * 80)
    
    # 加载配置
    config = get_config()
    llm = GeminiLLM(config.llm)
    
    # 创建测试模板
    template = PromptTemplate(
        template_id="test_template",
        title="测试模板",
        description="用于测试的模板",
        prompt_body="请根据以下会议内容生成纪要：\n\n{transcript}",
        artifact_type="meeting_minutes",
        supported_languages=["zh-CN"],
        parameter_schema={},
        is_system=False,
        scope="user"
    )
    
    # 测试场景 1: 使用模板 + 自定义指令
    print("\n【场景 1: 使用模板 + 自定义指令】")
    prompt_instance_1 = PromptInstance(
        template_id="test_template",
        language="zh-CN",
        parameters={},
        custom_instructions="请特别关注技术决策和风险点，输出要简洁明了，不要超过500字"
    )
    
    formatted_transcript = """
[00:00:10] 张三: 大家好，今天我们讨论一下新功能的技术方案
[00:00:20] 李四: 我建议使用微服务架构
[00:00:30] 张三: 这个方案有什么风险吗？
[00:00:40] 李四: 主要风险是服务间通信的复杂度会增加
"""
    
    prompt_1 = llm._build_prompt(
        template=template,
        prompt_instance=prompt_instance_1,
        formatted_transcript=formatted_transcript,
        output_language=OutputLanguage.ZH_CN
    )
    
    print("生成的提示词:")
    print("-" * 80)
    print(prompt_1)
    print("-" * 80)
    
    # 检查是否包含自定义指令
    if "用户补充要求" in prompt_1 and "技术决策和风险点" in prompt_1:
        print("✓ 自定义指令已正确添加到提示词中")
    else:
        print("✗ 自定义指令未添加到提示词中")
    
    # 测试场景 2: 空白模板 + 自定义指令
    print("\n【场景 2: 空白模板 + 自定义指令】")
    blank_template = PromptTemplate(
        template_id="__blank__",
        title="空白模板",
        description="用户自定义模板",
        prompt_body="请分析以下会议内容，重点关注产品决策和用户反馈\n\n{transcript}",
        artifact_type="meeting_minutes",
        supported_languages=["zh-CN"],
        parameter_schema={},
        is_system=False,
        scope="user"
    )
    
    prompt_instance_2 = PromptInstance(
        template_id="__blank__",
        language="zh-CN",
        parameters={},
        custom_instructions="输出格式：1. 核心决策 2. 待办事项 3. 风险提示"
    )
    
    prompt_2 = llm._build_prompt(
        template=blank_template,
        prompt_instance=prompt_instance_2,
        formatted_transcript=formatted_transcript,
        output_language=OutputLanguage.ZH_CN
    )
    
    print("生成的提示词:")
    print("-" * 80)
    print(prompt_2)
    print("-" * 80)
    
    # 检查是否包含自定义指令
    if "用户补充要求" in prompt_2 and "核心决策" in prompt_2:
        print("✓ 自定义指令已正确添加到提示词中")
    else:
        print("✗ 自定义指令未添加到提示词中")
    
    # 测试场景 3: 无自定义指令
    print("\n【场景 3: 无自定义指令】")
    prompt_instance_3 = PromptInstance(
        template_id="test_template",
        language="zh-CN",
        parameters={}
        # 没有 custom_instructions
    )
    
    prompt_3 = llm._build_prompt(
        template=template,
        prompt_instance=prompt_instance_3,
        formatted_transcript=formatted_transcript,
        output_language=OutputLanguage.ZH_CN
    )
    
    print("生成的提示词:")
    print("-" * 80)
    print(prompt_3)
    print("-" * 80)
    
    # 检查是否不包含自定义指令部分
    if "用户补充要求" not in prompt_3:
        print("✓ 没有自定义指令时，不添加额外内容")
    else:
        print("✗ 不应该包含用户补充要求部分")
    
    print("\n" + "=" * 80)
    print("测试完成")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(test_custom_instructions())

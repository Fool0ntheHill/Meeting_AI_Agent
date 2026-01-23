"""
测试 _build_prompt 方法是否正确使用 prompt_text
"""

import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.core.models import PromptInstance, PromptTemplate, OutputLanguage
from src.providers.gemini_llm import GeminiLLM
from src.config.models import GeminiConfig


def test_prompt_text_usage():
    """测试 prompt_text 是否被正确使用"""
    
    print("=" * 80)
    print("测试 _build_prompt 方法是否正确使用 prompt_text")
    print("=" * 80)
    
    # 1. 创建 LLM 实例
    config = GeminiConfig(
        api_keys=["test_key"],
        model="gemini-3-pro-preview",
    )
    llm = GeminiLLM(config)
    
    # 2. 创建一个空白模板
    template = PromptTemplate(
        template_id="__blank__",
        title="空白模板",
        description="测试用空白模板",
        prompt_body="这是模板的 prompt_body，不应该被使用",
        artifact_type="meeting_minutes",
        supported_languages=["zh-CN"],
        parameter_schema={},
        is_system=False,
        scope="user",
    )
    
    # 3. 创建 prompt_instance，包含 prompt_text
    prompt_instance = PromptInstance(
        template_id="__blank__",
        language="zh-CN",
        prompt_text="这是用户自定义的 prompt_text，应该被使用！\n\n转写内容：{transcript}",
        parameters={},
    )
    
    # 4. 调用 _build_prompt
    formatted_transcript = "这是测试转写内容"
    prompt = llm._build_prompt(
        template=template,
        prompt_instance=prompt_instance,
        formatted_transcript=formatted_transcript,
        output_language=OutputLanguage.ZH_CN,
    )
    
    # 5. 验证结果
    print("\n【测试结果】")
    print(f"\n生成的完整提示词：")
    print("-" * 80)
    print(prompt)
    print("-" * 80)
    
    # 6. 检查是否使用了 prompt_text
    if "这是用户自定义的 prompt_text，应该被使用！" in prompt:
        print("\n✓ 测试通过：prompt_text 被正确使用")
    else:
        print("\n✗ 测试失败：prompt_text 未被使用")
        
    if "这是模板的 prompt_body，不应该被使用" in prompt:
        print("✗ 错误：使用了模板的 prompt_body")
    else:
        print("✓ 正确：没有使用模板的 prompt_body")
    
    # 7. 测试没有 prompt_text 的情况
    print("\n" + "=" * 80)
    print("测试没有 prompt_text 时是否使用模板的 prompt_body")
    print("=" * 80)
    
    prompt_instance_no_text = PromptInstance(
        template_id="__blank__",
        language="zh-CN",
        parameters={},
    )
    
    prompt_2 = llm._build_prompt(
        template=template,
        prompt_instance=prompt_instance_no_text,
        formatted_transcript=formatted_transcript,
        output_language=OutputLanguage.ZH_CN,
    )
    
    print(f"\n生成的完整提示词：")
    print("-" * 80)
    print(prompt_2)
    print("-" * 80)
    
    if "这是模板的 prompt_body，不应该被使用" in prompt_2:
        print("\n✓ 测试通过：使用了模板的 prompt_body")
    else:
        print("\n✗ 测试失败：没有使用模板的 prompt_body")


if __name__ == "__main__":
    test_prompt_text_usage()

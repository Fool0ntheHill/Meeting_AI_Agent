"""测试会议日期是否正确传递到提示词"""

import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.core.models import PromptTemplate, PromptInstance, OutputLanguage
from src.providers.gemini_llm import GeminiLLM

def test_prompt_with_meeting_date():
    """测试提示词构建是否包含会议日期"""
    
    # 创建一个简单的模板
    template = PromptTemplate(
        template_id="test_template",
        name="测试模板",
        title="测试模板",
        description="用于测试的模板",
        artifact_type="meeting_minutes",
        prompt_body="请根据以下会议转写生成会议纪要：\n\n{transcript}",
        supported_languages=["zh-CN"],
        parameter_schema={},
    )
    
    prompt_instance = PromptInstance(
        template_id="test_template",
        language="zh-CN",
        parameters={},
    )
    
    # 创建 GeminiLLM 实例（使用 mock config）
    from src.config.models import GeminiConfig
    mock_config = GeminiConfig(
        model="gemini-3-pro-preview",
        api_key="test_key",
        temperature=0.7,
        max_tokens=8192,
    )
    llm = GeminiLLM(mock_config)
    
    # 测试用例 1: 有会议日期
    print("\n" + "="*60)
    print("测试用例 1: 有会议日期和时间")
    print("="*60)
    
    prompt = llm._build_prompt(
        template=template,
        prompt_instance=prompt_instance,
        formatted_transcript="[测试转写内容]",
        output_language=OutputLanguage.ZH_CN,
        meeting_date="2025-12-29",
        meeting_time="14:30",
    )
    
    print(prompt)
    print("\n检查:")
    if "2025年12月29日" in prompt:
        print("✓ 包含会议日期")
    else:
        print("✗ 未包含会议日期")
    
    if "14:30" in prompt:
        print("✓ 包含会议时间")
    else:
        print("✗ 未包含会议时间")
    
    # 测试用例 2: 只有会议日期
    print("\n" + "="*60)
    print("测试用例 2: 只有会议日期")
    print("="*60)
    
    prompt = llm._build_prompt(
        template=template,
        prompt_instance=prompt_instance,
        formatted_transcript="[测试转写内容]",
        output_language=OutputLanguage.ZH_CN,
        meeting_date="2025-12-29",
        meeting_time=None,
    )
    
    print(prompt)
    print("\n检查:")
    if "2025年12月29日" in prompt:
        print("✓ 包含会议日期")
    else:
        print("✗ 未包含会议日期")
    
    # 测试用例 3: 没有会议元数据
    print("\n" + "="*60)
    print("测试用例 3: 没有会议元数据")
    print("="*60)
    
    prompt = llm._build_prompt(
        template=template,
        prompt_instance=prompt_instance,
        formatted_transcript="[测试转写内容]",
        output_language=OutputLanguage.ZH_CN,
        meeting_date=None,
        meeting_time=None,
    )
    
    print(prompt)
    print("\n检查:")
    if "会议时间" in prompt:
        print("✗ 不应包含会议时间部分")
    else:
        print("✓ 正确：没有会议时间部分")


if __name__ == "__main__":
    test_prompt_with_meeting_date()

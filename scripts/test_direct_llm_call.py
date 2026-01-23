"""
直接调用 LLM 生成方法，查看日志输出
"""

import asyncio
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.core.models import (
    PromptInstance,
    PromptTemplate,
    OutputLanguage,
    TranscriptionResult,
    Segment,
)
from src.providers.gemini_llm import GeminiLLM
from src.config.loader import get_config


async def test_direct_llm_call():
    """直接调用 LLM 生成方法"""
    
    print("=" * 80)
    print("直接调用 LLM 生成方法测试")
    print("=" * 80)
    
    # 1. 加载配置
    config = get_config()
    llm = GeminiLLM(config.gemini)
    
    # 2. 创建一个简单的转写结果
    transcript = TranscriptionResult(
        segments=[
            Segment(
                text="这是一个测试会议。",
                start_time=0.0,
                end_time=2.0,
                speaker="Speaker 0",
            ),
            Segment(
                text="我们讨论了一些重要的事情。",
                start_time=2.0,
                end_time=5.0,
                speaker="Speaker 1",
            ),
        ],
        full_text="这是一个测试会议。我们讨论了一些重要的事情。",
        duration=5.0,
        language="zh-CN",
        provider="test",
    )
    
    # 3. 创建空白模板
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
    
    # 4. 创建 prompt_instance，包含自定义 prompt_text
    prompt_instance = PromptInstance(
        template_id="__blank__",
        language="zh-CN",
        prompt_text="""【测试提示词】
请只输出以下JSON格式，不要添加任何其他内容：

{
  "content": "这是一个测试。如果你看到这段文字，说明提示词被正确使用了。"
}

转写内容：
{transcript}""",
        parameters={},
    )
    
    print("\n【测试参数】")
    print(f"模板 ID: {template.template_id}")
    print(f"模板 prompt_body: {template.prompt_body}")
    print(f"prompt_instance.template_id: {prompt_instance.template_id}")
    print(f"prompt_instance.prompt_text: {prompt_instance.prompt_text}")
    
    # 5. 调用 LLM 生成
    print("\n【开始生成】")
    print("请查看日志输出，特别是：")
    print("  - 'Using user-edited prompt_text'")
    print("  - '=== PROMPT SENT TO GEMINI ==='")
    print()
    
    # 启用详细日志
    import logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(name)s: %(message)s')
    
    try:
        artifact = await llm.generate_artifact(
            transcript=transcript,
            prompt_instance=prompt_instance,
            output_language=OutputLanguage.ZH_CN,
            template=template,
            task_id="test_task",
            artifact_id="test_artifact",
            version=1,
            created_by="test_user",
        )
        
        print("\n【生成结果】")
        print(f"Artifact ID: {artifact.artifact_id}")
        print(f"Content: {artifact.content[:500]}")
        
        # 检查内容是否符合预期
        if "这是一个测试。如果你看到这段文字，说明提示词被正确使用了。" in artifact.content:
            print("\n✓ 测试通过：生成的内容符合提示词要求")
        else:
            print("\n✗ 测试失败：生成的内容不符合提示词要求")
            
    except Exception as e:
        print(f"\n✗ 生成失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_direct_llm_call())

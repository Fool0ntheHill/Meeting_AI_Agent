# -*- coding: utf-8 -*-
"""测试 LLM 集成"""

import asyncio
import sys
import os

# 设置测试环境
os.environ["APP_ENV"] = "test"

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.config.loader import get_config
from src.providers.gemini_llm import GeminiLLM
from src.core.models import OutputLanguage


async def test_llm_generation():
    """测试 LLM 生成"""
    print("=== 测试 LLM 集成 ===\n")
    
    try:
        # 加载配置
        print("1. 加载配置...")
        config = get_config()
        print(f"   ✓ 配置加载成功")
        print(f"   Gemini API Keys: {len(config.gemini.api_keys)} 个")
        
        # 初始化 LLM
        print("\n2. 初始化 Gemini LLM...")
        llm = GeminiLLM(config.gemini)
        print(f"   ✓ LLM 初始化成功")
        
        # 测试简单生成
        print("\n3. 测试简单文本生成...")
        
        # 创建一个简单的转写结果用于测试
        from src.core.models import TranscriptionResult, Segment, PromptInstance
        
        segments = [
            Segment(
                text="大家好，今天我们讨论一下项目进度。",
                start_time=5.0,
                end_time=10.0,
                speaker="张三",
            ),
            Segment(
                text="好的，我这边的前端开发已经完成了80%。",
                start_time=15.0,
                end_time=20.0,
                speaker="李四",
            ),
            Segment(
                text="很好，后端呢？",
                start_time=25.0,
                end_time=28.0,
                speaker="张三",
            ),
            Segment(
                text="后端API已经全部完成，正在进行测试。",
                start_time=30.0,
                end_time=35.0,
                speaker="王五",
            ),
        ]
        
        transcript = TranscriptionResult(
            segments=segments,
            full_text="大家好，今天我们讨论一下项目进度。好的，我这边的前端开发已经完成了80%。很好，后端呢？后端API已经全部完成，正在进行测试。",
            duration=35.0,
            language="zh-CN",
            provider="test",
        )
        
        prompt_instance = PromptInstance(
            template_id="default_meeting_minutes",
            language="zh-CN",
            parameters={"meeting_type": "项目进度会议"},
        )
        
        # 创建一个简单的模板
        from src.core.models import PromptTemplate
        
        template = PromptTemplate(
            template_id="default_meeting_minutes",
            title="默认会议纪要模板",
            description="生成结构化的会议纪要",
            prompt_body="""请根据以下会议转写内容，生成结构化的会议纪要。

会议类型：{meeting_type}

会议转写：
{transcript}

请按以下格式输出：
1. 会议主题
2. 参与人员
3. 讨论要点
4. 决策事项
5. 行动项
""",
            artifact_type="meeting_minutes",
            supported_languages=["zh-CN", "en-US"],
            parameter_schema={
                "meeting_type": {"type": "string", "required": False, "default": "常规会议"}
            },
            is_system=True,
        )
        
        result = await llm.generate_artifact(
            transcript=transcript,
            prompt_instance=prompt_instance,
            output_language=OutputLanguage.ZH_CN,
            task_id="test-task-123",
            artifact_id="test-artifact-123",
            version=1,
            created_by="test-user",
            template=template,  # 传入模板
        )
        
        print(f"   ✓ 生成成功")
        print(f"\n生成的 Artifact：\n{'-' * 50}")
        print(f"ID: {result.artifact_id}")
        print(f"类型: {result.artifact_type}")
        print(f"版本: {result.version}")
        print(f"\n内容：")
        print(result.content)
        print('-' * 50)
        
        print("\n✅ 所有测试通过！")
        return True
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(test_llm_generation())
    sys.exit(0 if success else 1)

"""
测试用户指令优先级

验证当用户提供自定义提示词时，即使转写内容看起来像会议，
也应该严格按照用户的指令执行，而不是自动推断为会议纪要生成。
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config.loader import get_config
from src.core.models import PromptInstance, OutputLanguage
from src.providers.gemini_llm import GeminiLLM
from src.services.artifact_generation import ArtifactGenerationService
from src.database.session import get_session
from src.database.repositories import TranscriptRepository


async def test_user_instruction_priority():
    """测试用户指令优先级"""
    
    print("=" * 80)
    print("测试场景：用户指令优先级")
    print("=" * 80)
    
    # 1. 加载配置
    config = get_config()
    
    # 2. 初始化 LLM
    llm = GeminiLLM(config.gemini)
    
    # 3. 初始化服务
    service = ArtifactGenerationService(llm_provider=llm)
    
    # 4. 从数据库获取一个真实的转写结果（包含会议内容）
    with get_session() as session:
        transcript_repo = TranscriptRepository(session)
        
        # 获取最新的转写记录
        transcript_record = session.query(transcript_repo.model).order_by(
            transcript_repo.model.created_at.desc()
        ).first()
        
        if not transcript_record:
            print("❌ 没有找到转写记录，请先创建一个任务")
            return
        
        transcript = transcript_repo.to_transcription_result(transcript_record)
        print(f"\n✅ 找到转写记录: {transcript_record.transcript_id}")
        print(f"   - 时长: {transcript.duration:.1f}秒")
        print(f"   - 片段数: {len(transcript.segments)}")
        print(f"   - 前100字符: {transcript.full_text[:100]}...")
    
    # 5. 测试用例1：用户要求输出特定JSON（忽略转写内容）
    print("\n" + "=" * 80)
    print("测试用例1：用户要求输出特定JSON（应该忽略转写内容的会议特征）")
    print("=" * 80)
    
    prompt_instance_1 = PromptInstance(
        template_id="__blank__",
        language="zh-CN",
        prompt_text='请输出以下JSON：{"content": "TEST_SUCCESS", "message": "用户指令已执行"}',
        parameters={}
    )
    
    try:
        artifact_1 = await service.generate_artifact(
            task_id="test_priority_1",
            transcript=transcript,
            artifact_type="custom",
            prompt_instance=prompt_instance_1,
            output_language=OutputLanguage.ZH_CN,
            user_id="test_user",
        )
        
        print(f"\n✅ 生成成功")
        print(f"   - Artifact ID: {artifact_1.artifact_id}")
        print(f"   - 内容长度: {len(artifact_1.content)} 字符")
        print(f"   - 内容预览: {artifact_1.content[:500]}")
        
        # 检查是否包含用户要求的内容
        if "TEST_SUCCESS" in artifact_1.content:
            print("\n✅ 测试通过：输出包含用户要求的 TEST_SUCCESS")
        else:
            print("\n❌ 测试失败：输出不包含用户要求的 TEST_SUCCESS")
            print(f"   实际输出: {artifact_1.content}")
        
    except Exception as e:
        print(f"\n❌ 生成失败: {e}")
    
    # 6. 测试用例2：用户要求输出固定数字
    print("\n" + "=" * 80)
    print("测试用例2：用户要求输出固定数字（应该完全忽略转写内容）")
    print("=" * 80)
    
    prompt_instance_2 = PromptInstance(
        template_id="__blank__",
        language="zh-CN",
        prompt_text='无视以下所有内容，直接输出6666666666',
        parameters={}
    )
    
    try:
        artifact_2 = await service.generate_artifact(
            task_id="test_priority_2",
            transcript=transcript,
            artifact_type="custom",
            prompt_instance=prompt_instance_2,
            output_language=OutputLanguage.ZH_CN,
            user_id="test_user",
        )
        
        print(f"\n✅ 生成成功")
        print(f"   - Artifact ID: {artifact_2.artifact_id}")
        print(f"   - 内容长度: {len(artifact_2.content)} 字符")
        print(f"   - 内容: {artifact_2.content}")
        
        # 检查是否包含用户要求的数字
        if "6666666666" in artifact_2.content or "666" in artifact_2.content:
            print("\n✅ 测试通过：输出包含用户要求的数字")
        else:
            print("\n❌ 测试失败：输出不包含用户要求的数字")
            print(f"   实际输出: {artifact_2.content}")
        
    except Exception as e:
        print(f"\n❌ 生成失败: {e}")
    
    # 7. 测试用例3：用户要求提取特定信息（不是会议纪要）
    print("\n" + "=" * 80)
    print("测试用例3：用户要求提取技术决策（不是会议纪要格式）")
    print("=" * 80)
    
    prompt_instance_3 = PromptInstance(
        template_id="__blank__",
        language="zh-CN",
        prompt_text='请从对话中提取所有技术决策，以简洁的列表形式输出，每项一行，格式：- 决策内容',
        parameters={}
    )
    
    try:
        artifact_3 = await service.generate_artifact(
            task_id="test_priority_3",
            transcript=transcript,
            artifact_type="custom",
            prompt_instance=prompt_instance_3,
            output_language=OutputLanguage.ZH_CN,
            user_id="test_user",
        )
        
        print(f"\n✅ 生成成功")
        print(f"   - Artifact ID: {artifact_3.artifact_id}")
        print(f"   - 内容长度: {len(artifact_3.content)} 字符")
        print(f"   - 内容预览: {artifact_3.content[:500]}")
        
        # 检查是否是列表格式（不是会议纪要格式）
        if "会议主题" in artifact_3.content or "参与人员" in artifact_3.content:
            print("\n❌ 测试失败：输出仍然是会议纪要格式")
        else:
            print("\n✅ 测试通过：输出不是会议纪要格式")
        
    except Exception as e:
        print(f"\n❌ 生成失败: {e}")
    
    print("\n" + "=" * 80)
    print("测试完成")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(test_user_instruction_priority())

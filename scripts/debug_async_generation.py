"""调试异步生成问题"""

import sys
import os
import asyncio

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.database.session import get_session
from src.database.repositories import (
    ArtifactRepository,
    TranscriptRepository,
    SpeakerMappingRepository,
    PromptTemplateRepository,
    TaskRepository,
)
from src.services.artifact_generation import ArtifactGenerationService
from src.services.correction import CorrectionService
from src.core.models import OutputLanguage, PromptInstance
from src.config.loader import get_config
from src.providers.gemini_llm import GeminiLLMProvider

async def test_async_generation():
    """测试异步生成逻辑"""
    
    # 使用最新的 artifact
    artifact_id = "artifact_e4915abadb624bdd"
    task_id = "task_dadac03a8f3048ef"
    
    print(f"测试 artifact: {artifact_id}")
    print(f"任务 ID: {task_id}")
    
    db = get_session()
    
    try:
        # 1. 获取 artifact 信息
        artifact_repo = ArtifactRepository(db)
        artifact = artifact_repo.get_by_id(artifact_id)
        
        if not artifact:
            print(f"❌ Artifact 不存在")
            return
        
        print(f"\n✅ Artifact 存在")
        print(f"   状态: {artifact.state}")
        print(f"   类型: {artifact.artifact_type}")
        print(f"   Display Name: {artifact.display_name}")
        
        # 2. 获取转写结果
        print(f"\n2. 获取转写结果...")
        transcript_repo = TranscriptRepository(db)
        transcript = transcript_repo.get_by_task_id(task_id)
        
        if not transcript:
            print(f"❌ 转写记录不存在")
            return
        
        print(f"✅ 转写记录存在，片段数: {len(transcript.segments)}")
        
        # 转换转写记录为 TranscriptionResult
        transcript_result = transcript_repo.to_transcription_result(transcript)
        
        # 3. 获取说话人映射
        print(f"\n3. 获取说话人映射...")
        speaker_mapping_repo = SpeakerMappingRepository(db)
        speaker_mapping = speaker_mapping_repo.get_mapping_dict(task_id)
        print(f"说话人映射: {speaker_mapping}")
        
        # 应用说话人映射
        if speaker_mapping:
            correction_service = CorrectionService()
            transcript_result = await correction_service.correct_speakers(transcript_result, speaker_mapping)
            print(f"✅ 已应用说话人映射")
        
        # 4. 创建 LLM provider
        print(f"\n4. 创建 LLM provider...")
        config = get_config()
        llm_provider = GeminiLLMProvider(config.gemini)
        print(f"✅ LLM provider 创建成功")
        
        # 5. 创建 ArtifactGenerationService
        print(f"\n5. 创建 ArtifactGenerationService...")
        template_repo = PromptTemplateRepository(db)
        
        artifact_service = ArtifactGenerationService(
            llm_provider=llm_provider,
            template_repo=template_repo,
            artifact_repo=artifact_repo,
        )
        print(f"✅ ArtifactGenerationService 创建成功")
        
        # 6. 准备参数
        print(f"\n6. 准备生成参数...")
        prompt_instance = PromptInstance(
            template_id=artifact.prompt_instance.get("template_id", "__blank__"),
            language=artifact.prompt_instance.get("language", "zh-CN"),
            parameters=artifact.prompt_instance.get("parameters", {}),
            prompt_text=artifact.prompt_instance.get("prompt_text"),
        )
        
        print(f"   template_id: {prompt_instance.template_id}")
        print(f"   language: {prompt_instance.language}")
        print(f"   prompt_text: {prompt_instance.prompt_text[:100] if prompt_instance.prompt_text else 'None'}...")
        
        # 7. 调用生成
        print(f"\n7. 调用 generate_artifact...")
        print(f"   传入 artifact_id: {artifact_id}")
        
        output_lang = OutputLanguage.ZH_CN
        generated_artifact = await artifact_service.generate_artifact(
            task_id=task_id,
            transcript=transcript_result,
            artifact_type=artifact.artifact_type,
            prompt_instance=prompt_instance,
            output_language=output_lang,
            user_id=artifact.created_by,
            template=None,
            artifact_id=artifact_id,  # 关键：传入 artifact_id
        )
        
        print(f"\n✅ 生成成功！")
        print(f"   返回的 artifact_id: {generated_artifact.artifact_id}")
        print(f"   是否匹配: {generated_artifact.artifact_id == artifact_id}")
        print(f"   内容预览: {str(generated_artifact.content)[:200]}...")
        
        # 8. 检查数据库中的状态
        print(f"\n8. 检查数据库中的状态...")
        db.refresh(artifact)
        print(f"   数据库中的状态: {artifact.state}")
        print(f"   内容: {str(artifact.content)[:200]}...")
        
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    print("=" * 60)
    print("调试异步生成问题")
    print("=" * 60)
    
    asyncio.run(test_async_generation())

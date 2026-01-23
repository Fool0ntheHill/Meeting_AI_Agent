"""
重试使用空白模板失败的任务

验证修复后，空白模板任务可以正常生成 artifact
"""

import asyncio
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.database.session import get_session
from src.database.repositories import TaskRepository, TranscriptRepository
from src.services.artifact_generation import ArtifactGenerationService
from src.providers.gemini_llm import GeminiLLMProvider
from src.config.loader import load_config
from src.core.models import PromptInstance


async def retry_task(task_id: str):
    """重试失败的任务"""
    
    print("=" * 60)
    print(f"重试任务: {task_id}")
    print("=" * 60)
    
    # 加载配置
    config = load_config()
    
    with get_session() as session:
        task_repo = TaskRepository(session)
        transcript_repo = TranscriptRepository(session)
        
        # 获取任务
        task = task_repo.get_by_id(task_id)
        if not task:
            print(f"✗ 任务不存在: {task_id}")
            return
        
        print(f"\n任务信息:")
        print(f"  状态: {task.state}")
        print(f"  错误: {task.error_message}")
        print(f"  音频时长: {task.audio_duration}s")
        
        # 获取转录结果
        transcript = transcript_repo.get_by_task_id(task_id)
        if not transcript:
            print(f"✗ 没有找到转录结果")
            return
        
        print(f"  转录段数: {len(transcript.segments)}")
        
        # 创建 LLM provider
        llm = GeminiLLMProvider(config.llm)
        
        # 创建 artifact generation service
        artifact_service = ArtifactGenerationService(
            llm=llm,
            templates=None  # 不使用模板仓库
        )
        
        # 创建空白模板的 prompt instance
        prompt_instance = PromptInstance(
            template_id="__blank__",
            language="zh-CN",
            custom_instructions="请根据会议内容生成详细的会议纪要，包括：\n1. 会议主题\n2. 参会人员\n3. 讨论要点\n4. 决策事项\n5. 待办事项"
        )
        
        print(f"\n开始生成 artifact...")
        print(f"  模板 ID: {prompt_instance.template_id}")
        print(f"  语言: {prompt_instance.language}")
        print(f"  自定义指令: {prompt_instance.custom_instructions[:50]}...")
        
        try:
            # 生成 artifact
            artifact = await artifact_service.generate_artifact(
                task_id=task_id,
                transcript=transcript,
                artifact_type="meeting_minutes",
                prompt_instance=prompt_instance,
                output_language="zh-CN"
            )
            
            print(f"\n✓ Artifact 生成成功!")
            print(f"  Artifact ID: {artifact.artifact_id}")
            print(f"  类型: {artifact.artifact_type}")
            print(f"  版本: {artifact.version}")
            print(f"  内容长度: {len(artifact.content)} 字符")
            print(f"\n内容预览:")
            print("-" * 60)
            print(artifact.content[:500])
            if len(artifact.content) > 500:
                print("...")
            print("-" * 60)
            
            # 更新任务状态为完成
            task_repo.update_state(
                task_id=task_id,
                state="completed",
                progress=100.0
            )
            session.commit()
            
            print(f"\n✓ 任务状态已更新为 completed")
            
        except Exception as e:
            print(f"\n✗ 生成失败: {e}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("用法: python scripts/retry_blank_template_task.py <task_id>")
        print("示例: python scripts/retry_blank_template_task.py task_71bd819743244a01")
        sys.exit(1)
    
    task_id = sys.argv[1]
    asyncio.run(retry_task(task_id))

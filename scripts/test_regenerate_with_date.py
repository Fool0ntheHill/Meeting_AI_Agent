#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""测试重新生成时是否传递了会议日期"""

import sys
import os
import asyncio
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.database.session import session_scope
from src.database.repositories import (
    TaskRepository,
    TranscriptRepository,
    ArtifactRepository,
    PromptTemplateRepository,
)
from src.services.artifact_generation import ArtifactGenerationService
from src.providers.gemini_llm import GeminiLLM
from src.core.models import PromptInstance, OutputLanguage
from src.config.loader import load_config

async def test_regenerate():
    config = load_config()
    
    with session_scope() as db:
        task_repo = TaskRepository(db)
        transcript_repo = TranscriptRepository(db)
        artifact_repo = ArtifactRepository(db)
        template_repo = PromptTemplateRepository(db)
        
        # 获取任务
        task = task_repo.get_by_id('task_7168f79dbb6147cc')
        print(f"任务: {task.task_id}")
        print(f"会议日期: {task.meeting_date}")
        print(f"会议时间: {task.meeting_time}")
        
        # 获取转写
        transcript_record = transcript_repo.get_by_task_id(task.task_id)
        transcript = transcript_repo.to_transcription_result(transcript_record)
        print(f"\n转写: {len(transcript.segments)} segments")
        print(f"前3个说话人: {[seg.speaker for seg in transcript.segments[:3]]}")
        
        # 创建 prompt_instance
        prompt_instance = PromptInstance(
            template_id="tpl_805016c71090",
            language="zh-CN",
            prompt_text="统计一下说话人说话的句数",
            parameters={},
            custom_instructions=None,
        )
        
        # 初始化服务
        llm = GeminiLLM(config=config.llm)
        service = ArtifactGenerationService(
            llm_provider=llm,
            template_repo=template_repo,
            artifact_repo=artifact_repo,
        )
        
        # 生成 artifact
        print("\n开始生成...")
        artifact = await service.generate_artifact(
            task_id=task.task_id,
            transcript=transcript,
            artifact_type="meeting_minutes",
            prompt_instance=prompt_instance,
            output_language=OutputLanguage.ZH_CN,
            user_id=task.user_id,
            template=None,
            meeting_date=task.meeting_date,  # 传递会议日期
            meeting_time=task.meeting_time,  # 传递会议时间
        )
        
        print(f"\n✅ 生成成功: {artifact.artifact_id}")
        print(f"版本: {artifact.version}")
        
        # 检查内容
        content = artifact.get_content_dict()
        if 'meeting_info' in content:
            print(f"\n会议信息:")
            print(f"  标题: {content['meeting_info'].get('title')}")
            print(f"  日期: {content['meeting_info'].get('date')}")
            print(f"  时间: {content['meeting_info'].get('time')}")
            print(f"  参与者: {content['meeting_info'].get('participants')}")

if __name__ == "__main__":
    asyncio.run(test_regenerate())

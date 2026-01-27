"""调试脚本：检查会议时间是否被添加到提示词中"""

import asyncio
import logging
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.database.session import session_scope
from src.database.repositories import (
    TaskRepository,
    TranscriptRepository,
    PromptTemplateRepository,
)
from src.providers.gemini_llm import GeminiLLM
from src.config.loader import get_config
from src.core.models import PromptInstance, OutputLanguage

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


async def debug_meeting_time_in_prompt(task_id: str):
    """
    调试会议时间是否被添加到提示词中
    
    Args:
        task_id: 任务 ID
    """
    print("=" * 80)
    print(f"  调试任务 {task_id} 的会议时间传递")
    print("=" * 80)
    print()
    
    with session_scope() as db:
        task_repo = TaskRepository(db)
        transcript_repo = TranscriptRepository(db)
        template_repo = PromptTemplateRepository(db)
        
        # 1. 获取任务信息
        task = task_repo.get_by_id(task_id)
        if not task:
            print(f"❌ 任务不存在: {task_id}")
            return
        
        print("1. 任务信息:")
        print(f"   - 任务 ID: {task.task_id}")
        print(f"   - 会议日期: {task.meeting_date}")
        print(f"   - 会议时间: {task.meeting_time}")
        print(f"   - 原始文件名: {task.original_filenames}")
        print()
        
        # 2. 获取转写记录
        transcript_record = transcript_repo.get_by_task_id(task_id)
        if not transcript_record:
            print(f"❌ 转写记录不存在")
            return
        
        transcript = transcript_repo.to_transcription_result(transcript_record)
        print("2. 转写记录:")
        print(f"   - 转写 ID: {transcript_record.transcript_id}")
        print(f"   - 片段数: {len(transcript.segments)}")
        print(f"   - 时长: {transcript.duration}s")
        print()
        
        # 3. 获取提示词模板
        template = template_repo.get_by_id("meeting_minutes_standard")
        if not template:
            print(f"❌ 提示词模板不存在")
            return
        
        print("3. 提示词模板:")
        print(f"   - 模板 ID: {template.template_id}")
        print(f"   - 模板名称: {template.name}")
        print(f"   - 提示词长度: {len(template.prompt_body)} 字符")
        print()
        
        # 4. 构建提示词实例
        prompt_instance = PromptInstance(
            template_id=template.template_id,
            language="zh-CN",
            parameters={},
            custom_instructions=None,
            prompt_text=None,
        )
        
        # 5. 初始化 LLM 提供商
        config = get_config()
        llm = GeminiLLM(config.gemini)
        
        # 6. 调用 _build_prompt 方法（不实际调用 API）
        print("4. 构建提示词（包含会议时间）:")
        print()
        
        prompt = llm._build_prompt(
            template=template,
            prompt_instance=prompt_instance,
            formatted_transcript=llm.format_transcript(transcript),
            output_language=OutputLanguage.ZH_CN,
            meeting_date=task.meeting_date,
            meeting_time=task.meeting_time,
        )
        
        # 7. 检查提示词中是否包含会议时间
        print("=" * 80)
        print("  提示词内容分析")
        print("=" * 80)
        print()
        
        print(f"提示词总长度: {len(prompt)} 字符")
        print()
        
        # 检查是否包含会议时间相关的关键词
        has_meeting_time_section = "## 会议时间" in prompt
        has_date = task.meeting_date and task.meeting_date in prompt if task.meeting_date else False
        has_time = task.meeting_time and task.meeting_time in prompt if task.meeting_time else False
        
        print("会议时间检查:")
        print(f"   - 包含 '## 会议时间' 标题: {'✅' if has_meeting_time_section else '❌'}")
        print(f"   - 包含会议日期 ({task.meeting_date}): {'✅' if has_date else '❌'}")
        print(f"   - 包含会议时间 ({task.meeting_time}): {'✅' if has_time else '❌'}")
        print()
        
        # 8. 显示提示词的最后 1000 个字符（会议时间应该在这里）
        print("=" * 80)
        print("  提示词末尾内容（最后 1000 字符）")
        print("=" * 80)
        print()
        print(prompt[-1000:])
        print()
        
        # 9. 如果没有会议时间，显示完整的提示词结构
        if not has_meeting_time_section:
            print("=" * 80)
            print("  ⚠️  提示词中没有找到会议时间！")
            print("=" * 80)
            print()
            print("提示词结构分析:")
            
            # 查找所有的 ## 标题
            lines = prompt.split('\n')
            sections = []
            for i, line in enumerate(lines):
                if line.startswith('##'):
                    sections.append((i, line))
            
            print(f"找到 {len(sections)} 个章节标题:")
            for line_num, section in sections:
                print(f"   第 {line_num} 行: {section}")
            print()
        
        # 10. 测试 format_meeting_datetime 函数
        print("=" * 80)
        print("  测试 format_meeting_datetime 函数")
        print("=" * 80)
        print()
        
        from src.utils.meeting_metadata import format_meeting_datetime
        
        formatted = format_meeting_datetime(task.meeting_date, task.meeting_time)
        print(f"输入:")
        print(f"   - meeting_date: {task.meeting_date}")
        print(f"   - meeting_time: {task.meeting_time}")
        print(f"输出:")
        print(f"   - formatted: '{formatted}'")
        print(f"   - 是否为空: {not formatted}")
        print()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python scripts/debug_meeting_time_in_prompt.py <task_id>")
        sys.exit(1)
    
    task_id = sys.argv[1]
    asyncio.run(debug_meeting_time_in_prompt(task_id))

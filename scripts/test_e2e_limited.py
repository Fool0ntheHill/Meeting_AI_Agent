#!/usr/bin/env python3
"""
端到端集成测试脚本 (限制输出长度版本)

此脚本测试完整的会议处理流程,并限制输出长度以避免音频二进制数据输出问题:
1. 音频转写 (ASR)
2. 说话人识别 (可选)
3. ASR 修正
4. 生成会议纪要

使用方法:
    python scripts/test_e2e_limited.py --audio meeting.wav
    python scripts/test_e2e_limited.py --audio meeting.wav --skip-speaker-recognition
    python scripts/test_e2e_limited.py --audio part1.wav part2.wav --file-order 0 1
"""

import argparse
import asyncio
import json
import logging
import sys
import yaml
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config.loader import ConfigLoader
from src.config.models import AppConfig
from src.core.models import (
    ASRLanguage,
    OutputLanguage,
    PromptInstance,
    PromptTemplate,
)
from src.providers.azure_asr import AzureASR
from src.providers.gemini_llm import GeminiLLM
from src.providers.iflytek_voiceprint import IFlyTekVoiceprint
from src.providers.volcano_asr import VolcanoASR
from src.services.artifact_generation import ArtifactGenerationService
from src.services.correction import CorrectionService
from src.services.pipeline import PipelineService
from src.services.speaker_recognition import SpeakerRecognitionService
from src.services.transcription import TranscriptionService
from src.utils.audio import AudioProcessor
from src.utils.logger import get_logger
from src.utils.storage import StorageClient

# 设置日志
logger = get_logger("e2e_test_limited")


def truncate_string(s: str, max_length: int = 100) -> str:
    """截断字符串到指定长度"""
    if len(s) <= max_length:
        return s
    return s[:max_length] + f"... (共 {len(s)} 字符)"


def truncate_bytes(b: bytes, max_length: int = 50) -> str:
    """截断字节数据并转换为可读字符串"""
    if len(b) <= max_length:
        return f"<bytes: {len(b)} bytes>"
    return f"<bytes: {len(b)} bytes, 前 {max_length} bytes: {b[:max_length].hex()}...>"


def safe_repr(obj: any, max_length: int = 200) -> str:
    """安全地表示对象,避免输出过长的二进制数据"""
    if isinstance(obj, bytes):
        return truncate_bytes(obj)
    elif isinstance(obj, str):
        return truncate_string(obj, max_length)
    elif isinstance(obj, dict):
        result = {}
        for k, v in obj.items():
            result[k] = safe_repr(v, max_length)
        return result
    elif isinstance(obj, list):
        return [safe_repr(item, max_length) for item in obj]
    else:
        s = str(obj)
        return truncate_string(s, max_length)


def create_sample_template() -> PromptTemplate:
    """创建示例提示词模板"""
    return PromptTemplate(
        template_id="tpl_test_001",
        title="测试会议纪要模板",
        description="用于端到端测试的会议纪要模板",
        prompt_body="""你是一个专业的会议纪要助手。

会议信息:
{meeting_description}

请根据以下会议转写生成结构化的会议纪要,以 JSON 格式返回,包含以下字段:
- title: 会议标题
- participants: 参与者列表(数组)
- summary: 会议摘要(简短概括)
- key_points: 关键要点(数组)
- action_items: 行动项(数组)

请确保返回的是有效的 JSON 格式。""",
        artifact_type="meeting_minutes",
        supported_languages=["zh-CN", "en-US"],
        parameter_schema={
            "meeting_description": {
                "type": "string",
                "required": False,
                "default": "",
                "description": "会议描述信息",
            }
        },
        is_system=True,
    )


async def test_pipeline(
    config: AppConfig,
    audio_files: list[str],
    file_order: list[int],
    skip_speaker_recognition: bool = False,
    meeting_description: str = "测试会议",
) -> None:
    """
    测试完整的管线流程
    
    Args:
        config: 应用配置
        audio_files: 音频文件列表
        file_order: 文件排序
        skip_speaker_recognition: 是否跳过说话人识别
        meeting_description: 会议描述
    """
    logger.info("=" * 80)
    logger.info("开始端到端集成测试 (限制输出版本)")
    logger.info("=" * 80)
    
    # 1. 初始化所有服务
    logger.info("\n[1/7] 初始化服务...")
    
    # 初始化提供商
    volcano_asr = VolcanoASR(config.volcano)
    azure_asr = AzureASR(config.azure)
    iflytek_voiceprint = IFlyTekVoiceprint(config.iflytek)
    gemini_llm = GeminiLLM(config.gemini)
    
    # 初始化工具
    audio_processor = AudioProcessor()
    storage_client = StorageClient(
        bucket=config.storage.bucket,
        region=config.storage.region,
        access_key=config.storage.access_key,
        secret_key=config.storage.secret_key,
    )
    
    # 初始化服务
    transcription_service = TranscriptionService(
        primary_asr=volcano_asr,
        fallback_asr=azure_asr,
        audio_processor=audio_processor,
        storage_client=storage_client,
    )
    
    speaker_recognition_service = SpeakerRecognitionService(
        voiceprint_provider=iflytek_voiceprint,
        audio_processor=audio_processor,
        storage_client=storage_client,
    )
    
    correction_service = CorrectionService()
    
    artifact_generation_service = ArtifactGenerationService(
        llm_provider=gemini_llm,
    )
    
    # 初始化管线服务
    pipeline_service = PipelineService(
        transcription_service=transcription_service,
        speaker_recognition_service=speaker_recognition_service,
        correction_service=correction_service,
        artifact_generation_service=artifact_generation_service,
    )
    
    logger.info("✓ 服务初始化完成")
    
    # 2. 准备测试数据
    logger.info("\n[2/7] 准备测试数据...")
    
    task_id = f"test_task_{asyncio.get_event_loop().time()}"
    
    # 创建提示词实例
    template = create_sample_template()
    prompt_instance = PromptInstance(
        template_id=template.template_id,
        language="zh-CN",
        parameters={"meeting_description": f"会议标题: {meeting_description}"},
    )
    
    logger.info(f"✓ 任务 ID: {task_id}")
    logger.info(f"✓ 音频文件: {audio_files}")
    logger.info(f"✓ 文件排序: {file_order}")
    logger.info(f"✓ 跳过说话人识别: {skip_speaker_recognition}")
    
    # 3. 执行管线处理
    logger.info("\n[3/7] 开始管线处理...")
    
    try:
        artifact = await pipeline_service.process_meeting(
            task_id=task_id,
            audio_files=audio_files,
            file_order=file_order,
            prompt_instance=prompt_instance,
            user_id="test_user",
            tenant_id="test_tenant",
            asr_language=ASRLanguage.ZH_EN,
            output_language=OutputLanguage.ZH_CN,
            skip_speaker_recognition=skip_speaker_recognition,
            template=template,
        )
        
        logger.info("✓ 管线处理完成")
        
    except Exception as e:
        logger.error(f"✗ 管线处理失败: {e}")
        # 限制异常信息输出长度
        import traceback
        tb = traceback.format_exc()
        logger.error(f"异常堆栈 (前 1000 字符):\n{tb[:1000]}")
        raise
    
    # 4. 显示结果 (限制输出长度)
    logger.info("\n[4/7] 处理结果:")
    logger.info(f"  - Artifact ID: {artifact.artifact_id}")
    logger.info(f"  - 任务 ID: {artifact.task_id}")
    logger.info(f"  - 内容类型: {artifact.artifact_type}")
    logger.info(f"  - 版本: {artifact.version}")
    logger.info(f"  - 创建者: {artifact.created_by}")
    logger.info(f"  - 创建时间: {artifact.created_at}")
    
    # 限制内容输出长度
    content_preview = truncate_string(artifact.content, 500)
    logger.info(f"  - 内容预览: {content_preview}")
    
    # 5. 解析会议纪要
    logger.info("\n[5/7] 会议纪要内容:")
    
    try:
        content_dict = artifact.get_content_dict()
        
        # 限制输出长度
        safe_content = safe_repr(content_dict, max_length=300)
        logger.info(f"\n{json.dumps(safe_content, ensure_ascii=False, indent=2)}")
        
        # 验证必需字段
        required_fields = ["title", "participants", "summary", "key_points", "action_items"]
        missing_fields = [f for f in required_fields if f not in content_dict]
        
        if missing_fields:
            logger.warning(f"⚠ 缺少字段: {missing_fields}")
        else:
            logger.info("✓ 所有必需字段都存在")
            
    except Exception as e:
        logger.error(f"✗ 解析内容失败: {e}")
        content_preview = truncate_string(artifact.content, 500)
        logger.info(f"原始内容预览: {content_preview}")
    
    # 6. 统计信息
    logger.info("\n[6/7] 统计信息:")
    
    meeting_minutes = artifact.get_meeting_minutes()
    if meeting_minutes:
        logger.info(f"  - 会议标题: {meeting_minutes.title}")
        logger.info(f"  - 参与者数量: {len(meeting_minutes.participants)}")
        logger.info(f"  - 参与者: {', '.join(meeting_minutes.participants)}")
        logger.info(f"  - 关键要点数量: {len(meeting_minutes.key_points)}")
        logger.info(f"  - 行动项数量: {len(meeting_minutes.action_items)}")
        
        # 显示关键要点 (限制长度)
        if meeting_minutes.key_points:
            logger.info("  - 关键要点:")
            for i, point in enumerate(meeting_minutes.key_points[:5], 1):  # 最多显示 5 个
                logger.info(f"    {i}. {truncate_string(point, 100)}")
            if len(meeting_minutes.key_points) > 5:
                logger.info(f"    ... 还有 {len(meeting_minutes.key_points) - 5} 个要点")
        
        # 显示行动项 (限制长度)
        if meeting_minutes.action_items:
            logger.info("  - 行动项:")
            for i, item in enumerate(meeting_minutes.action_items[:5], 1):  # 最多显示 5 个
                logger.info(f"    {i}. {truncate_string(item, 100)}")
            if len(meeting_minutes.action_items) > 5:
                logger.info(f"    ... 还有 {len(meeting_minutes.action_items) - 5} 个行动项")
    
    # 7. 测试完成
    logger.info("\n[7/7] 测试完成!")
    logger.info("=" * 80)
    logger.info("✓ 端到端集成测试成功")
    logger.info("=" * 80)


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="端到端集成测试脚本 (限制输出长度版本)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 测试单个音频文件
  python scripts/test_e2e_limited.py --audio meeting.wav
  
  # 测试多个音频文件
  python scripts/test_e2e_limited.py --audio part1.wav part2.wav --file-order 0 1
  
  # 跳过说话人识别
  python scripts/test_e2e_limited.py --audio meeting.wav --skip-speaker-recognition
  
  # 指定会议描述
  python scripts/test_e2e_limited.py --audio meeting.wav --description "产品规划会议"
        """,
    )
    
    parser.add_argument(
        "--audio",
        nargs="+",
        required=True,
        help="音频文件路径(支持多个文件)",
    )
    
    parser.add_argument(
        "--file-order",
        nargs="+",
        type=int,
        help="文件排序索引(默认按提供顺序)",
    )
    
    parser.add_argument(
        "--skip-speaker-recognition",
        action="store_true",
        help="跳过说话人识别",
    )
    
    parser.add_argument(
        "--description",
        default="测试会议",
        help="会议描述",
    )
    
    parser.add_argument(
        "--config",
        default="config/test.yaml",
        help="配置文件路径(默认: config/test.yaml)",
    )
    
    args = parser.parse_args()
    
    # 验证音频文件存在
    for audio_file in args.audio:
        if not Path(audio_file).exists():
            logger.error(f"音频文件不存在: {audio_file}")
            sys.exit(1)
    
    # 设置文件排序
    file_order = args.file_order
    if file_order is None:
        file_order = list(range(len(args.audio)))
    elif len(file_order) != len(args.audio):
        logger.error("文件排序索引数量必须与音频文件数量相同")
        sys.exit(1)
    
    # 加载配置
    logger.info(f"加载配置: {args.config}")
    
    try:
        config_file = Path(args.config)
        if not config_file.exists():
            logger.error(f"配置文件不存在: {args.config}")
            sys.exit(1)
        
        # 直接读取 YAML 文件
        with open(config_file, "r", encoding="utf-8") as f:
            import yaml
            config_data = yaml.safe_load(f)
        
        # 使用 ConfigLoader 的环境变量替换功能
        config_loader = ConfigLoader()
        config_data = config_loader._substitute_env_vars(config_data)
        
        # 创建配置对象
        config = AppConfig(**config_data)
        logger.info("✓ 配置加载成功")
    except Exception as e:
        logger.error(f"✗ 配置加载失败: {e}")
        sys.exit(1)
    
    # 运行测试
    try:
        asyncio.run(
            test_pipeline(
                config=config,
                audio_files=args.audio,
                file_order=file_order,
                skip_speaker_recognition=args.skip_speaker_recognition,
                meeting_description=args.description,
            )
        )
    except KeyboardInterrupt:
        logger.info("\n测试被用户中断")
        sys.exit(1)
    except Exception as e:
        logger.error(f"\n测试失败: {e}")
        # 限制异常信息输出长度
        import traceback
        tb = traceback.format_exc()
        logger.error(f"异常堆栈 (前 2000 字符):\n{tb[:2000]}")
        sys.exit(1)


if __name__ == "__main__":
    main()

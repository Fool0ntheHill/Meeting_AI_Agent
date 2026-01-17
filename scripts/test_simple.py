#!/usr/bin/env python3
"""
简化测试脚本 - 跳过 TOS 上传,直接测试 LLM 生成

此脚本用于测试 LLM 生成功能,跳过 ASR 和声纹识别步骤。
"""

import argparse
import asyncio
import json
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config.loader import ConfigLoader
from src.config.models import AppConfig
from src.core.models import (
    GeneratedArtifact,
    PromptInstance,
    PromptTemplate,
    Segment,
    TranscriptionResult,
)
from src.providers.gemini_llm import GeminiLLM
from src.services.artifact_generation import ArtifactGenerationService
from src.utils.logger import get_logger

logger = get_logger("simple_test")


def create_sample_template() -> PromptTemplate:
    """创建示例提示词模板"""
    return PromptTemplate(
        template_id="tpl_test_001",
        title="测试会议纪要模板",
        description="用于测试的会议纪要模板",
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


def create_mock_transcript() -> TranscriptionResult:
    """创建模拟的转写结果"""
    segments = [
        Segment(
            text="大家好,今天我们讨论一下 ONE 产品和业务规则中心的设计。",
            start_time=0.0,
            end_time=5.0,
            speaker="说话人1",
        ),
        Segment(
            text="好的,我先介绍一下背景。我们需要一个统一的业务规则管理平台。",
            start_time=5.5,
            end_time=10.0,
            speaker="说话人2",
        ),
        Segment(
            text="这个平台需要支持规则的版本管理和灰度发布。",
            start_time=10.5,
            end_time=15.0,
            speaker="说话人2",
        ),
        Segment(
            text="我觉得我们还需要考虑规则的优先级和冲突处理。",
            start_time=15.5,
            end_time=20.0,
            speaker="说话人1",
        ),
        Segment(
            text="对,这个很重要。我们可以参考一下业界的最佳实践。",
            start_time=20.5,
            end_time=25.0,
            speaker="说话人3",
        ),
        Segment(
            text="那我们下一步的行动计划是什么?",
            start_time=25.5,
            end_time=28.0,
            speaker="说话人1",
        ),
        Segment(
            text="我负责整理需求文档,下周一之前完成。",
            start_time=28.5,
            end_time=32.0,
            speaker="说话人2",
        ),
        Segment(
            text="我来调研技术方案,周三给大家分享。",
            start_time=32.5,
            end_time=36.0,
            speaker="说话人3",
        ),
    ]

    return TranscriptionResult(
        segments=segments,
        full_text=" ".join([seg.text for seg in segments]),
        duration=36.0,
        language="zh-CN",
        provider="mock",
    )


async def test_llm_generation(
    config: AppConfig,
    meeting_description: str = "ONE产品和业务规则中心的设计讨论会议",
) -> None:
    """
    测试 LLM 生成功能

    Args:
        config: 应用配置
        meeting_description: 会议描述
    """
    logger.info("=" * 80)
    logger.info("开始简化测试 - 仅测试 LLM 生成")
    logger.info("=" * 80)

    # 1. 初始化服务
    logger.info("\n[1/5] 初始化服务...")
    gemini_llm = GeminiLLM(config.gemini)
    artifact_generation_service = ArtifactGenerationService(llm_provider=gemini_llm)
    logger.info("✓ 服务初始化完成")

    # 2. 准备测试数据
    logger.info("\n[2/5] 准备测试数据...")
    task_id = "test_task_simple"
    template = create_sample_template()
    prompt_instance = PromptInstance(
        template_id=template.template_id,
        language="zh-CN",
        parameters={"meeting_description": f"会议标题: {meeting_description}"},
    )
    transcript = create_mock_transcript()
    logger.info(f"✓ 任务 ID: {task_id}")
    logger.info(f"✓ 模拟转写: {len(transcript.segments)} 个片段")

    # 3. 生成会议纪要
    logger.info("\n[3/5] 生成会议纪要...")
    try:
        artifact = await artifact_generation_service.generate_artifact(
            task_id=task_id,
            transcript=transcript,
            prompt_instance=prompt_instance,
            template=template,
            artifact_type="meeting_minutes",
            user_id="test_user",
            tenant_id="test_tenant",
        )
        logger.info("✓ 会议纪要生成完成")
    except Exception as e:
        logger.error(f"✗ 生成失败: {e}", exc_info=True)
        raise

    # 4. 显示结果
    logger.info("\n[4/5] 处理结果:")
    logger.info(f"  - Artifact ID: {artifact.artifact_id}")
    logger.info(f"  - 任务 ID: {artifact.task_id}")
    logger.info(f"  - 内容类型: {artifact.artifact_type}")
    logger.info(f"  - 版本: {artifact.version}")
    logger.info(f"  - 创建者: {artifact.created_by}")

    # 5. 解析会议纪要
    logger.info("\n[5/5] 会议纪要内容:")
    try:
        content_dict = artifact.get_content_dict()
        logger.info(f"\n{json.dumps(content_dict, ensure_ascii=False, indent=2)}")

        # 验证必需字段
        required_fields = ["title", "participants", "summary", "key_points", "action_items"]
        missing_fields = [f for f in required_fields if f not in content_dict]

        if missing_fields:
            logger.warning(f"⚠ 缺少字段: {missing_fields}")
        else:
            logger.info("✓ 所有必需字段都存在")

    except Exception as e:
        logger.error(f"✗ 解析内容失败: {e}")
        logger.info(f"原始内容: {artifact.content}")

    # 测试完成
    logger.info("\n" + "=" * 80)
    logger.info("✓ 简化测试成功")
    logger.info("=" * 80)


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="简化测试脚本 - 仅测试 LLM 生成",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "--description",
        default="ONE产品和业务规则中心的设计讨论会议",
        help="会议描述",
    )

    parser.add_argument(
        "--config",
        default="config/test.yaml",
        help="配置文件路径(默认: config/test.yaml)",
    )

    args = parser.parse_args()

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
            test_llm_generation(
                config=config,
                meeting_description=args.description,
            )
        )
    except KeyboardInterrupt:
        logger.info("\n测试被用户中断")
        sys.exit(1)
    except Exception as e:
        logger.error(f"\n测试失败: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
诊断脚本 - 分别测试 TOS 和 ASR 功能

此脚本用于诊断问题出在哪个环节:
1. TOS 上传功能
2. 火山引擎 ASR 认证
3. 火山引擎 ASR 提交任务
"""

import argparse
import asyncio
import sys
import yaml
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config.loader import ConfigLoader
from src.config.models import AppConfig
from src.core.models import ASRLanguage
from src.providers.volcano_asr import VolcanoASR
from src.utils.logger import get_logger
from src.utils.storage import StorageClient

logger = get_logger("diagnose")


async def test_tos_upload(config: AppConfig, test_file: str) -> tuple[str, str]:
    """
    测试 TOS 上传功能
    
    Args:
        config: 应用配置
        test_file: 测试文件路径
        
    Returns:
        tuple[str, str]: (object_key, presigned_url)
    """
    logger.info("=" * 80)
    logger.info("测试 1: TOS 上传功能")
    logger.info("=" * 80)
    
    try:
        # 初始化存储客户端
        storage_client = StorageClient(
            bucket=config.storage.bucket,
            region=config.storage.region,
            access_key=config.storage.access_key,
            secret_key=config.storage.secret_key,
        )
        
        logger.info(f"\n配置信息:")
        logger.info(f"  - Bucket: {config.storage.bucket}")
        logger.info(f"  - Region: {config.storage.region}")
        logger.info(f"  - Access Key: {config.storage.access_key[:10]}...")
        
        # 上传文件
        logger.info(f"\n上传文件: {test_file}")
        
        import os
        from datetime import datetime
        
        filename = os.path.basename(test_file)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        object_key = f"audio/{timestamp}_{filename}"
        
        url = await storage_client.upload_file(test_file, object_key)
        
        logger.info(f"✓ 上传成功!")
        logger.info(f"  - Object Key: {object_key}")
        logger.info(f"  - URL: {url}")
        
        # 生成预签名 URL (24小时有效)
        logger.info(f"\n生成预签名 URL...")
        presigned_url = await storage_client.generate_presigned_url(
            object_key, expires_in=86400
        )
        logger.info(f"✓ 预签名 URL 生成成功!")
        logger.info(f"  - Presigned URL: {presigned_url[:100]}...")
        
        return object_key, presigned_url
        
    except Exception as e:
        logger.error(f"✗ TOS 上传失败: {e}", exc_info=True)
        raise


async def test_volcano_asr_auth(config: AppConfig) -> None:
    """
    测试火山引擎 ASR 认证 (V3 API)
    
    Args:
        config: 应用配置
    """
    logger.info("\n" + "=" * 80)
    logger.info("测试 2: 火山引擎 ASR 认证 (V3 API)")
    logger.info("=" * 80)
    
    logger.info(f"\n配置信息:")
    logger.info(f"  - App ID: {config.volcano.app_id}")
    logger.info(f"  - Access Key: {config.volcano.access_key[:10]}...")
    logger.info(f"  - Secret Key: {config.volcano.secret_key[:10]}...")
    logger.info(f"  - TOS Bucket: {config.volcano.tos_bucket}")
    
    logger.info(f"\nV3 API 端点:")
    logger.info(f"  - Submit URL: https://openspeech-direct.zijieapi.com/api/v3/auc/bigmodel/submit")
    logger.info(f"  - Query URL: https://openspeech-direct.zijieapi.com/api/v3/auc/bigmodel/query")
    logger.info(f"  - Resource ID: volc.bigasr.auc")
    
    logger.info(f"\nV3 API 认证方式 (HTTP Headers):")
    logger.info(f"  - X-Api-App-Key: {config.volcano.app_id}")
    logger.info(f"  - X-Api-Access-Key: {config.volcano.access_key[:20]}...")
    logger.info(f"  - X-Api-Resource-Id: volc.bigasr.auc")


async def test_volcano_asr_submit(config: AppConfig, audio_url: str) -> None:
    """
    测试火山引擎 ASR 提交任务 (V3 API)
    
    Args:
        config: 应用配置
        audio_url: 音频 URL
    """
    logger.info("\n" + "=" * 80)
    logger.info("测试 3: 火山引擎 ASR 提交任务 (V3 API)")
    logger.info("=" * 80)
    
    try:
        # 初始化 ASR 提供商
        volcano_asr = VolcanoASR(config.volcano)
        
        logger.info(f"\n音频 URL: {audio_url}")
        logger.info(f"语言: zh-CN+en-US (中英混合)")
        
        # 构建 V3 API 请求体(用于显示)
        request_body = {
            "user": {"uid": "test_user"},
            "audio": {
                "url": audio_url,
                "format": "ogg",
            },
            "request": {
                "model_name": "bigmodel",
                "enable_channel_split": False,
                "enable_ddc": True,
                "enable_speaker_info": True,
                "enable_punc": True,
                "enable_itn": True,
                "language": "",  # 空字符串表示中英混合
                "corpus": {
                    "correct_table_name": "",
                    "context": ""
                }
            },
        }
        
        logger.info(f"\nV3 API 请求体:")
        import json
        logger.info(json.dumps(request_body, ensure_ascii=False, indent=2))
        
        # 提交任务
        logger.info(f"\n提交任务...")
        
        result = await volcano_asr.transcribe(
            audio_url=audio_url,
            asr_language=ASRLanguage.ZH_EN,
        )
        
        logger.info(f"✓ 任务提交成功!")
        logger.info(f"  - 片段数: {len(result.segments)}")
        logger.info(f"  - 时长: {result.duration:.2f}s")
        logger.info(f"  - 语言: {result.language}")
        
        # 显示前3个片段
        logger.info(f"\n前3个片段:")
        for i, seg in enumerate(result.segments[:3]):
            logger.info(f"  [{i+1}] {seg.start_time:.2f}s - {seg.end_time:.2f}s")
            logger.info(f"      说话人: {seg.speaker}")
            logger.info(f"      文本: {seg.text}")
        
    except Exception as e:
        logger.error(f"✗ ASR 提交失败: {e}", exc_info=True)
        
        # 分析错误类型
        error_str = str(e)
        if "403" in error_str or "Forbidden" in error_str:
            logger.error("\n❌ 认证失败 (403 Forbidden)")
            logger.error("可能原因:")
            logger.error("  1. Access Key 或 Secret Key 不正确")
            logger.error("  2. App ID 不正确")
            logger.error("  3. API 密钥没有访问该服务的权限")
            logger.error("  4. V3 API 认证方式不正确")
            logger.error("\n建议:")
            logger.error("  1. 检查火山引擎控制台,确认 API 密钥是否正确")
            logger.error("  2. 确认录音文件识别服务已开通")
            logger.error("  3. 确认使用的是 V3 API (bigmodel)")
            
        elif "404" in error_str or "Not Found" in error_str:
            logger.error("\n❌ 资源不存在 (404 Not Found)")
            logger.error("可能原因:")
            logger.error("  1. 音频 URL 不可访问")
            logger.error("  2. TOS bucket 配置错误")
            logger.error("  3. 音频文件未成功上传")
            
        elif "401" in error_str or "Unauthorized" in error_str:
            logger.error("\n❌ 未授权 (401 Unauthorized)")
            logger.error("可能原因:")
            logger.error("  1. Token 无效或过期")
            logger.error("  2. 认证方式不正确")
            
        raise


async def diagnose(config: AppConfig, test_file: str) -> None:
    """
    运行完整诊断
    
    Args:
        config: 应用配置
        test_file: 测试文件路径
    """
    logger.info("=" * 80)
    logger.info("开始诊断")
    logger.info("=" * 80)
    
    # 测试 1: TOS 上传
    try:
        object_key, presigned_url = await test_tos_upload(config, test_file)
    except Exception as e:
        logger.error("\n" + "=" * 80)
        logger.error("诊断结果: TOS 上传失败")
        logger.error("=" * 80)
        logger.error(f"错误: {e}")
        logger.error("\n请先解决 TOS 上传问题,然后再测试 ASR")
        return
    
    # 测试 2: 火山引擎 ASR 认证信息
    await test_volcano_asr_auth(config)
    
    # 测试 3: 火山引擎 ASR 提交任务 (使用预签名 URL)
    try:
        await test_volcano_asr_submit(config, presigned_url)
        
        logger.info("\n" + "=" * 80)
        logger.info("✓ 诊断完成: 所有测试通过!")
        logger.info("=" * 80)
        
    except Exception as e:
        logger.error("\n" + "=" * 80)
        logger.error("诊断结果: 火山引擎 ASR 失败")
        logger.error("=" * 80)
        logger.error(f"错误: {e}")
        logger.error("\nTOS 上传正常,问题出在火山引擎 ASR")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="诊断脚本 - 分别测试 TOS 和 ASR",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    
    parser.add_argument(
        "--audio",
        required=True,
        help="测试音频文件路径",
    )
    
    parser.add_argument(
        "--config",
        default="config/test.yaml",
        help="配置文件路径(默认: config/test.yaml)",
    )
    
    args = parser.parse_args()
    
    # 验证音频文件存在
    if not Path(args.audio).exists():
        logger.error(f"音频文件不存在: {args.audio}")
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
            config_data = yaml.safe_load(f)
        
        # 使用 ConfigLoader 的环境变量替换功能
        config_loader = ConfigLoader()
        config_data = config_loader._substitute_env_vars(config_data)
        
        # 创建配置对象
        config = AppConfig(**config_data)
        logger.info("✓ 配置加载成功\n")
    except Exception as e:
        logger.error(f"✗ 配置加载失败: {e}")
        sys.exit(1)
    
    # 运行诊断
    try:
        asyncio.run(diagnose(config, args.audio))
    except KeyboardInterrupt:
        logger.info("\n诊断被用户中断")
        sys.exit(1)
    except Exception as e:
        logger.error(f"\n诊断失败: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()

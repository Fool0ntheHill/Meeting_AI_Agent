#!/usr/bin/env python3
"""
配置检查脚本

检查配置文件是否正确,验证 API 密钥是否有效。

使用方法:
    python scripts/check_config.py
    python scripts/check_config.py --config config/test.yaml
"""

import argparse
import sys
import yaml
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config.loader import ConfigLoader
from src.config.models import AppConfig
from src.utils.logger import get_logger

logger = get_logger("config_check")


def check_config_file(config_path: str) -> bool:
    """
    检查配置文件
    
    Args:
        config_path: 配置文件路径
        
    Returns:
        bool: 配置是否有效
    """
    logger.info("=" * 80)
    logger.info("配置检查工具")
    logger.info("=" * 80)
    
    # 1. 检查文件是否存在
    logger.info(f"\n[1/5] 检查配置文件: {config_path}")
    
    config_file = Path(config_path)
    if not config_file.exists():
        logger.error(f"✗ 配置文件不存在: {config_path}")
        logger.info("\n建议:")
        logger.info(f"  cp config/test.yaml.example {config_path}")
        return False
    
    logger.info("✓ 配置文件存在")
    
    # 2. 加载配置
    logger.info("\n[2/5] 加载配置...")
    
    try:
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
        return False
    
    # 3. 检查必需的配置项
    logger.info("\n[3/5] 检查必需配置...")
    
    required_checks = []
    
    # 火山引擎 ASR
    logger.info("\n  火山引擎 ASR:")
    volcano_ok = True
    if not config.volcano.access_key or config.volcano.access_key.startswith("${"):
        logger.error("    ✗ access_key 未配置")
        volcano_ok = False
    else:
        logger.info(f"    ✓ access_key: {config.volcano.access_key[:10]}...")
    
    if not config.volcano.secret_key or config.volcano.secret_key.startswith("${"):
        logger.error("    ✗ secret_key 未配置")
        volcano_ok = False
    else:
        logger.info(f"    ✓ secret_key: {config.volcano.secret_key[:10]}...")
    
    if not config.volcano.app_id or config.volcano.app_id.startswith("${"):
        logger.error("    ✗ app_id 未配置")
        volcano_ok = False
    else:
        logger.info(f"    ✓ app_id: {config.volcano.app_id}")
    
    if not config.volcano.cluster_id or config.volcano.cluster_id.startswith("${"):
        logger.error("    ✗ cluster_id 未配置")
        volcano_ok = False
    else:
        logger.info(f"    ✓ cluster_id: {config.volcano.cluster_id}")
    
    if not config.volcano.tos_bucket or config.volcano.tos_bucket.startswith("${"):
        logger.error("    ✗ tos_bucket 未配置")
        volcano_ok = False
    else:
        logger.info(f"    ✓ tos_bucket: {config.volcano.tos_bucket}")
    
    required_checks.append(("火山引擎 ASR", volcano_ok))
    
    # Gemini LLM
    logger.info("\n  Gemini LLM:")
    gemini_ok = True
    if not config.gemini.api_keys or not config.gemini.api_keys[0] or config.gemini.api_keys[0].startswith("${"):
        logger.error("    ✗ api_keys 未配置")
        gemini_ok = False
    else:
        logger.info(f"    ✓ api_keys: {len(config.gemini.api_keys)} 个密钥")
        for i, key in enumerate(config.gemini.api_keys):
            if key and not key.startswith("${"):
                logger.info(f"      - 密钥 {i+1}: {key[:10]}...")
    
    logger.info(f"    ✓ model: {config.gemini.model}")
    logger.info(f"    ✓ max_tokens: {config.gemini.max_tokens}")
    
    required_checks.append(("Gemini LLM", gemini_ok))
    
    # 4. 检查可选配置
    logger.info("\n[4/5] 检查可选配置...")
    
    # Azure ASR
    logger.info("\n  Azure ASR (可选):")
    if config.azure.subscription_keys and config.azure.subscription_keys[0] and not config.azure.subscription_keys[0].startswith("${"):
        logger.info(f"    ✓ 已配置 {len(config.azure.subscription_keys)} 个密钥")
        logger.info(f"    ✓ region: {config.azure.region}")
    else:
        logger.info("    - 未配置(将无法使用 Azure 作为备用 ASR)")
    
    # 科大讯飞声纹识别
    logger.info("\n  科大讯飞声纹识别 (可选):")
    if (config.iflytek.app_id and not config.iflytek.app_id.startswith("${") and
        config.iflytek.api_key and not config.iflytek.api_key.startswith("${")):
        logger.info(f"    ✓ app_id: {config.iflytek.app_id}")
        logger.info(f"    ✓ api_key: {config.iflytek.api_key[:10]}...")
        if config.iflytek.group_id and not config.iflytek.group_id.startswith("${"):
            logger.info(f"    ✓ group_id: {config.iflytek.group_id}")
        else:
            logger.warning("    ⚠ group_id 未配置(需要创建声纹库)")
    else:
        logger.info("    - 未配置(将无法使用说话人识别)")
        logger.info("    - 测试时请使用 --skip-speaker-recognition")
    
    # 5. 总结
    logger.info("\n[5/5] 配置检查总结:")
    logger.info("")
    
    all_ok = all(ok for _, ok in required_checks)
    
    for name, ok in required_checks:
        status = "✓" if ok else "✗"
        logger.info(f"  {status} {name}: {'已配置' if ok else '未配置'}")
    
    logger.info("")
    
    if all_ok:
        logger.info("=" * 80)
        logger.info("✓ 配置检查通过!")
        logger.info("=" * 80)
        logger.info("\n下一步:")
        logger.info("  python scripts/test_e2e.py --audio test_data/meeting.wav")
        logger.info("")
        return True
    else:
        logger.error("=" * 80)
        logger.error("✗ 配置检查失败!")
        logger.error("=" * 80)
        logger.info("\n请检查以下配置项:")
        for name, ok in required_checks:
            if not ok:
                logger.error(f"  - {name}")
        logger.info("\n参考文档:")
        logger.info("  - docs/快速开始.md")
        logger.info("  - docs/测试配置指南.md")
        logger.info("")
        return False


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="配置检查工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    
    parser.add_argument(
        "--config",
        default="config/test.yaml",
        help="配置文件路径(默认: config/test.yaml)",
    )
    
    args = parser.parse_args()
    
    # 运行检查
    success = check_config_file(args.config)
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

# -*- coding: utf-8 -*-
"""将本地文件迁移到 TOS

使用方法:
    python scripts/migrate_files_to_tos.py \
        --config config/production.yaml \
        --source-dir uploads \
        --dry-run

注意:
    1. 确保 TOS 配置正确
    2. 建议先使用 --dry-run 演练
    3. 大量文件迁移可能需要较长时间
"""

import argparse
import asyncio
import sys
from pathlib import Path
from typing import List, Tuple

from src.config.loader import ConfigLoader
from src.utils.storage import StorageClient
from src.utils.logger import get_logger

logger = get_logger(__name__)


async def scan_files(source_dir: Path) -> List[Path]:
    """
    扫描源目录中的所有文件
    
    Args:
        source_dir: 源目录
    
    Returns:
        文件路径列表
    """
    files = []
    
    for item in source_dir.rglob("*"):
        if item.is_file():
            files.append(item)
    
    return files


async def migrate_file(
    storage: StorageClient,
    local_file: Path,
    source_dir: Path,
    prefix: str = "uploads",
    dry_run: bool = False,
) -> Tuple[bool, str]:
    """
    迁移单个文件
    
    Args:
        storage: 存储客户端
        local_file: 本地文件路径
        source_dir: 源目录
        prefix: TOS 对象键前缀
        dry_run: 是否为演练模式
    
    Returns:
        (成功, 消息)
    """
    try:
        # 计算相对路径
        relative_path = local_file.relative_to(source_dir)
        object_key = f"{prefix}/{relative_path}".replace("\\", "/")  # Windows 路径兼容
        
        if dry_run:
            return True, f"[演练] {relative_path} -> {object_key}"
        
        # 上传文件
        url = await storage.upload_file(
            local_path=str(local_file),
            object_key=object_key,
        )
        
        return True, f"{relative_path} -> {url}"
        
    except Exception as e:
        return False, f"{relative_path}: {e}"


async def migrate_files(
    config_path: str,
    source_dir: Path,
    prefix: str = "uploads",
    dry_run: bool = False,
    max_concurrent: int = 10,
):
    """
    迁移文件
    
    Args:
        config_path: 配置文件路径
        source_dir: 源目录
        prefix: TOS 对象键前缀
        dry_run: 是否为演练模式
        max_concurrent: 最大并发数
    """
    print("=" * 60)
    print("文件迁移工具")
    print("=" * 60)
    print(f"源目录: {source_dir}")
    print(f"配置文件: {config_path}")
    print(f"TOS 前缀: {prefix}")
    print(f"演练模式: {'是' if dry_run else '否'}")
    print(f"最大并发: {max_concurrent}")
    print("=" * 60)
    
    # 加载配置
    print("\n📡 加载配置...")
    loader = ConfigLoader(config_path.parent)
    config = loader.load(config_path.stem)
    
    # 初始化存储客户端
    storage = StorageClient(
        bucket=config.storage.bucket,
        region=config.storage.region,
        access_key=config.storage.access_key,
        secret_key=config.storage.secret_key,
        endpoint=config.storage.endpoint,
    )
    
    print(f"✅ TOS 配置: bucket={config.storage.bucket}, region={config.storage.region}")
    
    # 扫描文件
    print(f"\n📂 扫描文件: {source_dir}")
    files = await scan_files(source_dir)
    
    if not files:
        print("⚠️  未找到文件")
        return
    
    print(f"✅ 发现 {len(files)} 个文件")
    
    # 确认
    if not dry_run:
        confirm = input("\n⚠️  确认开始迁移？(yes/no): ")
        if confirm.lower() != "yes":
            print("已取消")
            return
    
    # 迁移文件
    print("\n📦 开始迁移文件...")
    
    success_count = 0
    failed_count = 0
    
    # 使用信号量控制并发
    semaphore = asyncio.Semaphore(max_concurrent)
    
    async def migrate_with_semaphore(file_path: Path, index: int):
        """带信号量的迁移"""
        async with semaphore:
            success, message = await migrate_file(
                storage, file_path, source_dir, prefix, dry_run
            )
            
            status = "✅" if success else "❌"
            print(f"  [{index}/{len(files)}] {status} {message}")
            
            return success
    
    # 并发迁移
    tasks = [
        migrate_with_semaphore(file_path, i + 1)
        for i, file_path in enumerate(files)
    ]
    
    results = await asyncio.gather(*tasks)
    
    success_count = sum(results)
    failed_count = len(results) - success_count
    
    # 完成
    print("\n" + "=" * 60)
    if dry_run:
        print(f"✅ 演练完成！")
    else:
        print(f"✅ 迁移完成！")
    print(f"   成功: {success_count}")
    print(f"   失败: {failed_count}")
    print("=" * 60)


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="文件迁移工具")
    parser.add_argument(
        "--config",
        default="config/production.yaml",
        help="配置文件路径",
    )
    parser.add_argument(
        "--source-dir",
        default="uploads",
        help="源目录",
    )
    parser.add_argument(
        "--prefix",
        default="uploads",
        help="TOS 对象键前缀",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="演练模式，不实际上传",
    )
    parser.add_argument(
        "--max-concurrent",
        type=int,
        default=10,
        help="最大并发数",
    )
    
    args = parser.parse_args()
    
    # 验证源目录
    source_dir = Path(args.source_dir)
    if not source_dir.exists():
        print(f"❌ 源目录不存在: {source_dir}")
        sys.exit(1)
    
    # 运行迁移
    try:
        asyncio.run(
            migrate_files(
                config_path=args.config,
                source_dir=source_dir,
                prefix=args.prefix,
                dry_run=args.dry_run,
                max_concurrent=args.max_concurrent,
            )
        )
    except KeyboardInterrupt:
        print("\n\n⚠️  用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 迁移失败: {e}")
        logger.exception("Migration failed")
        sys.exit(1)


if __name__ == "__main__":
    main()

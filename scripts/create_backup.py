#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""创建项目完整备份压缩包"""

import os
import zipfile
from datetime import datetime
from pathlib import Path

def create_backup():
    """创建完整项目备份"""
    
    # 备份文件名（带时间戳）
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_name = f"Meeting_AI_Agent_backup_{timestamp}.zip"
    
    print("=" * 60)
    print("创建项目完整备份")
    print("=" * 60)
    
    # 要排除的文件夹（可选，如果想全部打包就注释掉）
    exclude_dirs = {
        'venv',           # 虚拟环境（太大，另一台电脑重新创建）
        '__pycache__',    # Python 缓存
        '.pytest_cache',  # 测试缓存
        '.hypothesis',    # 测试缓存
        '.git',           # Git 仓库（如果有）
        '.vscode',        # IDE 配置
        '.idea',          # IDE 配置
    }
    
    # 要排除的文件扩展名（可选）
    exclude_extensions = {
        '.pyc',
        '.pyo',
        '.pyd',
    }
    
    # 创建压缩包
    with zipfile.ZipFile(backup_name, 'w', zipfile.ZIP_DEFLATED) as zipf:
        file_count = 0
        
        # 遍历所有文件
        for root, dirs, files in os.walk('.'):
            # 移除要排除的目录
            dirs[:] = [d for d in dirs if d not in exclude_dirs]
            
            for file in files:
                # 跳过排除的扩展名
                if any(file.endswith(ext) for ext in exclude_extensions):
                    continue
                
                file_path = os.path.join(root, file)
                arcname = file_path[2:]  # 移除开头的 './'
                
                try:
                    zipf.write(file_path, arcname)
                    file_count += 1
                    if file_count % 100 == 0:
                        print(f"已打包 {file_count} 个文件...")
                except Exception as e:
                    print(f"警告: 无法打包 {file_path}: {e}")
        
        print(f"\n✓ 完成！共打包 {file_count} 个文件")
    
    # 获取文件大小
    size_mb = os.path.getsize(backup_name) / (1024 * 1024)
    
    print("\n" + "=" * 60)
    print(f"备份文件: {backup_name}")
    print(f"文件大小: {size_mb:.2f} MB")
    print("=" * 60)
    print("\n使用方法:")
    print("1. 将此文件复制到另一台电脑")
    print("2. 解压: unzip " + backup_name)
    print("3. 创建虚拟环境: python -m venv venv")
    print("4. 激活虚拟环境: venv\\Scripts\\activate (Windows)")
    print("5. 安装依赖: pip install -r requirements.txt")
    print("6. 运行: python main.py")
    print("=" * 60)

if __name__ == "__main__":
    create_backup()

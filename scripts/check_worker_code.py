"""检查 worker 是否使用了最新的代码"""

import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def check_pipeline_code():
    """检查 pipeline.py 中是否有元数据保存代码"""
    pipeline_file = project_root / "src" / "services" / "pipeline.py"
    
    if not pipeline_file.exists():
        print(f"❌ 文件不存在: {pipeline_file}")
        return False
    
    content = pipeline_file.read_text(encoding='utf-8')
    
    # 检查关键代码片段
    checks = [
        ("元数据读取日志", "Loaded metadata from DB"),
        ("元数据提取", "extract_meeting_metadata"),
        ("元数据保存", "Meeting metadata saved to database"),
        ("数据库更新", "task.meeting_date = meeting_date"),
    ]
    
    print("\n" + "="*60)
    print("检查 pipeline.py 代码")
    print("="*60)
    
    all_passed = True
    for check_name, check_str in checks:
        if check_str in content:
            print(f"✓ {check_name}: 存在")
        else:
            print(f"✗ {check_name}: 缺失")
            all_passed = False
    
    return all_passed


def check_worker_running():
    """检查 worker 是否在运行"""
    import subprocess
    
    print("\n" + "="*60)
    print("检查 worker 进程")
    print("="*60)
    
    try:
        # Windows 使用 tasklist
        result = subprocess.run(
            ["tasklist", "/FI", "IMAGENAME eq python.exe"],
            capture_output=True,
            text=True,
        )
        
        if "python.exe" in result.stdout:
            print("✓ 发现 Python 进程")
            # 统计进程数
            lines = [line for line in result.stdout.split('\n') if 'python.exe' in line.lower()]
            print(f"  共 {len(lines)} 个 Python 进程")
        else:
            print("✗ 未发现 Python 进程")
    except Exception as e:
        print(f"⚠ 无法检查进程: {e}")


if __name__ == "__main__":
    print("\n" + "="*60)
    print("Worker 代码检查工具")
    print("="*60)
    
    code_ok = check_pipeline_code()
    check_worker_running()
    
    print("\n" + "="*60)
    if code_ok:
        print("✓ 代码已更新")
        print("\n请确保:")
        print("1. 已停止旧的 worker 进程")
        print("2. 重新启动 worker: python worker.py")
        print("3. 创建新任务测试")
    else:
        print("✗ 代码未完全更新")
        print("\n请检查 src/services/pipeline.py 文件")
    print("="*60 + "\n")

# -*- coding: utf-8 -*-
"""
API 层综合测试脚本 - Task 24 检查点

此脚本验证所有 API 层功能是否正常工作:
1. 单元测试 (pytest)
2. 数据库连接
3. API 服务器启动
4. 各个 API 端点功能

使用方法:
    python scripts/test_api_comprehensive.py
"""

import os
import sys
import subprocess
import time
import requests
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 测试结果
results = {
    "passed": [],
    "failed": [],
    "skipped": []
}


def print_section(title: str):
    """打印分隔线"""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)


def run_command(cmd: list, description: str, timeout: int = 60) -> bool:
    """运行命令并返回是否成功"""
    print(f"\n▶ {description}")
    print(f"  命令: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=project_root
        )
        
        if result.returncode == 0:
            print(f"  ✅ 成功")
            results["passed"].append(description)
            return True
        else:
            print(f"  ❌ 失败 (退出码: {result.returncode})")
            if result.stderr:
                print(f"  错误: {result.stderr[:500]}")
            results["failed"].append(description)
            return False
            
    except subprocess.TimeoutExpired:
        print(f"  ⏱️  超时 ({timeout}秒)")
        results["failed"].append(f"{description} (超时)")
        return False
    except Exception as e:
        print(f"  ❌ 异常: {e}")
        results["failed"].append(f"{description} (异常)")
        return False


def check_api_server() -> bool:
    """检查 API 服务器是否运行"""
    print("\n▶ 检查 API 服务器")
    
    try:
        response = requests.get("http://localhost:8000/health", timeout=5)
        if response.status_code == 200:
            print("  ✅ API 服务器正在运行")
            results["passed"].append("API 服务器运行检查")
            return True
        else:
            print(f"  ❌ API 服务器响应异常 (状态码: {response.status_code})")
            results["failed"].append("API 服务器运行检查")
            return False
    except requests.exceptions.ConnectionError:
        print("  ⚠️  API 服务器未运行")
        print("  提示: 请先启动 API 服务器: python main.py")
        results["skipped"].append("API 服务器运行检查 (未启动)")
        return False
    except Exception as e:
        print(f"  ❌ 检查失败: {e}")
        results["failed"].append("API 服务器运行检查")
        return False


def test_unit_tests():
    """运行单元测试"""
    print_section("1. 单元测试")
    
    # 运行 pytest
    success = run_command(
        ["python", "-m", "pytest", "tests/unit/", "-v", "--tb=short"],
        "运行所有单元测试",
        timeout=120
    )
    
    return success


def test_database():
    """测试数据库连接"""
    print_section("2. 数据库测试")
    
    success = run_command(
        ["python", "scripts/test_database.py"],
        "测试数据库连接和基本操作",
        timeout=30
    )
    
    return success


def test_api_endpoints():
    """测试 API 端点"""
    print_section("3. API 端点测试")
    
    # 检查服务器是否运行
    if not check_api_server():
        print("\n  ⚠️  跳过 API 端点测试 (服务器未运行)")
        results["skipped"].append("所有 API 端点测试")
        return False
    
    # 测试各个 API
    api_tests = [
        ("scripts/test_task_api_unit.py", "任务 API 测试"),
        ("scripts/test_corrections_api.py", "修正 API 测试"),
        ("scripts/test_hotwords_api.py", "热词 API 测试"),
        ("scripts/test_prompt_templates_api.py", "提示词模板 API 测试"),
        ("scripts/test_artifacts_api.py", "衍生内容 API 测试"),
    ]
    
    all_passed = True
    for script, description in api_tests:
        if os.path.exists(project_root / script):
            success = run_command(
                ["python", script],
                description,
                timeout=60
            )
            all_passed = all_passed and success
        else:
            print(f"\n  ⚠️  跳过: {description} (脚本不存在)")
            results["skipped"].append(description)
    
    return all_passed


def test_configuration():
    """测试配置"""
    print_section("4. 配置检查")
    
    success = run_command(
        ["python", "scripts/check_config.py"],
        "检查配置文件",
        timeout=30
    )
    
    return success


def print_summary():
    """打印测试总结"""
    print_section("测试总结")
    
    total = len(results["passed"]) + len(results["failed"]) + len(results["skipped"])
    
    print(f"\n总计: {total} 项测试")
    print(f"  ✅ 通过: {len(results['passed'])}")
    print(f"  ❌ 失败: {len(results['failed'])}")
    print(f"  ⏭️  跳过: {len(results['skipped'])}")
    
    if results["failed"]:
        print("\n失败的测试:")
        for item in results["failed"]:
            print(f"  ❌ {item}")
    
    if results["skipped"]:
        print("\n跳过的测试:")
        for item in results["skipped"]:
            print(f"  ⏭️  {item}")
    
    print("\n" + "=" * 80)
    
    if results["failed"]:
        print("❌ 部分测试失败")
        return False
    elif results["skipped"]:
        print("⚠️  部分测试被跳过")
        return True
    else:
        print("✅ 所有测试通过")
        return True


def main():
    """主函数"""
    print("=" * 80)
    print("  API 层综合测试 - Task 24 检查点")
    print("=" * 80)
    print(f"\n项目路径: {project_root}")
    print(f"Python 版本: {sys.version}")
    
    # 运行测试
    test_unit_tests()
    test_database()
    test_configuration()
    test_api_endpoints()
    
    # 打印总结
    success = print_summary()
    
    # 返回退出码
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

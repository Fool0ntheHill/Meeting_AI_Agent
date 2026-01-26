"""
调试新建 artifact 请求，检查 prompt_text 是否传递
"""
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.database.session import get_session
from src.database.models import Task
from sqlalchemy import select


def check_recent_task():
    """检查最近的任务"""
    with get_session() as db:
        # 查询最近的任务
        stmt = select(Task).order_by(Task.created_at.desc()).limit(5)
        tasks = db.execute(stmt).scalars().all()
        
        print("\n=== 最近的 5 个任务 ===\n")
        for task in tasks:
            print(f"Task ID: {task.task_id}")
            print(f"  状态: {task.state}")
            print(f"  创建时间: {task.created_at}")
            print(f"  用户: {task.user_id}")
            print()


def print_request_format():
    """打印正确的请求格式"""
    print("\n=== 正确的请求格式 ===\n")
    print("POST /api/v1/tasks/{task_id}/artifacts/{artifact_type}/generate")
    print()
    print("请求体:")
    print("""
{
  "prompt_instance": {
    "template_id": "__blank__",
    "language": "zh-CN",
    "prompt_text": "用户输入的自定义提示词内容",
    "parameters": {}
  }
}
""")
    print()
    print("注意事项:")
    print("1. prompt_text 字段是可选的，但对于空白模板建议提供")
    print("2. 如果 prompt_text 为空字符串，后端会使用默认提示词")
    print("3. 如果 prompt_text 有内容，后端会优先使用它")
    print()


def check_backend_logs():
    """提示如何查看后端日志"""
    print("\n=== 如何查看后端日志 ===\n")
    print("1. 查看后端控制台输出")
    print("2. 查找以下日志行:")
    print("   - 'Generating artifact with prompt_instance: template_id=..., has_prompt_text=...'")
    print("   - 'Converting dict to PromptInstance: ...'")
    print("   - 'Has prompt_text: ...'")
    print("   - 'prompt_text type: ..., length: ...'")
    print()
    print("3. 如果看到 'has_prompt_text=False'，说明前端没有传 prompt_text")
    print("4. 如果看到 'has_prompt_text=True' 但 'length: 0'，说明传了空字符串")
    print("5. 如果看到 'has_prompt_text=True' 且 'length: > 0'，说明传了有效内容")
    print()


def test_pydantic_parsing():
    """测试 Pydantic 解析"""
    from src.core.models import PromptInstance
    
    print("\n=== 测试 Pydantic 解析 ===\n")
    
    # 测试 1: 完整的数据
    print("测试 1: 完整的数据")
    data1 = {
        "template_id": "__blank__",
        "language": "zh-CN",
        "prompt_text": "用户输入的内容",
        "parameters": {}
    }
    try:
        instance1 = PromptInstance(**data1)
        print(f"  ✓ 解析成功")
        print(f"  template_id: {instance1.template_id}")
        print(f"  prompt_text: {repr(instance1.prompt_text)}")
        print(f"  prompt_text 长度: {len(instance1.prompt_text) if instance1.prompt_text else 0}")
    except Exception as e:
        print(f"  ✗ 解析失败: {e}")
    print()
    
    # 测试 2: 空字符串
    print("测试 2: prompt_text 为空字符串")
    data2 = {
        "template_id": "__blank__",
        "language": "zh-CN",
        "prompt_text": "",
        "parameters": {}
    }
    try:
        instance2 = PromptInstance(**data2)
        print(f"  ✓ 解析成功")
        print(f"  template_id: {instance2.template_id}")
        print(f"  prompt_text: {repr(instance2.prompt_text)}")
        print(f"  bool(prompt_text): {bool(instance2.prompt_text)}")
    except Exception as e:
        print(f"  ✗ 解析失败: {e}")
    print()
    
    # 测试 3: 不传 prompt_text
    print("测试 3: 不传 prompt_text 字段")
    data3 = {
        "template_id": "__blank__",
        "language": "zh-CN",
        "parameters": {}
    }
    try:
        instance3 = PromptInstance(**data3)
        print(f"  ✓ 解析成功")
        print(f"  template_id: {instance3.template_id}")
        print(f"  prompt_text: {repr(instance3.prompt_text)}")
        print(f"  prompt_text is None: {instance3.prompt_text is None}")
    except Exception as e:
        print(f"  ✗ 解析失败: {e}")
    print()
    
    # 测试 4: 前端可能发送的格式（JSON）
    print("测试 4: 模拟前端 JSON 请求")
    import json
    json_str = """
    {
        "prompt_instance": {
            "template_id": "__blank__",
            "language": "zh-CN",
            "prompt_text": "用户在前端输入的内容",
            "parameters": {}
        }
    }
    """
    try:
        json_data = json.loads(json_str)
        instance4 = PromptInstance(**json_data["prompt_instance"])
        print(f"  ✓ 解析成功")
        print(f"  template_id: {instance4.template_id}")
        print(f"  prompt_text: {repr(instance4.prompt_text[:50])}...")
    except Exception as e:
        print(f"  ✗ 解析失败: {e}")
    print()


if __name__ == "__main__":
    print("=" * 60)
    print("调试新建 Artifact 请求")
    print("=" * 60)
    
    check_recent_task()
    print_request_format()
    check_backend_logs()
    test_pydantic_parsing()
    
    print("\n" + "=" * 60)
    print("调试建议:")
    print("=" * 60)
    print()
    print("1. 检查前端发送的请求体")
    print("   - 打开浏览器开发者工具 (F12)")
    print("   - 切换到 Network 标签")
    print("   - 找到 generate 请求")
    print("   - 查看 Request Payload")
    print()
    print("2. 检查后端日志")
    print("   - 查看后端控制台")
    print("   - 搜索 'Generating artifact with prompt_instance'")
    print("   - 查看 has_prompt_text 的值")
    print()
    print("3. 如果前端传了但后端没收到")
    print("   - 检查 Content-Type 是否为 application/json")
    print("   - 检查请求体格式是否正确")
    print("   - 检查字段名是否拼写正确 (prompt_text)")
    print()
    print("4. 如果后端收到了但是空字符串")
    print("   - 检查前端是否正确获取用户输入")
    print("   - 检查前端是否在发送前清空了字段")
    print()

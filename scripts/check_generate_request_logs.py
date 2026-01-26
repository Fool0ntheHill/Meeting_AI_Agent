"""
检查生成 artifact 请求的后端日志
帮助判断是前端没传还是后端没解析
"""
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def print_instructions():
    """打印检查说明"""
    print("=" * 80)
    print("检查新建 Artifact 请求 - 调试指南")
    print("=" * 80)
    print()
    
    print("📋 问题：生成新 artifact 时提示没有 prompt")
    print()
    
    print("🔍 需要确认的问题：")
    print("  1. 前端是否传递了 prompt_text 字段？")
    print("  2. 后端是否接收到了 prompt_text？")
    print("  3. 后端是否正确解析了 prompt_text？")
    print()
    
    print("=" * 80)
    print("步骤 1: 检查前端请求")
    print("=" * 80)
    print()
    print("在浏览器中：")
    print("  1. 打开开发者工具 (F12)")
    print("  2. 切换到 Network (网络) 标签")
    print("  3. 清空现有请求")
    print("  4. 在前端操作：输入自定义提示词，点击生成")
    print("  5. 找到 'generate' 请求")
    print("  6. 点击查看 Request Payload (请求负载)")
    print()
    print("✅ 正确的请求应该包含：")
    print("""
{
  "prompt_instance": {
    "template_id": "__blank__",
    "language": "zh-CN",
    "prompt_text": "用户输入的内容在这里",  ← 检查这个字段
    "parameters": {}
  }
}
""")
    print()
    print("❌ 如果看到以下情况，说明前端有问题：")
    print("  - 没有 prompt_text 字段")
    print("  - prompt_text 是 null")
    print("  - prompt_text 是空字符串 \"\"")
    print("  - prompt_text 的值不是用户输入的内容")
    print()
    
    print("=" * 80)
    print("步骤 2: 检查后端日志")
    print("=" * 80)
    print()
    print("在后端控制台中查找以下日志：")
    print()
    print("🔎 关键日志 1: API 接收到请求")
    print("  搜索: 'Generating artifact with prompt_instance'")
    print("  示例: Generating artifact with prompt_instance: template_id=__blank__, has_prompt_text=True")
    print()
    print("  ✅ 如果 has_prompt_text=True，说明后端接收到了 prompt_text")
    print("  ❌ 如果 has_prompt_text=False，说明后端没有接收到 prompt_text")
    print()
    
    print("🔎 关键日志 2: 服务层处理")
    print("  搜索: 'Converting dict to PromptInstance'")
    print("  示例: Converting dict to PromptInstance: __blank__")
    print()
    print("  然后查看下一行:")
    print("  - 'Has prompt_text: True'")
    print("  - 'prompt_text type: <class 'str'>, length: 25 chars'")
    print("  - 'prompt_text preview: 用户输入的内容...'")
    print()
    print("  ✅ 如果 length > 0，说明有内容")
    print("  ❌ 如果 length = 0，说明是空字符串")
    print()
    
    print("🔎 关键日志 3: 模板处理")
    print("  搜索以下任一日志:")
    print("  - 'Using prompt_text from prompt_instance'  ← 使用了 prompt_text")
    print("  - 'Template is __blank__, creating blank template'  ← 使用空白模板")
    print("  - '模板不存在: __blank__'  ← 错误：没有正确处理")
    print()
    
    print("=" * 80)
    print("步骤 3: 根据日志判断问题")
    print("=" * 80)
    print()
    
    print("📊 情况 1: 前端没传 prompt_text")
    print("  前端请求: prompt_text 字段缺失或为 null")
    print("  后端日志: has_prompt_text=False")
    print("  解决方案: 修复前端代码，确保传递 prompt_text")
    print()
    
    print("📊 情况 2: 前端传了空字符串")
    print("  前端请求: prompt_text: \"\"")
    print("  后端日志: has_prompt_text=True, length: 0")
    print("  解决方案: 检查前端是否正确获取用户输入")
    print()
    
    print("📊 情况 3: 后端没有正确解析")
    print("  前端请求: prompt_text: \"用户输入的内容\"")
    print("  后端日志: has_prompt_text=False 或没有相关日志")
    print("  解决方案: 检查后端 Pydantic 模型定义")
    print()
    
    print("📊 情况 4: 后端解析了但没有使用")
    print("  前端请求: prompt_text: \"用户输入的内容\"")
    print("  后端日志: has_prompt_text=True, length > 0")
    print("  但仍然报错: '模板不存在: __blank__'")
    print("  解决方案: 检查服务层的模板处理逻辑")
    print()
    
    print("=" * 80)
    print("步骤 4: 测试修复")
    print("=" * 80)
    print()
    print("使用 curl 测试后端是否正常工作：")
    print()
    print("curl -X POST 'http://localhost:8000/api/v1/tasks/task_1c8f2c5d561048db/artifacts/meeting_minutes/generate' \\")
    print("  -H 'Authorization: Bearer YOUR_TOKEN' \\")
    print("  -H 'Content-Type: application/json' \\")
    print("  -d '{")
    print('    "prompt_instance": {')
    print('      "template_id": "__blank__",')
    print('      "language": "zh-CN",')
    print('      "prompt_text": "请生成一份简短的会议纪要",')
    print('      "parameters": {}')
    print('    }')
    print("  }'")
    print()
    print("如果 curl 测试成功，说明后端没问题，是前端的问题")
    print("如果 curl 测试失败，说明后端有问题，需要修复")
    print()
    
    print("=" * 80)
    print("常见前端问题")
    print("=" * 80)
    print()
    print("1. 前端没有绑定用户输入")
    print("   检查: 用户输入框的 v-model 或 onChange 是否正确绑定")
    print()
    print("2. 前端在发送前清空了字段")
    print("   检查: 发送请求前是否有代码修改了 prompt_text")
    print()
    print("3. 前端使用了错误的字段名")
    print("   检查: 是否拼写为 prompt_text (不是 promptText 或 prompt)")
    print()
    print("4. 前端没有包含在请求体中")
    print("   检查: 是否正确构造了 prompt_instance 对象")
    print()
    
    print("=" * 80)
    print("需要的信息")
    print("=" * 80)
    print()
    print("请提供以下信息以便进一步诊断：")
    print()
    print("1. 前端请求的完整 Request Payload (从浏览器开发者工具复制)")
    print("2. 后端日志中包含 'Generating artifact' 的完整日志行")
    print("3. 后端日志中包含 'Converting dict to PromptInstance' 的后续几行")
    print("4. 是否看到 '模板不存在: __blank__' 错误")
    print()


if __name__ == "__main__":
    print_instructions()

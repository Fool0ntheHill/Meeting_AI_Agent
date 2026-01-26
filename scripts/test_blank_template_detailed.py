"""
测试空白模板的详细调试脚本
"""
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.core.models import PromptInstance


def test_blank_template():
    """测试空白模板的各种情况"""
    
    # 测试用例 1: prompt_text 是 None
    print("\n=== 测试 1: prompt_text = None ===")
    prompt1 = PromptInstance(
        template_id="__blank__",
        language="zh-CN",
        prompt_text=None,
        parameters={}
    )
    print(f"prompt_text: {repr(prompt1.prompt_text)}")
    print(f"bool(prompt_text): {bool(prompt1.prompt_text)}")
    
    # 测试用例 2: prompt_text 是空字符串
    print("\n=== 测试 2: prompt_text = '' ===")
    prompt2 = PromptInstance(
        template_id="__blank__",
        language="zh-CN",
        prompt_text="",
        parameters={}
    )
    print(f"prompt_text: {repr(prompt2.prompt_text)}")
    print(f"bool(prompt_text): {bool(prompt2.prompt_text)}")
    if prompt2.prompt_text is not None:
        print(f"prompt_text.strip(): {repr(prompt2.prompt_text.strip())}")
        print(f"bool(prompt_text.strip()): {bool(prompt2.prompt_text.strip())}")
    
    # 测试用例 3: prompt_text 有内容
    print("\n=== 测试 3: prompt_text = '请生成会议纪要' ===")
    prompt3 = PromptInstance(
        template_id="__blank__",
        language="zh-CN",
        prompt_text="请生成会议纪要",
        parameters={}
    )
    print(f"prompt_text: {repr(prompt3.prompt_text)}")
    print(f"bool(prompt_text): {bool(prompt3.prompt_text)}")
    
    # 测试用例 4: 从 dict 创建（模拟 API 调用）
    print("\n=== 测试 4: 从 dict 创建 ===")
    prompt_dict = {
        "template_id": "__blank__",
        "language": "zh-CN",
        "prompt_text": "",
        "parameters": {}
    }
    print(f"Dict prompt_text: {repr(prompt_dict['prompt_text'])}")
    prompt4 = PromptInstance(**prompt_dict)
    print(f"PromptInstance prompt_text: {repr(prompt4.prompt_text)}")
    print(f"bool(prompt_text): {bool(prompt4.prompt_text)}")
    
    # 测试模板创建逻辑
    print("\n=== 测试模板创建逻辑 ===")
    for i, prompt in enumerate([prompt1, prompt2, prompt3], 1):
        print(f"\n测试用例 {i}:")
        print(f"  template_id: {prompt.template_id}")
        print(f"  prompt_text: {repr(prompt.prompt_text)}")
        
        # 模拟代码中的条件判断
        if prompt.prompt_text and prompt.prompt_text.strip():
            print(f"  ✓ 会使用 prompt_text")
        elif prompt.template_id == "__blank__":
            print(f"  ✓ 会创建空白模板（因为 template_id == '__blank__'）")
        else:
            print(f"  ✗ 会尝试从数据库查询模板（会失败）")


if __name__ == "__main__":
    test_blank_template()


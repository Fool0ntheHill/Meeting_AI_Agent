"""测试提示词构建功能"""

import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def test_meeting_metadata_in_prompt():
    """测试会议元数据是否正确添加到提示词"""
    
    from src.utils.meeting_metadata import format_meeting_datetime
    
    print("\n" + "="*60)
    print("测试会议元数据格式化")
    print("="*60)
    
    # 测试用例 1: 有日期和时间
    result = format_meeting_datetime("2025-12-29", "14:30")
    print(f"\n日期: 2025-12-29, 时间: 14:30")
    print(f"格式化结果: {result}")
    print(f"预期: 2025年12月29日 14:30")
    
    # 测试用例 2: 只有日期
    result = format_meeting_datetime("2025-12-29", None)
    print(f"\n日期: 2025-12-29, 时间: None")
    print(f"格式化结果: {result}")
    print(f"预期: 2025年12月29日")
    
    # 测试用例 3: 都没有
    result = format_meeting_datetime(None, None)
    print(f"\n日期: None, 时间: None")
    print(f"格式化结果: {result}")
    print(f"预期: (空字符串)")
    
    print("\n" + "="*60)
    print("测试提示词构建逻辑")
    print("="*60)
    
    # 模拟提示词构建
    prompt_body = "请根据以下会议转写生成会议纪要："
    meeting_date = "2025-12-29"
    meeting_time = None
    
    # 添加会议元数据（模拟 _build_prompt 中的逻辑）
    if meeting_date or meeting_time:
        datetime_str = format_meeting_datetime(meeting_date, meeting_time)
        if datetime_str:
            prompt_body += f"\n\n## 会议时间\n{datetime_str}"
    
    print(f"\n最终提示词:")
    print(prompt_body)
    
    if "2025年12月29日" in prompt_body:
        print("\n✓ 会议日期已正确添加到提示词")
    else:
        print("\n✗ 会议日期未添加到提示词")


if __name__ == "__main__":
    test_meeting_metadata_in_prompt()

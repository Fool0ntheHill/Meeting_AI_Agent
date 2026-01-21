"""测试会议元数据提取功能"""

import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.utils.meeting_metadata import extract_meeting_metadata, extract_date_from_filename

def test_date_extraction():
    """测试日期提取"""
    print("\n" + "="*60)
    print("测试日期提取")
    print("="*60)
    
    test_cases = [
        "20251229ONE产品和业务规则中心的设计讨论会议.ogg",
        "meeting_20260121.wav",
        "会议_2026-01-21.mp3",
        "20260121_meeting.ogg",
        "meeting_2026_01_21.wav",
        "no_date_in_filename.mp3",
    ]
    
    for filename in test_cases:
        extracted_date = extract_date_from_filename(filename)
        print(f"\n文件名: {filename}")
        print(f"提取日期: {extracted_date or '(无法提取)'}")


def test_metadata_extraction():
    """测试完整的元数据提取"""
    print("\n" + "="*60)
    print("测试完整的元数据提取")
    print("="*60)
    
    # 测试用例 1: 从文件名提取日期
    print("\n--- 测试用例 1: 从文件名提取日期 ---")
    filenames = ["20251229ONE产品和业务规则中心的设计讨论会议.ogg"]
    date, time = extract_meeting_metadata(
        original_filenames=filenames,
        meeting_date=None,
        meeting_time=None,
    )
    print(f"输入文件名: {filenames}")
    print(f"提取结果: date={date}, time={time}")
    
    # 测试用例 2: 用户提供日期和时间
    print("\n--- 测试用例 2: 用户提供日期和时间 ---")
    date, time = extract_meeting_metadata(
        original_filenames=filenames,
        meeting_date="2025-12-30",
        meeting_time="14:00",
    )
    print(f"输入: date=2025-12-30, time=14:00")
    print(f"提取结果: date={date}, time={time}")
    
    # 测试用例 3: 无文件名，使用当前日期
    print("\n--- 测试用例 3: 无文件名，使用当前日期 ---")
    date, time = extract_meeting_metadata(
        original_filenames=None,
        meeting_date=None,
        meeting_time=None,
    )
    print(f"输入: 无文件名，无用户提供")
    print(f"提取结果: date={date}, time={time}")
    
    # 测试用例 4: 文件名无日期，使用当前日期
    print("\n--- 测试用例 4: 文件名无日期，使用当前日期 ---")
    filenames = ["meeting_recording.mp3"]
    date, time = extract_meeting_metadata(
        original_filenames=filenames,
        meeting_date=None,
        meeting_time=None,
    )
    print(f"输入文件名: {filenames}")
    print(f"提取结果: date={date}, time={time}")


if __name__ == "__main__":
    test_date_extraction()
    test_metadata_extraction()
    print("\n" + "="*60)
    print("测试完成")
    print("="*60 + "\n")

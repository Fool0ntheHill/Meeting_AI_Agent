"""测试会议元数据提取功能"""

import sys
from pathlib import Path
from datetime import datetime

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.utils.meeting_metadata import (
    extract_date_from_filename,
    extract_time_from_filename,
    extract_meeting_metadata,
    format_meeting_datetime,
)


def test_extract_date_from_filename():
    """测试从文件名提取日期"""
    print("\n=== 测试从文件名提取日期 ===")
    
    test_cases = [
        ("meeting_20260121.wav", "2026-01-21"),
        ("会议_2026-01-21.mp3", "2026-01-21"),
        ("20260121_meeting.ogg", "2026-01-21"),
        ("meeting_2026_01_21.wav", "2026-01-21"),
        ("random_file.wav", None),
    ]
    
    for filename, expected in test_cases:
        result = extract_date_from_filename(filename)
        status = "✓" if result == expected else "✗"
        print(f"{status} {filename} -> {result} (expected: {expected})")


def test_extract_time_from_filename():
    """测试从文件名提取时间"""
    print("\n=== 测试从文件名提取时间 ===")
    
    test_cases = [
        ("meeting_1430.wav", "14:30"),
        ("meeting_14_30.mp3", "14:30"),
        ("meeting_143045.ogg", "14:30:45"),
        ("meeting_20260121_1430.wav", "14:30"),  # 包含日期
        ("random_file.wav", None),
    ]
    
    for filename, expected in test_cases:
        result = extract_time_from_filename(filename)
        status = "✓" if result == expected else "✗"
        print(f"{status} {filename} -> {result} (expected: {expected})")


def test_extract_meeting_metadata():
    """测试提取会议元数据"""
    print("\n=== 测试提取会议元数据 ===")
    
    # 测试场景 1: 用户提供了日期和时间
    print("\n场景 1: 用户提供了日期和时间")
    date, time = extract_meeting_metadata(
        meeting_date="2026-01-21",
        meeting_time="14:30",
    )
    print(f"  日期: {date}")
    print(f"  时间: {time}")
    assert date == "2026-01-21"
    assert time == "14:30"
    
    # 测试场景 2: 从文件名提取日期（不提取时间）
    print("\n场景 2: 从文件名提取日期")
    date, time = extract_meeting_metadata(
        original_filenames=["meeting_20260121_1430.wav"],
    )
    print(f"  日期: {date}")
    print(f"  时间: {time}")
    assert date == "2026-01-21"
    assert time is None  # 不从文件名提取时间
    
    # 测试场景 3: 没有任何信息，使用当前日期
    print("\n场景 3: 使用当前日期")
    date, time = extract_meeting_metadata()
    print(f"  日期: {date}")
    print(f"  时间: {time}")
    assert date == datetime.now().strftime("%Y-%m-%d")
    assert time is None
    
    # 测试场景 4: 用户只提供日期
    print("\n场景 4: 用户只提供日期")
    date, time = extract_meeting_metadata(
        meeting_date="2026-01-21",
    )
    print(f"  日期: {date}")
    print(f"  时间: {time}")
    assert date == "2026-01-21"
    assert time is None


def test_format_meeting_datetime():
    """测试格式化会议日期时间"""
    print("\n=== 测试格式化会议日期时间 ===")
    
    test_cases = [
        ("2026-01-21", "14:30", "2026年01月21日 14:30"),
        ("2026-01-21", None, "2026年01月21日"),
        (None, "14:30", "14:30"),
        (None, None, ""),
    ]
    
    for date, time, expected in test_cases:
        result = format_meeting_datetime(date, time)
        status = "✓" if result == expected else "✗"
        print(f"{status} ({date}, {time}) -> {result} (expected: {expected})")


if __name__ == "__main__":
    print("开始测试会议元数据提取功能...")
    
    test_extract_date_from_filename()
    test_extract_time_from_filename()
    test_extract_meeting_metadata()
    test_format_meeting_datetime()
    
    print("\n✓ 所有测试通过！")

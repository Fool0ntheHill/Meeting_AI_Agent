"""会议元数据提取工具"""

import re
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Tuple
import logging

logger = logging.getLogger(__name__)


def get_file_modified_time(file_path: str) -> Optional[datetime]:
    """
    获取文件的最后修改时间
    
    Args:
        file_path: 文件路径
        
    Returns:
        datetime: 文件最后修改时间，如果文件不存在则返回 None
    """
    try:
        if not os.path.exists(file_path):
            return None
        
        mtime = os.path.getmtime(file_path)
        return datetime.fromtimestamp(mtime)
    except Exception as e:
        logger.warning(f"Failed to get file modified time for {file_path}: {e}")
        return None


def calculate_meeting_time_range(
    file_modified_time: datetime,
    audio_duration_seconds: float,
) -> Tuple[str, str, str]:
    """
    根据文件修改时间和音频时长计算会议时间区间
    
    假设：文件修改时间 ≈ 会议结束时间（录音停止时间）
    
    Args:
        file_modified_time: 文件最后修改时间
        audio_duration_seconds: 音频时长（秒）
        
    Returns:
        Tuple[str, str, str]: (开始时间, 结束时间, 时间区间)
        例如: ("14:00", "15:30", "14:00 - 15:30")
    """
    # 会议结束时间 = 文件修改时间
    end_time = file_modified_time
    
    # 会议开始时间 = 文件修改时间 - 音频时长
    start_time = end_time - timedelta(seconds=audio_duration_seconds)
    
    # 格式化时间
    start_time_str = start_time.strftime("%H:%M")
    end_time_str = end_time.strftime("%H:%M")
    time_range = f"{start_time_str} - {end_time_str}"
    
    return start_time_str, end_time_str, time_range


def extract_date_from_filename(filename: str) -> Optional[str]:
    """
    从文件名中提取日期
    
    支持的格式：
    - meeting_20260121.wav -> 2026-01-21
    - 会议_2026-01-21.mp3 -> 2026-01-21
    - 20260121_meeting.ogg -> 2026-01-21
    - meeting_2026_01_21.wav -> 2026-01-21
    
    Args:
        filename: 文件名
        
    Returns:
        str: 日期字符串（YYYY-MM-DD），如果无法提取则返回 None
    """
    if not filename:
        return None
    
    # 模式 1: YYYYMMDD (8位数字)
    pattern1 = r'(\d{8})'
    match = re.search(pattern1, filename)
    if match:
        date_str = match.group(1)
        try:
            # 验证日期有效性
            date_obj = datetime.strptime(date_str, "%Y%m%d")
            return date_obj.strftime("%Y-%m-%d")
        except ValueError:
            pass
    
    # 模式 2: YYYY-MM-DD 或 YYYY_MM_DD
    pattern2 = r'(\d{4})[-_](\d{2})[-_](\d{2})'
    match = re.search(pattern2, filename)
    if match:
        year, month, day = match.groups()
        try:
            # 验证日期有效性
            date_obj = datetime(int(year), int(month), int(day))
            return date_obj.strftime("%Y-%m-%d")
        except ValueError:
            pass
    
    return None


def extract_time_from_filename(filename: str) -> Optional[str]:
    """
    从文件名中提取时间
    
    支持的格式：
    - meeting_1430.wav -> 14:30
    - meeting_14_30.mp3 -> 14:30
    - meeting_143045.ogg -> 14:30:45
    
    Args:
        filename: 文件名
        
    Returns:
        str: 时间字符串（HH:MM 或 HH:MM:SS），如果无法提取则返回 None
    """
    if not filename:
        return None
    
    # 模式 1: HHMM (4位数字，不在日期中)
    # 先移除日期部分，避免误匹配
    filename_without_date = re.sub(r'\d{8}', '', filename)
    filename_without_date = re.sub(r'\d{4}[-_]\d{2}[-_]\d{2}', '', filename_without_date)
    
    pattern1 = r'(\d{4})(?!\d)'  # 4位数字，后面不跟数字
    match = re.search(pattern1, filename_without_date)
    if match:
        time_str = match.group(1)
        hour = int(time_str[:2])
        minute = int(time_str[2:])
        if 0 <= hour < 24 and 0 <= minute < 60:
            return f"{hour:02d}:{minute:02d}"
    
    # 模式 2: HH:MM 或 HH_MM
    pattern2 = r'(\d{2})[:_](\d{2})'
    match = re.search(pattern2, filename_without_date)
    if match:
        hour, minute = match.groups()
        hour, minute = int(hour), int(minute)
        if 0 <= hour < 24 and 0 <= minute < 60:
            return f"{hour:02d}:{minute:02d}"
    
    # 模式 3: HHMMSS (6位数字)
    pattern3 = r'(\d{6})(?!\d)'
    match = re.search(pattern3, filename_without_date)
    if match:
        time_str = match.group(1)
        hour = int(time_str[:2])
        minute = int(time_str[2:4])
        second = int(time_str[4:])
        if 0 <= hour < 24 and 0 <= minute < 60 and 0 <= second < 60:
            return f"{hour:02d}:{minute:02d}:{second:02d}"
    
    return None


def extract_meeting_metadata(
    original_filenames: Optional[list[str]] = None,
    meeting_date: Optional[str] = None,
    meeting_time: Optional[str] = None,
) -> Tuple[Optional[str], Optional[str]]:
    """
    提取会议元数据（日期和时间）
    
    策略：
    - 日期：用户提供 > 文件名提取 > 当前日期
    - 时间：仅使用用户明确提供的时间（不推算，避免不准确）
    
    Args:
        original_filenames: 原始文件名列表
        meeting_date: 用户提供的会议日期
        meeting_time: 用户提供的会议时间
        
    Returns:
        Tuple[Optional[str], Optional[str]]: (日期, 时间)
    """
    # 如果用户已提供，直接使用
    if meeting_date and meeting_time:
        return meeting_date, meeting_time
    
    extracted_date = meeting_date
    extracted_time = meeting_time  # 只使用用户提供的时间
    
    # 从文件名提取日期（如果用户未提供）
    if not extracted_date and original_filenames and len(original_filenames) > 0:
        first_filename = original_filenames[0]
        extracted_date = extract_date_from_filename(first_filename)
        if extracted_date:
            logger.info(f"Extracted date from filename: {extracted_date}")
    
    # 如果还是没有日期，使用当前日期
    if not extracted_date:
        extracted_date = datetime.now().strftime("%Y-%m-%d")
        logger.info(f"Using current date: {extracted_date}")
    
    return extracted_date, extracted_time


def format_meeting_datetime(date: Optional[str], time: Optional[str]) -> str:
    """
    格式化会议日期时间为可读字符串
    
    Args:
        date: 日期字符串（YYYY-MM-DD）
        time: 时间字符串（HH:MM 或 HH:MM - HH:MM）
        
    Returns:
        str: 格式化后的字符串，如 "2026年1月21日 14:00 - 15:30"
    """
    if not date and not time:
        return ""
    
    result = []
    
    if date:
        try:
            date_obj = datetime.strptime(date, "%Y-%m-%d")
            result.append(date_obj.strftime("%Y年%m月%d日"))
        except ValueError:
            result.append(date)
    
    if time:
        result.append(time)
    
    return " ".join(result)

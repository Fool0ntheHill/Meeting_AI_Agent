"""Property-based tests for audio processing utilities.

Feature: meeting-minutes-agent
Property 9: 音频格式转换
Property 13: 音频文件连接顺序
Property 14: 时间戳偏移调整
验证: 需求 11.2, 18.1, 18.2

属性 9: 对于任何音频文件,转换为目标格式后应当满足 16kHz, mono, 16-bit WAV 的规格。
属性 13: 对于任何音频文件列表,拼接后的音频时长应当等于所有输入音频时长之和。
属性 14: 对于任何音频文件列表,拼接时返回的时间戳偏移应当正确反映每个音频在拼接结果中的起始位置。
"""

import tempfile
from pathlib import Path
from typing import List

import pytest
from hypothesis import given, strategies as st

from src.core.exceptions import AudioFormatError
from src.utils.audio import AudioProcessor

# 检查是否有 pydub
try:
    from pydub import AudioSegment as PydubAudioSegment
    PYDUB_AVAILABLE = True
except ImportError:
    PYDUB_AVAILABLE = False


# ============================================================================
# Helper Functions
# ============================================================================


def create_test_audio_file(duration_ms: int = 1000, sample_rate: int = 44100) -> str:
    """
    创建测试音频文件
    
    Args:
        duration_ms: 时长(毫秒)
        sample_rate: 采样率
        
    Returns:
        str: 临时文件路径
    """
    if not PYDUB_AVAILABLE:
        pytest.skip("pydub not available")
    
    # 创建静音音频
    audio = PydubAudioSegment.silent(duration=duration_ms, frame_rate=sample_rate)
    
    # 保存到临时文件
    temp_file = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    temp_file.close()
    audio.export(temp_file.name, format="wav")
    
    return temp_file.name


def get_audio_properties(audio_path: str) -> dict:
    """
    获取音频属性
    
    Args:
        audio_path: 音频文件路径
        
    Returns:
        dict: 音频属性 {sample_rate, channels, sample_width, duration_ms}
    """
    if not PYDUB_AVAILABLE:
        pytest.skip("pydub not available")
    
    audio = PydubAudioSegment.from_wav(audio_path)
    return {
        "sample_rate": audio.frame_rate,
        "channels": audio.channels,
        "sample_width": audio.sample_width,
        "duration_ms": len(audio),
    }


# ============================================================================
# Property 9: 音频格式转换
# ============================================================================


@pytest.mark.skipif(not PYDUB_AVAILABLE, reason="pydub not available")
class TestAudioFormatConversion:
    """Test audio format conversion properties"""
    
    @given(
        st.integers(min_value=500, max_value=5000),  # duration_ms
        st.sampled_from([8000, 16000, 22050, 44100, 48000]),  # sample_rate
    )
    @pytest.mark.asyncio
    async def test_convert_format_produces_target_specs(
        self, duration_ms: int, sample_rate: int
    ):
        """
        Property: 对于任何音频文件,转换后应当满足目标规格
        (16kHz, mono, 16-bit WAV)
        """
        processor = AudioProcessor()
        
        # 创建测试音频
        input_file = create_test_audio_file(duration_ms, sample_rate)
        
        try:
            # 转换格式
            output_file = await processor.convert_format(input_file)
            
            # 验证输出格式
            props = get_audio_properties(output_file)
            
            assert props["sample_rate"] == 16000, "采样率应为 16kHz"
            assert props["channels"] == 1, "应为单声道"
            assert props["sample_width"] == 2, "应为 16-bit (2 bytes)"
            
            # 清理
            Path(output_file).unlink(missing_ok=True)
            
        finally:
            # 清理输入文件
            Path(input_file).unlink(missing_ok=True)
    
    @pytest.mark.asyncio
    async def test_convert_format_preserves_approximate_duration(self):
        """
        Property: 转换格式不应显著改变音频时长
        (允许小幅度差异,因为重采样可能导致轻微变化)
        """
        processor = AudioProcessor()
        
        # 创建 2 秒的测试音频
        duration_ms = 2000
        input_file = create_test_audio_file(duration_ms, 44100)
        
        try:
            # 转换格式
            output_file = await processor.convert_format(input_file)
            
            # 验证时长(允许 5% 的误差)
            output_props = get_audio_properties(output_file)
            duration_diff = abs(output_props["duration_ms"] - duration_ms)
            tolerance = duration_ms * 0.05
            
            assert duration_diff <= tolerance, (
                f"时长变化过大: {duration_diff}ms (tolerance: {tolerance}ms)"
            )
            
            # 清理
            Path(output_file).unlink(missing_ok=True)
            
        finally:
            Path(input_file).unlink(missing_ok=True)


# ============================================================================
# Property 13: 音频文件连接顺序
# ============================================================================


@pytest.mark.skipif(not PYDUB_AVAILABLE, reason="pydub not available")
class TestAudioConcatenation:
    """Test audio concatenation properties"""
    
    @given(
        st.lists(
            st.integers(min_value=500, max_value=2000),  # duration_ms for each file
            min_size=2,
            max_size=5,
        )
    )
    @pytest.mark.asyncio
    async def test_concatenate_preserves_total_duration(self, durations: List[int]):
        """
        Property: 拼接后的音频时长应当等于所有输入音频时长之和
        """
        processor = AudioProcessor()
        
        # 创建多个测试音频文件
        input_files = []
        try:
            for duration_ms in durations:
                file_path = create_test_audio_file(duration_ms, 16000)
                input_files.append(file_path)
            
            # 拼接音频
            output_file, offsets = await processor.concatenate_audio(input_files)
            
            # 验证总时长
            expected_duration_ms = sum(durations)
            output_props = get_audio_properties(output_file)
            
            # 允许小幅度误差(每个文件 10ms)
            tolerance = len(durations) * 10
            duration_diff = abs(output_props["duration_ms"] - expected_duration_ms)
            
            assert duration_diff <= tolerance, (
                f"总时长不匹配: expected {expected_duration_ms}ms, "
                f"got {output_props['duration_ms']}ms, "
                f"diff {duration_diff}ms (tolerance: {tolerance}ms)"
            )
            
            # 清理
            Path(output_file).unlink(missing_ok=True)
            
        finally:
            # 清理所有输入文件
            for file_path in input_files:
                Path(file_path).unlink(missing_ok=True)
    
    @pytest.mark.asyncio
    async def test_concatenate_empty_list_raises_error(self):
        """
        Property: 空的音频文件列表应当抛出错误
        """
        processor = AudioProcessor()
        
        with pytest.raises(AudioFormatError, match="音频文件列表为空"):
            await processor.concatenate_audio([])


# ============================================================================
# Property 14: 时间戳偏移调整
# ============================================================================


@pytest.mark.skipif(not PYDUB_AVAILABLE, reason="pydub not available")
class TestTimestampOffsets:
    """Test timestamp offset calculation properties"""
    
    @given(
        st.lists(
            st.integers(min_value=500, max_value=2000),  # duration_ms for each file
            min_size=2,
            max_size=5,
        )
    )
    @pytest.mark.asyncio
    async def test_offsets_reflect_cumulative_positions(self, durations: List[int]):
        """
        Property: 时间戳偏移应当正确反映每个音频在拼接结果中的起始位置
        """
        processor = AudioProcessor()
        
        # 创建多个测试音频文件
        input_files = []
        try:
            for duration_ms in durations:
                file_path = create_test_audio_file(duration_ms, 16000)
                input_files.append(file_path)
            
            # 拼接音频
            output_file, offsets = await processor.concatenate_audio(input_files)
            
            # 验证偏移数量
            assert len(offsets) == len(durations), (
                f"偏移数量应等于输入文件数量: {len(offsets)} != {len(durations)}"
            )
            
            # 验证第一个偏移为 0
            assert offsets[0] == 0.0, "第一个音频的偏移应为 0"
            
            # 验证每个偏移是前面所有音频时长的累加
            cumulative_duration = 0.0
            for i, duration_ms in enumerate(durations[:-1]):  # 不包括最后一个
                cumulative_duration += duration_ms / 1000.0  # 转换为秒
                
                # 允许小幅度误差(10ms = 0.01s)
                offset_diff = abs(offsets[i + 1] - cumulative_duration)
                assert offset_diff <= 0.01, (
                    f"偏移 {i+1} 不正确: expected {cumulative_duration}s, "
                    f"got {offsets[i+1]}s, diff {offset_diff}s"
                )
            
            # 清理
            Path(output_file).unlink(missing_ok=True)
            
        finally:
            # 清理所有输入文件
            for file_path in input_files:
                Path(file_path).unlink(missing_ok=True)
    
    @pytest.mark.asyncio
    async def test_offsets_are_monotonically_increasing(self):
        """
        Property: 时间戳偏移应当单调递增
        """
        processor = AudioProcessor()
        
        # 创建 3 个测试音频文件
        durations = [1000, 1500, 2000]  # ms
        input_files = []
        
        try:
            for duration_ms in durations:
                file_path = create_test_audio_file(duration_ms, 16000)
                input_files.append(file_path)
            
            # 拼接音频
            output_file, offsets = await processor.concatenate_audio(input_files)
            
            # 验证单调递增
            for i in range(len(offsets) - 1):
                assert offsets[i] < offsets[i + 1], (
                    f"偏移应单调递增: offsets[{i}]={offsets[i]} >= "
                    f"offsets[{i+1}]={offsets[i+1]}"
                )
            
            # 清理
            Path(output_file).unlink(missing_ok=True)
            
        finally:
            # 清理所有输入文件
            for file_path in input_files:
                Path(file_path).unlink(missing_ok=True)


# ============================================================================
# Run tests
# ============================================================================


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

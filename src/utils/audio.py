"""Audio processing utilities."""

import io
import subprocess
import tempfile
from pathlib import Path
from typing import List, Optional, Tuple

try:
    from pydub import AudioSegment as PydubAudioSegment
    from pydub.exceptions import CouldntDecodeError

    PYDUB_AVAILABLE = True
except ImportError:
    PYDUB_AVAILABLE = False
    PydubAudioSegment = None
    CouldntDecodeError = Exception

from src.core.exceptions import AudioFormatError


class AudioProcessor:
    """音频处理器"""

    def __init__(self):
        """初始化音频处理器"""
        self.target_sample_rate = 16000  # 16kHz
        self.target_channels = 1  # Mono
        self.target_sample_width = 2  # 16-bit

    async def extract_segment(
        self, audio_path: str, start_time: float, end_time: float
    ) -> bytes:
        """
        提取音频片段

        Args:
            audio_path: 音频文件路径
            start_time: 开始时间(秒)
            end_time: 结束时间(秒)

        Returns:
            bytes: 音频片段数据(WAV 格式)

        Raises:
            AudioFormatError: 音频格式错误
        """
        try:
            # 确保路径是字符串格式
            audio_path_str = str(Path(audio_path))
            
            # 计算持续时间
            duration = end_time - start_time
            
            # 创建临时输出文件
            temp_output = tempfile.NamedTemporaryFile(
                delete=False,
                suffix='.wav'
            )
            temp_output.close()
            
            try:
                # 使用 ffmpeg 提取并转换片段
                cmd = [
                    'ffmpeg',
                    '-y',  # 覆盖输出文件
                    '-ss', str(start_time),  # 开始时间
                    '-t', str(duration),  # 持续时间
                    '-i', audio_path_str,  # 输入文件
                    '-ar', str(self.target_sample_rate),  # 采样率 16kHz
                    '-ac', str(self.target_channels),  # 单声道
                    '-sample_fmt', 's16',  # 16bit
                    '-f', 'wav',  # WAV格式
                    temp_output.name  # 输出文件
                ]
                
                # 执行 ffmpeg
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                
                if result.returncode != 0:
                    raise AudioFormatError(
                        f"ffmpeg 转换失败: {result.stderr}",
                        details={"path": audio_path, "start": start_time, "end": end_time},
                    )
                
                # 读取输出文件
                with open(temp_output.name, 'rb') as f:
                    audio_bytes = f.read()
                
                return audio_bytes
                
            finally:
                # 清理临时文件
                import os
                try:
                    if os.path.exists(temp_output.name):
                        os.unlink(temp_output.name)
                except:
                    pass

        except subprocess.TimeoutExpired:
            raise AudioFormatError(
                f"ffmpeg 转换超时",
                details={"path": audio_path, "start": start_time, "end": end_time},
            )
        except AudioFormatError:
            raise
        except Exception as e:
            raise AudioFormatError(
                f"提取音频片段失败: {e}",
                details={"path": audio_path, "start": start_time, "end": end_time, "error": str(e)},
            )

    async def convert_format(
        self, audio_path: str, output_path: Optional[str] = None
    ) -> str:
        """
        转换音频格式为 16kHz, mono, 16-bit WAV

        Args:
            audio_path: 输入音频文件路径
            output_path: 输出文件路径,如果为 None 则使用临时文件

        Returns:
            str: 输出文件路径

        Raises:
            AudioFormatError: 音频格式错误
        """
        try:
            # 确保路径是字符串格式
            audio_path_str = str(Path(audio_path))
            
            # 确定输出路径
            if output_path is None:
                # 创建临时文件
                temp_file = tempfile.NamedTemporaryFile(
                    suffix=".wav", delete=False, mode="wb"
                )
                output_path = temp_file.name
                temp_file.close()
            
            # 使用 ffmpeg 转换
            cmd = [
                'ffmpeg',
                '-y',  # 覆盖输出文件
                '-i', audio_path_str,  # 输入文件
                '-ar', str(self.target_sample_rate),  # 采样率 16kHz
                '-ac', str(self.target_channels),  # 单声道
                '-sample_fmt', 's16',  # 16bit
                '-f', 'wav',  # WAV格式
                output_path  # 输出文件
            ]
            
            # 执行 ffmpeg
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode != 0:
                raise AudioFormatError(
                    f"ffmpeg 转换失败: {result.stderr}",
                    details={"path": audio_path},
                )
            
            return output_path

        except subprocess.TimeoutExpired:
            raise AudioFormatError(
                f"ffmpeg 转换超时",
                details={"path": audio_path},
            )
        except AudioFormatError:
            raise
        except Exception as e:
            raise AudioFormatError(
                f"转换音频格式失败: {e}",
                details={"path": audio_path, "error": str(e)},
            )

    async def concatenate_audio(
        self, audio_paths: List[str], output_path: Optional[str] = None
    ) -> Tuple[str, List[float]]:
        """
        拼接多个音频文件

        Args:
            audio_paths: 音频文件路径列表(按顺序)
            output_path: 输出文件路径,如果为 None 则使用临时文件

        Returns:
            Tuple[str, List[float]]: (输出文件路径, 每个音频的时间戳偏移列表)

        Raises:
            AudioFormatError: 音频格式错误
        """
        if not audio_paths:
            raise AudioFormatError("音频文件列表为空")

        try:
            # 加载并拼接音频
            combined = None
            offsets = [0.0]  # 第一个音频的偏移为 0

            for audio_path in audio_paths:
                # 确保路径是字符串格式
                audio_path_str = str(Path(audio_path))
                
                # 加载音频 - 明确指定格式以避免 codec_type 错误
                file_ext = Path(audio_path).suffix.lower().lstrip('.')
                if file_ext in ['ogg', 'oga']:
                    audio = PydubAudioSegment.from_ogg(audio_path_str)
                elif file_ext in ['mp3']:
                    audio = PydubAudioSegment.from_mp3(audio_path_str)
                elif file_ext in ['wav']:
                    audio = PydubAudioSegment.from_wav(audio_path_str)
                elif file_ext in ['m4a', 'mp4']:
                    audio = PydubAudioSegment.from_file(audio_path_str, format='m4a')
                else:
                    # 对于其他格式，使用通用方法
                    audio = PydubAudioSegment.from_file(audio_path_str)
                
                audio = self._convert_to_target_format(audio)

                if combined is None:
                    combined = audio
                else:
                    # 记录当前偏移(秒)
                    current_offset = len(combined) / 1000.0
                    offsets.append(current_offset)
                    # 拼接
                    combined += audio

            # 确定输出路径
            if output_path is None:
                temp_file = tempfile.NamedTemporaryFile(
                    suffix=".wav", delete=False, mode="wb"
                )
                output_path = temp_file.name
                temp_file.close()

            # 导出
            combined.export(output_path, format="wav")
            return output_path, offsets

        except CouldntDecodeError as e:
            raise AudioFormatError(
                f"无法解码音频文件",
                details={"error": str(e)},
            )
        except Exception as e:
            raise AudioFormatError(
                f"拼接音频失败: {e}",
                details={"error": str(e)},
            )

    def get_duration(self, audio_path: str) -> float:
        """
        获取音频时长

        Args:
            audio_path: 音频文件路径

        Returns:
            float: 时长(秒)

        Raises:
            AudioFormatError: 音频格式错误
        """
        try:
            # 确保路径是字符串格式
            audio_path_str = str(Path(audio_path))
            
            # 使用 ffprobe 获取音频时长
            cmd = [
                'ffprobe',
                '-v', 'error',
                '-show_entries', 'format=duration',
                '-of', 'default=noprint_wrappers=1:nokey=1',
                audio_path_str
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode != 0:
                raise AudioFormatError(
                    f"ffprobe 获取时长失败: {result.stderr}",
                    details={"path": audio_path},
                )
            
            # 解析时长
            duration_str = result.stdout.strip()
            duration = float(duration_str)
            
            return duration
            
        except subprocess.TimeoutExpired:
            raise AudioFormatError(
                f"ffprobe 获取时长超时",
                details={"path": audio_path},
            )
        except ValueError as e:
            raise AudioFormatError(
                f"无法解析音频时长: {e}",
                details={"path": audio_path, "error": str(e)},
            )
        except Exception as e:
            raise AudioFormatError(
                f"获取音频时长失败: {e}",
                details={"path": str(audio_path), "error": str(e)},
            )

    def _convert_to_target_format(self, audio: PydubAudioSegment) -> PydubAudioSegment:
        """
        转换音频为目标格式

        Args:
            audio: 输入音频

        Returns:
            PydubAudioSegment: 转换后的音频
        """
        # 设置采样率
        if audio.frame_rate != self.target_sample_rate:
            audio = audio.set_frame_rate(self.target_sample_rate)

        # 设置声道数
        if audio.channels != self.target_channels:
            audio = audio.set_channels(self.target_channels)

        # 设置采样宽度
        if audio.sample_width != self.target_sample_width:
            audio = audio.set_sample_width(self.target_sample_width)

        return audio

    def validate_audio_format(self, audio_path: str) -> bool:
        """
        验证音频格式是否符合要求

        Args:
            audio_path: 音频文件路径

        Returns:
            bool: 是否符合要求

        Raises:
            AudioFormatError: 音频格式错误
        """
        try:
            # 确保路径是字符串格式
            audio_path_str = str(Path(audio_path))
            
            # 加载音频 - 明确指定格式以避免 codec_type 错误
            file_ext = Path(audio_path).suffix.lower().lstrip('.')
            if file_ext in ['ogg', 'oga']:
                audio = PydubAudioSegment.from_ogg(audio_path_str)
            elif file_ext in ['mp3']:
                audio = PydubAudioSegment.from_mp3(audio_path_str)
            elif file_ext in ['wav']:
                audio = PydubAudioSegment.from_wav(audio_path_str)
            elif file_ext in ['m4a', 'mp4']:
                audio = PydubAudioSegment.from_file(audio_path_str, format='m4a')
            else:
                # 对于其他格式，使用通用方法
                audio = PydubAudioSegment.from_file(audio_path_str)
            
            return (
                audio.frame_rate == self.target_sample_rate
                and audio.channels == self.target_channels
                and audio.sample_width == self.target_sample_width
            )
        except CouldntDecodeError as e:
            raise AudioFormatError(
                f"无法解码音频文件: {audio_path}",
                details={"path": audio_path, "error": str(e)},
            )
        except Exception as e:
            raise AudioFormatError(
                f"验证音频格式失败: {e}",
                details={"path": audio_path, "error": str(e)},
            )

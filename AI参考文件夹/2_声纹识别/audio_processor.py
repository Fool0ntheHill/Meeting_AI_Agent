#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
音频处理器 - 用于从火山引擎TOS提取会议录音片段并转换为讯飞声纹识别格式

功能：
1. 从TOS流式下载音频文件
2. 根据火山ASR结果筛选最佳说话人片段
3. 转换为讯飞声纹识别要求的格式（16kHz, 单声道, 16bit, WAV）

依赖：
- tos: 火山引擎 TOS SDK
- ffmpeg: 音频处理工具（需要安装到系统）
"""

import io
import os
import subprocess
import tempfile
from typing import Dict, List, Optional
import tos


class AudioProcessor:
    """音频处理器类 - 处理TOS音频并提取声纹样本"""
    
    # 讯飞声纹识别格式要求
    TARGET_SAMPLE_RATE = 16000  # 采样率：16kHz
    TARGET_CHANNELS = 1         # 声道：单声道
    TARGET_SAMPLE_WIDTH = 2     # 位深：2字节（16bit）
    TARGET_FORMAT = "wav"       # 格式：WAV
    
    # 片段筛选参数
    MIN_DURATION = 0.5          # 最小时长（秒）- 讯飞要求
    IDEAL_MIN_DURATION = 3.0    # 理想最小时长（秒）
    IDEAL_MAX_DURATION = 6.0    # 理想最大时长（秒）- 讯飞推荐3-5秒
    
    def __init__(self, verbose: bool = True):
        """
        初始化音频处理器
        
        Args:
            verbose: 是否打印详细日志
        """
        self.verbose = verbose
    
    def _log(self, message: str):
        """打印日志（如果启用）"""
        if self.verbose:
            print(f"[AudioProcessor] {message}")
    
    def process_segments(
        self,
        tos_client: tos.TosClientV2,
        bucket_name: str,
        object_key: str,
        utterances: List[Dict]
    ) -> Dict[str, bytes]:
        """
        处理音频片段，提取每个说话人的最佳样本
        
        Args:
            tos_client: 已初始化的TOS客户端
            bucket_name: TOS存储桶名称
            object_key: 音频文件的Key
            utterances: 火山ASR结果的utterances列表
                       每个元素包含: speaker, start_time(ms), end_time(ms), text
        
        Returns:
            字典，格式为 {"Speaker 0": wav_bytes, "Speaker 1": wav_bytes, ...}
            如果处理失败，返回空字典
        """
        self._log(f"开始处理音频: {object_key}")
        self._log(f"总片段数: {len(utterances)}")
        
        # 第一步：从TOS下载音频到内存
        audio = self._download_audio_from_tos(tos_client, bucket_name, object_key)
        if audio is None:
            return {}
        
        # 第二步：筛选每个说话人的最佳片段
        best_segments = self._select_best_segments(utterances)
        if not best_segments:
            self._log("未找到符合条件的片段")
            return {}
        
        # 第三步：提取并转换音频片段
        result = {}
        for speaker, segment_info in best_segments.items():
            try:
                # 提取片段
                audio_bytes = self._extract_and_convert_segment(
                    audio,
                    segment_info['start_time'],
                    segment_info['end_time']
                )
                
                if audio_bytes:
                    result[speaker] = audio_bytes
                    duration = (segment_info['end_time'] - segment_info['start_time']) / 1000.0
                    self._log(f"✓ {speaker}: {duration:.2f}秒 -> {len(audio_bytes)} 字节")
                else:
                    self._log(f"✗ {speaker}: 转换失败")
                    
            except Exception as e:
                self._log(f"✗ {speaker}: 处理出错 - {e}")
                continue
        
        # 清理临时文件
        try:
            if audio and os.path.exists(audio):
                os.unlink(audio)
                self._log(f"清理临时文件: {audio}")
        except:
            pass
        
        self._log(f"处理完成，成功提取 {len(result)}/{len(best_segments)} 个说话人样本")
        return result
    
    def _download_audio_from_tos(
        self,
        tos_client: tos.TosClientV2,
        bucket_name: str,
        object_key: str
    ) -> Optional[str]:
        """
        从TOS下载音频文件到临时文件
        
        Args:
            tos_client: TOS客户端
            bucket_name: 存储桶名称
            object_key: 对象Key
        
        Returns:
            临时文件路径，失败返回None
        """
        try:
            self._log(f"从TOS下载: {bucket_name}/{object_key}")
            
            # 使用TOS SDK下载对象
            response = tos_client.get_object(bucket_name, object_key)
            
            # 读取音频数据
            audio_data = response.content.read()
            audio_size_mb = len(audio_data) / (1024 * 1024)
            self._log(f"下载完成: {audio_size_mb:.2f} MB")
            
            # 保存到临时文件
            # 获取文件扩展名
            _, ext = os.path.splitext(object_key)
            if not ext:
                ext = '.ogg'  # 默认扩展名
            
            # 创建临时文件
            temp_file = tempfile.NamedTemporaryFile(
                delete=False,
                suffix=ext
            )
            temp_file.write(audio_data)
            temp_file.close()
            
            self._log(f"保存到临时文件: {temp_file.name}")
            
            # 使用 ffprobe 获取音频信息
            try:
                result = subprocess.run(
                    ['ffprobe', '-v', 'error', '-show_entries',
                     'stream=sample_rate,channels,duration',
                     '-of', 'default=noprint_wrappers=1',
                     temp_file.name],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                
                if result.returncode == 0:
                    info = result.stdout
                    self._log(f"音频信息:\n{info.strip()}")
            except:
                pass  # 获取信息失败不影响主流程
            
            return temp_file.name
            
        except tos.exceptions.TosClientError as e:
            self._log(f"TOS下载失败: {e.message}")
            return None
        except Exception as e:
            self._log(f"音频下载失败: {e}")
            return None
    
    def _select_best_segments(self, utterances: List[Dict]) -> Dict[str, Dict]:
        """
        为每个说话人筛选最佳片段
        
        筛选策略：
        1. 优先选择3-6秒的片段（讯飞推荐）
        2. 如果没有，选择最长的片段
        3. 忽略小于0.5秒的片段
        
        Args:
            utterances: 火山ASR的utterances列表
        
        Returns:
            字典，格式为 {"Speaker 0": {"start_time": ms, "end_time": ms, "duration": s}, ...}
        """
        self._log("开始筛选最佳片段...")
        
        # 按说话人分组
        speaker_segments = {}
        
        for utt in utterances:
            speaker = utt.get('additions', {}).get('speaker', 'Unknown')
            if speaker == 'Unknown':
                continue
            
            # 格式化说话人标签
            speaker_label = f"Speaker {speaker}"
            
            start_time = utt.get('start_time', 0)  # 毫秒
            end_time = utt.get('end_time', 0)      # 毫秒
            duration = (end_time - start_time) / 1000.0  # 转换为秒
            
            # 过滤太短的片段
            if duration < self.MIN_DURATION:
                continue
            
            if speaker_label not in speaker_segments:
                speaker_segments[speaker_label] = []
            
            speaker_segments[speaker_label].append({
                'start_time': start_time,
                'end_time': end_time,
                'duration': duration
            })
        
        self._log(f"找到 {len(speaker_segments)} 个说话人")
        
        # 为每个说话人选择最佳片段
        best_segments = {}
        
        for speaker, segments in speaker_segments.items():
            # 策略1：优先选择3-6秒的片段
            ideal_segments = [
                seg for seg in segments
                if self.IDEAL_MIN_DURATION <= seg['duration'] <= self.IDEAL_MAX_DURATION
            ]
            
            if ideal_segments:
                # 策略改进：优先选择最长的片段（包含更多声音信息）
                # 在 3-6 秒范围内，越长越好
                best = max(ideal_segments, key=lambda x: x['duration'])
                best_segments[speaker] = best
                self._log(f"  {speaker}: 选择理想片段 {best['duration']:.2f}秒")
            else:
                # 策略2：选择最长的片段
                best = max(segments, key=lambda x: x['duration'])
                best_segments[speaker] = best
                self._log(f"  {speaker}: 选择最长片段 {best['duration']:.2f}秒 "
                         f"(无3-6秒片段)")
        
        return best_segments
    
    def _extract_and_convert_segment(
        self,
        audio_file: str,
        start_ms: int,
        end_ms: int
    ) -> Optional[bytes]:
        """
        使用 ffmpeg 提取音频片段并转换为讯飞要求的格式
        
        Args:
            audio_file: 音频文件路径
            start_ms: 开始时间（毫秒）
            end_ms: 结束时间（毫秒）
        
        Returns:
            WAV格式的音频字节，失败返回None
        """
        try:
            # 转换时间为秒
            start_sec = start_ms / 1000.0
            duration_sec = (end_ms - start_ms) / 1000.0
            
            # 创建临时输出文件
            output_file = tempfile.NamedTemporaryFile(
                delete=False,
                suffix='.wav'
            )
            output_file.close()
            
            # 使用 ffmpeg 提取并转换片段
            # -ss: 开始时间
            # -t: 持续时间
            # -ar: 采样率 16000Hz
            # -ac: 声道数 1 (单声道)
            # -sample_fmt: 采样格式 s16 (16bit有符号整数)
            # -f: 输出格式 wav
            cmd = [
                'ffmpeg',
                '-y',  # 覆盖输出文件
                '-ss', str(start_sec),  # 开始时间
                '-t', str(duration_sec),  # 持续时间
                '-i', audio_file,  # 输入文件
                '-ar', str(self.TARGET_SAMPLE_RATE),  # 采样率 16kHz
                '-ac', str(self.TARGET_CHANNELS),  # 单声道
                '-sample_fmt', 's16',  # 16bit
                '-f', 'wav',  # WAV格式
                output_file.name  # 输出文件
            ]
            
            # 执行 ffmpeg
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode != 0:
                self._log(f"ffmpeg 转换失败: {result.stderr}")
                os.unlink(output_file.name)
                return None
            
            # 读取输出文件
            with open(output_file.name, 'rb') as f:
                audio_bytes = f.read()
            
            # 删除临时文件
            os.unlink(output_file.name)
            
            # 验证大小（讯飞要求Base64后不超过4M，原始约3M）
            size_mb = len(audio_bytes) / (1024 * 1024)
            if size_mb > 3.0:
                self._log(f"警告: 音频片段过大 ({size_mb:.2f}MB)，可能超过讯飞限制")
            
            return audio_bytes
            
        except subprocess.TimeoutExpired:
            self._log(f"ffmpeg 转换超时")
            return None
        except Exception as e:
            self._log(f"片段转换失败: {e}")
            return None
    
    def save_segments_to_files(
        self,
        segments: Dict[str, bytes],
        output_dir: str = ".",
        prefix: str = "speaker"
    ):
        """
        将提取的音频片段保存为文件（可选功能，用于调试）
        
        Args:
            segments: process_segments返回的字典
            output_dir: 输出目录
            prefix: 文件名前缀
        """
        import os
        
        os.makedirs(output_dir, exist_ok=True)
        
        for speaker, audio_bytes in segments.items():
            # 清理说话人标签作为文件名
            speaker_clean = speaker.replace(" ", "_").lower()
            filename = f"{prefix}_{speaker_clean}.wav"
            filepath = os.path.join(output_dir, filename)
            
            with open(filepath, 'wb') as f:
                f.write(audio_bytes)
            
            self._log(f"保存: {filepath} ({len(audio_bytes)} 字节)")


# 使用示例
if __name__ == "__main__":
    """
    使用示例：从TOS提取会议录音的说话人样本
    """
    import tos
    
    # 1. 初始化TOS客户端
    tos_config = {
        "access_key": "YOUR_ACCESS_KEY",
        "secret_key": "YOUR_SECRET_KEY",
        "endpoint": "https://tos-cn-beijing.volces.com",
        "region": "cn-beijing"
    }
    
    tos_client = tos.TosClientV2(
        tos_config['access_key'],
        tos_config['secret_key'],
        tos_config['endpoint'],
        tos_config['region']
    )
    
    # 2. 准备参数
    bucket_name = "meeting-agent-test"
    object_key = "20251229ONE产品和业务规则中心的设计讨论会议.ogg"
    
    # 3. 模拟火山ASR结果（实际使用时从API获取）
    utterances = [
        {
            "additions": {"speaker": "1"},
            "start_time": 2000,   # 2秒
            "end_time": 6500,     # 6.5秒（4.5秒片段）
            "text": "我先简单的实现了一下样例..."
        },
        {
            "additions": {"speaker": "2"},
            "start_time": 27000,  # 27秒
            "end_time": 30000,    # 30秒（3秒片段）
            "text": "但是他们是在一个统一的导航里面..."
        },
        {
            "additions": {"speaker": "1"},
            "start_time": 35000,
            "end_time": 36000,    # 1秒片段（较短）
            "text": "对"
        }
    ]
    
    # 4. 创建处理器并处理
    processor = AudioProcessor(verbose=True)
    
    result = processor.process_segments(
        tos_client=tos_client,
        bucket_name=bucket_name,
        object_key=object_key,
        utterances=utterances
    )
    
    # 5. 查看结果
    print("\n" + "=" * 60)
    print("处理结果:")
    print("=" * 60)
    for speaker, audio_bytes in result.items():
        print(f"{speaker}: {len(audio_bytes)} 字节 ({len(audio_bytes)/1024:.1f} KB)")
    
    # 6. （可选）保存为文件用于测试
    if result:
        processor.save_segments_to_files(result, output_dir="./voiceprint_samples")
        print("\n音频样本已保存到 ./voiceprint_samples/")

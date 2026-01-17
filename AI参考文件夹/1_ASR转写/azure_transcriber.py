"""
Azure语音服务Fast Transcription API实现
支持本地文件直接上传，无需URL
"""

import json
import time
import os
import subprocess
import requests
from .transcription_tester import TranscriptionTester


class AzureTranscriber(TranscriptionTester):
    """Azure语音识别实现（Fast Transcription API）"""
    
    def __init__(self, subscription_key, region, config=None):
        super().__init__(name="Azure")
        
        self.subscription_key = subscription_key
        self.region = region
        
        # API端点 - 根据文档，应该使用 YourServiceRegion.api.cognitive.microsoft.com
        self.api_version = "2024-11-15"
        self.endpoint = f"https://{region}.api.cognitive.microsoft.com/speechtotext/transcriptions:transcribe?api-version={self.api_version}"
        
        print(f"[DEBUG] API端点: {self.endpoint}")
        
        # 默认配置
        self.config = {
            "locales": ["zh-CN", "en-US"],  # 中英文混合
            "profanityFilterMode": "None",  # 不过滤脏词
            # 注意：eastasia区域不支持diarization
        }
        
        # 更新用户配置
        if config:
            self.config.update(config)
        
        # 文件大小限制
        self.max_file_size = 300 * 1024 * 1024  # 300MB
        self.max_duration = 2 * 3600  # 2小时
    
    def get_audio_duration(self, file_path):
        """获取音频文件的真实时长（秒）"""
        # 方法1: 尝试使用mutagen库
        try:
            from mutagen import File
            audio = File(file_path)
            if audio is not None and hasattr(audio.info, 'length'):
                return audio.info.length
        except ImportError:
            pass
        except Exception:
            pass
        
        # 方法2: 尝试使用ffprobe
        try:
            result = subprocess.run(
                ['ffprobe', '-v', 'error', '-show_entries', 'format=duration', 
                 '-of', 'default=noprint_wrappers=1:nokey=1', file_path],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                return float(result.stdout.strip())
        except Exception:
            pass
        
        # 方法3: 使用文件大小估算
        file_size = os.path.getsize(file_path)
        estimated_duration = (file_size * 8) / (64 * 1000)
        return estimated_duration
    
    def split_audio_file(self, audio_path, chunk_duration=120):
        """
        智能切分音频文件（参考腾讯云的实现）
        
        参数:
            audio_path: 音频文件路径
            chunk_duration: 每段目标时长（秒），默认120秒
        
        返回:
            切分后的文件路径列表 [(file_path, start_offset_ms), ...]
        """
        print(f"[*] 开始切分音频文件...")
        
        # 获取音频总时长
        total_duration_sec = self.get_audio_duration(audio_path)
        file_size = os.path.getsize(audio_path)
        file_size_mb = file_size / 1024 / 1024
        
        print(f"[*] 音频总时长: {total_duration_sec:.1f}秒")
        print(f"[*] 原始文件大小: {file_size_mb:.2f}MB")
        
        # 计算需要切分的段数
        num_chunks = int(total_duration_sec / chunk_duration) + 1
        
        if num_chunks == 1:
            print(f"[*] 音频时长较短，无需切分")
            return [(audio_path, 0)]
        
        print(f"[*] 预计切分为 {num_chunks} 段")
        
        # 创建临时目录
        temp_dir = "temp_audio_chunks"
        os.makedirs(temp_dir, exist_ok=True)
        
        # 使用ffmpeg切分音频
        chunk_files = []
        base_name = os.path.splitext(os.path.basename(audio_path))[0]
        
        for i in range(num_chunks):
            start_sec = i * chunk_duration
            start_ms = start_sec * 1000
            
            chunk_file = os.path.join(temp_dir, f"{base_name}_chunk_{i+1}.wav")
            
            print(f"[*] 切分片段 {i+1}/{num_chunks}: 从 {start_sec}秒 开始")
            
            # ffmpeg命令
            cmd = [
                'ffmpeg', '-i', audio_path,
                '-ss', str(start_sec),
                '-t', str(chunk_duration),
                '-acodec', 'pcm_s16le',
                '-ar', '16000',
                '-ac', '1',
                '-y',
                chunk_file
            ]
            
            try:
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=60
                )
                
                if result.returncode == 0 and os.path.exists(chunk_file):
                    chunk_size = os.path.getsize(chunk_file)
                    chunk_size_mb = chunk_size / 1024 / 1024
                    print(f"[+] 切分成功: {chunk_file} ({chunk_size_mb:.2f}MB)")
                    
                    chunk_files.append((chunk_file, start_ms))
                else:
                    print(f"[-] 切分片段 {i+1} 失败")
            except Exception as e:
                print(f"[-] 切分片段 {i+1} 异常: {e}")
        
        return chunk_files
    
    def transcribe_file(self, audio_path):
        """
        使用Fast Transcription API转写单个音频文件
        
        参数:
            audio_path: 音频文件路径
        
        返回:
            识别结果字典
        """
        try:
            # 检查文件格式，如果不是WAV，先转换
            file_ext = os.path.splitext(audio_path)[1].lower()
            
            if file_ext != '.wav':
                print(f"[*] 检测到 {file_ext} 格式，转换为WAV...")
                temp_wav = audio_path.replace(file_ext, '_temp.wav')
                
                # 使用ffmpeg转换
                cmd = [
                    'ffmpeg', '-i', audio_path,
                    '-acodec', 'pcm_s16le',
                    '-ar', '16000',
                    '-ac', '1',
                    '-y',
                    temp_wav
                ]
                
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=60
                )
                
                if result.returncode != 0:
                    print(f"[-] 音频转换失败")
                    return None
                
                audio_path = temp_wav
                print(f"[+] 转换成功: {temp_wav}")
            
            # 读取音频文件
            with open(audio_path, 'rb') as f:
                audio_data = f.read()
            
            file_size = len(audio_data)
            file_size_mb = file_size / 1024 / 1024
            
            print(f"[*] 文件大小: {file_size_mb:.2f}MB")
            
            # 检查文件大小
            if file_size > self.max_file_size:
                print(f"[!] 警告：文件大小 {file_size_mb:.2f}MB 超过限制 300MB")
                # 清理临时文件
                if file_ext != '.wav' and os.path.exists(audio_path):
                    try:
                        os.remove(audio_path)
                    except:
                        pass
                return None
            
            # 准备请求
            headers = {
                'Ocp-Apim-Subscription-Key': self.subscription_key
            }
            
            # 准备multipart/form-data
            files = {
                'audio': (os.path.basename(audio_path), audio_data, 'audio/wav')
            }
            
            # 准备definition（配置）
            definition = json.dumps(self.config)
            data = {
                'definition': definition
            }
            
            print(f"[*] 提交转写请求...")
            print(f"[*] 配置: {self.config}")
            
            # 发送请求
            response = requests.post(
                self.endpoint,
                headers=headers,
                files=files,
                data=data,
                timeout=6000  # 10分钟超时（8分钟音频可能需要较长时间）
            )
            
            # 清理临时文件
            if file_ext != '.wav' and os.path.exists(audio_path):
                try:
                    os.remove(audio_path)
                    print(f"[*] 清理临时文件: {audio_path}")
                except:
                    pass
            
            if response.status_code != 200:
                print(f"[-] HTTP错误: {response.status_code}")
                print(f"[-] 响应内容: {response.text}")
                return None
            
            result = response.json()
            print(f"[+] 转写成功！")
            
            return result
            
        except Exception as e:
            print(f"[-] 转写异常: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def parse_result(self, result, time_offset_ms=0):
        """
        解析Azure识别结果
        
        参数:
            result: Azure API返回的结果
            time_offset_ms: 时间偏移（用于合并多个片段）
        
        返回:
            (segments, plain_text)
        """
        segments = []
        plain_text = ""
        
        if not result or 'phrases' not in result:
            return segments, plain_text
        
        phrases = result.get('phrases', [])
        
        # 按说话人分组
        current_speaker = None
        current_text = ""
        current_start_ms = 0
        
        for phrase in phrases:
            offset_ms = phrase.get('offsetMilliseconds', 0) + time_offset_ms
            text = phrase.get('text', '')
            
            # 获取说话人ID（如果有diarization）
            speaker_id = phrase.get('speaker', 0)
            speaker = f"Speaker {speaker_id + 1}"
            
            # 如果说话人变化，保存前一个片段
            if current_speaker and current_speaker != speaker:
                if current_text.strip():
                    segments.append({
                        "timestamp": self.format_timestamp(current_start_ms),
                        "timestamp_ms": current_start_ms,
                        "speaker": current_speaker,
                        "text": current_text.strip()
                    })
                    plain_text += current_text.strip()
                
                current_text = ""
                current_start_ms = offset_ms
            
            # 更新当前说话人
            if not current_speaker:
                current_speaker = speaker
                current_start_ms = offset_ms
            
            current_speaker = speaker
            current_text += text + " "
        
        # 保存最后一个片段
        if current_text.strip():
            segments.append({
                "timestamp": self.format_timestamp(current_start_ms),
                "timestamp_ms": current_start_ms,
                "speaker": current_speaker,
                "text": current_text.strip()
            })
            plain_text += current_text.strip()
        
        return segments, plain_text
    
    def merge_results(self, results, time_offsets):
        """
        合并多个识别结果
        
        参数:
            results: 识别结果列表
            time_offsets: 每段的时间偏移（毫秒）
        
        返回:
            合并后的segments和plain_text
        """
        merged_segments = []
        merged_text = ""
        
        for i, (result, offset) in enumerate(zip(results, time_offsets)):
            if not result:
                continue
            
            segments, text = self.parse_result(result, offset)
            merged_segments.extend(segments)
            merged_text += text
        
        return merged_segments, merged_text
    
    def test_single_file(self, audio_path, ground_truth_path=None):
        """测试单个音频文件"""
        if not os.path.exists(audio_path):
            return {
                "audio_file": audio_path,
                "success": False,
                "error": "音频文件不存在"
            }
        
        # 记录开始时间
        start_time = time.time()
        
        # 获取音频时长
        audio_duration_sec = self.get_audio_duration(audio_path)
        
        # 检查文件大小和时长
        file_size = os.path.getsize(audio_path)
        file_size_mb = file_size / 1024 / 1024
        
        print(f"[*] 音频文件: {audio_path}")
        print(f"[*] 文件大小: {file_size_mb:.2f}MB")
        print(f"[*] 音频时长: {audio_duration_sec:.1f}秒")
        
        # 检查是否需要切分
        need_split = file_size > self.max_file_size or audio_duration_sec > self.max_duration
        
        if not need_split:
            # 直接转写
            print(f"[*] 文件符合要求，直接转写")
            
            result = self.transcribe_file(audio_path)
            
            if not result:
                return {
                    "audio_file": audio_path,
                    "success": False,
                    "error": "转写失败"
                }
            
            # 解析结果
            segments, plain_text = self.parse_result(result)
            
            # 记录结束时间
            end_time = time.time()
            processing_time = end_time - start_time
            
            print(f"[*] 处理耗时: {processing_time:.1f}秒")
            print(f"[*] 音频时长: {audio_duration_sec:.1f}秒")
            print(f"[*] RTF: {processing_time / audio_duration_sec:.3f}")
            print(f"[*] 识别片段数: {len(segments)}")
            
            return {
                "audio_file": audio_path,
                "success": True,
                "segments": segments,
                "plain_text": plain_text,
                "processing_time": processing_time,
                "audio_duration": audio_duration_sec
            }
        
        else:
            # 需要切分
            print(f"[!] 文件超过限制，需要切分处理")
            print(f"[!] 限制：文件 < 300MB，时长 < 2小时")
            
            # 切分音频
            chunk_data = self.split_audio_file(audio_path, chunk_duration=110)  # 110秒，留余量
            
            if not chunk_data:
                return {
                    "audio_file": audio_path,
                    "success": False,
                    "error": "音频切分失败"
                }
            
            # 处理每个片段
            results = []
            time_offsets = []
            
            for i, (chunk_file, start_offset_ms) in enumerate(chunk_data, 1):
                print(f"\n[*] 处理片段 {i}/{len(chunk_data)}: {chunk_file}")
                
                result = self.transcribe_file(chunk_file)
                
                if result:
                    results.append(result)
                    time_offsets.append(start_offset_ms)
                    print(f"[+] 片段 {i} 转写完成")
                else:
                    print(f"[-] 片段 {i} 转写失败")
                    results.append(None)
                    time_offsets.append(start_offset_ms)
            
            # 清理临时文件
            print(f"\n[*] 清理临时文件...")
            for chunk_file, _ in chunk_data:
                try:
                    os.remove(chunk_file)
                except:
                    pass
            
            try:
                os.rmdir("temp_audio_chunks")
            except:
                pass
            
            # 合并结果
            print(f"[*] 合并识别结果...")
            merged_segments, merged_text = self.merge_results(results, time_offsets)
            
            # 记录结束时间
            end_time = time.time()
            processing_time = end_time - start_time
            
            print(f"[+] 合并完成，总片段数: {len(merged_segments)}")
            print(f"[*] 处理耗时: {processing_time:.1f}秒")
            print(f"[*] RTF: {processing_time / audio_duration_sec:.3f}")
            
            return {
                "audio_file": audio_path,
                "success": True,
                "segments": merged_segments,
                "plain_text": merged_text,
                "processing_time": processing_time,
                "audio_duration": audio_duration_sec
            }

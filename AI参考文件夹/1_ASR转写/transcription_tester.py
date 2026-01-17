"""
音频转写测试框架
用于测试和对比不同的语音转写API
"""

import os
import json
import re
import time
from datetime import datetime

# 导入pyannote.metrics用于专业的DER计算
try:
    from pyannote.core import Annotation, Segment
    from pyannote.metrics.diarization import DiarizationErrorRate
    PYANNOTE_AVAILABLE = True
except ImportError:
    PYANNOTE_AVAILABLE = False
    print("[!] 警告: pyannote.metrics未安装，DER计算将使用简化算法")


class TranscriptionTester:
    """转写测试器基类"""
    
    def __init__(self, name="Unknown API"):
        self.name = name
        self.results = []
        self.timing_info = {}  # 记录时间信息
    
    def format_timestamp(self, ms):
        """将毫秒转换为 HH:MM:SS 格式"""
        seconds = ms // 1000
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    
    def timestamp_to_ms(self, timestamp_str):
        """将 HH:MM:SS 格式转换为毫秒"""
        parts = timestamp_str.split(':')
        if len(parts) == 3:
            hours, minutes, seconds = map(int, parts)
            return (hours * 3600 + minutes * 60 + seconds) * 1000
        return 0
    
    def parse_ground_truth(self, file_path):
        """
        解析真值文本文件，提取时间戳、说话人和文本内容
        格式示例：00:00:01 蓝为一\n对，然后你你帮我看一下异常。
        """
        segments = []
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            if not line:
                i += 1
                continue
            
            # 尝试匹配时间戳和说话人格式：HH:MM:SS 说话人名
            match = re.match(r'^(\d{2}:\d{2}:\d{2})\s+(.+)$', line)
            if match:
                timestamp = match.group(1)
                speaker = match.group(2)
                
                # 读取下一行作为文本内容
                i += 1
                if i < len(lines):
                    text = lines[i].strip()
                    segments.append({
                        "timestamp": timestamp,
                        "timestamp_ms": self.timestamp_to_ms(timestamp),
                        "speaker": speaker,
                        "text": text
                    })
            i += 1
        
        return segments
    
    def calculate_cer(self, reference, hypothesis):
        """
        计算字错误率 (CER - Character Error Rate)
        CER = (S + D + I) / N
        其中 S=替换, D=删除, I=插入, N=参考文本长度
        """
        # 简单预处理：去标点、去空格、转小写
        def normalize(text):
            text = re.sub(r'[^\w\u4e00-\u9fa5]', '', text)  # 仅保留中英文数字
            return text.lower()
        
        ref = normalize(reference)
        hyp = normalize(hypothesis)
        
        if not ref:
            return 0.0 if not hyp else 1.0, 0, 0
        
        # 编辑距离算法 (Levenshtein)
        n = len(ref)
        m = len(hyp)
        dp = [[0] * (m + 1) for _ in range(n + 1)]
        
        for i in range(n + 1):
            dp[i][0] = i
        for j in range(m + 1):
            dp[0][j] = j
        
        for i in range(1, n + 1):
            for j in range(1, m + 1):
                if ref[i - 1] == hyp[j - 1]:
                    dp[i][j] = dp[i - 1][j - 1]
                else:
                    dp[i][j] = min(
                        dp[i - 1][j],      # 删除
                        dp[i][j - 1],      # 插入
                        dp[i - 1][j - 1]   # 替换
                    ) + 1
        
        distance = dp[n][m]
        cer = distance / len(ref)
        return cer, distance, len(ref)
    
    def estimate_segment_duration(self, text):
        """
        根据文本长度估算说话时长（秒）
        假设平均语速：中文约4字/秒，英文约2.5词/秒
        """
        if not text:
            return 2.0  # 默认2秒
        
        # 统计中文字符数
        chinese_chars = len(re.findall(r'[\u4e00-\u9fa5]', text))
        # 统计英文单词数
        english_words = len(re.findall(r'[a-zA-Z]+', text))
        
        # 计算时长
        duration = chinese_chars / 4.0 + english_words / 2.5
        
        # 最小1秒，最大30秒
        return max(1.0, min(30.0, duration))
    
    def calculate_der(self, ground_truth_segments, ai_segments):
        """
        计算说话人区分错误率 (DER - Diarization Error Rate)
        
        使用pyannote.metrics专业库进行计算（如果可用）
        
        返回:
            der: 总体DER
            confusion: 说话人混淆率
            missed: 漏检率
            false_alarm: 虚检率
            details: 详细信息
        """
        if not ground_truth_segments or not ai_segments:
            return None, None, None, None, {}
        
        if not PYANNOTE_AVAILABLE:
            # 如果pyannote不可用，返回None
            return None, None, None, None, {"error": "pyannote.metrics未安装"}
        
        try:
            # 检查AI片段是否有有效的时间戳
            ai_times = [seg.get("timestamp_ms", 0) if "timestamp_ms" in seg else self.timestamp_to_ms(seg.get("timestamp", "00:00:00")) for seg in ai_segments[:10]]
            if len(set(ai_times)) == 1 and ai_times[0] == 0:
                # 所有时间戳都是0，说明时间戳信息缺失
                return None, None, None, None, {"error": "时间戳信息缺失（所有片段时间戳为00:00:00）"}
            
            # 第一步：检查是否需要说话人映射
            # 如果AI的说话人标签都是"Speaker X"格式，则需要映射
            ai_speakers = set(seg.get("speaker", "") for seg in ai_segments)
            
            # 检查是否所有AI说话人都是"Speaker X"格式
            all_speaker_format = all(
                speaker.startswith("Speaker ") and speaker.split()[-1].isdigit()
                for speaker in ai_speakers if speaker
            )
            
            # 如果都是Speaker格式，需要映射；否则直接匹配
            need_mapping = all_speaker_format
            
            speaker_mapping = {}
            
            if need_mapping:
                # 建立说话人映射（AI Speaker -> GT Speaker）
                speaker_votes = {}
                
                for ai_seg in ai_segments:
                    ai_speaker = ai_seg.get("speaker", "Unknown")
                    ai_time = ai_seg.get("timestamp_ms") if "timestamp_ms" in ai_seg else self.timestamp_to_ms(ai_seg.get("timestamp", "00:00:00"))
                    
                    # 找到时间上最接近的GT片段
                    min_diff = float('inf')
                    closest_gt_speaker = None
                    
                    for gt_seg in ground_truth_segments:
                        gt_time = gt_seg.get("timestamp_ms", 0)
                        diff = abs(ai_time - gt_time)
                        if diff < min_diff:
                            min_diff = diff
                            closest_gt_speaker = gt_seg.get("speaker", "")
                    
                    # 只统计时间差在10秒内的匹配
                    if min_diff < 10000 and closest_gt_speaker:
                        if ai_speaker not in speaker_votes:
                            speaker_votes[ai_speaker] = {}
                        speaker_votes[ai_speaker][closest_gt_speaker] = speaker_votes[ai_speaker].get(closest_gt_speaker, 0) + 1
                
                # 确定最终映射（每个AI说话人对应出现最多的GT说话人）
                for ai_speaker, votes in speaker_votes.items():
                    if votes:
                        speaker_mapping[ai_speaker] = max(votes.items(), key=lambda x: x[1])[0]
            
            # 第二步：创建pyannote Annotation对象
            reference = Annotation()
            hypothesis = Annotation()
            
            # 将真值片段转换为pyannote格式
            for i, gt_seg in enumerate(ground_truth_segments):
                start_sec = gt_seg.get("timestamp_ms", 0) / 1000.0
                
                # 使用下一个片段的开始时间作为结束时间
                if i + 1 < len(ground_truth_segments):
                    end_sec = ground_truth_segments[i + 1].get("timestamp_ms", 0) / 1000.0
                else:
                    # 最后一个片段，根据文本长度估算
                    text = gt_seg.get("text", "")
                    duration = self.estimate_segment_duration(text)
                    end_sec = start_sec + duration
                
                # 确保end > start
                if end_sec <= start_sec:
                    end_sec = start_sec + 2.0
                
                speaker = gt_seg.get("speaker", "Unknown")
                reference[Segment(start_sec, end_sec)] = speaker
            
            # 将AI片段转换为pyannote格式（使用映射后的说话人标签）
            for i, ai_seg in enumerate(ai_segments):
                start_sec = ai_seg.get("timestamp_ms") if "timestamp_ms" in ai_seg else self.timestamp_to_ms(ai_seg.get("timestamp", "00:00:00"))
                start_sec = start_sec / 1000.0
                
                # 使用下一个片段的开始时间作为结束时间
                if i + 1 < len(ai_segments):
                    next_time = ai_segments[i + 1].get("timestamp_ms") if "timestamp_ms" in ai_segments[i + 1] else self.timestamp_to_ms(ai_segments[i + 1].get("timestamp", "00:00:00"))
                    end_sec = next_time / 1000.0
                else:
                    # 最后一个片段，根据文本长度估算
                    text = ai_seg.get("text", "")
                    duration = self.estimate_segment_duration(text)
                    end_sec = start_sec + duration
                
                # 确保end > start
                if end_sec <= start_sec:
                    end_sec = start_sec + 2.0
                
                # 使用映射后的说话人标签（如果需要映射）
                ai_speaker = ai_seg.get("speaker", "Unknown")
                if need_mapping and ai_speaker in speaker_mapping:
                    mapped_speaker = speaker_mapping[ai_speaker]
                else:
                    mapped_speaker = ai_speaker
                hypothesis[Segment(start_sec, end_sec)] = mapped_speaker
            
            # 第三步：使用pyannote计算DER
            metric = DiarizationErrorRate()
            der_components = metric.compute_components(reference, hypothesis)
            
            # 提取各个组件
            confusion = der_components.get('confusion', 0.0)
            false_alarm = der_components.get('false alarm', 0.0)
            missed = der_components.get('missed detection', 0.0)
            total = der_components.get('total', 1.0)
            
            # 计算总DER
            der = (confusion + false_alarm + missed) / total if total > 0 else 0.0
            
            # 归一化各个组件（转换为比率）
            confusion_rate = confusion / total if total > 0 else 0.0
            false_alarm_rate = false_alarm / total if total > 0 else 0.0
            missed_rate = missed / total if total > 0 else 0.0
            
            details = {
                "method": "pyannote.metrics" + (" (with speaker mapping)" if need_mapping else " (direct match)"),
                "speaker_mapping": speaker_mapping if need_mapping else "不需要映射（说话人标签已匹配）",
                "confusion_duration": confusion,
                "false_alarm_duration": false_alarm,
                "missed_duration": missed,
                "total_duration": total,
                "total_ai_segments": len(ai_segments),
                "total_gt_segments": len(ground_truth_segments)
            }
            
            return der, confusion_rate, missed_rate, false_alarm_rate, details
            
        except Exception as e:
            print(f"[!] DER计算出错: {e}")
            import traceback
            traceback.print_exc()
            return None, None, None, None, {"error": str(e)}
    
    def calculate_timestamp_offset(self, ground_truth_segments, ai_segments):
        """
        计算时间戳偏移 (Time Offset) - 改进版
        
        使用智能匹配+切分检测算法：
        1. 通过文本相似度找到AI片段对应的真值片段
        2. 过滤超短文本的真值（避免"对"、"嗯"等误匹配）
        3. 检测过度切分：如果多个AI片段匹配到同一个真值，只计算第一个的偏移
        4. 检测子串切分：如果AI文本是真值的子串（后半句），标记为切分，不计入统计
        5. 过滤掉因AI切分导致的虚假偏移
        
        返回平均毫秒误差和偏移列表
        """
        if not ground_truth_segments or not ai_segments:
            return None, []
        
        import difflib
        
        def normalize_text(text):
            """标准化文本用于比较"""
            import re
            text = re.sub(r'[^\w\u4e00-\u9fa5]', '', text)
            return text.lower()
        
        # 为每个真值片段分配唯一ID
        for idx, gt_seg in enumerate(ground_truth_segments):
            gt_seg['_temp_id'] = idx
        
        # 记录每个真值片段被匹配的情况
        gt_match_info = {}
        
        # 第一遍：为每个AI片段找到最佳匹配的真值片段
        ai_matches = []
        
        for ai_idx, ai_seg in enumerate(ai_segments):
            ai_time = ai_seg["timestamp_ms"]
            ai_text = ai_seg.get("text", "")
            ai_norm = normalize_text(ai_text)
            
            if not ai_norm or len(ai_norm) < 2:  # 过滤超短AI文本
                continue
            
            # 找时间接近的候选（±15秒）
            time_candidates = []
            for gt_seg in ground_truth_segments:
                gt_time = gt_seg["timestamp_ms"]
                gt_text = gt_seg.get("text", "")
                gt_norm = normalize_text(gt_text)
                
                # 过滤超短真值文本（<5个字符），避免"对"、"嗯"等误匹配
                if not gt_norm or len(gt_norm) < 5:
                    continue
                
                time_diff = abs(ai_time - gt_time)
                if time_diff < 15000:
                    time_candidates.append((gt_seg, time_diff))
            
            # 如果没有时间接近的候选，扩大到全部真值（仍然过滤超短文本）
            if not time_candidates:
                for gt_seg in ground_truth_segments:
                    gt_text = gt_seg.get("text", "")
                    gt_norm = normalize_text(gt_text)
                    
                    if not gt_norm or len(gt_norm) < 5:
                        continue
                    
                    time_diff = abs(ai_time - gt_seg["timestamp_ms"])
                    time_candidates.append((gt_seg, time_diff))
            
            if not time_candidates:
                continue
            
            # 在候选中找文本最相似的
            best_match = None
            best_score = 0
            best_time_diff = float('inf')
            is_substring = False
            
            for gt_seg, time_diff in time_candidates:
                gt_text = gt_seg.get("text", "")
                gt_norm = normalize_text(gt_text)
                
                # 计算文本相似度
                similarity = difflib.SequenceMatcher(None, ai_norm, gt_norm).ratio()
                
                # 检查包含关系
                current_is_substring = False
                if ai_norm in gt_norm:
                    # AI文本是真值的子串
                    similarity = max(similarity, 0.85)
                    current_is_substring = True
                elif gt_norm in ai_norm:
                    similarity = max(similarity, 0.75)
                
                # 长度惩罚：如果长度差异太大，降低评分
                len_ratio = min(len(ai_norm), len(gt_norm)) / max(len(ai_norm), len(gt_norm))
                if len_ratio < 0.3:  # 长度差异超过3倍
                    similarity *= 0.8
                
                # 综合评分：时间权重0.3，文本相似度权重0.7
                time_score = 1.0 - min(time_diff / 15000.0, 1.0)
                combined_score = 0.3 * time_score + 0.7 * similarity
                
                if combined_score > best_score:
                    best_score = combined_score
                    best_match = gt_seg
                    best_time_diff = time_diff
                    is_substring = current_is_substring
            
            # 只保留相似度足够高且时间差合理的匹配
            if best_match and best_score > 0.40 and best_time_diff < 30000:  # 提高阈值到0.40
                ai_matches.append((ai_idx, best_match, best_score, best_time_diff, is_substring))
        
        # 第二遍：检测切分，只保留首次匹配
        offsets = []
        
        for ai_idx, gt_seg, similarity, time_diff, is_substring in ai_matches:
            gt_id = gt_seg['_temp_id']
            
            if gt_id not in gt_match_info:
                # 首次匹配
                if is_substring:
                    # 如果是子串，检查是否是句首
                    # 如果AI时间戳与真值时间戳接近（<2秒），认为是句首
                    if time_diff < 2000:
                        # 句首，计入统计
                        gt_match_info[gt_id] = True
                        offsets.append(time_diff)
                    else:
                        # 后半句（子串且时间差大），标记为已匹配但不计入统计
                        gt_match_info[gt_id] = True
                        # 不计入offsets
                else:
                    # 不是子串，正常计入统计
                    gt_match_info[gt_id] = True
                    offsets.append(time_diff)
            # 重复匹配（切分）：不计入统计
        
        # 清理临时ID
        for gt_seg in ground_truth_segments:
            if '_temp_id' in gt_seg:
                del gt_seg['_temp_id']
        
        if offsets:
            avg_offset = sum(offsets) / len(offsets)
            return avg_offset, offsets
        
        return None, []
    
    def save_transcript(self, segments, output_file):
        """保存转写结果到文件"""
        with open(output_file, "w", encoding="utf-8") as f:
            for seg in segments:
                # 支持两种格式：timestamp字段 或 start字段
                if 'timestamp' in seg:
                    timestamp = seg.get("timestamp", "00:00:00")
                elif 'start' in seg:
                    # 从start字段计算时间戳（秒）
                    start_sec = seg.get('start', 0)
                    hours = int(start_sec // 3600)
                    minutes = int((start_sec % 3600) // 60)
                    seconds = int(start_sec % 60)
                    timestamp = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
                else:
                    timestamp = "00:00:00"
                
                speaker = seg.get("speaker", "未知说话人")
                text = seg.get("text", "")
                f.write(f"{timestamp} {speaker}\n")
                f.write(f"{text}\n\n")
        print(f"[+] 转写结果已保存到: {output_file}")
    
    def test_single_file(self, audio_path, ground_truth_path=None):
        """
        测试单个音频文件
        子类需要实现具体的转写逻辑
        
        返回格式：
        {
            "audio_file": str,
            "success": bool,
            "segments": list,  # [{"timestamp": str, "speaker": str, "text": str}, ...]
            "plain_text": str,
            "processing_time": float,  # 处理耗时（秒）
            "audio_duration": float,   # 音频时长（秒）
            "error": str (可选)
        }
        """
        raise NotImplementedError("子类必须实现 test_single_file 方法")
    
    def evaluate_result(self, result, ground_truth_path):
        """评估转写结果"""
        if not result.get("success", False):
            return {
                "has_ground_truth": False,
                "error": result.get("error", "转写失败")
            }
        
        evaluation = {
            "ai_segments_count": len(result.get("segments", [])),
            "has_ground_truth": False
        }
        
        # 计算RTF（实时因子）
        if result.get("processing_time") and result.get("audio_duration"):
            rtf = result["processing_time"] / result["audio_duration"]
            evaluation["rtf"] = rtf
            evaluation["processing_time"] = result["processing_time"]
            evaluation["audio_duration"] = result["audio_duration"]
        
        if ground_truth_path and os.path.exists(ground_truth_path):
            # 解析真值文本
            ground_truth_segments = self.parse_ground_truth(ground_truth_path)
            ground_truth_text = "".join([seg["text"] for seg in ground_truth_segments])
            
            # 1. 计算CER（字错误率）
            cer_score, err_num, total_len = self.calculate_cer(
                ground_truth_text, 
                result.get("plain_text", "")
            )
            
            # 2. 计算DER（说话人区分错误率）
            der, confusion, missed, false_alarm, der_details = self.calculate_der(
                ground_truth_segments,
                result.get("segments", [])
            )
            
            # 3. 计算时间戳偏移
            avg_offset, offsets = self.calculate_timestamp_offset(
                ground_truth_segments,
                result.get("segments", [])
            )
            
            # 评级
            if cer_score < 0.15:
                rating = "优秀 (Excellent)"
            elif cer_score < 0.30:
                rating = "良好 (Good) - 需人工辅助"
            else:
                rating = "不及格 (Fail) - 需检查音频质量或方言"
            
            evaluation.update({
                "has_ground_truth": True,
                "ground_truth_file": ground_truth_path,
                "ground_truth_segments_count": len(ground_truth_segments),
                "ground_truth_chars": total_len,
                "edit_distance": err_num,
                "cer": cer_score,
                "accuracy": 1 - cer_score,
                "rating": rating
            })
            
            # 添加DER相关指标
            if der is not None:
                evaluation.update({
                    "der": der,
                    "speaker_confusion": confusion,
                    "missed_speech": missed,
                    "false_alarm": false_alarm,
                    "speaker_mapping": der_details.get("speaker_mapping", {})
                })
            
            # 添加时间戳偏移
            if avg_offset is not None:
                evaluation.update({
                    "avg_timestamp_offset_ms": avg_offset,
                    "timestamp_offset_samples": len(offsets)
                })
        
        return evaluation
    
    def load_transcript(self, transcript_file):
        """
        从文件加载转写结果
        
        参数:
            transcript_file: 转写结果文件路径
        
        返回:
            segments: 片段列表
            plain_text: 纯文本
        """
        if not os.path.exists(transcript_file):
            return None, None
        
        segments = []
        plain_text = ""
        
        with open(transcript_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            if not line:
                i += 1
                continue
            
            # 匹配时间戳和说话人格式：HH:MM:SS 说话人名
            match = re.match(r'^(\d{2}:\d{2}:\d{2})\s+(.+)$', line)
            if match:
                timestamp = match.group(1)
                speaker = match.group(2)
                
                # 读取下一行作为文本内容
                i += 1
                if i < len(lines):
                    text = lines[i].strip()
                    segments.append({
                        "timestamp": timestamp,
                        "timestamp_ms": self.timestamp_to_ms(timestamp),  # 添加毫秒字段
                        "speaker": speaker,
                        "text": text
                    })
                    plain_text += text
            i += 1
        
        return segments, plain_text
    
    def batch_test(self, audio_files, audio_ext=".ogg", transcript_ext="-transcript.txt", 
                   mode="transcribe"):
        """
        批量测试多个音频文件
        
        参数:
            audio_files: 音频文件基础名列表（不含扩展名）
            audio_ext: 音频文件扩展名
            transcript_ext: 真值文件扩展名后缀
            mode: 运行模式
                - "transcribe": 转写模式（调用API）
                - "evaluate": 评估模式（只计算CER，不调用API）
                - "both": 两者都做（默认行为）
        """
        self.results = []
        
        for audio_base in audio_files:
            audio_path = audio_base + audio_ext
            ground_truth_path = audio_base + transcript_ext
            output_path = audio_base + f"-{self.name.replace(' ', '_')}-transcript.txt"
            
            print("\n" + "=" * 80)
            print(f"[{self.name}] 处理: {audio_base}")
            print("=" * 80)
            
            try:
                result = None
                
                # 转写模式或两者都做
                if mode in ["transcribe", "both"]:
                    print(f"[*] 模式: 转写")
                    
                    # 转写
                    result = self.test_single_file(audio_path, ground_truth_path)
                    
                    if result.get("success", False):
                        # 保存结果
                        self.save_transcript(result.get("segments", []), output_path)
                        
                        # 如果只是转写模式（不评估），也要保存基本结果
                        if mode == "transcribe":
                            basic_result = {
                                "audio_file": audio_path,
                                "output_file": output_path,
                                "success": True,
                                "segments_count": len(result.get("segments", [])),
                                "processing_time": result.get("processing_time", 0),
                                "audio_duration": result.get("audio_duration", 0),
                            }
                            # 如果有真值文件，也计算评估指标
                            if os.path.exists(ground_truth_path):
                                evaluation = self.evaluate_result(result, ground_truth_path)
                                basic_result.update(evaluation)
                            
                            self.results.append(basic_result)
                            continue
                    else:
                        final_result = {
                            "audio_file": audio_path,
                            "success": False,
                            "error": result.get("error", "未知错误")
                        }
                        self.results.append(final_result)
                        continue
                
                # 评估模式或两者都做
                if mode in ["evaluate", "both"]:
                    print(f"[*] 模式: 评估")
                    
                    # 如果是纯评估模式，从文件加载转写结果
                    if mode == "evaluate":
                        if not os.path.exists(output_path):
                            print(f"[-] 转写结果文件不存在: {output_path}")
                            print(f"[!] 请先运行转写模式生成结果文件")
                            self.results.append({
                                "audio_file": audio_path,
                                "success": False,
                                "error": "转写结果文件不存在"
                            })
                            continue
                        
                        segments, plain_text = self.load_transcript(output_path)
                        if segments is None:
                            print(f"[-] 无法加载转写结果: {output_path}")
                            self.results.append({
                                "audio_file": audio_path,
                                "success": False,
                                "error": "无法加载转写结果"
                            })
                            continue
                        
                        result = {
                            "audio_file": audio_path,
                            "success": True,
                            "segments": segments,
                            "plain_text": plain_text
                        }
                    
                    # 评估
                    evaluation = self.evaluate_result(result, ground_truth_path)
                    
                    # 合并结果
                    final_result = {
                        "audio_file": audio_path,
                        "output_file": output_path,
                        "success": True,
                        **evaluation
                    }
                    
                    # 打印评估结果
                    if evaluation.get("has_ground_truth", False):
                        print("\n================ 评估报告 ================")
                        print(f"真值片段数: {evaluation['ground_truth_segments_count']}")
                        print(f"AI转写片段数: {evaluation['ai_segments_count']}")
                        print(f"真值字数: {evaluation['ground_truth_chars']}")
                        print(f"编辑距离: {evaluation['edit_distance']}")
                        print(f"CER (字错误率): {evaluation['cer']:.2%}")
                        print(f"准确率: {evaluation['accuracy']:.2%}")
                        print(f"评价: {evaluation['rating']}")
                        
                        # DER相关指标
                        if 'der' in evaluation:
                            print(f"\n--- 说话人区分指标 (DER) ---")
                            print(f"DER (说话人区分错误率): {evaluation['der']:.2%}")
                            print(f"  - 说话人混淆率: {evaluation['speaker_confusion']:.2%}")
                            print(f"  - 漏检率: {evaluation['missed_speech']:.2%}")
                            print(f"  - 虚检率: {evaluation['false_alarm']:.2%}")
                            if evaluation.get('speaker_mapping'):
                                print(f"说话人映射: {evaluation['speaker_mapping']}")
                        
                        # RTF指标
                        if 'rtf' in evaluation:
                            print(f"\n--- 性能指标 (RTF) ---")
                            print(f"RTF (实时因子): {evaluation['rtf']:.3f}")
                            print(f"处理耗时: {evaluation['processing_time']:.1f}秒")
                            print(f"音频时长: {evaluation['audio_duration']:.1f}秒")
                            if evaluation['rtf'] < 0.2:
                                print(f"性能评价: 优秀 (RTF < 0.2)")
                            elif evaluation['rtf'] < 0.5:
                                print(f"性能评价: 良好 (RTF < 0.5)")
                            elif evaluation['rtf'] < 1.0:
                                print(f"性能评价: 一般 (RTF < 1.0)")
                            else:
                                print(f"性能评价: 较慢 (RTF ≥ 1.0)")
                        
                        # 时间戳偏移
                        if 'avg_timestamp_offset_ms' in evaluation:
                            print(f"\n--- 时间戳精度 ---")
                            print(f"平均时间戳偏移: {evaluation['avg_timestamp_offset_ms']:.0f}毫秒")
                            print(f"样本数: {evaluation['timestamp_offset_samples']}")
                            if evaluation['avg_timestamp_offset_ms'] < 500:
                                print(f"精度评价: 优秀 (< 500ms)")
                            elif evaluation['avg_timestamp_offset_ms'] < 1000:
                                print(f"精度评价: 良好 (< 1s)")
                            elif evaluation['avg_timestamp_offset_ms'] < 2000:
                                print(f"精度评价: 一般 (< 2s)")
                            else:
                                print(f"精度评价: 较差 (≥ 2s)")
                        
                        print("==========================================")
                    
                    self.results.append(final_result)
                
            except Exception as e:
                print(f"\n[-] 处理 {audio_base} 时出错: {e}")
                import traceback
                traceback.print_exc()
                self.results.append({
                    "audio_file": audio_path,
                    "success": False,
                    "error": str(e)
                })
        
        return self.results
    
    def generate_report(self, output_file="转写测试报告.txt", config=None):
        """生成测试报告"""
        with open(output_file, "w", encoding="utf-8") as f:
            f.write("=" * 80 + "\n")
            f.write(f"{self.name} - 转写测试报告\n")
            f.write("=" * 80 + "\n")
            f.write(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            # 配置信息
            if config:
                f.write("## 测试配置\n\n")
                for key, value in config.items():
                    f.write(f"{key}: {value}\n")
                f.write("\n")
            
            # 测试结果汇总
            f.write("## 测试结果汇总\n\n")
            f.write(f"总文件数: {len(self.results)}\n")
            f.write(f"成功处理: {sum(1 for r in self.results if r.get('success', False))}\n")
            f.write(f"失败处理: {sum(1 for r in self.results if not r.get('success', False))}\n\n")
            
            # 详细结果
            f.write("## 详细结果\n\n")
            
            for i, result in enumerate(self.results, 1):
                f.write(f"### {i}. {result['audio_file']}\n\n")
                
                if not result.get('success', False):
                    f.write(f"❌ 处理失败\n")
                    f.write(f"错误信息: {result.get('error', '未知错误')}\n\n")
                    continue
                
                f.write(f"✅ 处理成功\n\n")
                f.write(f"- 输出文件: {result.get('output_file', 'N/A')}\n")
                f.write(f"- AI转写片段数: {result.get('ai_segments_count', 0)}\n")
                
                if result.get('has_ground_truth', False):
                    f.write(f"- 真值文件: {result['ground_truth_file']}\n")
                    f.write(f"- 真值片段数: {result['ground_truth_segments_count']}\n")
                    f.write(f"- 真值字数: {result['ground_truth_chars']}\n")
                    f.write(f"- 编辑距离: {result['edit_distance']}\n")
                    f.write(f"- CER (字错误率): {result['cer']:.2%}\n")
                    f.write(f"- 准确率: {result['accuracy']:.2%}\n")
                    f.write(f"- 评价: {result['rating']}\n")
                    
                    # DER指标
                    if 'der' in result:
                        f.write(f"\n说话人区分指标:\n")
                        f.write(f"- DER (说话人区分错误率): {result['der']:.2%}\n")
                        f.write(f"  - 说话人混淆率: {result['speaker_confusion']:.2%}\n")
                        f.write(f"  - 漏检率: {result['missed_speech']:.2%}\n")
                        f.write(f"  - 虚检率: {result['false_alarm']:.2%}\n")
                        if result.get('speaker_mapping'):
                            f.write(f"- 说话人映射: {result['speaker_mapping']}\n")
                    
                    # RTF指标
                    if 'rtf' in result:
                        f.write(f"\n性能指标:\n")
                        f.write(f"- RTF (实时因子): {result['rtf']:.3f}\n")
                        f.write(f"- 处理耗时: {result['processing_time']:.1f}秒\n")
                        f.write(f"- 音频时长: {result['audio_duration']:.1f}秒\n")
                    
                    # 时间戳偏移
                    if 'avg_timestamp_offset_ms' in result:
                        f.write(f"\n时间戳精度:\n")
                        f.write(f"- 平均偏移: {result['avg_timestamp_offset_ms']:.0f}毫秒\n")
                        f.write(f"- 样本数: {result['timestamp_offset_samples']}\n")
                else:
                    f.write(f"- 真值文件: 未找到\n")
                
                f.write("\n")
            
            # 统计分析
            f.write("## 统计分析\n\n")
            
            results_with_cer = [r for r in self.results if r.get('has_ground_truth', False)]
            
            if results_with_cer:
                # CER统计
                avg_cer = sum(r['cer'] for r in results_with_cer) / len(results_with_cer)
                avg_accuracy = 1 - avg_cer
                min_cer = min(r['cer'] for r in results_with_cer)
                max_cer = max(r['cer'] for r in results_with_cer)
                
                f.write(f"### 文本识别准确率\n\n")
                f.write(f"有真值文件的测试数: {len(results_with_cer)}\n")
                f.write(f"平均准确率: {avg_accuracy:.2%}\n")
                f.write(f"平均 CER: {avg_cer:.2%}\n")
                f.write(f"最低 CER: {min_cer:.2%} (最高准确率: {(1-min_cer):.2%})\n")
                f.write(f"最高 CER: {max_cer:.2%} (最低准确率: {(1-max_cer):.2%})\n\n")
                
                # 评级分布
                excellent = sum(1 for r in results_with_cer if r['cer'] < 0.15)
                good = sum(1 for r in results_with_cer if 0.15 <= r['cer'] < 0.30)
                fail = sum(1 for r in results_with_cer if r['cer'] >= 0.30)
                
                f.write("评级分布:\n")
                f.write(f"- 优秀 (准确率 > 85%): {excellent} 个\n")
                f.write(f"- 良好 (70% < 准确率 ≤ 85%): {good} 个\n")
                f.write(f"- 不及格 (准确率 ≤ 70%): {fail} 个\n\n")
                
                # DER统计
                results_with_der = [r for r in results_with_cer if 'der' in r]
                if results_with_der:
                    avg_der = sum(r['der'] for r in results_with_der) / len(results_with_der)
                    avg_confusion = sum(r['speaker_confusion'] for r in results_with_der) / len(results_with_der)
                    avg_missed = sum(r['missed_speech'] for r in results_with_der) / len(results_with_der)
                    avg_false_alarm = sum(r['false_alarm'] for r in results_with_der) / len(results_with_der)
                    
                    f.write(f"### 说话人区分准确率 (DER)\n\n")
                    f.write(f"平均 DER: {avg_der:.2%}\n")
                    f.write(f"平均说话人混淆率: {avg_confusion:.2%}\n")
                    f.write(f"平均漏检率: {avg_missed:.2%}\n")
                    f.write(f"平均虚检率: {avg_false_alarm:.2%}\n\n")
                    
                    # DER评级
                    der_excellent = sum(1 for r in results_with_der if r['der'] < 0.10)
                    der_good = sum(1 for r in results_with_der if 0.10 <= r['der'] < 0.25)
                    der_fail = sum(1 for r in results_with_der if r['der'] >= 0.25)
                    
                    f.write("DER评级分布:\n")
                    f.write(f"- 优秀 (DER < 10%): {der_excellent} 个\n")
                    f.write(f"- 良好 (10% ≤ DER < 25%): {der_good} 个\n")
                    f.write(f"- 不及格 (DER ≥ 25%): {der_fail} 个\n\n")
                
                # RTF统计
                results_with_rtf = [r for r in results_with_cer if 'rtf' in r]
                if results_with_rtf:
                    avg_rtf = sum(r['rtf'] for r in results_with_rtf) / len(results_with_rtf)
                    min_rtf = min(r['rtf'] for r in results_with_rtf)
                    max_rtf = max(r['rtf'] for r in results_with_rtf)
                    
                    f.write(f"### 处理性能 (RTF)\n\n")
                    f.write(f"平均 RTF: {avg_rtf:.3f}\n")
                    f.write(f"最低 RTF: {min_rtf:.3f} (最快)\n")
                    f.write(f"最高 RTF: {max_rtf:.3f} (最慢)\n\n")
                    
                    # RTF评级
                    rtf_excellent = sum(1 for r in results_with_rtf if r['rtf'] < 0.2)
                    rtf_good = sum(1 for r in results_with_rtf if 0.2 <= r['rtf'] < 0.5)
                    rtf_normal = sum(1 for r in results_with_rtf if 0.5 <= r['rtf'] < 1.0)
                    rtf_slow = sum(1 for r in results_with_rtf if r['rtf'] >= 1.0)
                    
                    f.write("RTF评级分布:\n")
                    f.write(f"- 优秀 (RTF < 0.2): {rtf_excellent} 个\n")
                    f.write(f"- 良好 (0.2 ≤ RTF < 0.5): {rtf_good} 个\n")
                    f.write(f"- 一般 (0.5 ≤ RTF < 1.0): {rtf_normal} 个\n")
                    f.write(f"- 较慢 (RTF ≥ 1.0): {rtf_slow} 个\n\n")
                
                # 时间戳偏移统计
                results_with_offset = [r for r in results_with_cer if 'avg_timestamp_offset_ms' in r]
                if results_with_offset:
                    avg_offset = sum(r['avg_timestamp_offset_ms'] for r in results_with_offset) / len(results_with_offset)
                    min_offset = min(r['avg_timestamp_offset_ms'] for r in results_with_offset)
                    max_offset = max(r['avg_timestamp_offset_ms'] for r in results_with_offset)
                    
                    f.write(f"### 时间戳精度\n\n")
                    f.write(f"平均时间戳偏移: {avg_offset:.0f}毫秒\n")
                    f.write(f"最小偏移: {min_offset:.0f}毫秒 (最精确)\n")
                    f.write(f"最大偏移: {max_offset:.0f}毫秒 (最不精确)\n\n")
                    
                    # 时间戳精度评级
                    offset_excellent = sum(1 for r in results_with_offset if r['avg_timestamp_offset_ms'] < 500)
                    offset_good = sum(1 for r in results_with_offset if 500 <= r['avg_timestamp_offset_ms'] < 1000)
                    offset_normal = sum(1 for r in results_with_offset if 1000 <= r['avg_timestamp_offset_ms'] < 2000)
                    offset_poor = sum(1 for r in results_with_offset if r['avg_timestamp_offset_ms'] >= 2000)
                    
                    f.write("时间戳精度评级分布:\n")
                    f.write(f"- 优秀 (< 500ms): {offset_excellent} 个\n")
                    f.write(f"- 良好 (500-1000ms): {offset_good} 个\n")
                    f.write(f"- 一般 (1-2s): {offset_normal} 个\n")
                    f.write(f"- 较差 (≥ 2s): {offset_poor} 个\n\n")
            else:
                f.write("没有可用于统计的真值文件。\n\n")
            
            # 结论
            f.write("## 结论\n\n")
            if results_with_cer:
                if avg_cer < 0.15:
                    f.write(f"整体表现优秀，平均准确率 {avg_accuracy:.2%}，转写质量很高。\n")
                elif avg_cer < 0.30:
                    f.write(f"整体表现良好，平均准确率 {avg_accuracy:.2%}，大部分内容识别准确，建议人工辅助校对。\n")
                else:
                    f.write(f"整体表现不理想，平均准确率 {avg_accuracy:.2%}，建议检查音频质量、方言设置或优化参数配置。\n")
            else:
                f.write("所有文件均已成功转写，但缺少真值文件进行准确率评估。\n")
            
            f.write("\n" + "=" * 80 + "\n")
            f.write("报告生成完成\n")
            f.write("=" * 80 + "\n")
        
        print(f"\n[+] 测试报告已保存到: {output_file}")
        return output_file

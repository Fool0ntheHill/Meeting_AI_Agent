#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ASR 聚类修正模块
利用声纹识别的高置信度结果，反向修正火山引擎 ASR 中的说话人聚类错误

核心功能：
1. 全局身份选举与合并（解决"同人异名"问题）
2. 异常点清洗（解决"鸠占鹊巢"问题）

依赖：
- audio_processor.py: AudioProcessor 类
- iflytek_voiceprint.py: iFLYTEKVoiceprint 类
"""

import copy
import os
import time
import random
from collections import Counter
from typing import Dict, List, Tuple, Optional


class ASRClusterCorrector:
    """ASR 说话人聚类修正器"""
    
    # 阈值配置
    CONFIRM_THRESHOLD = 0.50    # 确认身份的基准线（全局映射，降低以适应短样本）
    CORRECTION_THRESHOLD = 0.90  # 用于推翻 ASR 结果的超高置信度红线（异常点修正，必须很高）
    MIN_DURATION = 2000          # 毫秒，忽略短于 2 秒的短语
    
    # 采样配置
    SAMPLE_COUNT = 5             # 每个 Speaker 抽取的样本数（增加到5次提高准确性）
    MIN_SAMPLE_DURATION = 4000   # 采样片段最小时长（毫秒，提高到4秒以获得更好质量）
    
    def __init__(
        self,
        asr_data: Dict,
        voiceprint_client,
        audio_processor,
        tos_client,
        bucket_name: str,
        object_key: str,
        verbose: bool = True
    ):
        """
        初始化 ASR 聚类修正器
        
        Args:
            asr_data: 原始 ASR 结果 JSON
            voiceprint_client: 讯飞声纹识别客户端
            audio_processor: AudioProcessor 实例
            tos_client: TOS 客户端
            bucket_name: TOS 存储桶名称
            object_key: 音频文件 Key
            verbose: 是否打印详细日志
        """
        self.asr_data = copy.deepcopy(asr_data)  # 深拷贝，防止污染原数据
        self.voiceprint_client = voiceprint_client
        self.audio_processor = audio_processor
        self.tos_client = tos_client
        self.bucket_name = bucket_name
        self.object_key = object_key
        self.verbose = verbose
        
        # 提取 utterances
        self.utterances = self.asr_data.get('result', {}).get('utterances', [])
        
        if not self.utterances:
            raise ValueError("ASR 数据中没有 utterances")
        
        # 统计信息
        self.correction_count = 0
        self.merge_count = 0
        
        # 预下载音频文件（避免异常点检测时重复下载）
        self._log(f"预下载音频文件...")
        self.audio_file = self.audio_processor._download_audio_from_tos(
            tos_client=self.tos_client,
            bucket_name=self.bucket_name,
            object_key=self.object_key
        )
        
        if not self.audio_file:
            raise ValueError("音频文件下载失败")
        
        self._log(f"初始化完成，共 {len(self.utterances)} 个片段")
    
    def _log(self, message: str):
        """打印日志"""
        if self.verbose:
            print(f"[ASRClusterCorrector] {message}")
    
    def _group_by_speaker(self) -> Dict[str, List[Dict]]:
        """
        按说话人分组
        
        Returns:
            字典 {"Speaker 1": [utt1, utt2, ...], ...}
        """
        groups = {}
        
        for utt in self.utterances:
            speaker = utt.get('speaker', 'Unknown')
            
            if speaker not in groups:
                groups[speaker] = []
            
            groups[speaker].append(utt)
        
        return groups
    
    def _sample_utterances(
        self,
        utterances: List[Dict],
        count: int = SAMPLE_COUNT
    ) -> List[Dict]:
        """
        从片段列表中采样
        
        优先选择时长较长的片段
        
        Args:
            utterances: 片段列表
            count: 采样数量
        
        Returns:
            采样的片段列表
        """
        # 过滤：只保留时长 >= MIN_SAMPLE_DURATION 的片段
        long_utterances = [
            utt for utt in utterances
            if (utt.get('end_time', 0) - utt.get('start_time', 0)) >= self.MIN_SAMPLE_DURATION
        ]
        
        if not long_utterances:
            # 如果没有足够长的片段，使用所有片段
            long_utterances = utterances
        
        # 随机采样
        sample_count = min(count, len(long_utterances))
        sampled = random.sample(long_utterances, sample_count)
        
        return sampled
    
    def _identify_utterance(self, utterance: Dict, verbose_error: bool = False) -> Optional[Tuple[str, float, str]]:
        """
        识别单个片段的说话人
        
        Args:
            utterance: 片段数据
            verbose_error: 是否打印详细错误信息
        
        Returns:
            (识别的姓名, 相似度得分, 状态) 或 (None, None, 失败原因)
            状态: "success", "no_audio", "low_confidence", "exception"
        """
        try:
            # 提取音频片段
            start_time = utterance.get('start_time', 0)
            end_time = utterance.get('end_time', 0)
            duration = end_time - start_time
            
            # 构造 utterances 格式
            temp_utterances = [{
                'additions': {'speaker': '0'},
                'start_time': start_time,
                'end_time': end_time,
                'text': utterance.get('text', '')
            }]
            
            # 直接提取音频片段（使用预下载的文件）
            audio_bytes = self.audio_processor._extract_and_convert_segment(
                audio_file=self.audio_file,
                start_ms=start_time,
                end_ms=end_time
            )
            
            if not audio_bytes or len(audio_bytes) < 1000:  # 音频太短
                if verbose_error:
                    self._log(f"    ✗ 音频数据太短 (大小: {len(audio_bytes) if audio_bytes else 0} bytes)")
                return None, None, "no_audio"
            
            # 识别（启用分差挽救机制，适合短音频片段）
            # 注意：这里总是返回最高分的候选人，即使分数很低
            result = self.voiceprint_client.identify_speaker(
                audio_bytes=audio_bytes,
                top_k=2,  # 至少取 Top-2 用于分差计算
                threshold=0.0,  # 设为 0，总是返回最高分候选人
                use_gap_rescue=True,  # 启用分差挽救
                min_accept_score=0.0,  # 设为 0，不拒绝任何结果
                gap_threshold=0.2  # 分差阈值
            )
            
            if result:
                return (result['feature_info'], result['score'], "success")
            else:
                # 理论上不应该到这里，因为阈值设为 0
                if verbose_error:
                    self._log(f"    ✗ 声纹识别无结果 (时长: {duration}ms)")
                return None, None, "low_confidence"
            
        except Exception as e:
            if verbose_error:
                self._log(f"    ✗ 识别异常: {e}")
            return None, None, "exception"
    
    def global_identity_election(self) -> Dict[str, str]:
        """
        方法 A: 全局身份选举与合并
        
        解决"同人异名"问题（Over-segmentation）
        
        Returns:
            映射表 {"Speaker 1": "张三", "Speaker 2": "张三", ...}
        """
        self._log("\n" + "=" * 80)
        self._log("方法 A: 全局身份选举与合并")
        self._log("=" * 80)
        
        # 1. 按说话人分组
        groups = self._group_by_speaker()
        
        self._log(f"\n检测到 {len(groups)} 个 Speaker ID:")
        for speaker_id in groups.keys():
            self._log(f"  - {speaker_id}: {len(groups[speaker_id])} 个片段")
        
        # 2. 对每个 Speaker ID 进行投票（基于投票一致性）
        speaker_votes = {}  # {speaker_id: Counter({name: count})}
        speaker_scores = {}  # {speaker_id: {name: [scores]}}
        
        MAX_RETRY = 5  # 最多重试5次（增加重试次数）
        VOTE_CONSISTENCY_THRESHOLD = 0.7  # 投票一致性阈值（70%，降低以适应困难样本）
        
        for speaker_id, utterances in groups.items():
            self._log(f"\n[投票] 处理 {speaker_id}...")
            
            retry_count = 0
            votes = []
            scores_dict = {}
            failure_stats = {"no_audio": 0, "low_confidence": 0, "exception": 0}
            
            while retry_count <= MAX_RETRY:
                if retry_count > 0:
                    self._log(f"  [重试 {retry_count}/{MAX_RETRY}] 投票一致性不足，重新采样...")
                
                # 采样
                sampled = self._sample_utterances(utterances, self.SAMPLE_COUNT)
                self._log(f"  采样 {len(sampled)} 个片段进行识别")
                
                # 重置统计
                votes = []
                scores_dict = {}
                failure_stats = {"no_audio": 0, "low_confidence": 0, "exception": 0}
                success_count = 0
                
                for i, utt in enumerate(sampled, 1):
                    self._log(f"  [{i}/{len(sampled)}] 识别中...")
                    
                    # 第一次尝试时显示详细错误，重试时不显示
                    verbose_error = (retry_count == 0)
                    name, score, status = self._identify_utterance(utt, verbose_error=verbose_error)
                    
                    if status == "success":
                        votes.append(name)
                        
                        if name not in scores_dict:
                            scores_dict[name] = []
                        scores_dict[name].append(score)
                        
                        self._log(f"    ✓ 识别为: {name} (相似度: {score:.3f})")
                        success_count += 1
                    else:
                        failure_stats[status] += 1
                        if not verbose_error:
                            self._log(f"    ✗ 识别失败 ({status})")
                    
                    # 延迟
                    time.sleep(0.5)
                
                # 计算投票一致性
                vote_counter = Counter(votes)
                if vote_counter:
                    most_common_name, most_common_count = vote_counter.most_common(1)[0]
                    vote_consistency = most_common_count / len(votes) if votes else 0.0
                else:
                    vote_consistency = 0.0
                
                self._log(f"  投票结果: {dict(vote_counter)}")
                self._log(f"  有效投票数: {len(votes)}/{len(sampled)}")
                if vote_counter:
                    self._log(f"  投票一致性: {vote_consistency*100:.1f}% ({most_common_name}: {most_common_count}/{len(votes)})")
                
                if failure_stats["no_audio"] > 0 or failure_stats["low_confidence"] > 0 or failure_stats["exception"] > 0:
                    self._log(f"  失败统计: 音频提取失败={failure_stats['no_audio']}, 低置信度={failure_stats['low_confidence']}, 异常={failure_stats['exception']}")
                
                # 判断是否需要重试：投票一致性 >= 70% 才接受
                if vote_consistency >= VOTE_CONSISTENCY_THRESHOLD:
                    # 一致性足够，接受结果
                    break
                elif retry_count < MAX_RETRY:
                    # 一致性不足，继续重试
                    retry_count += 1
                    time.sleep(1)  # 重试前等待1秒
                else:
                    # 已达到最大重试次数，接受当前结果
                    break
            
            # 统计投票
            vote_counter = Counter(votes)
            speaker_votes[speaker_id] = vote_counter
            speaker_scores[speaker_id] = scores_dict
        
        # 3. 建立映射表（基于投票一致性，而非绝对分数）
        self._log(f"\n[映射] 建立全局身份映射表...")
        
        id_map = {}
        name_to_speakers = {}  # {name: [speaker_ids]}
        
        for speaker_id, vote_counter in speaker_votes.items():
            if not vote_counter:
                # 没有投票结果，保持原样
                id_map[speaker_id] = speaker_id
                self._log(f"  {speaker_id} → {speaker_id} (无有效投票)")
                continue
            
            # 获取最高票
            most_common_name, count = vote_counter.most_common(1)[0]
            total_votes = sum(vote_counter.values())
            
            # 计算平均置信度
            scores = speaker_scores[speaker_id].get(most_common_name, [])
            avg_score = sum(scores) / len(scores) if scores else 0.0
            
            # 新策略：优先看投票一致性，其次看置信度
            # 1. 如果投票一致性高（>=60%），且平均分>=0.40，接受
            # 2. 如果平均分很高（>=0.60），即使一致性不高也接受
            vote_ratio = count / total_votes if total_votes > 0 else 0.0
            
            accept = False
            reason = ""
            
            if vote_ratio >= 0.6 and avg_score >= 0.40:
                accept = True
                reason = f"投票一致性高 ({vote_ratio*100:.0f}%, {count}/{total_votes})"
            elif avg_score >= self.CONFIRM_THRESHOLD:
                accept = True
                reason = f"置信度高 ({avg_score:.3f})"
            
            if accept:
                id_map[speaker_id] = most_common_name
                
                if most_common_name not in name_to_speakers:
                    name_to_speakers[most_common_name] = []
                name_to_speakers[most_common_name].append(speaker_id)
                
                self._log(f"  {speaker_id} → {most_common_name} (置信度: {avg_score:.3f}, {reason})")
            else:
                # 不满足条件，保持原样
                id_map[speaker_id] = speaker_id
                self._log(f"  {speaker_id} → {speaker_id} (置信度: {avg_score:.3f}, 一致性: {vote_ratio*100:.0f}%, 不满足条件)")
        
        # 4. 检测合并
        self._log(f"\n[合并] 检测需要合并的 Speaker ID...")
        
        for name, speaker_ids in name_to_speakers.items():
            if len(speaker_ids) > 1:
                self._log(f"  [合并策略] 检测到 {', '.join(speaker_ids)} 均为 {name}，已合并")
                self.merge_count += len(speaker_ids) - 1
        
        self._log(f"\n✓ 全局映射表建立完成")
        self._log(f"  映射关系: {id_map}")
        
        return id_map
    
    def outlier_detection_and_fixing(self, id_map: Dict[str, str]):
        """
        方法 B: 异常点清洗
        
        解决"鸠占鹊巢"问题（Label Swap）
        
        Args:
            id_map: 全局身份映射表
        """
        self._log("\n" + "=" * 80)
        self._log("方法 B: 异常点清洗")
        self._log("=" * 80)
        
        self._log(f"\n开始逐句检查，共 {len(self.utterances)} 个片段")
        
        # 统计需要检查的片段数
        check_count = 0
        
        for i, utt in enumerate(self.utterances):
            # 1. 获取当前片段信息
            original_speaker = utt.get('speaker', 'Unknown')
            start_time = utt.get('start_time', 0)
            end_time = utt.get('end_time', 0)
            duration = end_time - start_time
            
            # 2. 检查是否需要抽检
            if duration < self.MIN_DURATION:
                # 片段太短，跳过
                continue
            
            # 3. 获取主流身份
            mainstream_identity = id_map.get(original_speaker, original_speaker)
            
            # 4. 抽检（可选：只检查部分片段以节省时间）
            # 这里简化为检查所有符合条件的片段
            # 实际应用中可以只检查对话交替频繁的区域
            
            check_count += 1
            
            if check_count % 10 == 0:
                self._log(f"  已检查 {check_count} 个片段...")
            
            # 5. 执行识别
            name, score, status = self._identify_utterance(utt, verbose_error=False)
            
            if status != "success":
                continue
            
            detected_name = name
            
            # 6. 纠错仲裁
            if detected_name != mainstream_identity and score >= self.CORRECTION_THRESHOLD:
                # 执行修正
                self._log(f"\n  [清洗策略] 修正时间戳 {self._format_time(start_time)}-{self._format_time(end_time)}:")
                self._log(f"    ASR 标为: {original_speaker} ({mainstream_identity})")
                self._log(f"    声纹确认为: {detected_name} (置信度: {score:.3f})")
                
                # 修改 speaker 字段
                utt['speaker'] = detected_name
                utt['corrected'] = True
                utt['original_speaker_before_correction'] = original_speaker
                utt['correction_score'] = score
                
                self.correction_count += 1
            
            # 延迟
            time.sleep(0.3)
        
        self._log(f"\n✓ 异常点清洗完成")
        self._log(f"  检查片段数: {check_count}")
        self._log(f"  修正片段数: {self.correction_count}")
    
    def _format_time(self, milliseconds: int) -> str:
        """格式化时间戳"""
        seconds = milliseconds // 1000
        minutes = seconds // 60
        secs = seconds % 60
        return f"{minutes:02d}:{secs:02d}"
    
    def correct_transcript(self) -> Dict:
        """
        执行完整的修正流程
        
        Returns:
            修正后的 ASR 数据
        """
        self._log("\n" + "=" * 80)
        self._log("ASR 聚类修正流程")
        self._log("=" * 80)
        
        try:
            # 步骤 1: 全局身份选举与合并
            id_map = self.global_identity_election()
            
            # 应用全局映射
            self._log(f"\n[应用] 应用全局身份映射...")
            for utt in self.utterances:
                original_speaker = utt.get('speaker', 'Unknown')
                if original_speaker in id_map:
                    new_speaker = id_map[original_speaker]
                    if new_speaker != original_speaker:
                        utt['speaker'] = new_speaker
                        if 'original_speaker' not in utt:
                            utt['original_speaker'] = original_speaker
            
            # 步骤 2: 异常点清洗
            self.outlier_detection_and_fixing(id_map)
            
            # 统计
            self._log("\n" + "=" * 80)
            self._log("修正统计")
            self._log("=" * 80)
            self._log(f"  合并的 Speaker ID 数: {self.merge_count}")
            self._log(f"  修正的片段数: {self.correction_count}")
            self._log(f"  总片段数: {len(self.utterances)}")
            
            if self.correction_count > 0:
                correction_rate = (self.correction_count / len(self.utterances)) * 100
                self._log(f"  修正率: {correction_rate:.2f}%")
            
            self._log("\n✓ ASR 聚类修正完成")
            
            # 清理临时音频文件
            try:
                if self.audio_file and os.path.exists(self.audio_file):
                    os.unlink(self.audio_file)
                    self._log(f"清理临时文件: {self.audio_file}")
            except:
                pass
            
            return self.asr_data
            
        except Exception as e:
            self._log(f"\n✗ 修正流程异常: {e}")
            import traceback
            traceback.print_exc()
            raise


# ==================== 使用示例 ====================

def main():
    """使用示例"""
    import json
    import tos
    from audio_processor import AudioProcessor
    from iflytek_voiceprint import iFLYTEKVoiceprint
    
    # 配置
    TOS_CONFIG = {
        "access_key": "YOUR_ACCESS_KEY",
        "secret_key": "YOUR_SECRET_KEY",
        "endpoint": "https://tos-cn-beijing.volces.com",
        "region": "cn-beijing",
        "bucket": "meeting-agent-test"
    }
    
    IFLYTEK_CONFIG = {
        "app_id": "YOUR_APP_ID",
        "api_key": "YOUR_API_KEY",
        "api_secret": "YOUR_API_SECRET",
        "group_id": "YOUR_GROUP_ID"
    }
    
    # 读取 ASR 结果
    with open("asr_result.json", 'r', encoding='utf-8') as f:
        asr_data = json.load(f)
    
    # 初始化客户端
    tos_client = tos.TosClientV2(
        TOS_CONFIG['access_key'],
        TOS_CONFIG['secret_key'],
        TOS_CONFIG['endpoint'],
        TOS_CONFIG['region']
    )
    
    voiceprint_client = iFLYTEKVoiceprint(
        app_id=IFLYTEK_CONFIG['app_id'],
        api_key=IFLYTEK_CONFIG['api_key'],
        api_secret=IFLYTEK_CONFIG['api_secret'],
        group_id=IFLYTEK_CONFIG['group_id'],
        verbose=False
    )
    
    audio_processor = AudioProcessor(verbose=False)
    
    # 创建修正器
    corrector = ASRClusterCorrector(
        asr_data=asr_data,
        voiceprint_client=voiceprint_client,
        audio_processor=audio_processor,
        tos_client=tos_client,
        bucket_name=TOS_CONFIG['bucket'],
        object_key="meeting.ogg",
        verbose=True
    )
    
    # 执行修正
    corrected_data = corrector.correct_transcript()
    
    # 保存结果
    with open("asr_result_corrected.json", 'w', encoding='utf-8') as f:
        json.dump(corrected_data, f, ensure_ascii=False, indent=2)
    
    print("\n修正完成，结果已保存到 asr_result_corrected.json")


if __name__ == "__main__":
    main()

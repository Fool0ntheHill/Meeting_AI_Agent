#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
会议录音实名识别主流程
从火山 ASR 结果 + 声纹识别 → 实名会议纪要

功能流程：
1. 读取火山 ASR 识别结果（JSON）
2. 从 TOS 下载音频并提取说话人样本
3. 调用讯飞声纹识别 API 识别说话人
4. 将识别结果回填到 ASR 数据中
5. 输出实名会议纪要

依赖：
- audio_processor.py: AudioProcessor 类
- iflytek_voiceprint.py: iFLYTEKVoiceprint 类
- tos: 火山引擎 TOS SDK
"""

import os
import json
import time
from typing import Dict, Optional

import tos
from audio_processor import AudioProcessor
from iflytek_voiceprint import iFLYTEKVoiceprint


# ==================== 配置区域 ====================

# 火山引擎 TOS 配置（从环境变量读取）
TOS_CONFIG = {
    "access_key": os.getenv("TOS_ACCESS_KEY", "AKLTNmY4N2Y1ZDU2OWY4NDI5ZWIwMDY2NjUyMzFlNzA1YzE"),
    "secret_key": os.getenv("TOS_SECRET_KEY", "TVdJeFlUTmtZbUZrWldFeE5HVmxORGxsTmpoaFpqRXdabVl5WkdRek9XRQ=="),
    "endpoint": os.getenv("TOS_ENDPOINT", "https://tos-cn-beijing.volces.com"),
    "region": os.getenv("TOS_REGION", "cn-beijing"),
    "bucket": os.getenv("TOS_BUCKET", "meeting-agent-test")
}

# 讯飞声纹识别配置（从环境变量读取）
IFLYTEK_CONFIG = {
    "app_id": os.getenv("XF_APP_ID", "55646860"),
    "api_key": os.getenv("XF_API_KEY", "77750e732ba4296d3a7d89e1deafbf22"),
    "api_secret": os.getenv("XF_API_SECRET", "YzdiYzhiNjkwNWNmZmY5YTlmNDlhMDJi"),
    "group_id": os.getenv("XF_GROUP_ID", "meeting_agent_test_group")
}

# 声纹识别参数
VOICEPRINT_THRESHOLD = 0.6  # 匹配阈值
VOICEPRINT_DELAY = 0.5      # 请求间隔（秒），防止 QPS 超限


# ==================== 核心函数 ====================

def load_asr_result(asr_json_path: str) -> Optional[Dict]:
    """
    加载火山 ASR 识别结果
    
    Args:
        asr_json_path: ASR 结果 JSON 文件路径
    
    Returns:
        ASR 结果字典，失败返回 None
    """
    try:
        print(f"\n[1] 加载 ASR 结果: {asr_json_path}")
        
        if not os.path.exists(asr_json_path):
            print(f"  ✗ 文件不存在: {asr_json_path}")
            return None
        
        with open(asr_json_path, 'r', encoding='utf-8') as f:
            asr_data = json.load(f)
        
        # 验证数据结构
        if 'result' not in asr_data or 'utterances' not in asr_data['result']:
            print(f"  ✗ 数据格式错误：缺少 result.utterances 字段")
            return None
        
        utterances = asr_data['result']['utterances']
        print(f"  ✓ 加载成功，共 {len(utterances)} 个语句片段")
        
        return asr_data
        
    except json.JSONDecodeError as e:
        print(f"  ✗ JSON 解析失败: {e}")
        return None
    except Exception as e:
        print(f"  ✗ 加载失败: {e}")
        return None


def initialize_clients():
    """
    初始化 TOS 和讯飞声纹识别客户端
    
    Returns:
        (tos_client, voiceprint_client) 元组，失败返回 (None, None)
    """
    try:
        print(f"\n[2] 初始化客户端...")
        
        # 初始化 TOS 客户端
        print(f"  [2.1] 初始化 TOS 客户端...")
        tos_client = tos.TosClientV2(
            TOS_CONFIG['access_key'],
            TOS_CONFIG['secret_key'],
            TOS_CONFIG['endpoint'],
            TOS_CONFIG['region']
        )
        print(f"    ✓ TOS 客户端初始化成功")
        print(f"      Endpoint: {TOS_CONFIG['endpoint']}")
        print(f"      Region: {TOS_CONFIG['region']}")
        print(f"      Bucket: {TOS_CONFIG['bucket']}")
        
        # 初始化讯飞声纹识别客户端
        print(f"  [2.2] 初始化讯飞声纹识别客户端...")
        voiceprint_client = iFLYTEKVoiceprint(
            app_id=IFLYTEK_CONFIG['app_id'],
            api_key=IFLYTEK_CONFIG['api_key'],
            api_secret=IFLYTEK_CONFIG['api_secret'],
            group_id=IFLYTEK_CONFIG['group_id'],
            verbose=False  # 关闭详细日志，避免刷屏
        )
        print(f"    ✓ 讯飞客户端初始化成功")
        print(f"      APP_ID: {IFLYTEK_CONFIG['app_id']}")
        print(f"      GROUP_ID: {IFLYTEK_CONFIG['group_id']}")
        
        return tos_client, voiceprint_client
        
    except Exception as e:
        print(f"  ✗ 客户端初始化失败: {e}")
        return None, None


def extract_voiceprint_samples(
    tos_client: tos.TosClientV2,
    object_key: str,
    utterances: list
) -> Optional[Dict[str, bytes]]:
    """
    从 TOS 提取说话人声纹样本
    
    Args:
        tos_client: TOS 客户端
        object_key: 音频文件在 TOS 中的 Key
        utterances: 火山 ASR 的 utterances 列表
    
    Returns:
        字典 {"Speaker 0": audio_bytes, ...}，失败返回 None
    """
    try:
        print(f"\n[3] 提取说话人声纹样本...")
        print(f"  音频文件: {object_key}")
        print(f"  语句片段: {len(utterances)}")
        
        # 初始化 AudioProcessor
        processor = AudioProcessor(verbose=False)
        
        # 提取样本
        print(f"  [3.1] 从 TOS 下载并提取样本...")
        samples = processor.process_segments(
            tos_client=tos_client,
            bucket_name=TOS_CONFIG['bucket'],
            object_key=object_key,
            utterances=utterances
        )
        
        if not samples:
            print(f"  ✗ 未提取到任何样本")
            return None
        
        print(f"  ✓ 提取成功，共 {len(samples)} 个说话人样本:")
        for speaker, audio_bytes in samples.items():
            size_kb = len(audio_bytes) / 1024
            print(f"    - {speaker}: {size_kb:.1f} KB")
        
        return samples
        
    except Exception as e:
        print(f"  ✗ 提取样本失败: {e}")
        import traceback
        traceback.print_exc()
        return None


def identify_speakers(
    voiceprint_client: iFLYTEKVoiceprint,
    samples: Dict[str, bytes]
) -> Dict[str, str]:
    """
    使用讯飞声纹识别 API 识别说话人
    
    Args:
        voiceprint_client: 讯飞声纹识别客户端
        samples: 说话人样本字典 {"Speaker 0": audio_bytes, ...}
    
    Returns:
        映射表 {"Speaker 0": "张三", "Speaker 1": "未知人员", ...}
    """
    print(f"\n[4] 识别说话人身份...")
    print(f"  阈值: {VOICEPRINT_THRESHOLD}")
    print(f"  请求间隔: {VOICEPRINT_DELAY} 秒")
    
    speaker_map = {}
    
    for i, (speaker, audio_bytes) in enumerate(samples.items(), 1):
        try:
            print(f"\n  [4.{i}] 识别 {speaker}...")
            
            # 调用讯飞 1:N 检索（启用分差挽救机制）
            result = voiceprint_client.identify_speaker(
                audio_bytes=audio_bytes,
                top_k=2,  # 至少取 Top-2 用于分差计算
                threshold=VOICEPRINT_THRESHOLD,
                use_gap_rescue=True,  # 启用分差挽救机制
                min_accept_score=0.35,  # 最低容忍分数
                gap_threshold=0.2  # 分差阈值
            )
            
            if result:
                # 识别成功
                real_name = result['feature_info']
                score = result['score']
                speaker_map[speaker] = real_name
                print(f"    ✓ 识别成功: {real_name} (相似度: {score:.3f})")
            else:
                # 未识别出
                speaker_map[speaker] = "未知人员"
                print(f"    ✗ 未识别出，标记为: 未知人员")
            
            # 延迟，防止 QPS 超限
            if i < len(samples):
                time.sleep(VOICEPRINT_DELAY)
                
        except Exception as e:
            # 识别失败，保持原名
            speaker_map[speaker] = speaker
            print(f"    ✗ 识别失败: {e}")
            print(f"    保持原名: {speaker}")
    
    # 打印映射表
    print(f"\n  识别结果汇总:")
    print(f"  " + "=" * 60)
    for speaker, real_name in speaker_map.items():
        print(f"    {speaker:15} → {real_name}")
    print(f"  " + "=" * 60)
    
    return speaker_map


def enrich_asr_data(asr_data: Dict, speaker_map: Dict[str, str]) -> Dict:
    """
    将识别结果回填到 ASR 数据中
    
    Args:
        asr_data: 原始 ASR 数据
        speaker_map: 说话人映射表
    
    Returns:
        更新后的 ASR 数据
    """
    print(f"\n[5] 回填识别结果到 ASR 数据...")
    
    utterances = asr_data['result']['utterances']
    updated_count = 0
    
    for utt in utterances:
        original_speaker = utt.get('speaker', 'Unknown')
        
        if original_speaker in speaker_map:
            # 替换为真实姓名
            utt['speaker'] = speaker_map[original_speaker]
            utt['original_speaker'] = original_speaker  # 保留原始标签
            updated_count += 1
    
    print(f"  ✓ 更新完成，共更新 {updated_count}/{len(utterances)} 条记录")
    
    return asr_data


def save_result(asr_data: Dict, output_path: str = "final_meeting_record.json"):
    """
    保存最终结果
    
    Args:
        asr_data: 更新后的 ASR 数据
        output_path: 输出文件路径
    """
    try:
        print(f"\n[6] 保存最终结果...")
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(asr_data, f, ensure_ascii=False, indent=2)
        
        print(f"  ✓ 保存成功: {output_path}")
        
        # 统计信息
        utterances = asr_data['result']['utterances']
        speakers = set(utt['speaker'] for utt in utterances)
        
        print(f"\n  统计信息:")
        print(f"    总语句数: {len(utterances)}")
        print(f"    说话人数: {len(speakers)}")
        print(f"    说话人列表: {', '.join(speakers)}")
        
    except Exception as e:
        print(f"  ✗ 保存失败: {e}")


# ==================== 主流程函数 ====================

def process_meeting(asr_json_path: str, object_key: str):
    """
    处理会议录音，生成实名会议纪要
    
    Args:
        asr_json_path: ASR 结果 JSON 文件路径
        object_key: 音频文件在 TOS 中的 Key
    """
    print("=" * 80)
    print("会议录音实名识别主流程")
    print("=" * 80)
    print(f"\n输入参数:")
    print(f"  ASR 结果: {asr_json_path}")
    print(f"  音频文件: {object_key}")
    
    try:
        # 步骤 A: 准备阶段
        # A1. 加载 ASR 结果
        asr_data = load_asr_result(asr_json_path)
        if not asr_data:
            print("\n✗ 加载 ASR 结果失败，流程终止")
            return
        
        # A2. 初始化客户端
        tos_client, voiceprint_client = initialize_clients()
        if not tos_client or not voiceprint_client:
            print("\n✗ 客户端初始化失败，流程终止")
            return
        
        # 步骤 B: 提取与识别
        # B1. 提取声纹样本
        utterances = asr_data['result']['utterances']
        samples = extract_voiceprint_samples(tos_client, object_key, utterances)
        
        if not samples:
            print("\n⚠️  未提取到声纹样本，跳过识别步骤")
            print("  保持原始 Speaker 标签，保证保底可用性")
            
            # 保底：直接保存原始数据
            save_result(asr_data, "final_meeting_record.json")
            print("\n✓ 处理完成（保底模式）")
            return
        
        # B2. 识别说话人
        try:
            speaker_map = identify_speakers(voiceprint_client, samples)
        except Exception as e:
            print(f"\n⚠️  声纹识别失败: {e}")
            print("  保持原始 Speaker 标签，保证保底可用性")
            
            # 保底：使用原始标签
            speaker_map = {speaker: speaker for speaker in samples.keys()}
        
        # 步骤 C: 结果回填
        enriched_data = enrich_asr_data(asr_data, speaker_map)
        
        # 步骤 D: 输出
        save_result(enriched_data, "final_meeting_record.json")
        
        print("\n" + "=" * 80)
        print("✓ 处理完成！")
        print("=" * 80)
        
    except Exception as e:
        print(f"\n✗ 流程异常: {e}")
        import traceback
        traceback.print_exc()
        
        print("\n⚠️  发生异常，尝试保底处理...")
        
        # 保底：如果有 ASR 数据，直接保存
        try:
            if 'asr_data' in locals() and asr_data:
                save_result(asr_data, "final_meeting_record.json")
                print("✓ 保底处理完成（保存原始 ASR 数据）")
        except:
            print("✗ 保底处理也失败了")


# ==================== 命令行入口 ====================

def main():
    """
    命令行入口
    """
    import sys
    
    if len(sys.argv) < 3:
        print("用法: python main_pipeline.py <asr_json_path> <object_key>")
        print("\n示例:")
        print("  python main_pipeline.py asr_result.json 20251229会议录音.ogg")
        print("\n环境变量配置:")
        print("  TOS_ACCESS_KEY, TOS_SECRET_KEY, TOS_ENDPOINT, TOS_REGION, TOS_BUCKET")
        print("  XF_APP_ID, XF_API_KEY, XF_API_SECRET, XF_GROUP_ID")
        sys.exit(1)
    
    asr_json_path = sys.argv[1]
    object_key = sys.argv[2]
    
    process_meeting(asr_json_path, object_key)


if __name__ == "__main__":
    main()

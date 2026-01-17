#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
火山引擎语音识别实现（V3 API - 大模型版本）
基于官方示例代码实现
"""

import os
import sys
import json
import time
import uuid
import requests
from .transcription_tester import TranscriptionTester


class VolcanoTranscriberV3(TranscriptionTester):
    """火山引擎语音识别类（V3 API）"""
    
    def __init__(self, appid, access_token, audio_files=None, 
                 reference_files=None, speaker_mapping=None):
        """
        初始化火山引擎识别器（V3 API）
        
        Args:
            appid: 应用ID
            access_token: 访问令牌
            audio_files: 音频文件列表（可选）
            reference_files: 参考文本文件列表（可选）
            speaker_mapping: 说话人映射字典（可选）
        """
        super().__init__(name="Volcano-V3")
        
        self.appid = appid
        self.access_token = access_token
        self.audio_files = audio_files or []
        self.reference_files = reference_files or []
        self.speaker_mapping = speaker_mapping or {}
        
        # V3 API端点
        self.submit_url = "https://openspeech-direct.zijieapi.com/api/v3/auc/bigmodel/submit"
        self.query_url = "https://openspeech-direct.zijieapi.com/api/v3/auc/bigmodel/query"
        
        # 资源ID
        self.resource_id = "volc.bigasr.auc"
        
        print(f"[*] 初始化火山引擎识别器（V3 API - 大模型版本）")
        print(f"[*] APP ID: {self.appid}")
        print(f"[*] Access Token: {self.access_token[:20]}...")
        
    def transcribe_from_url(self, audio_url, audio_format=None):
        """
        从URL转写音频
        
        Args:
            audio_url: 音频文件URL
            audio_format: 音频格式（可选）
            
        Returns:
            dict: 包含识别结果的字典
        """
        print(f"\n[*] 开始识别URL: {audio_url}")
        
        # 1. 提交任务
        task_id, x_tt_logid = self._submit_task(audio_url, audio_format)
        if not task_id:
            print("[-] 提交任务失败")
            return None
        
        print(f"[+] 任务创建成功，TaskId: {task_id}")
        
        # 2. 轮询查询结果
        start_time = time.time()
        max_wait_time = 6000  # 最多等待100分钟
        query_interval = 10  # 每10秒查询一次
        query_count = 0
        
        while True:
            query_count += 1
            time.sleep(query_interval)
            
            result = self._query_task(task_id, x_tt_logid)
            if not result:
                print(f"[-] 第{query_count}次查询失败")
                continue
            
            code = result.get('code', '')
            
            if code == '20000000':
                # 识别成功
                print(f"[+] 识别完成！")
                elapsed = time.time() - start_time
                print(f"[*] 处理耗时: {elapsed:.1f}秒")
                return self._parse_result(result.get('data', {}))
                
            elif code == '20000001' or code == '20000002':
                # 处理中或排队中
                status = "处理中" if code == '20000001' else "排队中"
                print(f"[*] 第{query_count}次查询，任务{status}... 等待{query_interval}秒后重试")
                
            else:
                # 错误
                message = result.get('message', 'unknown error')
                print(f"[-] 识别失败: [{code}] {message}")
                return None
            
            # 检查超时
            if time.time() - start_time > max_wait_time:
                print(f"[-] 等待超时（{max_wait_time}秒）")
                return None
    
    def _submit_task(self, audio_url, audio_format=None):
        """
        提交识别任务（V3 API）
        
        Args:
            audio_url: 音频URL
            audio_format: 音频格式
            
        Returns:
            tuple: (task_id, x_tt_logid)，失败返回(None, None)
        """
        # 生成任务ID
        task_id = str(uuid.uuid4())
        
        # 构建请求头（V3 API格式）
        headers = {
            "X-Api-App-Key": self.appid,
            "X-Api-Access-Key": self.access_token,
            "X-Api-Resource-Id": self.resource_id,
            "X-Api-Request-Id": task_id,
            "X-Api-Sequence": "-1"
        }
        
        # 构建请求体
        request_data = {
            "user": {
                "uid": "python_client_demo"
            },
            "audio": {
                "url": audio_url
            },
            "request": {
                "model_name": "bigmodel",  # 大模型
                "enable_channel_split": False,  # 单声道不需要
                "enable_ddc": True,  # 顺滑（语言顺滑）
                "enable_speaker_info": True,  # 说话人信息（说话人分离）
                "enable_punc": True,  # 标点
                "enable_itn": True,  # 数字归一化
                "language": "",  # 空=支持中英文、上海话、闽南语、四川话、陕西话、粤语
                "corpus": {
                    "correct_table_name": "dff94f69-aeef-47cb-b10b-1f72ed998a27",  # 热词表ID
                    "context": ""
                }
            }
        }
        
        # 如果指定了格式，添加到audio字段
        if audio_format:
            request_data["audio"]["format"] = audio_format
        
        try:
            response = requests.post(
                self.submit_url,
                data=json.dumps(request_data),
                headers=headers,
                timeout=30
            )
            
            # V3 API使用header返回状态
            status_code = response.headers.get('X-Api-Status-Code', '')
            
            if status_code == '20000000':
                message = response.headers.get('X-Api-Message', '')
                x_tt_logid = response.headers.get('X-Tt-Logid', '')
                print(f"[+] 提交成功: {message}")
                print(f"[*] X-Tt-Logid: {x_tt_logid}")
                return task_id, x_tt_logid
            else:
                print(f"[-] 提交任务失败")
                print(f"[*] Status Code: {status_code}")
                print(f"[*] Message: {response.headers.get('X-Api-Message', 'unknown')}")
                print(f"[*] Response Headers: {dict(response.headers)}")
                return None, None
                
        except Exception as e:
            print(f"[-] 提交任务异常: {e}")
            import traceback
            traceback.print_exc()
            return None, None
    
    def _query_task(self, task_id, x_tt_logid):
        """
        查询任务结果（V3 API）
        
        Args:
            task_id: 任务ID
            x_tt_logid: 日志ID
            
        Returns:
            dict: 查询结果，失败返回None
        """
        # 构建请求头
        headers = {
            "X-Api-App-Key": self.appid,
            "X-Api-Access-Key": self.access_token,
            "X-Api-Resource-Id": self.resource_id,
            "X-Api-Request-Id": task_id,
            "X-Tt-Logid": x_tt_logid  # 固定传递
        }
        
        try:
            response = requests.post(
                self.query_url,
                data=json.dumps({}),
                headers=headers,
                timeout=30
            )
            
            # V3 API使用header返回状态
            status_code = response.headers.get('X-Api-Status-Code', '')
            message = response.headers.get('X-Api-Message', '')
            
            # 返回结果
            result = {
                'code': status_code,
                'message': message,
                'data': response.json() if response.text else {}
            }
            
            return result
            
        except Exception as e:
            print(f"[-] 查询任务异常: {e}")
            return None
    
    def _parse_result(self, data):
        """
        解析识别结果
        
        Args:
            data: API返回的数据
            
        Returns:
            dict: 标准化的识别结果
        """
        # 调试：打印原始数据结构
        print(f"\n[DEBUG] 原始返回数据结构:")
        print(f"  - 顶层keys: {list(data.keys())}")
        
        # V3 API的结果在result字段下
        result = data.get('result', {})
        print(f"  - result keys: {list(result.keys())}")
        
        # 获取完整文本
        full_text = result.get('text', '')
        print(f"  - 文本长度: {len(full_text)}")
        
        # V3 API可能没有utterances，需要检查
        utterances = result.get('utterances', [])
        print(f"  - utterances数量: {len(utterances)}")
        
        # 如果没有utterances，尝试从text创建简单的segment
        segments = []
        
        if utterances:
            # 有分段信息
            # 调试：查看第一个utterance的结构
            if len(utterances) > 0:
                print(f"[DEBUG] 第一个utterance的keys: {list(utterances[0].keys())}")
            
            for utt in utterances:
                # 说话人信息在additions.speaker字段
                speaker_id = utt.get('additions', {}).get('speaker', '1')
                speaker_label = f"Speaker {speaker_id}"
                
                # 时间戳字段（毫秒）
                start_time = utt.get('start_time', 0) / 1000.0
                end_time = utt.get('end_time', 0) / 1000.0
                
                segment = {
                    'text': utt.get('text', ''),
                    'start': start_time,
                    'end': end_time,
                    'speaker': speaker_label
                }
                segments.append(segment)
        elif full_text:
            # 没有分段信息，创建单个segment
            print(f"[*] 没有分段信息，将完整文本作为单个segment")
            segment = {
                'text': full_text,
                'start': 0.0,
                'end': data.get('audio_info', {}).get('duration', 0) / 1000.0,
                'speaker': 'Speaker 1'
            }
            segments.append(segment)
        
        print(f"[DEBUG] 最终segments数量: {len(segments)}")
        
        return {
            'segments': segments,
            'full_text': full_text
        }


def main():
    """测试函数"""
    print("=" * 80)
    print("火山引擎语音识别测试（V3 API - 大模型版本）")
    print("=" * 80)
    
    # 配置信息
    appid = "6543693041"
    access_token = "SrfaymE6iu2XSOEAg_C-6vc5PynqTbkT"
    
    # 测试音频URL
    audio_url = "http://10.11.0.80:8000/20251229ONE产品和业务规则中心的设计讨论会议.ogg"
    
    # 创建识别器
    transcriber = VolcanoTranscriberV3(
        appid=appid,
        access_token=access_token,
        audio_files=[]
    )
    
    # 测试URL识别
    result = transcriber.transcribe_from_url(audio_url, audio_format='ogg')
    
    if result:
        print("\n--- 识别结果 ---")
        print(f"完整文本: {result.get('full_text', '')[:200]}...")
        print(f"\n分段数: {len(result['segments'])}")
        for i, seg in enumerate(result['segments'][:5], 1):
            print(f"{i}. [{seg['start']:.1f}s - {seg['end']:.1f}s] {seg['speaker']}: {seg['text']}")
    
    print("\n" + "=" * 80)
    print("测试完成")
    print("=" * 80)


if __name__ == "__main__":
    main()

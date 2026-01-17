#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
讯飞声纹识别 (iFLYTEK Voiceprint Recognition) API 客户端

功能：
1. 1:N 说话人检索 (identify_speaker)
2. 1:1 说话人验证 (verify_speaker)
3. 声纹特征管理 (创建、删除、更新)

依赖：
- requests: HTTP 请求库
"""

import base64
import hashlib
import hmac
import json
import time
from datetime import datetime
from typing import Optional, Dict, List, Tuple
from urllib.parse import urlencode

import requests


class iFLYTEKVoiceprint:
    """讯飞声纹识别客户端类"""
    
    # API 配置
    API_HOST = "api.xf-yun.com"
    API_PATH = "/v1/private/s1aa729d0"
    API_URL = f"https://{API_HOST}{API_PATH}"
    
    # 推荐阈值
    RECOMMENDED_THRESHOLD = 0.6  # 得分 >= 0.6 判定为匹配
    
    def __init__(
        self,
        app_id: str,
        api_key: str,
        api_secret: str,
        group_id: str,
        verbose: bool = True
    ):
        """
        初始化讯飞声纹识别客户端
        
        Args:
            app_id: 应用 ID
            api_key: API Key (32位字符串)
            api_secret: API Secret (32位字符串)
            group_id: 目标声纹库 ID
            verbose: 是否打印详细日志
        """
        self.app_id = app_id
        self.api_key = api_key
        self.api_secret = api_secret
        self.group_id = group_id
        self.verbose = verbose
    
    def _log(self, message: str):
        """打印日志（如果启用）"""
        if self.verbose:
            print(f"[iFLYTEK Voiceprint] {message}")
    
    def _get_rfc1123_date(self) -> str:
        """
        获取 RFC1123 格式的当前 UTC 时间
        
        Returns:
            格式化的时间字符串，例如: "Fri, 23 Apr 2021 02:35:47 GMT"
        """
        # 获取当前 UTC 时间
        now = datetime.utcnow()
        
        # RFC1123 格式: %a, %d %b %Y %H:%M:%S GMT
        # %a: 星期几缩写 (Mon, Tue, ...)
        # %d: 日期 (01-31)
        # %b: 月份缩写 (Jan, Feb, ...)
        # %Y: 年份 (2021)
        # %H:%M:%S: 时:分:秒
        date_str = now.strftime("%a, %d %b %Y %H:%M:%S GMT")
        
        return date_str
    
    def _get_auth_headers(self) -> Dict[str, str]:
        """
        生成鉴权 HTTP Headers
        
        严格遵循 HMAC-SHA256 鉴权规则：
        1. 生成 RFC1123 格式的 Date
        2. 构造 SignatureOrigin
        3. 使用 HMAC-SHA256 计算签名
        4. 构造 Authorization 字符串
        5. Base64 编码 Authorization
        
        Returns:
            包含鉴权信息的 Headers 字典
        """
        # 1. 生成 Date (RFC1123 格式)
        date = self._get_rfc1123_date()
        
        # 2. 构造 SignatureOrigin
        # 格式: host: {host}\ndate: {date}\n{request-line}
        # request-line 格式: POST {path} HTTP/1.1
        signature_origin = (
            f"host: {self.API_HOST}\n"
            f"date: {date}\n"
            f"POST {self.API_PATH} HTTP/1.1"
        )
        
        # 3. 计算 HMAC-SHA256 签名
        # 使用 api_secret 作为密钥
        signature_sha = hmac.new(
            self.api_secret.encode('utf-8'),
            signature_origin.encode('utf-8'),
            hashlib.sha256
        ).digest()
        
        # 4. Base64 编码签名
        signature = base64.b64encode(signature_sha).decode('utf-8')
        
        # 5. 构造 Authorization 原始串
        # 格式: api_key="{api_key}", algorithm="hmac-sha256", headers="host date request-line", signature="{signature}"
        authorization_origin = (
            f'api_key="{self.api_key}", '
            f'algorithm="hmac-sha256", '
            f'headers="host date request-line", '
            f'signature="{signature}"'
        )
        
        # 6. Base64 编码 Authorization
        authorization = base64.b64encode(
            authorization_origin.encode('utf-8')
        ).decode('utf-8')
        
        # 7. 构造最终 Headers
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Host": self.API_HOST,
            "Date": date,
            "Authorization": authorization
        }
        
        return headers
    
    def _send_request(self, request_body: Dict) -> Optional[Dict]:
        """
        发送 HTTP 请求到讯飞 API
        
        Args:
            request_body: 请求体 (JSON)
        
        Returns:
            响应 JSON，失败返回 None
        """
        try:
            # 生成鉴权信息
            date = self._get_rfc1123_date()
            
            # 构造 SignatureOrigin
            signature_origin = (
                f"host: {self.API_HOST}\n"
                f"date: {date}\n"
                f"POST {self.API_PATH} HTTP/1.1"
            )
            
            # 计算 HMAC-SHA256 签名
            signature_sha = hmac.new(
                self.api_secret.encode('utf-8'),
                signature_origin.encode('utf-8'),
                hashlib.sha256
            ).digest()
            
            # Base64 编码签名
            signature = base64.b64encode(signature_sha).decode('utf-8')
            
            # 构造 Authorization 原始串
            authorization_origin = (
                f'api_key="{self.api_key}", '
                f'algorithm="hmac-sha256", '
                f'headers="host date request-line", '
                f'signature="{signature}"'
            )
            
            # Base64 编码 Authorization
            authorization = base64.b64encode(
                authorization_origin.encode('utf-8')
            ).decode('utf-8')
            
            # 构造 URL（鉴权参数作为 URL 参数）
            from urllib.parse import urlencode
            url_params = {
                "authorization": authorization,
                "date": date,
                "host": self.API_HOST
            }
            
            full_url = f"{self.API_URL}?{urlencode(url_params)}"
            
            # 构造 Headers（不包含鉴权信息）
            headers = {
                "Content-Type": "application/json",
                "Accept": "application/json"
            }
            
            # 发送 POST 请求
            self._log(f"发送请求到: {self.API_URL}")
            
            response = requests.post(
                full_url,
                headers=headers,
                json=request_body,
                timeout=30
            )
            
            # 检查 HTTP 状态码
            if response.status_code != 200:
                # 尝试解析业务错误
                try:
                    result = response.json()
                    self._log(f"响应 JSON: {result}")
                    
                    code = result.get('header', {}).get('code')
                    message = result.get('header', {}).get('message', 'Unknown error')
                    
                    if code:
                        self._log(f"业务错误: code={code}, message={message}")
                    else:
                        self._log(f"HTTP 错误: {response.status_code}")
                        self._log(f"响应内容: {response.text}")
                except Exception as e:
                    self._log(f"解析响应失败: {e}")
                    self._log(f"HTTP 错误: {response.status_code}")
                    self._log(f"响应内容: {response.text}")
                
                return None
            
            # 解析 JSON
            result = response.json()
            self._log(f"响应 JSON: {result}")
            
            # 检查业务状态码
            code = result.get('header', {}).get('code')
            if code is not None and code != 0:
                message = result.get('header', {}).get('message', 'Unknown error')
                self._log(f"业务错误: code={code}, message={message}")
                return None
            
            return result
            
        except requests.exceptions.Timeout:
            self._log("请求超时")
            return None
        except requests.exceptions.RequestException as e:
            self._log(f"网络请求失败: {e}")
            return None
        except json.JSONDecodeError as e:
            self._log(f"JSON 解析失败: {e}")
            return None
        except Exception as e:
            self._log(f"未知错误: {e}")
            return None
    
    def _decode_payload_text(self, payload_text: str) -> Optional[Dict]:
        """
        解码 payload 中的 Base64 编码文本
        
        讯飞 API 返回的结果中，payload.*.text 字段是 Base64 编码的 JSON 字符串
        
        Args:
            payload_text: Base64 编码的文本
        
        Returns:
            解码后的 JSON 对象，失败返回 None
        """
        try:
            # Base64 解码
            decoded_bytes = base64.b64decode(payload_text)
            decoded_str = decoded_bytes.decode('utf-8')
            
            # JSON 解析
            result = json.loads(decoded_str)
            
            return result
            
        except Exception as e:
            self._log(f"解码 payload 失败: {e}")
            return None
    
    def identify_speaker(
        self,
        audio_bytes: bytes,
        top_k: int = 1,
        threshold: float = RECOMMENDED_THRESHOLD,
        use_gap_rescue: bool = True,
        min_accept_score: float = 0.35,
        gap_threshold: float = 0.2
    ) -> Optional[Dict]:
        """
        1:N 说话人检索 (验证"你是谁")
        
        在指定的声纹库中检索与音频最相似的说话人
        
        优化策略：
        1. 高置信度：score >= threshold，直接采纳
        2. 分差挽救：score < threshold 但显著高于第二名，也采纳（适用于短音频）
        3. 完全拒绝：score 太低或分差不明显，返回 None
        
        Args:
            audio_bytes: 音频数据 (WAV/PCM, 16kHz, 16bit, 单声道)
            top_k: 返回最相似的 K 个结果 (默认 1，最大 10)
            threshold: 高置信度阈值 (默认 0.6，推荐范围 0.6-1.0)
            use_gap_rescue: 是否启用分差挽救机制 (默认 True)
            min_accept_score: 最低容忍分数 (默认 0.35，防止完全是噪音)
            gap_threshold: 分差阈值 (默认 0.2，需显著高于第二名)
        
        Returns:
            识别结果字典，格式:
            {
                'feature_id': '特征ID',
                'feature_info': '特征信息(真实姓名)',
                'score': 0.85,
                'rescue_mode': 'gap'  # 可选，表示通过分差挽救
            }
            如果未识别出或得分低于阈值，返回 None
        """
        self._log(f"开始 1:N 说话人检索...")
        self._log(f"  音频大小: {len(audio_bytes)} 字节")
        self._log(f"  目标库: {self.group_id}")
        self._log(f"  Top-K: {max(top_k, 2)}")  # 至少取 Top-2 用于分差计算
        self._log(f"  高置信度阈值: {threshold}")
        if use_gap_rescue:
            self._log(f"  分差挽救: 启用 (最低分数: {min_accept_score}, 分差: {gap_threshold})")
        
        # 1. Base64 编码音频
        audio_base64 = base64.b64encode(audio_bytes).decode('utf-8')
        
        # 2. 构造请求体（至少取 Top-2 用于分差计算）
        actual_top_k = max(top_k, 2) if use_gap_rescue else top_k
        
        request_body = {
            "header": {
                "app_id": self.app_id,
                "status": 3  # 固定值
            },
            "parameter": {
                "s1aa729d0": {
                    "func": "searchFea",  # 1:N 检索接口
                    "groupId": self.group_id,
                    "topK": actual_top_k,
                    "searchFeaRes": {
                        "encoding": "utf8",
                        "compress": "raw",
                        "format": "json"
                    }
                }
            },
            "payload": {
                "resource": {
                    "encoding": "raw",
                    "sample_rate": 16000,
                    "channels": 1,
                    "bit_depth": 16,
                    "status": 3,
                    "audio": audio_base64
                }
            }
        }
        
        # 3. 发送请求
        response = self._send_request(request_body)
        
        if not response:
            self._log("请求失败")
            return None
        
        # 4. 解析响应
        try:
            # 获取 payload.searchFeaRes.text (Base64 编码)
            payload = response.get('payload', {})
            search_fea_res = payload.get('searchFeaRes', {})
            text_base64 = search_fea_res.get('text')
            
            if not text_base64:
                self._log("响应中没有 searchFeaRes.text 字段")
                return None
            
            # 5. 解码 Base64
            result = self._decode_payload_text(text_base64)
            
            if not result:
                self._log("解码结果失败")
                return None
            
            # 6. 提取 scoreList
            score_list = result.get('scoreList', [])
            
            if not score_list:
                self._log("未找到匹配的说话人 (scoreList 为空)")
                return None
            
            # 7. 获取 Top-1 和 Top-2
            top1 = score_list[0]
            top1_score = top1.get('score', 0.0)
            top1_feature_id = top1.get('featureId', '')
            top1_feature_info = top1.get('featureInfo', '')
            
            top2_score = score_list[1].get('score', 0.0) if len(score_list) > 1 else 0.0
            
            self._log(f"检索结果:")
            self._log(f"  Top-1: {top1_feature_info} (ID: {top1_feature_id}, 分数: {top1_score:.3f})")
            if len(score_list) > 1:
                top2_feature_info = score_list[1].get('featureInfo', '')
                self._log(f"  Top-2: {top2_feature_info} (分数: {top2_score:.3f})")
                self._log(f"  分差: {top1_score - top2_score:.3f}")
            
            # 8. 判断策略
            
            # 特殊情况：如果阈值为 0，总是返回 Top-1（用于投票场景）
            if threshold == 0.0:
                self._log(f"✓ 识别成功 [投票模式] (得分 {top1_score:.3f})")
                return {
                    'feature_id': top1_feature_id,
                    'feature_info': top1_feature_info,
                    'score': top1_score
                }
            
            # 情况 A: 高置信度，直接采纳
            if top1_score >= threshold:
                self._log(f"✓ 识别成功 [高置信度] (得分 {top1_score:.3f} >= 阈值 {threshold})")
                return {
                    'feature_id': top1_feature_id,
                    'feature_info': top1_feature_info,
                    'score': top1_score
                }
            
            # 情况 B: 分差挽救机制
            if use_gap_rescue:
                score_gap = top1_score - top2_score
                
                if (top1_score >= min_accept_score and 
                    score_gap >= gap_threshold):
                    self._log(f"✓ 识别成功 [分差挽救] (得分 {top1_score:.3f}, 分差 {score_gap:.3f} >= {gap_threshold})")
                    self._log(f"  说明: 虽然绝对分数不高，但显著高于第二名，在封闭集合中可信")
                    return {
                        'feature_id': top1_feature_id,
                        'feature_info': top1_feature_info,
                        'score': top1_score,
                        'rescue_mode': 'gap',
                        'score_gap': score_gap
                    }
            
            # 情况 C: 完全拒绝
            self._log(f"✗ 识别失败:")
            self._log(f"  得分过低 ({top1_score:.3f} < 高阈值 {threshold})")
            if use_gap_rescue:
                if top1_score < min_accept_score:
                    self._log(f"  且低于最低容忍分数 ({top1_score:.3f} < {min_accept_score})")
                else:
                    score_gap = top1_score - top2_score
                    self._log(f"  且分差不明显 ({score_gap:.3f} < {gap_threshold})")
            
            return None
                
        except Exception as e:
            self._log(f"解析响应失败: {e}")
            return None
    
    def verify_speaker(
        self,
        audio_bytes: bytes,
        target_feature_id: str,
        threshold: float = RECOMMENDED_THRESHOLD
    ) -> Tuple[bool, float]:
        """
        1:1 说话人验证 (验证"你是你")
        
        验证音频是否与指定的特征 ID 匹配
        
        Args:
            audio_bytes: 音频数据 (WAV/PCM, 16kHz, 16bit, 单声道)
            target_feature_id: 目标特征 ID
            threshold: 匹配阈值 (默认 0.6)
        
        Returns:
            (is_match, score) 元组
            - is_match: 是否匹配 (bool)
            - score: 相似度得分 (float, -1 到 1)
        """
        self._log(f"开始 1:1 说话人验证...")
        self._log(f"  目标特征ID: {target_feature_id}")
        self._log(f"  阈值: {threshold}")
        
        # 1. Base64 编码音频
        audio_base64 = base64.b64encode(audio_bytes).decode('utf-8')
        
        # 2. 构造请求体
        request_body = {
            "header": {
                "app_id": self.app_id,
                "status": 3
            },
            "parameter": {
                "s1aa729d0": {
                    "func": "searchScoreFea",  # 1:1 验证接口
                    "groupId": self.group_id,
                    "dstFeatureId": target_feature_id,
                    "searchScoreFeaRes": {
                        "encoding": "utf8",
                        "compress": "raw",
                        "format": "json"
                    }
                }
            },
            "payload": {
                "resource": {
                    "encoding": "raw",
                    "sample_rate": 16000,
                    "channels": 1,
                    "bit_depth": 16,
                    "status": 3,
                    "audio": audio_base64
                }
            }
        }
        
        # 3. 发送请求
        response = self._send_request(request_body)
        
        if not response:
            return False, -1.0
        
        # 4. 解析响应
        try:
            payload = response.get('payload', {})
            search_score_fea_res = payload.get('searchScoreFeaRes', {})
            text_base64 = search_score_fea_res.get('text')
            
            if not text_base64:
                self._log("响应中没有 searchScoreFeaRes.text 字段")
                return False, -1.0
            
            # 5. 解码 Base64
            result = self._decode_payload_text(text_base64)
            
            if not result:
                return False, -1.0
            
            # 6. 提取得分
            score = result.get('score', -1.0)
            feature_id = result.get('featureId', '')
            feature_info = result.get('featureInfo', '')
            
            self._log(f"验证结果:")
            self._log(f"  特征ID: {feature_id}")
            self._log(f"  特征信息: {feature_info}")
            self._log(f"  相似度: {score:.3f}")
            
            # 7. 判断是否匹配
            is_match = score >= threshold
            
            if is_match:
                self._log(f"✓ 验证通过 (得分 {score:.3f} >= 阈值 {threshold})")
            else:
                self._log(f"✗ 验证失败 (得分 {score:.3f} < 阈值 {threshold})")
            
            return is_match, score
            
        except Exception as e:
            self._log(f"解析响应失败: {e}")
            return False, -1.0
    
    def create_feature(
        self,
        audio_bytes: bytes,
        feature_id: str,
        feature_info: str = ""
    ) -> bool:
        """
        添加声纹特征到声纹库
        
        Args:
            audio_bytes: 音频数据 (WAV/PCM, 16kHz, 16bit, 单声道)
            feature_id: 特征 ID (唯一标识，最大 32 字符)
            feature_info: 特征描述信息 (如真实姓名，最大 256 字符)
        
        Returns:
            是否添加成功
        """
        self._log(f"添加声纹特征...")
        self._log(f"  特征ID: {feature_id}")
        self._log(f"  特征信息: {feature_info}")
        
        # Base64 编码音频
        audio_base64 = base64.b64encode(audio_bytes).decode('utf-8')
        
        # 构造请求体
        request_body = {
            "header": {
                "app_id": self.app_id,
                "status": 3
            },
            "parameter": {
                "s1aa729d0": {
                    "func": "createFeature",
                    "groupId": self.group_id,
                    "featureId": feature_id,
                    "featureInfo": feature_info,
                    "createFeatureRes": {
                        "encoding": "utf8",
                        "compress": "raw",
                        "format": "json"
                    }
                }
            },
            "payload": {
                "resource": {
                    "encoding": "raw",
                    "sample_rate": 16000,
                    "channels": 1,
                    "bit_depth": 16,
                    "status": 3,
                    "audio": audio_base64
                }
            }
        }
        
        # 发送请求
        response = self._send_request(request_body)
        
        if not response:
            return False
        
        # 解析响应
        try:
            payload = response.get('payload', {})
            create_feature_res = payload.get('createFeatureRes', {})
            text_base64 = create_feature_res.get('text')
            
            if not text_base64:
                return False
            
            result = self._decode_payload_text(text_base64)
            
            if result and result.get('featureId') == feature_id:
                self._log(f"✓ 特征添加成功")
                return True
            else:
                self._log(f"✗ 特征添加失败")
                return False
                
        except Exception as e:
            self._log(f"解析响应失败: {e}")
            return False
    
    def delete_feature(self, feature_id: str) -> bool:
        """
        删除声纹特征
        
        Args:
            feature_id: 要删除的特征 ID
        
        Returns:
            是否删除成功
        """
        self._log(f"删除声纹特征: {feature_id}")
        
        request_body = {
            "header": {
                "app_id": self.app_id,
                "status": 3
            },
            "parameter": {
                "s1aa729d0": {
                    "func": "deleteFeature",
                    "groupId": self.group_id,
                    "featureId": feature_id,
                    "deleteFeatureRes": {
                        "encoding": "utf8",
                        "compress": "raw",
                        "format": "json"
                    }
                }
            }
        }
        
        response = self._send_request(request_body)
        
        if not response:
            return False
        
        try:
            payload = response.get('payload', {})
            delete_feature_res = payload.get('deleteFeatureRes', {})
            text_base64 = delete_feature_res.get('text')
            
            if not text_base64:
                return False
            
            result = self._decode_payload_text(text_base64)
            
            # API实际返回 {"featureId": "xxx"} 而不是 {"msg": "success"}
            if result and (result.get('msg') == 'success' or result.get('featureId') == feature_id):
                self._log(f"✓ 特征删除成功")
                return True
            else:
                self._log(f"✗ 特征删除失败: {result}")
                return False
                
        except Exception as e:
            self._log(f"解析响应失败: {e}")
            return False
    
    def query_feature_list(self) -> Optional[List[Dict]]:
        """
        查询声纹库中的特征列表
        
        Returns:
            特征列表，每个元素包含 featureId 和 featureInfo
            失败返回 None
        """
        self._log(f"查询特征列表: {self.group_id}")
        
        request_body = {
            "header": {
                "app_id": self.app_id,
                "status": 3
            },
            "parameter": {
                "s1aa729d0": {
                    "func": "queryFeatureList",
                    "groupId": self.group_id,
                    "queryFeatureListRes": {
                        "encoding": "utf8",
                        "compress": "raw",
                        "format": "json"
                    }
                }
            }
        }
        
        response = self._send_request(request_body)
        
        if not response:
            return None
        
        try:
            payload = response.get('payload', {})
            query_feature_list_res = payload.get('queryFeatureListRes', {})
            text_base64 = query_feature_list_res.get('text')
            
            if not text_base64:
                return None
            
            result = self._decode_payload_text(text_base64)
            
            if result:
                feature_list = result if isinstance(result, list) else []
                self._log(f"✓ 查询成功，共 {len(feature_list)} 个特征")
                return feature_list
            else:
                return None
                
        except Exception as e:
            self._log(f"解析响应失败: {e}")
            return None


# 使用示例
if __name__ == "__main__":
    """
    使用示例：1:N 说话人检索
    """
    
    # 1. 初始化客户端
    client = iFLYTEKVoiceprint(
        app_id="YOUR_APP_ID",
        api_key="YOUR_API_KEY",
        api_secret="YOUR_API_SECRET",
        group_id="YOUR_GROUP_ID",
        verbose=True
    )
    
    # 2. 读取音频文件
    with open("speaker_sample.wav", "rb") as f:
        audio_bytes = f.read()
    
    # 3. 1:N 检索
    result = client.identify_speaker(
        audio_bytes=audio_bytes,
        top_k=1,
        threshold=0.6
    )
    
    if result:
        print(f"\n识别成功！")
        print(f"说话人: {result['feature_info']}")
        print(f"特征ID: {result['feature_id']}")
        print(f"相似度: {result['score']:.3f}")
    else:
        print(f"\n未识别出已知说话人")
    
    # 4. 1:1 验证
    is_match, score = client.verify_speaker(
        audio_bytes=audio_bytes,
        target_feature_id="speaker_001",
        threshold=0.6
    )
    
    print(f"\n验证结果: {'匹配' if is_match else '不匹配'}")
    print(f"相似度: {score:.3f}")

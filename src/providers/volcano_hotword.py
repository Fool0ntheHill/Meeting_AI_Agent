# -*- coding: utf-8 -*-
"""火山引擎热词管理客户端"""

import binascii
import datetime
import hashlib
import hmac
import json
import urllib.parse
from typing import Dict, List, Optional

import requests

from src.utils.logger import get_logger

logger = get_logger(__name__)


class VolcanoHotwordClient:
    """火山引擎热词管理客户端"""

    def __init__(self, app_id: str, access_key: str, secret_key: str):
        """
        初始化客户端

        Args:
            app_id: 应用 ID
            access_key: Access Key
            secret_key: Secret Key
        """
        self.app_id = app_id
        self.access_key = access_key
        self.secret_key = secret_key
        self.domain = "open.volcengineapi.com"
        self.region = "cn-north-1"
        self.service = "speech_saas_prod"
        self.version = "2022-08-30"

    def _get_hmac_encode16(self, data: str) -> str:
        """计算 SHA256 哈希"""
        return binascii.b2a_hex(hashlib.sha256(data.encode("utf-8")).digest()).decode("ascii")

    def _get_volc_signature(self, secret_key: bytes, data: str) -> bytes:
        """计算 HMAC-SHA256 签名"""
        return hmac.new(secret_key, data.encode("utf-8"), digestmod=hashlib.sha256).digest()

    def _get_headers(
        self,
        canonical_query_string: str,
        http_method: str,
        canonical_uri: str,
        content_type: str,
        payload_sign: str,
    ) -> Dict[str, str]:
        """生成请求头"""
        utc_time_second = datetime.datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
        utc_time_day = datetime.datetime.utcnow().strftime("%Y%m%d")
        credential_scope = f"{utc_time_day}/{self.region}/{self.service}/request"

        headers = {
            "content-type": content_type,
            "x-date": utc_time_second,
        }

        canonical_headers = (
            f"content-type:{content_type}\n"
            f"host:{self.domain}\n"
            f"x-content-sha256:\n"
            f"x-date:{utc_time_second}\n"
        )

        signed_headers = "content-type;host;x-content-sha256;x-date"

        canonical_request = (
            f"{http_method}\n"
            f"{canonical_uri}\n"
            f"{canonical_query_string}\n"
            f"{canonical_headers}\n"
            f"{signed_headers}\n"
            f"{payload_sign}"
        )

        string_to_sign = (
            f"HMAC-SHA256\n"
            f"{utc_time_second}\n"
            f"{credential_scope}\n"
            f"{self._get_hmac_encode16(canonical_request)}"
        )

        signing_key = self._get_volc_signature(
            self._get_volc_signature(
                self._get_volc_signature(
                    self._get_volc_signature(self.secret_key.encode("utf-8"), utc_time_day),
                    self.region,
                ),
                self.service,
            ),
            "request",
        )

        signature = binascii.b2a_hex(self._get_volc_signature(signing_key, string_to_sign)).decode("ascii")

        headers["Authorization"] = (
            f"HMAC-SHA256 Credential={self.access_key}/{credential_scope}, "
            f"SignedHeaders={signed_headers}, Signature={signature}"
        )

        return headers

    def create_boosting_table(
        self,
        name: str,
        hotwords_content: str,
    ) -> Dict:
        """
        创建热词库

        Args:
            name: 热词库名称
            hotwords_content: 热词内容 (每行一个热词,格式: "词语|权重")

        Returns:
            Dict: 包含 BoostingTableID 等信息

        Raises:
            Exception: API 调用失败
        """
        logger.info(f"Creating boosting table: {name}")
        
        # 边界字符串
        boundary = "----WebKitFormBoundaryLPAZvyOnASevwDBv"
        content_type = f"multipart/form-data; boundary={boundary}"
        
        # 构建 multipart/form-data body (按照官方示例的顺序)
        body_parts = []
        
        # File 字段
        body_parts.append(f"--{boundary}")
        body_parts.append(f'Content-Disposition: form-data; name="File"; filename="{name}.txt"')
        body_parts.append("Content-Type: text/plain")
        body_parts.append("")
        body_parts.append(hotwords_content)
        
        # AppID 字段
        body_parts.append(f"--{boundary}")
        body_parts.append('Content-Disposition: form-data; name="AppID"')
        body_parts.append("")
        body_parts.append(str(self.app_id))
        
        # BoostingTableName 字段
        body_parts.append(f"--{boundary}")
        body_parts.append('Content-Disposition: form-data; name="BoostingTableName"')
        body_parts.append("")
        body_parts.append(name)
        
        # 结束边界
        body_parts.append(f"--{boundary}--")
        body_parts.append("")
        
        # 拼接 body
        body = "\r\n".join(body_parts)
        
        # 构建查询参数
        canonical_query_string = f"Action=CreateBoostingTable&Version={self.version}"
        url = f"https://{self.domain}/?{canonical_query_string}"
        
        # 计算 payload 签名
        payload_sign = self._get_hmac_encode16(body)
        
        # 构建 headers
        headers = self._get_headers(
            canonical_query_string,
            "POST",
            "/",
            content_type,
            payload_sign,
        )

        # 发送请求
        response = requests.post(url=url, headers=headers, data=body.encode('utf-8'))

        if response.status_code != 200:
            logger.error(f"Failed to create boosting table: {response.text}")
            raise Exception(f"创建热词库失败: {response.text}")

        result = response.json()
        if "Result" in result:
            logger.info(f"Boosting table created: {result['Result'].get('BoostingTableID')}")
            return result["Result"]
        else:
            raise Exception(f"创建热词库失败: {result}")

    def list_boosting_tables(
        self,
        page_number: int = 1,
        page_size: int = 10,
        preview_size: int = 10,
    ) -> Dict:
        """
        列出热词库

        Args:
            page_number: 页码
            page_size: 每页数量
            preview_size: 预览词数

        Returns:
            Dict: 热词库列表
        """
        params_body = {
            "Action": "ListBoostingTable",
            "Version": self.version,
            "AppID": self.app_id,
            "PageNumber": page_number,
            "PageSize": page_size,
            "PreviewSize": preview_size,
        }

        canonical_query_string = f"Action=ListBoostingTable&Version={self.version}"
        url = f"https://{self.domain}/?{canonical_query_string}"
        content_type = "application/json; charset=utf-8"
        payload_sign = self._get_hmac_encode16(json.dumps(params_body))

        headers = self._get_headers(
            canonical_query_string,
            "POST",
            "/",
            content_type,
            payload_sign,
        )

        response = requests.post(url=url, headers=headers, data=json.dumps(params_body))

        if response.status_code != 200:
            logger.error(f"Failed to list boosting tables: {response.text}")
            raise Exception(f"列出热词库失败: {response.text}")

        result = response.json()
        if "Result" in result:
            return result["Result"]
        else:
            raise Exception(f"列出热词库失败: {result}")

    def get_boosting_table(self, boosting_table_id: str) -> Dict:
        """
        获取热词库详情

        Args:
            boosting_table_id: 热词库 ID

        Returns:
            Dict: 热词库详情
        """
        params_body = {
            "Action": "GetBoostingTable",
            "Version": self.version,
            "AppID": self.app_id,
            "BoostingTableID": boosting_table_id,
        }

        canonical_query_string = f"Action=GetBoostingTable&Version={self.version}"
        url = f"https://{self.domain}/?{canonical_query_string}"
        content_type = "application/json; charset=utf-8"
        payload_sign = self._get_hmac_encode16(json.dumps(params_body))

        headers = self._get_headers(
            canonical_query_string,
            "POST",
            "/",
            content_type,
            payload_sign,
        )

        response = requests.post(url=url, headers=headers, data=json.dumps(params_body))

        if response.status_code != 200:
            logger.error(f"Failed to get boosting table: {response.text}")
            raise Exception(f"获取热词库失败: {response.text}")

        result = response.json()
        if "Result" in result:
            return result["Result"]
        else:
            raise Exception(f"获取热词库失败: {result}")

    def delete_boosting_table(self, boosting_table_id: str) -> bool:
        """
        删除热词库

        Args:
            boosting_table_id: 热词库 ID

        Returns:
            bool: 是否成功
        """
        params_body = {
            "Action": "DeleteBoostingTable",
            "Version": self.version,
            "AppID": self.app_id,
            "BoostingTableID": boosting_table_id,
        }

        canonical_query_string = f"Action=DeleteBoostingTable&Version={self.version}"
        url = f"https://{self.domain}/?{canonical_query_string}"
        content_type = "application/json; charset=utf-8"
        payload_sign = self._get_hmac_encode16(json.dumps(params_body))

        headers = self._get_headers(
            canonical_query_string,
            "POST",
            "/",
            content_type,
            payload_sign,
        )

        response = requests.post(url=url, headers=headers, data=json.dumps(params_body))

        if response.status_code != 200:
            logger.error(f"Failed to delete boosting table: {response.text}")
            raise Exception(f"删除热词库失败: {response.text}")

        result = response.json()
        logger.info(f"Boosting table deleted: {boosting_table_id}")
        return True

    def update_boosting_table(
        self,
        boosting_table_id: str,
        name: Optional[str] = None,
        hotwords_content: Optional[str] = None,
    ) -> Dict:
        """
        更新热词库

        Args:
            boosting_table_id: 热词库 ID
            name: 新名称 (可选)
            hotwords_content: 新热词内容 (可选)

        Returns:
            Dict: 更新后的热词库信息
        """
        logger.info(f"Updating boosting table: {boosting_table_id}")
        
        # 边界字符串
        boundary = "----WebKitFormBoundaryLPAZvyOnASevwDBv"
        content_type = f"multipart/form-data; boundary={boundary}"
        
        # 构建 multipart/form-data body
        body_parts = []
        
        # File 字段 (如果提供)
        if hotwords_content:
            body_parts.append(f"--{boundary}")
            body_parts.append(f'Content-Disposition: form-data; name="File"; filename="{name or "hotwords"}.txt"')
            body_parts.append("Content-Type: text/plain")
            body_parts.append("")
            body_parts.append(hotwords_content)
        
        # AppID 字段
        body_parts.append(f"--{boundary}")
        body_parts.append('Content-Disposition: form-data; name="AppID"')
        body_parts.append("")
        body_parts.append(str(self.app_id))
        
        # BoostingTableID 字段
        body_parts.append(f"--{boundary}")
        body_parts.append('Content-Disposition: form-data; name="BoostingTableID"')
        body_parts.append("")
        body_parts.append(boosting_table_id)
        
        # BoostingTableName 字段 (如果提供)
        if name:
            body_parts.append(f"--{boundary}")
            body_parts.append('Content-Disposition: form-data; name="BoostingTableName"')
            body_parts.append("")
            body_parts.append(name)
        
        # 结束边界
        body_parts.append(f"--{boundary}--")
        body_parts.append("")
        
        # 拼接 body
        body = "\r\n".join(body_parts)
        
        # 构建查询参数
        canonical_query_string = f"Action=UpdateBoostingTable&Version={self.version}"
        url = f"https://{self.domain}/?{canonical_query_string}"
        
        # 计算 payload 签名
        payload_sign = self._get_hmac_encode16(body)
        
        # 构建 headers
        headers = self._get_headers(
            canonical_query_string,
            "POST",
            "/",
            content_type,
            payload_sign,
        )

        # 发送请求
        response = requests.post(url=url, headers=headers, data=body.encode('utf-8'))

        if response.status_code != 200:
            logger.error(f"Failed to update boosting table: {response.text}")
            raise Exception(f"更新热词库失败: {response.text}")

        result = response.json()
        if "Result" in result:
            logger.info(f"Boosting table updated: {boosting_table_id}")
            return result["Result"]
        else:
            raise Exception(f"更新热词库失败: {result}")

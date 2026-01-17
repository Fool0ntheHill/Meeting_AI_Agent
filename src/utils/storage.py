"""Storage client for TOS (Tencent Object Storage) operations."""

import asyncio
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import tos

from src.core.exceptions import DownloadError, StorageError, UploadError


class StorageClient:
    """存储客户端(TOS)"""

    def __init__(
        self,
        bucket: str,
        region: str,
        access_key: str,
        secret_key: str,
        endpoint: Optional[str] = None,
        temp_file_ttl: int = 3600,
    ):
        """
        初始化存储客户端

        Args:
            bucket: 存储桶名称
            region: 区域
            access_key: Access Key
            secret_key: Secret Key
            endpoint: 自定义端点
            temp_file_ttl: 临时文件 TTL(秒)
        """
        self.bucket = bucket
        self.region = region
        self.access_key = access_key
        self.secret_key = secret_key
        self.endpoint = endpoint or f"tos-{region}.volces.com"
        self.temp_file_ttl = temp_file_ttl
        self._temp_files = set()  # 跟踪临时文件
        
        # 初始化 TOS 客户端
        self.client = tos.TosClientV2(
            ak=access_key,
            sk=secret_key,
            endpoint=self.endpoint,
            region=region,
        )

    async def upload_file(
        self, local_path: str, object_key: str, content_type: Optional[str] = None
    ) -> str:
        """
        上传文件到 TOS

        Args:
            local_path: 本地文件路径
            object_key: 对象键(存储路径)
            content_type: 内容类型

        Returns:
            str: 对象 URL

        Raises:
            UploadError: 上传失败
        """
        try:
            # 验证文件存在
            if not Path(local_path).exists():
                raise UploadError(
                    f"本地文件不存在: {local_path}",
                    details={"path": local_path},
                )

            # 在线程池中执行同步上传操作
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                lambda: self.client.put_object_from_file(
                    bucket=self.bucket,
                    key=object_key,
                    file_path=local_path,
                    content_type=content_type,
                ),
            )

            # 返回对象 URL
            url = f"https://{self.bucket}.{self.endpoint}/{object_key}"
            return url

        except Exception as e:
            raise UploadError(
                f"上传文件失败: {e}",
                details={"local_path": local_path, "object_key": object_key, "error": str(e)},
            )

    async def download_file(self, object_key: str, local_path: Optional[str] = None) -> str:
        """
        从 TOS 下载文件

        Args:
            object_key: 对象键或完整的 TOS URL (支持预签名 URL)
            local_path: 本地保存路径,如果为 None 则使用临时文件

        Returns:
            str: 本地文件路径

        Raises:
            DownloadError: 下载失败
        """
        try:
            # 如果是完整 URL,提取 object_key
            if object_key.startswith("http://") or object_key.startswith("https://"):
                # 从 URL 中提取 object_key
                # URL 格式: https://{bucket}.{endpoint}/{object_key}?query_params
                from urllib.parse import urlparse, unquote
                parsed = urlparse(object_key)
                # 移除开头的 / 并解码 URL 编码
                object_key = unquote(parsed.path.lstrip("/"))
            
            # 确定本地路径
            if local_path is None:
                # 创建临时文件
                suffix = Path(object_key).suffix or ".tmp"
                temp_file = tempfile.NamedTemporaryFile(
                    suffix=suffix, delete=False, mode="wb"
                )
                local_path = temp_file.name
                temp_file.close()
                self._temp_files.add(local_path)
            
            # 如果目标文件已存在,先删除(避免 TOS 客户端重命名失败)
            local_path_obj = Path(local_path)
            if local_path_obj.exists():
                local_path_obj.unlink()

            # 在线程池中执行同步下载操作
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                lambda: self.client.get_object_to_file(
                    bucket=self.bucket,
                    key=object_key,
                    file_path=local_path,
                ),
            )

            return local_path

        except Exception as e:
            raise DownloadError(
                f"下载文件失败: {e}",
                details={"object_key": object_key, "local_path": local_path, "error": str(e)},
            )

    async def delete_file(self, object_key: str) -> None:
        """
        删除 TOS 中的文件

        Args:
            object_key: 对象键

        Raises:
            StorageError: 删除失败
        """
        try:
            # 在线程池中执行同步删除操作
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                lambda: self.client.delete_object(bucket=self.bucket, key=object_key),
            )

        except Exception as e:
            raise StorageError(
                f"删除文件失败: {e}",
                details={"object_key": object_key, "error": str(e)},
            )

    async def generate_presigned_url(
        self, object_key: str, expires_in: int = 3600
    ) -> str:
        """
        生成预签名 URL

        Args:
            object_key: 对象键
            expires_in: 过期时间(秒)

        Returns:
            str: 预签名 URL

        Raises:
            StorageError: 生成失败
        """
        try:
            # 在线程池中执行同步操作
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                lambda: self.client.pre_signed_url(
                    http_method=tos.HttpMethodType.Http_Method_Get,
                    bucket=self.bucket,
                    key=object_key,
                    expires=expires_in,
                ),
            )
            
            return result.signed_url

        except Exception as e:
            raise StorageError(
                f"生成预签名 URL 失败: {e}",
                details={"object_key": object_key, "error": str(e)},
            )

    async def cleanup_temp_files(self) -> None:
        """清理临时文件"""
        for temp_file in self._temp_files:
            try:
                path = Path(temp_file)
                if path.exists():
                    path.unlink()
            except Exception:
                # 忽略清理错误
                pass
        self._temp_files.clear()

    def __del__(self):
        """析构函数,清理临时文件"""
        # 同步清理临时文件
        for temp_file in self._temp_files:
            try:
                path = Path(temp_file)
                if path.exists():
                    path.unlink()
            except Exception:
                pass

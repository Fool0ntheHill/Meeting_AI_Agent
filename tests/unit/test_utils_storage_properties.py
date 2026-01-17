"""Property-based tests for storage utilities.

Feature: meeting-minutes-agent
Property 10: 临时文件清理
验证: 需求 12.4

属性 10: 对于任何 StorageClient 实例,调用 cleanup_temp_files 后,
所有通过该实例下载的临时文件应当被删除。
"""

import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from hypothesis import given, strategies as st

from src.utils.storage import StorageClient


# ============================================================================
# Helper Functions
# ============================================================================


def create_mock_tos_client():
    """创建模拟的 TOS 客户端"""
    mock_client = MagicMock()
    mock_client.get_object_to_file = MagicMock()
    mock_client.put_object_from_file = MagicMock()
    mock_client.delete_object = MagicMock()
    return mock_client


# ============================================================================
# Property 10: 临时文件清理
# ============================================================================


class TestTemporaryFileCleanup:
    """Test temporary file cleanup properties"""
    
    @pytest.mark.asyncio
    async def test_cleanup_removes_all_temp_files(self):
        """
        Property: cleanup_temp_files 应当删除所有临时文件
        """
        # 创建 StorageClient (使用模拟的 TOS 客户端)
        with patch('src.utils.storage.tos.TosClientV2') as mock_tos:
            mock_tos.return_value = create_mock_tos_client()
            
            client = StorageClient(
                bucket="test-bucket",
                region="test-region",
                access_key="test-key",
                secret_key="test-secret",
            )
            
            # 模拟下载多个文件(不指定 local_path,使用临时文件)
            temp_files = []
            for i in range(3):
                # 创建临时文件模拟下载结果
                temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".tmp")
                temp_file.write(b"test content")
                temp_file.close()
                temp_files.append(temp_file.name)
                
                # 手动添加到 _temp_files 集合(模拟 download_file 的行为)
                client._temp_files.add(temp_file.name)
            
            # 验证文件存在
            for temp_file in temp_files:
                assert Path(temp_file).exists(), f"临时文件应存在: {temp_file}"
            
            # 清理临时文件
            await client.cleanup_temp_files()
            
            # 验证所有文件已删除
            for temp_file in temp_files:
                assert not Path(temp_file).exists(), f"临时文件应被删除: {temp_file}"
            
            # 验证 _temp_files 集合已清空
            assert len(client._temp_files) == 0, "_temp_files 集合应为空"
    
    @pytest.mark.asyncio
    async def test_cleanup_handles_missing_files_gracefully(self):
        """
        Property: cleanup_temp_files 应当优雅处理已删除的文件
        """
        with patch('src.utils.storage.tos.TosClientV2') as mock_tos:
            mock_tos.return_value = create_mock_tos_client()
            
            client = StorageClient(
                bucket="test-bucket",
                region="test-region",
                access_key="test-key",
                secret_key="test-secret",
            )
            
            # 添加不存在的文件路径
            non_existent_file = "/tmp/non_existent_file_12345.tmp"
            client._temp_files.add(non_existent_file)
            
            # 清理应当不抛出异常
            await client.cleanup_temp_files()
            
            # 验证 _temp_files 集合已清空
            assert len(client._temp_files) == 0
    
    @pytest.mark.asyncio
    async def test_cleanup_is_idempotent(self):
        """
        Property: cleanup_temp_files 应当是幂等的(多次调用结果相同)
        """
        with patch('src.utils.storage.tos.TosClientV2') as mock_tos:
            mock_tos.return_value = create_mock_tos_client()
            
            client = StorageClient(
                bucket="test-bucket",
                region="test-region",
                access_key="test-key",
                secret_key="test-secret",
            )
            
            # 创建临时文件
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".tmp")
            temp_file.write(b"test content")
            temp_file.close()
            client._temp_files.add(temp_file.name)
            
            # 第一次清理
            await client.cleanup_temp_files()
            assert not Path(temp_file.name).exists()
            assert len(client._temp_files) == 0
            
            # 第二次清理(应当不抛出异常)
            await client.cleanup_temp_files()
            assert len(client._temp_files) == 0
    
    @given(st.integers(min_value=1, max_value=10))
    @pytest.mark.asyncio
    async def test_cleanup_removes_all_files_regardless_of_count(self, file_count: int):
        """
        Property: 无论临时文件数量多少,cleanup_temp_files 都应当全部删除
        """
        with patch('src.utils.storage.tos.TosClientV2') as mock_tos:
            mock_tos.return_value = create_mock_tos_client()
            
            client = StorageClient(
                bucket="test-bucket",
                region="test-region",
                access_key="test-key",
                secret_key="test-secret",
            )
            
            # 创建多个临时文件
            temp_files = []
            for i in range(file_count):
                temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=f"_{i}.tmp")
                temp_file.write(f"test content {i}".encode())
                temp_file.close()
                temp_files.append(temp_file.name)
                client._temp_files.add(temp_file.name)
            
            # 验证文件数量
            assert len(client._temp_files) == file_count
            
            # 清理
            await client.cleanup_temp_files()
            
            # 验证所有文件已删除
            for temp_file in temp_files:
                assert not Path(temp_file).exists(), f"文件应被删除: {temp_file}"
            
            # 验证集合已清空
            assert len(client._temp_files) == 0


class TestStorageClientDestructor:
    """Test StorageClient destructor cleanup"""
    
    def test_destructor_cleans_up_temp_files(self):
        """
        Property: StorageClient 析构时应当清理临时文件
        """
        with patch('src.utils.storage.tos.TosClientV2') as mock_tos:
            mock_tos.return_value = create_mock_tos_client()
            
            # 创建临时文件
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".tmp")
            temp_file.write(b"test content")
            temp_file.close()
            temp_file_path = temp_file.name
            
            # 创建 client 并添加临时文件
            client = StorageClient(
                bucket="test-bucket",
                region="test-region",
                access_key="test-key",
                secret_key="test-secret",
            )
            client._temp_files.add(temp_file_path)
            
            # 验证文件存在
            assert Path(temp_file_path).exists()
            
            # 删除 client 对象(触发析构函数)
            del client
            
            # 验证文件已被删除
            assert not Path(temp_file_path).exists(), "析构函数应删除临时文件"


# ============================================================================
# Additional Storage Tests
# ============================================================================


class TestStorageClientURLHandling:
    """Test URL handling in download_file"""
    
    @pytest.mark.asyncio
    async def test_download_extracts_object_key_from_url(self):
        """
        Property: download_file 应当能从完整 URL 中提取 object_key
        """
        with patch('src.utils.storage.tos.TosClientV2') as mock_tos:
            mock_client = create_mock_tos_client()
            mock_tos.return_value = mock_client
            
            client = StorageClient(
                bucket="test-bucket",
                region="test-region",
                access_key="test-key",
                secret_key="test-secret",
            )
            
            # 测试完整 URL
            full_url = "https://test-bucket.tos-test-region.volces.com/path/to/file.wav"
            
            # 创建临时输出文件
            temp_output = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
            temp_output.close()
            
            try:
                # 模拟下载
                await client.download_file(full_url, temp_output.name)
                
                # 验证调用参数(应当提取出 object_key)
                mock_client.get_object_to_file.assert_called_once()
                call_args = mock_client.get_object_to_file.call_args
                
                # 验证 object_key 被正确提取
                assert call_args[1]["key"] == "path/to/file.wav"
                
            finally:
                # 清理
                Path(temp_output.name).unlink(missing_ok=True)
    
    @pytest.mark.asyncio
    async def test_download_handles_url_encoded_paths(self):
        """
        Property: download_file 应当正确处理 URL 编码的路径
        """
        with patch('src.utils.storage.tos.TosClientV2') as mock_tos:
            mock_client = create_mock_tos_client()
            mock_tos.return_value = mock_client
            
            client = StorageClient(
                bucket="test-bucket",
                region="test-region",
                access_key="test-key",
                secret_key="test-secret",
            )
            
            # 测试 URL 编码的路径
            encoded_url = "https://test-bucket.tos-test-region.volces.com/path%20with%20spaces/file.wav"
            
            # 创建临时输出文件
            temp_output = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
            temp_output.close()
            
            try:
                # 模拟下载
                await client.download_file(encoded_url, temp_output.name)
                
                # 验证 object_key 被正确解码
                call_args = mock_client.get_object_to_file.call_args
                assert call_args[1]["key"] == "path with spaces/file.wav"
                
            finally:
                # 清理
                Path(temp_output.name).unlink(missing_ok=True)


# ============================================================================
# Run tests
# ============================================================================


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

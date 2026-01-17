"""
集成测试配置和共享 fixtures
"""

import pytest
import os
from pathlib import Path
from unittest.mock import Mock

from src.config.models import (
    AppConfig,
    DatabaseConfig,
    RedisConfig,
    VolcanoConfig,
    AzureConfig,
    IFlyTekConfig,
    GeminiConfig,
    StorageConfig,
)


@pytest.fixture(scope="session")
def test_config():
    """创建测试配置"""
    return AppConfig(
        environment="test",
        database=DatabaseConfig(
            url="sqlite:///./test_meeting_agent.db",
            echo=False,
        ),
        redis=RedisConfig(
            url="redis://localhost:6379/15",  # 使用测试数据库
            max_connections=10,
        ),
        volcano=VolcanoConfig(
            app_id=os.getenv("VOLCANO_APP_ID", "test_app_id"),
            access_key=os.getenv("VOLCANO_ACCESS_KEY", "test_access_key"),
            secret_key=os.getenv("VOLCANO_SECRET_KEY", "test_secret_key"),
            cluster_id=os.getenv("VOLCANO_CLUSTER_ID", "test_cluster_id"),
            boosting_table_id=os.getenv("VOLCANO_BOOSTING_TABLE_ID", ""),
        ),
        azure=AzureConfig(
            subscription_key=os.getenv("AZURE_SUBSCRIPTION_KEY", "test_key"),
            region=os.getenv("AZURE_REGION", "eastus"),
        ),
        iflytek=IFlyTekConfig(
            app_id=os.getenv("IFLYTEK_APP_ID", "test_app_id"),
            api_key=os.getenv("IFLYTEK_API_KEY", "test_api_key"),
            api_secret=os.getenv("IFLYTEK_API_SECRET", "test_api_secret"),
            group_id=os.getenv("IFLYTEK_GROUP_ID", "test_group_id"),
        ),
        gemini=GeminiConfig(
            api_key=os.getenv("GEMINI_API_KEY", "test_api_key"),
            model=os.getenv("GEMINI_MODEL", "gemini-1.5-flash"),
        ),
        storage=StorageConfig(
            bucket=os.getenv("TOS_BUCKET", "test-bucket"),
            region=os.getenv("TOS_REGION", "cn-beijing"),
            access_key=os.getenv("TOS_ACCESS_KEY", "test_access_key"),
            secret_key=os.getenv("TOS_SECRET_KEY", "test_secret_key"),
        ),
        jwt_secret_key=os.getenv("JWT_SECRET_KEY", "test_secret_key_for_jwt"),
        jwt_algorithm="HS256",
        jwt_expiration_hours=24,
    )


@pytest.fixture
def test_audio_file(tmp_path):
    """创建测试音频文件"""
    audio_file = tmp_path / "test_audio.wav"
    
    # 创建一个简单的 WAV 文件头
    # 注意: 这不是真实的音频数据，只是用于测试文件操作
    wav_header = bytes([
        0x52, 0x49, 0x46, 0x46,  # "RIFF"
        0x24, 0x00, 0x00, 0x00,  # ChunkSize
        0x57, 0x41, 0x56, 0x45,  # "WAVE"
        0x66, 0x6D, 0x74, 0x20,  # "fmt "
        0x10, 0x00, 0x00, 0x00,  # Subchunk1Size
        0x01, 0x00,              # AudioFormat (PCM)
        0x01, 0x00,              # NumChannels (Mono)
        0x44, 0xAC, 0x00, 0x00,  # SampleRate (44100)
        0x88, 0x58, 0x01, 0x00,  # ByteRate
        0x02, 0x00,              # BlockAlign
        0x10, 0x00,              # BitsPerSample (16)
        0x64, 0x61, 0x74, 0x61,  # "data"
        0x00, 0x00, 0x00, 0x00,  # Subchunk2Size
    ])
    
    audio_file.write_bytes(wav_header)
    return str(audio_file)


@pytest.fixture
def mock_database_session():
    """创建 mock 数据库会话"""
    session = Mock()
    session.add = Mock()
    session.commit = Mock()
    session.rollback = Mock()
    session.close = Mock()
    session.query = Mock()
    return session


@pytest.fixture
def mock_redis_client():
    """创建 mock Redis 客户端"""
    client = Mock()
    client.get = Mock(return_value=None)
    client.set = Mock(return_value=True)
    client.delete = Mock(return_value=1)
    client.exists = Mock(return_value=False)
    client.expire = Mock(return_value=True)
    return client


@pytest.fixture(autouse=True)
def cleanup_test_files(tmp_path):
    """自动清理测试文件"""
    yield
    # 测试后清理
    if tmp_path.exists():
        for file in tmp_path.iterdir():
            if file.is_file():
                file.unlink()


@pytest.fixture
def sample_jwt_token():
    """创建示例 JWT token"""
    # 注意: 这是一个简化的 token，实际测试应该使用真实的 JWT 生成
    return "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoidGVzdF91c2VyIiwidGVuYW50X2lkIjoidGVzdF90ZW5hbnQifQ.test_signature"


@pytest.fixture
def integration_test_marker():
    """标记集成测试"""
    # 可以用于跳过需要外部服务的测试
    skip_integration = os.getenv("SKIP_INTEGRATION_TESTS", "false").lower() == "true"
    if skip_integration:
        pytest.skip("跳过集成测试 (SKIP_INTEGRATION_TESTS=true)")

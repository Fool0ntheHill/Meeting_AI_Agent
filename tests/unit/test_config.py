"""Unit tests for configuration management."""

import os
from pathlib import Path

import pytest

from src.config.loader import ConfigLoader
from src.config.models import (
    AppConfig,
    AzureConfig,
    DatabaseConfig,
    GeminiConfig,
    IFlyTekConfig,
    RedisConfig,
    VolcanoConfig,
)
from src.core.exceptions import InvalidConfigError, MissingConfigError


def test_database_config_connection_string():
    """Test DatabaseConfig connection string generation"""
    config = DatabaseConfig(
        host="localhost",
        port=5432,
        database="testdb",
        username="user",
        password="pass",
    )
    assert config.connection_string == "postgresql+asyncpg://user:pass@localhost:5432/testdb"


def test_redis_config_connection_string():
    """Test RedisConfig connection string generation"""
    # Without password
    config1 = RedisConfig(host="localhost", port=6379, db=0)
    assert config1.connection_string == "redis://localhost:6379/0"

    # With password
    config2 = RedisConfig(host="localhost", port=6379, password="secret", db=1)
    assert config2.connection_string == "redis://:secret@localhost:6379/1"


def test_volcano_config_validation():
    """Test VolcanoConfig validation"""
    # Valid config
    config = VolcanoConfig(
        access_key="test_key",
        secret_key="test_secret",
        app_id="test_app",
        cluster_id="test_cluster",
        tos_bucket="test-bucket",
    )
    assert config.access_key == "test_key"

    # Empty access_key should raise ValueError
    with pytest.raises(ValueError, match="字段不能为空"):
        VolcanoConfig(
            access_key="",
            secret_key="test_secret",
            app_id="test_app",
            cluster_id="test_cluster",
            tos_bucket="test-bucket",
        )


def test_azure_config_validation():
    """Test AzureConfig validation"""
    # Valid config
    config = AzureConfig(subscription_keys=["key1", "key2"])
    assert len(config.subscription_keys) == 2

    # Empty keys list should raise ValueError
    with pytest.raises(ValueError, match="至少需要一个订阅密钥"):
        AzureConfig(subscription_keys=[])

    # Empty key in list should raise ValueError
    with pytest.raises(ValueError, match="订阅密钥不能为空"):
        AzureConfig(subscription_keys=["key1", ""])


def test_iflytek_config_validation():
    """Test IFlyTekConfig validation"""
    # Valid config
    config = IFlyTekConfig(
        app_id="test_app",
        api_key="test_key",
        api_secret="test_secret",
        group_id="test_group",
    )
    assert config.app_id == "test_app"

    # Empty api_key should raise ValueError
    with pytest.raises(ValueError, match="字段不能为空"):
        IFlyTekConfig(
            app_id="test_app",
            api_key="",
            api_secret="test_secret",
            group_id="test_group",
        )


def test_gemini_config_validation():
    """Test GeminiConfig validation"""
    # Valid config
    config = GeminiConfig(api_keys=["key1", "key2"])
    assert len(config.api_keys) == 2
    assert config.model == "gemini-2.0-flash-exp"

    # Empty keys list should raise ValueError
    with pytest.raises(ValueError, match="至少需要一个 API 密钥"):
        GeminiConfig(api_keys=[])


def test_app_config_env_validation():
    """Test AppConfig environment validation"""
    minimal_config = {
        "env": "development",
        "database": {
            "host": "localhost",
            "database": "test",
            "username": "user",
            "password": "pass",
        },
        "redis": {"host": "localhost"},
        "volcano": {
            "access_key": "key",
            "secret_key": "secret",
            "app_id": "app",
            "cluster_id": "cluster",
            "tos_bucket": "bucket",
        },
        "azure": {"subscription_keys": ["key1"]},
        "iflytek": {
            "app_id": "app",
            "api_key": "key",
            "api_secret": "secret",
            "group_id": "group",
        },
        "gemini": {"api_keys": ["key1"]},
        "storage": {
            "bucket": "bucket",
            "region": "region",
            "access_key": "key",
            "secret_key": "secret",
        },
        "jwt_secret_key": "test-secret-key-for-testing",
    }

    # Valid env
    config = AppConfig(**minimal_config)
    assert config.env == "development"

    # Invalid env should raise ValueError
    invalid_config = minimal_config.copy()
    invalid_config["env"] = "invalid"
    with pytest.raises(ValueError, match="env 必须是"):
        AppConfig(**invalid_config)


def test_app_config_asr_provider_validation():
    """Test AppConfig ASR provider validation"""
    minimal_config = {
        "env": "development",
        "database": {
            "host": "localhost",
            "database": "test",
            "username": "user",
            "password": "pass",
        },
        "redis": {"host": "localhost"},
        "volcano": {
            "access_key": "key",
            "secret_key": "secret",
            "app_id": "app",
            "cluster_id": "cluster",
            "tos_bucket": "bucket",
        },
        "azure": {"subscription_keys": ["key1"]},
        "iflytek": {
            "app_id": "app",
            "api_key": "key",
            "api_secret": "secret",
            "group_id": "group",
        },
        "gemini": {"api_keys": ["key1"]},
        "storage": {
            "bucket": "bucket",
            "region": "region",
            "access_key": "key",
            "secret_key": "secret",
        },
        "jwt_secret_key": "test-secret-key-for-testing",
        "default_asr_provider": "volcano",
    }

    # Valid provider
    config = AppConfig(**minimal_config)
    assert config.default_asr_provider == "volcano"

    # Invalid provider should raise ValueError
    invalid_config = minimal_config.copy()
    invalid_config["default_asr_provider"] = "invalid"
    with pytest.raises(ValueError, match="default_asr_provider 必须是"):
        AppConfig(**invalid_config)


def test_config_loader_load_from_dict():
    """Test ConfigLoader.load_from_dict()"""
    loader = ConfigLoader()
    
    config_dict = {
        "env": "test",
        "database": {
            "host": "localhost",
            "database": "test",
            "username": "user",
            "password": "pass",
        },
        "redis": {"host": "localhost"},
        "volcano": {
            "access_key": "key",
            "secret_key": "secret",
            "app_id": "app",
            "cluster_id": "cluster",
            "tos_bucket": "bucket",
        },
        "azure": {"subscription_keys": ["key1"]},
        "iflytek": {
            "app_id": "app",
            "api_key": "key",
            "api_secret": "secret",
            "group_id": "group",
        },
        "gemini": {"api_keys": ["key1"]},
        "storage": {
            "bucket": "bucket",
            "region": "region",
            "access_key": "key",
            "secret_key": "secret",
        },
        "jwt_secret_key": "test-secret-key-for-testing",
    }
    
    config = loader.load_from_dict(config_dict)
    assert config.env == "test"
    assert config.database.host == "localhost"


def test_config_loader_substitute_env_vars():
    """Test ConfigLoader environment variable substitution"""
    loader = ConfigLoader()
    
    # Set test environment variables
    os.environ["TEST_HOST"] = "testhost"
    os.environ["TEST_PORT"] = "5432"
    
    # Test simple substitution
    result = loader._substitute_string("${TEST_HOST}")
    assert result == "testhost"
    
    # Test with default value
    result = loader._substitute_string("${NONEXISTENT:default}")
    assert result == "default"
    
    # Test nested dict substitution
    data = {
        "host": "${TEST_HOST}",
        "port": "${TEST_PORT}",
        "nested": {
            "value": "${TEST_HOST}",
        },
    }
    result = loader._substitute_env_vars(data)
    assert result["host"] == "testhost"
    assert result["port"] == "5432"
    assert result["nested"]["value"] == "testhost"
    
    # Clean up
    del os.environ["TEST_HOST"]
    del os.environ["TEST_PORT"]


def test_config_loader_missing_env_var():
    """Test ConfigLoader raises error for missing environment variable"""
    loader = ConfigLoader()
    
    # Should raise MissingConfigError for missing env var without default
    with pytest.raises(MissingConfigError, match="环境变量未设置"):
        loader._substitute_string("${NONEXISTENT_VAR}")


def test_config_loader_missing_config_file():
    """Test ConfigLoader raises error for missing config file"""
    loader = ConfigLoader(config_dir="nonexistent")
    
    with pytest.raises(MissingConfigError, match="配置文件不存在"):
        loader.load(env="development")

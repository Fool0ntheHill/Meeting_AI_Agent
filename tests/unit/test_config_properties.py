"""Property-based tests for configuration validation.

Feature: meeting-minutes-agent, Property 2 & 8: 配置验证
验证: 需求 1.4, 10.3

属性 2: 对于任何 ASR 提供商实例,如果配置无效,则在调用 transcribe 方法之前应当抛出 ConfigurationError 异常。
属性 8: 对于任何配置类,如果必需的环境变量缺失或格式无效,则在加载配置时应当抛出 ConfigurationError 并包含缺失字段的描述。
"""

import os
import tempfile
from pathlib import Path
from typing import Any, Dict

import pytest
import yaml
from hypothesis import given, strategies as st
from pydantic import ValidationError

from src.config.loader import ConfigLoader
from src.config.models import (
    AppConfig,
    AzureConfig,
    DatabaseConfig,
    GeminiConfig,
    IFlyTekConfig,
    PricingConfig,
    RedisConfig,
    StorageConfig,
    VolcanoConfig,
)
from src.core.exceptions import InvalidConfigError, MissingConfigError


# ============================================================================
# Property 8: 配置验证错误
# ============================================================================


class TestDatabaseConfigValidation:
    """Test DatabaseConfig validation"""
    
    def test_missing_required_host_raises_error(self):
        """Property: Missing required 'host' field should raise ValidationError"""
        with pytest.raises(ValidationError):
            DatabaseConfig(
                port=5432,
                database="testdb",
                username="user",
                password="pass",
            )
    
    def test_missing_required_database_raises_error(self):
        """Property: Missing required 'database' field should raise ValidationError"""
        with pytest.raises(ValidationError):
            DatabaseConfig(
                host="localhost",
                port=5432,
                username="user",
                password="pass",
            )
    
    def test_missing_required_username_raises_error(self):
        """Property: Missing required 'username' field should raise ValidationError"""
        with pytest.raises(ValidationError):
            DatabaseConfig(
                host="localhost",
                port=5432,
                database="testdb",
                password="pass",
            )
    
    def test_missing_required_password_raises_error(self):
        """Property: Missing required 'password' field should raise ValidationError"""
        with pytest.raises(ValidationError):
            DatabaseConfig(
                host="localhost",
                port=5432,
                database="testdb",
                username="user",
            )
    
    @given(
        st.text(min_size=1),
        st.text(min_size=1),
        st.text(min_size=1),
        st.text(min_size=1),
    )
    def test_valid_database_config_accepted(
        self, host: str, database: str, username: str, password: str
    ):
        """Property: Valid DatabaseConfig should be accepted"""
        config = DatabaseConfig(
            host=host,
            database=database,
            username=username,
            password=password,
        )
        assert config.host == host
        assert config.database == database


class TestRedisConfigValidation:
    """Test RedisConfig validation"""
    
    def test_missing_required_host_raises_error(self):
        """Property: Missing required 'host' field should raise ValidationError"""
        with pytest.raises(ValidationError):
            RedisConfig(port=6379)
    
    @given(st.text(min_size=1))
    def test_valid_redis_config_accepted(self, host: str):
        """Property: Valid RedisConfig should be accepted"""
        config = RedisConfig(host=host)
        assert config.host == host
        assert config.port == 6379  # default value


class TestVolcanoConfigValidation:
    """Test VolcanoConfig validation"""
    
    def test_empty_access_key_raises_error(self):
        """Property: Empty access_key should raise ValueError"""
        with pytest.raises(ValueError, match="字段不能为空"):
            VolcanoConfig(
                access_key="",
                secret_key="secret",
                app_id="app123",
                cluster_id="cluster123",
                tos_bucket="bucket",
            )
    
    def test_whitespace_access_key_raises_error(self):
        """Property: Whitespace-only access_key should raise ValueError"""
        with pytest.raises(ValueError, match="字段不能为空"):
            VolcanoConfig(
                access_key="   ",
                secret_key="secret",
                app_id="app123",
                cluster_id="cluster123",
                tos_bucket="bucket",
            )
    
    def test_empty_secret_key_raises_error(self):
        """Property: Empty secret_key should raise ValueError"""
        with pytest.raises(ValueError, match="字段不能为空"):
            VolcanoConfig(
                access_key="access",
                secret_key="",
                app_id="app123",
                cluster_id="cluster123",
                tos_bucket="bucket",
            )
    
    def test_empty_app_id_raises_error(self):
        """Property: Empty app_id should raise ValueError"""
        with pytest.raises(ValueError, match="字段不能为空"):
            VolcanoConfig(
                access_key="access",
                secret_key="secret",
                app_id="",
                cluster_id="cluster123",
                tos_bucket="bucket",
            )
    
    @given(
        st.text(min_size=1).filter(lambda x: x.strip()),
        st.text(min_size=1).filter(lambda x: x.strip()),
        st.text(min_size=1).filter(lambda x: x.strip()),
    )
    def test_valid_volcano_config_accepted(
        self, access_key: str, secret_key: str, app_id: str
    ):
        """Property: Valid VolcanoConfig should be accepted"""
        config = VolcanoConfig(
            access_key=access_key,
            secret_key=secret_key,
            app_id=app_id,
            cluster_id="cluster123",
            tos_bucket="bucket",
        )
        assert config.access_key == access_key
        assert config.secret_key == secret_key
        assert config.app_id == app_id


class TestAzureConfigValidation:
    """Test AzureConfig validation"""
    
    def test_empty_subscription_keys_raises_error(self):
        """Property: Empty subscription_keys list should raise ValueError"""
        with pytest.raises(ValueError, match="至少需要一个订阅密钥"):
            AzureConfig(subscription_keys=[])
    
    def test_subscription_keys_with_empty_string_raises_error(self):
        """Property: subscription_keys containing empty string should raise ValueError"""
        with pytest.raises(ValueError, match="订阅密钥不能为空"):
            AzureConfig(subscription_keys=["key1", "", "key3"])
    
    def test_subscription_keys_with_whitespace_raises_error(self):
        """Property: subscription_keys containing whitespace-only string should raise ValueError"""
        with pytest.raises(ValueError, match="订阅密钥不能为空"):
            AzureConfig(subscription_keys=["key1", "   ", "key3"])
    
    @given(st.lists(st.text(min_size=1).filter(lambda x: x.strip()), min_size=1))
    def test_valid_azure_config_accepted(self, keys: list):
        """Property: Valid AzureConfig should be accepted"""
        config = AzureConfig(subscription_keys=keys)
        assert config.subscription_keys == keys


class TestIFlyTekConfigValidation:
    """Test IFlyTekConfig validation"""
    
    def test_empty_app_id_raises_error(self):
        """Property: Empty app_id should raise ValueError"""
        with pytest.raises(ValueError, match="字段不能为空"):
            IFlyTekConfig(
                app_id="",
                api_key="key",
                api_secret="secret",
                group_id="group123",
            )
    
    def test_empty_api_key_raises_error(self):
        """Property: Empty api_key should raise ValueError"""
        with pytest.raises(ValueError, match="字段不能为空"):
            IFlyTekConfig(
                app_id="app123",
                api_key="",
                api_secret="secret",
                group_id="group123",
            )
    
    def test_empty_api_secret_raises_error(self):
        """Property: Empty api_secret should raise ValueError"""
        with pytest.raises(ValueError, match="字段不能为空"):
            IFlyTekConfig(
                app_id="app123",
                api_key="key",
                api_secret="",
                group_id="group123",
            )


class TestGeminiConfigValidation:
    """Test GeminiConfig validation"""
    
    def test_empty_api_keys_raises_error(self):
        """Property: Empty api_keys list should raise ValueError"""
        with pytest.raises(ValueError, match="至少需要一个 API 密钥"):
            GeminiConfig(api_keys=[])
    
    def test_api_keys_with_empty_string_raises_error(self):
        """Property: api_keys containing empty string should raise ValueError"""
        with pytest.raises(ValueError, match="API 密钥不能为空"):
            GeminiConfig(api_keys=["key1", "", "key3"])
    
    @given(st.floats(min_value=-1, max_value=-0.1))
    def test_negative_temperature_raises_error(self, temperature: float):
        """Property: Negative temperature should raise ValidationError"""
        with pytest.raises(ValidationError):
            GeminiConfig(api_keys=["key1"], temperature=temperature)
    
    @given(st.floats(min_value=2.1, max_value=10))
    def test_temperature_over_2_raises_error(self, temperature: float):
        """Property: Temperature > 2 should raise ValidationError"""
        with pytest.raises(ValidationError):
            GeminiConfig(api_keys=["key1"], temperature=temperature)


class TestPricingConfigValidation:
    """Test PricingConfig validation"""
    
    @given(st.floats(max_value=0))
    def test_non_positive_volcano_asr_price_raises_error(self, price: float):
        """Property: Non-positive volcano_asr_per_second should raise ValueError"""
        with pytest.raises(ValueError, match="价格必须大于 0"):
            PricingConfig(volcano_asr_per_second=price)
    
    @given(st.floats(max_value=0))
    def test_non_positive_azure_asr_price_raises_error(self, price: float):
        """Property: Non-positive azure_asr_per_second should raise ValueError"""
        with pytest.raises(ValueError, match="价格必须大于 0"):
            PricingConfig(azure_asr_per_second=price)
    
    @given(st.floats(max_value=0))
    def test_non_positive_voiceprint_price_raises_error(self, price: float):
        """Property: Non-positive iflytek_voiceprint_per_second should raise ValueError"""
        with pytest.raises(ValueError, match="价格必须大于 0"):
            PricingConfig(iflytek_voiceprint_per_second=price)
    
    @given(st.floats(min_value=0.00001, max_value=1.0))
    def test_valid_pricing_config_accepted(self, price: float):
        """Property: Valid positive prices should be accepted"""
        config = PricingConfig(
            volcano_asr_per_second=price,
            azure_asr_per_second=price,
            iflytek_voiceprint_per_second=price,
            gemini_flash_per_token=price,
            gemini_pro_per_token=price,
        )
        assert config.volcano_asr_per_second == price


class TestAppConfigValidation:
    """Test AppConfig validation"""
    
    def test_invalid_env_raises_error(self):
        """Property: Invalid env value should raise ValueError"""
        with pytest.raises(ValueError, match="env 必须是"):
            AppConfig(
                env="invalid_env",
                jwt_secret_key="secret",
                database=DatabaseConfig(
                    host="localhost",
                    database="db",
                    username="user",
                    password="pass",
                ),
                redis=RedisConfig(host="localhost"),
                volcano=VolcanoConfig(
                    access_key="key",
                    secret_key="secret",
                    app_id="app",
                    cluster_id="cluster",
                    tos_bucket="bucket",
                ),
                azure=AzureConfig(subscription_keys=["key"]),
                iflytek=IFlyTekConfig(
                    app_id="app",
                    api_key="key",
                    api_secret="secret",
                    group_id="group",
                ),
                gemini=GeminiConfig(api_keys=["key"]),
                storage=StorageConfig(
                    bucket="bucket",
                    region="region",
                    access_key="key",
                    secret_key="secret",
                ),
            )
    
    def test_invalid_asr_provider_raises_error(self):
        """Property: Invalid default_asr_provider should raise ValueError"""
        with pytest.raises(ValueError, match="default_asr_provider 必须是"):
            AppConfig(
                env="development",
                jwt_secret_key="secret",
                default_asr_provider="invalid_provider",
                database=DatabaseConfig(
                    host="localhost",
                    database="db",
                    username="user",
                    password="pass",
                ),
                redis=RedisConfig(host="localhost"),
                volcano=VolcanoConfig(
                    access_key="key",
                    secret_key="secret",
                    app_id="app",
                    cluster_id="cluster",
                    tos_bucket="bucket",
                ),
                azure=AzureConfig(subscription_keys=["key"]),
                iflytek=IFlyTekConfig(
                    app_id="app",
                    api_key="key",
                    api_secret="secret",
                    group_id="group",
                ),
                gemini=GeminiConfig(api_keys=["key"]),
                storage=StorageConfig(
                    bucket="bucket",
                    region="region",
                    access_key="key",
                    secret_key="secret",
                ),
            )
    
    @given(st.sampled_from(["development", "test", "production"]))
    def test_valid_env_accepted(self, env: str):
        """Property: Valid env values should be accepted"""
        config = AppConfig(
            env=env,
            jwt_secret_key="secret",
            database=DatabaseConfig(
                host="localhost",
                database="db",
                username="user",
                password="pass",
            ),
            redis=RedisConfig(host="localhost"),
            volcano=VolcanoConfig(
                access_key="key",
                secret_key="secret",
                app_id="app",
                cluster_id="cluster",
                tos_bucket="bucket",
            ),
            azure=AzureConfig(subscription_keys=["key"]),
            iflytek=IFlyTekConfig(
                app_id="app",
                api_key="key",
                api_secret="secret",
                group_id="group",
            ),
            gemini=GeminiConfig(api_keys=["key"]),
            storage=StorageConfig(
                bucket="bucket",
                region="region",
                access_key="key",
                secret_key="secret",
            ),
        )
        assert config.env == env


class TestConfigLoaderValidation:
    """Test ConfigLoader validation and error handling"""
    
    def test_missing_config_file_raises_error(self):
        """Property: Missing config file should raise MissingConfigError"""
        with tempfile.TemporaryDirectory() as tmpdir:
            loader = ConfigLoader(config_dir=tmpdir)
            with pytest.raises(MissingConfigError, match="配置文件不存在"):
                loader.load(env="nonexistent")
    
    def test_invalid_yaml_raises_error(self):
        """Property: Invalid YAML format should raise InvalidConfigError"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_file = Path(tmpdir) / "test.yaml"
            config_file.write_text("invalid: yaml: content: [", encoding="utf-8")
            
            loader = ConfigLoader(config_dir=tmpdir)
            with pytest.raises(InvalidConfigError, match="配置文件格式错误"):
                loader.load(env="test")
    
    def test_missing_required_field_raises_error(self):
        """Property: Missing required field should raise InvalidConfigError"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_file = Path(tmpdir) / "test.yaml"
            # Missing 'database' field
            config_data = {
                "env": "test",
                "jwt_secret_key": "secret",
                "redis": {"host": "localhost"},
            }
            config_file.write_text(yaml.dump(config_data), encoding="utf-8")
            
            loader = ConfigLoader(config_dir=tmpdir)
            with pytest.raises(InvalidConfigError, match="配置验证失败"):
                loader.load(env="test")
    
    def test_missing_env_var_without_default_raises_error(self):
        """Property: Missing env var without default should raise MissingConfigError"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_file = Path(tmpdir) / "test.yaml"
            config_data = {
                "env": "test",
                "jwt_secret_key": "${MISSING_VAR}",
                "database": {
                    "host": "localhost",
                    "database": "db",
                    "username": "user",
                    "password": "pass",
                },
            }
            config_file.write_text(yaml.dump(config_data), encoding="utf-8")
            
            # Ensure the env var doesn't exist
            if "MISSING_VAR" in os.environ:
                del os.environ["MISSING_VAR"]
            
            loader = ConfigLoader(config_dir=tmpdir)
            with pytest.raises(MissingConfigError, match="环境变量未设置"):
                loader.load(env="test")
    
    def test_env_var_with_default_uses_default(self):
        """Property: Missing env var with default should use default value"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_file = Path(tmpdir) / "test.yaml"
            config_data = {
                "env": "test",
                "jwt_secret_key": "${MISSING_VAR:default_secret}",
                "database": {
                    "host": "localhost",
                    "database": "db",
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
                "azure": {"subscription_keys": ["key"]},
                "iflytek": {
                    "app_id": "app",
                    "api_key": "key",
                    "api_secret": "secret",
                    "group_id": "group",
                },
                "gemini": {"api_keys": ["key"]},
                "storage": {
                    "bucket": "bucket",
                    "region": "region",
                    "access_key": "key",
                    "secret_key": "secret",
                },
            }
            config_file.write_text(yaml.dump(config_data), encoding="utf-8")
            
            # Ensure the env var doesn't exist
            if "MISSING_VAR" in os.environ:
                del os.environ["MISSING_VAR"]
            
            loader = ConfigLoader(config_dir=tmpdir)
            config = loader.load(env="test")
            assert config.jwt_secret_key == "default_secret"


# ============================================================================
# Run tests
# ============================================================================


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

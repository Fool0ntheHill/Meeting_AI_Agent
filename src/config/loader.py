"""Configuration loader with YAML support and environment variable substitution."""

import os
import re
from pathlib import Path
from typing import Any, Dict, Optional

import yaml

from src.core.exceptions import ConfigurationError, InvalidConfigError, MissingConfigError
from src.config.models import AppConfig


class ConfigLoader:
    """配置加载器"""

    def __init__(self, config_dir: str = "config"):
        """
        初始化配置加载器

        Args:
            config_dir: 配置文件目录
        """
        self.config_dir = Path(config_dir)
        self._env_pattern = re.compile(r"\$\{([^}]+)\}")

    def load(self, env: Optional[str] = None) -> AppConfig:
        """
        加载配置

        Args:
            env: 环境名称(development/test/production),如果为 None 则从环境变量读取

        Returns:
            AppConfig: 应用配置

        Raises:
            MissingConfigError: 配置文件不存在
            InvalidConfigError: 配置无效
        """
        # 确定环境
        if env is None:
            env = os.getenv("APP_ENV", "development")

        # 加载配置文件
        config_file = self.config_dir / f"{env}.yaml"
        if not config_file.exists():
            raise MissingConfigError(
                f"配置文件不存在: {config_file}",
                details={"config_file": str(config_file), "env": env},
            )

        try:
            with open(config_file, "r", encoding="utf-8") as f:
                config_data = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise InvalidConfigError(
                f"配置文件格式错误: {e}",
                details={"config_file": str(config_file), "error": str(e)},
            )

        # 替换环境变量
        config_data = self._substitute_env_vars(config_data)

        # 验证并创建配置对象
        try:
            return AppConfig(**config_data)
        except Exception as e:
            raise InvalidConfigError(
                f"配置验证失败: {e}",
                details={"config_file": str(config_file), "error": str(e)},
            )

    def _substitute_env_vars(self, data: Any) -> Any:
        """
        递归替换环境变量

        支持格式: ${VAR_NAME} 或 ${VAR_NAME:default_value}

        Args:
            data: 配置数据

        Returns:
            Any: 替换后的数据
        """
        if isinstance(data, dict):
            return {key: self._substitute_env_vars(value) for key, value in data.items()}
        elif isinstance(data, list):
            return [self._substitute_env_vars(item) for item in data]
        elif isinstance(data, str):
            return self._substitute_string(data)
        else:
            return data

    def _substitute_string(self, value: str) -> str:
        """
        替换字符串中的环境变量

        Args:
            value: 原始字符串

        Returns:
            str: 替换后的字符串
        """

        def replace_match(match: re.Match) -> str:
            var_expr = match.group(1)
            # 支持默认值: ${VAR:default}
            if ":" in var_expr:
                var_name, default = var_expr.split(":", 1)
                return os.getenv(var_name.strip(), default.strip())
            else:
                var_name = var_expr.strip()
                env_value = os.getenv(var_name)
                if env_value is None:
                    raise MissingConfigError(
                        f"环境变量未设置: {var_name}",
                        details={"variable": var_name},
                    )
                return env_value

        return self._env_pattern.sub(replace_match, value)

    def load_from_dict(self, config_dict: Dict[str, Any]) -> AppConfig:
        """
        从字典加载配置(用于测试)

        Args:
            config_dict: 配置字典

        Returns:
            AppConfig: 应用配置

        Raises:
            InvalidConfigError: 配置无效
        """
        try:
            return AppConfig(**config_dict)
        except Exception as e:
            raise InvalidConfigError(
                f"配置验证失败: {e}",
                details={"error": str(e)},
            )


# Global config instance
_config_instance: Optional[AppConfig] = None


def get_config(env: Optional[str] = None) -> AppConfig:
    """
    获取全局配置实例(单例模式)
    
    Args:
        env: 环境名称(development/test/production),如果为 None 则从环境变量读取
        
    Returns:
        AppConfig: 应用配置
    """
    global _config_instance
    
    if _config_instance is None:
        loader = ConfigLoader()
        _config_instance = loader.load(env)
    
    return _config_instance


def reset_config():
    """重置全局配置实例(用于测试)"""
    global _config_instance
    _config_instance = None

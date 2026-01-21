"""Configuration data models."""

from typing import Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


class DatabaseConfig(BaseModel):
    """数据库配置"""

    host: str = Field(..., description="数据库主机")
    port: int = Field(default=5432, description="数据库端口")
    database: str = Field(..., description="数据库名称")
    username: str = Field(..., description="用户名")
    password: str = Field(..., description="密码")
    pool_size: int = Field(default=10, description="连接池大小")
    max_overflow: int = Field(default=20, description="最大溢出连接数")
    echo: bool = Field(default=False, description="是否打印 SQL 语句")

    @property
    def connection_string(self) -> str:
        """生成数据库连接字符串"""
        return f"postgresql+asyncpg://{self.username}:{self.password}@{self.host}:{self.port}/{self.database}"


class RedisConfig(BaseModel):
    """Redis 配置"""

    host: str = Field(..., description="Redis 主机")
    port: int = Field(default=6379, description="Redis 端口")
    password: Optional[str] = Field(None, description="密码")
    db: int = Field(default=0, description="数据库编号")
    max_connections: int = Field(default=50, description="最大连接数")
    decode_responses: bool = Field(default=True, description="是否解码响应")

    @property
    def connection_string(self) -> str:
        """生成 Redis 连接字符串"""
        if self.password:
            return f"redis://:{self.password}@{self.host}:{self.port}/{self.db}"
        return f"redis://{self.host}:{self.port}/{self.db}"


class VolcanoConfig(BaseModel):
    """火山引擎配置"""

    access_key: str = Field(..., description="Access Key")
    secret_key: str = Field(..., description="Secret Key")
    app_id: str = Field(..., description="应用 ID")
    cluster_id: str = Field(..., description="集群 ID")
    tos_bucket: str = Field(..., description="TOS 存储桶名称")
    tos_region: str = Field(default="cn-beijing", description="TOS 区域")
    api_endpoint: str = Field(
        default="https://openspeech.bytedance.com/api/v1/asr",
        description="ASR API 端点",
    )
    boosting_table_id: Optional[str] = Field(None, description="全局热词库 ID (BoostingTableID)")
    max_retries: int = Field(default=3, description="最大重试次数")
    timeout: int = Field(default=300, description="超时时间(秒)")

    @field_validator("access_key", "secret_key", "app_id")
    @classmethod
    def validate_not_empty(cls, v: str) -> str:
        """验证字段非空"""
        if not v or not v.strip():
            raise ValueError("字段不能为空")
        return v


class AzureConfig(BaseModel):
    """Azure 配置"""

    subscription_keys: List[str] = Field(..., description="订阅密钥列表(支持多密钥轮换)")
    region: str = Field(default="eastus", description="区域")
    endpoint: Optional[str] = Field(None, description="自定义端点")
    max_retries: int = Field(default=3, description="最大重试次数")
    timeout: int = Field(default=300, description="超时时间(秒)")

    @field_validator("subscription_keys")
    @classmethod
    def validate_keys(cls, v: List[str]) -> List[str]:
        """验证密钥列表"""
        if not v:
            raise ValueError("至少需要一个订阅密钥")
        if any(not key.strip() for key in v):
            raise ValueError("订阅密钥不能为空")
        return v


class IFlyTekConfig(BaseModel):
    """科大讯飞配置"""

    app_id: str = Field(..., description="应用 ID")
    api_key: str = Field(..., description="API Key")
    api_secret: str = Field(..., description="API Secret")
    api_endpoint: str = Field(
        default="https://api.xfyun.cn/v1/private/sf8e6aca1",
        description="声纹识别 API 端点",
    )
    group_id: str = Field(..., description="声纹库 ID")
    max_retries: int = Field(default=3, description="最大重试次数")
    timeout: int = Field(default=30, description="超时时间(秒)")

    @field_validator("app_id", "api_key", "api_secret")
    @classmethod
    def validate_not_empty(cls, v: str) -> str:
        """验证字段非空"""
        if not v or not v.strip():
            raise ValueError("字段不能为空")
        return v


class GeminiConfig(BaseModel):
    """Gemini 配置"""

    api_keys: List[str] = Field(..., description="API 密钥列表(支持多密钥轮换)")
    model: str = Field(default="gemini-2.0-flash-exp", description="模型名称")
    max_tokens: int = Field(default=8192, description="最大 Token 数")
    temperature: float = Field(default=0.7, ge=0, le=2, description="温度参数")
    max_retries: int = Field(default=3, description="最大重试次数")
    timeout: int = Field(default=120, description="超时时间(秒)")

    @field_validator("api_keys")
    @classmethod
    def validate_keys(cls, v: List[str]) -> List[str]:
        """验证密钥列表"""
        if not v:
            raise ValueError("至少需要一个 API 密钥")
        if any(not key.strip() for key in v):
            raise ValueError("API 密钥不能为空")
        return v


class LogConfig(BaseModel):
    """日志配置"""

    level: str = Field(default="INFO", description="日志级别")
    format: str = Field(default="json", description="日志格式(json/text)")
    output: str = Field(default="stdout", description="输出目标(stdout/file)")
    file_path: Optional[str] = Field(None, description="日志文件路径")
    max_bytes: int = Field(default=10485760, description="单个日志文件最大字节数(10MB)")
    backup_count: int = Field(default=5, description="保留的日志文件数量")
    filter_sensitive: bool = Field(default=True, description="是否过滤敏感信息")


class QueueConfig(BaseModel):
    """消息队列配置"""

    backend: str = Field(default="redis", description="队列后端(redis/rabbitmq)")
    redis_url: Optional[str] = Field(None, description="Redis URL")
    rabbitmq_url: Optional[str] = Field(None, description="RabbitMQ URL")
    queue_name: str = Field(default="meeting_tasks", description="队列名称")
    max_priority: int = Field(default=10, description="最大优先级")


class StorageConfig(BaseModel):
    """存储配置"""

    provider: str = Field(default="tos", description="存储提供商(tos/s3)")
    bucket: str = Field(..., description="存储桶名称")
    region: str = Field(..., description="区域")
    access_key: str = Field(..., description="Access Key")
    secret_key: str = Field(..., description="Secret Key")
    endpoint: Optional[str] = Field(None, description="自定义端点")
    temp_file_ttl: int = Field(default=3600, description="临时文件 TTL(秒)")


class PricingConfig(BaseModel):
    """价格配置"""

    # ASR 价格 (元/秒)
    volcano_asr_per_second: float = Field(default=0.00005, description="火山引擎 ASR 价格(元/秒)")
    azure_asr_per_second: float = Field(default=0.00006, description="Azure ASR 价格(元/秒)")
    
    # 声纹识别价格 (元/次) - 10万次200元
    iflytek_voiceprint_per_call: float = Field(default=0.002, description="讯飞声纹识别价格(元/次)")
    
    # LLM 价格 (元/Token)
    gemini_flash_per_token: float = Field(default=0.00002, description="Gemini Flash 价格(元/Token)")
    gemini_pro_per_token: float = Field(default=0.00005, description="Gemini Pro 价格(元/Token)")
    
    # 估算参数
    estimated_tokens_per_second: int = Field(default=10, description="每秒音频估算产生的 Token 数")
    estimated_speakers_count: int = Field(default=3, description="平均说话人数量")
    estimated_sample_duration: float = Field(default=5.0, description="每个说话人样本时长(秒)")

    @field_validator("volcano_asr_per_second", "azure_asr_per_second", "iflytek_voiceprint_per_call", 
                     "gemini_flash_per_token", "gemini_pro_per_token")
    @classmethod
    def validate_positive(cls, v: float) -> float:
        """验证价格为正数"""
        if v <= 0:
            raise ValueError("价格必须大于 0")
        return v


class AppConfig(BaseModel):
    """应用配置"""

    env: str = Field(default="development", description="环境(development/test/production)")
    debug: bool = Field(default=False, description="调试模式")
    api_host: str = Field(default="0.0.0.0", description="API 主机")
    api_port: int = Field(default=8000, description="API 端口")
    worker_count: int = Field(default=4, description="Worker 数量")
    
    # JWT 配置
    jwt_secret_key: str = Field(..., description="JWT 密钥")
    jwt_algorithm: str = Field(default="HS256", description="JWT 算法")
    jwt_expire_hours: int = Field(default=24, description="JWT 过期时间(小时)")
    
    # 子配置
    database: DatabaseConfig
    redis: RedisConfig
    volcano: VolcanoConfig
    azure: AzureConfig
    iflytek: IFlyTekConfig
    gemini: GeminiConfig
    log: LogConfig = Field(default_factory=LogConfig)
    queue: QueueConfig = Field(default_factory=QueueConfig)
    storage: StorageConfig
    pricing: PricingConfig = Field(default_factory=PricingConfig)
    
    # 业务配置
    audio_retention_days: int = Field(default=7, description="音频默认保留天数")
    audio_retention_max_days: int = Field(default=90, description="音频最大保留天数")
    enable_speaker_recognition: bool = Field(default=True, description="是否启用说话人识别")
    default_asr_provider: str = Field(default="volcano", description="默认 ASR 提供商")
    
    @field_validator("env")
    @classmethod
    def validate_env(cls, v: str) -> str:
        """验证环境"""
        allowed = ["development", "test", "production"]
        if v not in allowed:
            raise ValueError(f"env 必须是 {allowed} 之一")
        return v
    
    @field_validator("default_asr_provider")
    @classmethod
    def validate_asr_provider(cls, v: str) -> str:
        """验证 ASR 提供商"""
        allowed = ["volcano", "azure"]
        if v not in allowed:
            raise ValueError(f"default_asr_provider 必须是 {allowed} 之一")
        return v

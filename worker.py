"""
Worker 进程入口

从队列拉取任务并执行处理。
"""

import sys
import logging
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent))

from src.config.loader import get_config
from src.queue.manager import QueueManager, QueueBackend
from src.queue.worker import TaskWorker
from src.services.pipeline import PipelineService
from src.services.transcription import TranscriptionService
from src.services.speaker_recognition import SpeakerRecognitionService
from src.services.correction import CorrectionService
from src.services.artifact_generation import ArtifactGenerationService
from src.providers.volcano_asr import VolcanoASR
from src.providers.azure_asr import AzureASR
from src.providers.iflytek_voiceprint import IFlyTekVoiceprint
from src.providers.gemini_llm import GeminiLLM
from src.utils.storage import StorageClient
from src.utils.audio import AudioProcessor
from src.database.session import init_db
from src.utils.logger import setup_logger

# 设置日志
setup_logger()
logger = logging.getLogger(__name__)


def _build_database_url(config) -> str:
    db = config.database
    if db.host and db.username and db.password and db.database:
        return f"postgresql://{db.username}:{db.password}@{db.host}:{db.port}/{db.database}"
    if db.database:
        return f"sqlite:///./{db.database}"
    return "sqlite:///./meeting_agent.db"


def create_worker() -> TaskWorker:
    """
    创建 Worker 实例
    
    Returns:
        TaskWorker 实例
    """
    # 加载配置
    config = get_config()
    
    # 初始化数据库
    database_url = _build_database_url(config)
    init_db(database_url, echo=config.database.echo)
    
    # 创建提供商
    volcano_asr = VolcanoASR(config.volcano)
    azure_asr = AzureASR(config.azure)
    iflytek_voiceprint = IFlyTekVoiceprint(config.iflytek)
    gemini_llm = GeminiLLM(config.gemini)
    
    # 创建工具
    storage_client = StorageClient(
        bucket=config.storage.bucket,
        region=config.storage.region,
        access_key=config.storage.access_key,
        secret_key=config.storage.secret_key,
    )
    audio_processor = AudioProcessor()
    
    # 创建服务
    transcription_service = TranscriptionService(
        primary_asr=volcano_asr,
        fallback_asr=azure_asr,
        storage_client=storage_client,
        audio_processor=audio_processor,
    )
    
    speaker_recognition_service = SpeakerRecognitionService(
        voiceprint_provider=iflytek_voiceprint,
        audio_processor=audio_processor,
        storage_client=storage_client,
    )
    
    correction_service = CorrectionService()
    
    # 创建 template repository (使用数据库会话)
    from src.database.session import session_scope
    from src.database.repositories import PromptTemplateRepository, TranscriptRepository, ArtifactRepository
    
    # 注意：这里我们需要为每次使用创建新的 session
    # 但为了简化，我们先传 None，让 artifact_generation_service 在需要时创建
    artifact_generation_service = ArtifactGenerationService(
        llm_provider=gemini_llm,
        template_repo=None,  # 将在 pipeline 中通过 session 传递
        artifact_repo=None,  # 将在 TaskWorker 中通过 session 传递
    )
    
    # 创建 transcript repository (使用 session_scope)
    # 注意：这里我们传递 None，在 pipeline 中使用 session_scope 创建
    transcript_repo = None  # 将在 TaskWorker 中通过 session 传递
    
    pipeline_service = PipelineService(
        transcription_service=transcription_service,
        speaker_recognition_service=speaker_recognition_service,
        correction_service=correction_service,
        artifact_generation_service=artifact_generation_service,
        transcript_repo=transcript_repo,
    )
    
    # 创建队列管理器
    # 优先使用 Redis,如果未配置则使用内存队列(仅用于测试)
    redis_url = getattr(config, "redis_url", None) or "redis://localhost:6379/0"
    
    try:
        queue_manager = QueueManager(
            backend=QueueBackend.REDIS,
            redis_url=redis_url,
        )
        logger.info(f"Using Redis queue: {redis_url}")
    except Exception as e:
        logger.warning(f"Failed to connect to Redis: {e}")
        logger.warning("Worker requires Redis to be running. Please start Redis or configure redis_url.")
        sys.exit(1)
    
    # 创建 Worker
    worker = TaskWorker(
        queue_manager=queue_manager,
        pipeline_service=pipeline_service,
    )
    
    return worker


def main():
    """主函数"""
    try:
        logger.info("=" * 60)
        logger.info("Starting Meeting Agent Worker")
        logger.info("=" * 60)
        
        worker = create_worker()
        worker.start()
    
    except KeyboardInterrupt:
        logger.info("Worker interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Worker failed to start: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()

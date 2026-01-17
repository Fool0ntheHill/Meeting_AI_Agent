"""Utility modules for audio processing, storage, logging, and cost tracking."""

from src.utils.cost import CostTracker
from src.utils.storage import StorageClient

# Audio and logger imports are optional (require external dependencies)
try:
    from src.utils.audio import AudioProcessor
except ImportError:
    AudioProcessor = None  # type: ignore

try:
    from src.utils.logger import setup_logger
except ImportError:
    setup_logger = None  # type: ignore

__all__ = [
    "AudioProcessor",
    "StorageClient",
    "CostTracker",
    "setup_logger",
]

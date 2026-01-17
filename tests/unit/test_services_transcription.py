"""Unit tests for transcription service."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.core.exceptions import ASRError, AudioFormatError
from src.core.models import ASRLanguage, HotwordSet, Segment, TranscriptionResult
from src.services.transcription import TranscriptionService


@pytest.fixture
def mock_primary_asr():
    """Mock primary ASR provider"""
    asr = MagicMock()
    asr.get_provider_name.return_value = "volcano"
    return asr


@pytest.fixture
def mock_fallback_asr():
    """Mock fallback ASR provider"""
    asr = MagicMock()
    asr.get_provider_name.return_value = "azure"
    return asr


@pytest.fixture
def mock_storage():
    """Mock storage client"""
    storage = MagicMock()
    storage.upload_file = AsyncMock(return_value="https://tos.example.com/audio/test.wav")
    storage.generate_presigned_url = AsyncMock(
        return_value="https://tos.example.com/audio/test.wav?X-Tos-Signature=xxx"
    )
    return storage


@pytest.fixture
def mock_audio_processor():
    """Mock audio processor"""
    processor = MagicMock()
    processor.concatenate_audio = AsyncMock(
        return_value=("/tmp/concatenated.wav", [0.0, 10.0, 20.0])
    )
    processor.get_duration = MagicMock(return_value=30.0)
    return processor


@pytest.fixture
def transcription_service(mock_primary_asr, mock_fallback_asr, mock_storage, mock_audio_processor):
    """Transcription service fixture"""
    return TranscriptionService(
        primary_asr=mock_primary_asr,
        fallback_asr=mock_fallback_asr,
        storage_client=mock_storage,
        audio_processor=mock_audio_processor,
    )


@pytest.fixture
def sample_transcript():
    """Sample transcription result"""
    return TranscriptionResult(
        segments=[
            Segment(
                text="Hello world",
                start_time=0.0,
                end_time=2.0,
                speaker="Speaker 0",
                confidence=0.95,
            )
        ],
        full_text="Hello world",
        duration=2.0,
        language="zh-CN",
        provider="volcano",
    )


class TestTranscriptionService:
    """TranscriptionService 测试类"""

    @pytest.mark.asyncio
    async def test_transcribe_single_file_success(
        self, transcription_service, mock_primary_asr, sample_transcript
    ):
        """测试单文件转写成功"""
        mock_primary_asr.transcribe = AsyncMock(return_value=sample_transcript)

        result, audio_url, local_path = await transcription_service.transcribe(
            audio_files=["audio1.wav"],
            asr_language=ASRLanguage.ZH_CN,
        )

        assert result == sample_transcript
        assert audio_url == "https://tos.example.com/audio/test.wav?X-Tos-Signature=xxx"
        assert local_path == "audio1.wav"
        mock_primary_asr.transcribe.assert_called_once()

    @pytest.mark.asyncio
    async def test_transcribe_multiple_files(
        self, transcription_service, mock_primary_asr, mock_audio_processor, sample_transcript
    ):
        """测试多文件拼接转写"""
        mock_primary_asr.transcribe = AsyncMock(return_value=sample_transcript)

        result, audio_url, local_path = await transcription_service.transcribe(
            audio_files=["audio1.wav", "audio2.wav", "audio3.wav"],
            file_order=[0, 1, 2],
            asr_language=ASRLanguage.ZH_EN,
        )

        assert result == sample_transcript
        assert audio_url == "https://tos.example.com/audio/test.wav?X-Tos-Signature=xxx"
        assert local_path == "/tmp/concatenated.wav"
        mock_audio_processor.concatenate_audio.assert_called_once()

    @pytest.mark.asyncio
    async def test_transcribe_with_custom_file_order(
        self, transcription_service, mock_primary_asr, mock_audio_processor, sample_transcript
    ):
        """测试自定义文件顺序"""
        mock_primary_asr.transcribe = AsyncMock(return_value=sample_transcript)

        result, audio_url, local_path = await transcription_service.transcribe(
            audio_files=["audio1.wav", "audio2.wav", "audio3.wav"],
            file_order=[2, 0, 1],  # 自定义顺序
            asr_language=ASRLanguage.ZH_CN,
        )

        # 验证文件按指定顺序传递
        call_args = mock_audio_processor.concatenate_audio.call_args[0][0]
        assert call_args == ["audio3.wav", "audio1.wav", "audio2.wav"]

    @pytest.mark.asyncio
    async def test_transcribe_fallback_on_primary_failure(
        self, transcription_service, mock_primary_asr, mock_fallback_asr, sample_transcript
    ):
        """测试主 ASR 失败时降级到备用 ASR"""
        mock_primary_asr.transcribe = AsyncMock(
            side_effect=ASRError("Primary ASR failed", provider="volcano")
        )
        mock_fallback_asr.transcribe = AsyncMock(return_value=sample_transcript)

        result, audio_url, local_path = await transcription_service.transcribe(
            audio_files=["audio1.wav"],
            asr_language=ASRLanguage.ZH_CN,
        )

        assert result == sample_transcript
        assert audio_url == "https://tos.example.com/audio/test.wav?X-Tos-Signature=xxx"
        assert local_path == "audio1.wav"
        mock_primary_asr.transcribe.assert_called_once()
        mock_fallback_asr.transcribe.assert_called_once()

    @pytest.mark.asyncio
    async def test_transcribe_with_hotword_set(
        self, transcription_service, mock_primary_asr, sample_transcript
    ):
        """测试使用热词集转写"""
        mock_primary_asr.transcribe = AsyncMock(return_value=sample_transcript)

        hotword_set = HotwordSet(
            hotword_set_id="hs_001",
            name="技术术语",
            provider="volcano",
            provider_resource_id="lib_tech_001",
            scope="global",
            asr_language=ASRLanguage.ZH_CN,
        )

        result, audio_url, local_path = await transcription_service.transcribe(
            audio_files=["audio1.wav"],
            asr_language=ASRLanguage.ZH_CN,
            hotword_set=hotword_set,
        )

        assert result == sample_transcript
        assert audio_url == "https://tos.example.com/audio/test.wav?X-Tos-Signature=xxx"
        assert local_path == "audio1.wav"
        # 验证热词集被传递
        call_kwargs = mock_primary_asr.transcribe.call_args[1]
        assert call_kwargs["hotword_set"] == hotword_set

    @pytest.mark.asyncio
    async def test_transcribe_both_asr_fail(
        self, transcription_service, mock_primary_asr, mock_fallback_asr
    ):
        """测试主备 ASR 都失败"""
        mock_primary_asr.transcribe = AsyncMock(
            side_effect=ASRError("Primary failed", provider="volcano")
        )
        mock_fallback_asr.transcribe = AsyncMock(
            side_effect=ASRError("Fallback failed", provider="azure")
        )

        with pytest.raises(ASRError):
            await transcription_service.transcribe(
                audio_files=["audio1.wav"],
                asr_language=ASRLanguage.ZH_CN,
            )

    @pytest.mark.asyncio
    async def test_prepare_audio_invalid_file_order(self, transcription_service):
        """测试无效的文件顺序"""
        with pytest.raises(AudioFormatError, match="file_order length"):
            await transcription_service._prepare_audio(
                audio_files=["audio1.wav", "audio2.wav"],
                file_order=[0],  # 长度不匹配
            )

    @pytest.mark.asyncio
    async def test_upload_audio(self, transcription_service, mock_storage):
        """测试音频上传"""
        url = await transcription_service._upload_audio("/tmp/test.wav")

        # 验证返回的是预签名 URL
        assert url == "https://tos.example.com/audio/test.wav?X-Tos-Signature=xxx"
        mock_storage.upload_file.assert_called_once()
        mock_storage.generate_presigned_url.assert_called_once()
        
        # 验证上传参数
        upload_kwargs = mock_storage.upload_file.call_args[1]
        assert upload_kwargs["local_path"] == "/tmp/test.wav"
        assert upload_kwargs["content_type"] == "audio/wav"
        
        # 验证预签名 URL 参数
        presigned_kwargs = mock_storage.generate_presigned_url.call_args[1]
        assert presigned_kwargs["expires_in"] == 86400  # 24 hours

    @pytest.mark.asyncio
    async def test_get_audio_duration(self, transcription_service, mock_audio_processor):
        """测试获取音频时长"""
        duration = await transcription_service.get_audio_duration("/tmp/test.wav")

        assert duration == 30.0
        mock_audio_processor.get_duration.assert_called_once_with("/tmp/test.wav")

    @pytest.mark.asyncio
    async def test_transcribe_cleanup_temp_file(
        self, transcription_service, mock_primary_asr, mock_audio_processor, sample_transcript
    ):
        """测试临时文件清理 - 现在由 pipeline 负责清理"""
        mock_primary_asr.transcribe = AsyncMock(return_value=sample_transcript)

        result, audio_url, local_path = await transcription_service.transcribe(
            audio_files=["audio1.wav", "audio2.wav"],
            asr_language=ASRLanguage.ZH_CN,
        )

        # 验证返回了拼接后的文件路径
        assert local_path == "/tmp/concatenated.wav"
        # 注意: 临时文件不再在这里清理,而是由 pipeline 在使用完后清理

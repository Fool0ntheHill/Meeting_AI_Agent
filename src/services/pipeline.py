"""Pipeline orchestration service implementation."""

import logging
from datetime import datetime
from typing import List, Optional

from src.core.exceptions import MeetingAgentError
from src.core.models import (
    ASRLanguage,
    GeneratedArtifact,
    OutputLanguage,
    PromptInstance,
    TaskState,
    TranscriptionResult,
)
from src.services.artifact_generation import ArtifactGenerationService
from src.services.correction import CorrectionService
from src.services.speaker_recognition import SpeakerRecognitionService
from src.services.transcription import TranscriptionService
from src.utils.cost import CostTracker
from src.utils.error_handler import classify_exception
from src.utils.wecom_notification import get_wecom_service
from src.config.models import PricingConfig

logger = logging.getLogger(__name__)


class PipelineService:
    """
    管线编排服务
    
    负责编排整个会议处理流程:
    转写 → 说话人识别 → 修正 → 生成衍生内容
    """

    def __init__(
        self,
        transcription_service: TranscriptionService,
        speaker_recognition_service: SpeakerRecognitionService,
        correction_service: CorrectionService,
        artifact_generation_service: ArtifactGenerationService,
        task_repo=None,
        transcript_repo=None,
        speaker_mapping_repo=None,
        speaker_repo=None,
        audit_logger=None,
        pricing_config: Optional[PricingConfig] = None,
    ):
        """
        初始化管线服务
        
        Args:
            transcription_service: 转写服务
            speaker_recognition_service: 说话人识别服务
            correction_service: 修正服务
            artifact_generation_service: 衍生内容生成服务
            task_repo: 任务仓库(可选,Phase 1 可为 None)
            transcript_repo: 转写记录仓库(可选)
            speaker_mapping_repo: 说话人映射仓库(可选)
            speaker_repo: 说话人仓库(可选)
            audit_logger: 审计日志记录器(可选)
            pricing_config: 价格配置(可选)
        """
        self.transcription = transcription_service
        self.speaker_recognition = speaker_recognition_service
        self.correction = correction_service
        self.artifact_generation = artifact_generation_service
        self.tasks = task_repo
        self.transcripts = transcript_repo
        self.speaker_mappings = speaker_mapping_repo
        self.speakers = speaker_repo
        self.audit_logger = audit_logger
        self.cost_tracker = CostTracker(pricing_config) if pricing_config else CostTracker()

    async def process_meeting(
        self,
        task_id: str,
        audio_files: List[str],
        file_order: List[int],
        prompt_instance: PromptInstance,
        user_id: str,
        tenant_id: str = "default",
        asr_language: ASRLanguage = ASRLanguage.ZH_EN,
        output_language: OutputLanguage = OutputLanguage.ZH_CN,
        skip_speaker_recognition: bool = False,
        hotword_set_id: Optional[str] = None,
        template=None,
        cancellation_check=None,  # 新增：取消检查回调函数
        **kwargs,
    ) -> GeneratedArtifact:
        """
        处理会议录音
        
        核心返回类型统一为 GeneratedArtifact(type=meeting_minutes)
        
        流程:
        1. 更新任务状态为 TRANSCRIBING
        2. 调用转写服务
        3. 更新任务状态为 IDENTIFYING (如果未跳过)
        4. 调用说话人识别服务 (如果未跳过)
        5. 调用修正服务
        6. 更新任务状态为 SUMMARIZING
        7. 调用衍生内容生成服务
        8. 更新任务状态为 SUCCESS
        9. 返回 GeneratedArtifact(type=meeting_minutes)
        
        异常处理:
        - 任何阶段失败,更新状态为 FAILED
        - 记录错误详情
        - 支持部分成功 (PARTIAL_SUCCESS)
        
        Args:
            task_id: 任务 ID
            audio_files: 音频文件列表
            file_order: 文件排序索引
            prompt_instance: 提示词实例
            user_id: 用户 ID
            tenant_id: 租户 ID
            asr_language: ASR 识别语言
            output_language: 输出语言
            skip_speaker_recognition: 是否跳过说话人识别
            hotword_set_id: 热词集 ID
            template: 提示词模板(可选)
            **kwargs: 其他参数
            
        Returns:
            GeneratedArtifact: 生成的会议纪要
            
        Raises:
            MeetingAgentError: 处理失败
        """
        transcript = None
        audio_url = None
        local_audio_path = None
        
        # 跟踪实际使用情况
        actual_usage = {
            "asr_provider": None,
            "asr_duration": 0.0,
            "voiceprint_samples": 0,
            "voiceprint_duration": 0.0,
            "llm_model": None,
            "llm_tokens": 0,
        }
        
        # 读取任务信息，获取会议元数据
        meeting_date = None
        meeting_time = None
        original_filenames = None
        
        try:
            from src.database.repositories import TaskRepository
            from src.database.session import session_scope
            
            with session_scope() as db:
                task_repo = TaskRepository(db)
                task = task_repo.get_by_id(task_id)
                if task:
                    meeting_date = task.meeting_date
                    meeting_time = task.meeting_time
                    original_filenames = task.get_original_filenames_list()
                    logger.info(
                        f"Task {task_id}: Loaded metadata from DB - "
                        f"date={meeting_date}, time={meeting_time}, "
                        f"filenames={original_filenames}"
                    )
        except Exception as e:
            logger.warning(f"Task {task_id}: Failed to load task metadata: {e}")
        
        try:
            # 1. 转写阶段 (0-40%)
            logger.info(f"Task {task_id}: Starting transcription phase")
            self._update_task_status(
                task_id, 
                TaskState.TRANSCRIBING, 
                progress=0.0,
                audio_duration=None,  # 还不知道音频时长
            )
            
            try:
                transcript, audio_url, local_audio_path = await self.transcription.transcribe(
                    audio_files=audio_files,
                    file_order=file_order,
                    asr_language=asr_language,
                    hotword_set_id=hotword_set_id,
                    tenant_id=tenant_id,
                    user_id=user_id,
                )
            except Exception as e:
                # ASR 阶段错误
                logger.error(f"Task {task_id}: ASR failed: {e}", exc_info=True)
                error = classify_exception(e, context="ASR")
                self._update_task_error(task_id, error)
                self._update_task_status(task_id, TaskState.FAILED)
                raise
            
            logger.info(
                f"Task {task_id}: Transcription completed, "
                f"duration={transcript.duration}s, "
                f"segments={len(transcript.segments)}, "
                f"audio_url={audio_url[:100]}..., "
                f"local_audio_path={local_audio_path}"
            )
            
            # 检查任务是否被取消
            if cancellation_check and cancellation_check(task_id):
                logger.info(f"Task {task_id}: Cancelled after transcription")
                self._update_task_status(task_id, TaskState.CANCELLED)
                raise Exception("Task cancelled by user")
            
            # 更新进度：转写完成 (40%)
            audio_duration = transcript.duration
            self._update_task_status(
                task_id,
                TaskState.TRANSCRIBING,
                progress=40.0,
                audio_duration=audio_duration,
            )
            
            # 提取会议元数据（在转写完成后）
            if not meeting_date:
                from src.utils.meeting_metadata import extract_meeting_metadata
                extracted_date, extracted_time = extract_meeting_metadata(
                    original_filenames=original_filenames,
                    meeting_date=meeting_date,
                    meeting_time=meeting_time,
                )
                meeting_date = extracted_date or meeting_date
                # 只有用户明确提供时才使用时间
                if not meeting_time and extracted_time:
                    meeting_time = extracted_time
                
                logger.info(f"Task {task_id}: Meeting metadata - date={meeting_date}, time={meeting_time}")
                
                # 保存提取的元数据到数据库
                try:
                    from src.database.repositories import TaskRepository
                    from src.database.session import session_scope
                    
                    with session_scope() as db:
                        task_repo = TaskRepository(db)
                        task = task_repo.get_by_id(task_id)
                        if task:
                            task.meeting_date = meeting_date
                            task.meeting_time = meeting_time
                            logger.info(f"Task {task_id}: Meeting metadata saved to database")
                except Exception as e:
                    logger.warning(f"Task {task_id}: Failed to save meeting metadata: {e}")
            
            # 保存转写记录到数据库
            if self.transcripts is not None:
                try:
                    import uuid
                    transcript_id = f"transcript_{uuid.uuid4().hex[:16]}"
                    self.transcripts.create(
                        transcript_id=transcript_id,
                        task_id=task_id,
                        transcript_result=transcript,
                    )
                    logger.info(f"Task {task_id}: Transcript saved to database: {transcript_id}")
                except Exception as e:
                    logger.warning(f"Task {task_id}: Failed to save transcript to database: {e}")
            
            # 记录实际 ASR 使用
            actual_usage["asr_provider"] = transcript.provider
            actual_usage["asr_duration"] = transcript.duration
            
            # 2. 说话人识别阶段 (40-60%)
            speaker_mapping = {}
            if not skip_speaker_recognition:
                logger.info(f"Task {task_id}: Starting speaker recognition phase")
                self._update_task_status(
                    task_id, 
                    TaskState.IDENTIFYING, 
                    progress=40.0,
                    audio_duration=audio_duration,
                )
                
                try:
                    # 调用说话人识别服务 (使用本地音频路径)
                    speaker_mapping = await self.speaker_recognition.recognize_speakers(
                        transcript=transcript,
                        audio_path=local_audio_path,
                        known_speakers=None,  # TODO: 从数据库加载已知说话人
                    )
                except Exception as e:
                    # 声纹识别阶段错误
                    logger.error(f"Task {task_id}: Voiceprint recognition failed: {e}", exc_info=True)
                    error = classify_exception(e, context="Voiceprint")
                    self._update_task_error(task_id, error)
                    self._update_task_status(task_id, TaskState.FAILED)
                    raise
                
                logger.info(
                    f"Task {task_id}: Speaker recognition completed, "
                    f"identified {len(speaker_mapping)} speakers: {speaker_mapping}"
                )
                
                # 更新进度：说话人识别完成 (60%)
                self._update_task_status(
                    task_id,
                    TaskState.IDENTIFYING,
                    progress=60.0,
                    audio_duration=audio_duration,
                )
                
                # 保存 speaker mapping 到数据库（使用真实姓名）
                if self.speaker_mappings is not None and speaker_mapping:
                    try:
                        # 批量查询真实姓名
                        speaker_ids = list(speaker_mapping.values())
                        display_names = {}
                        if self.speakers is not None:
                            display_names = self.speakers.get_display_names_batch(speaker_ids)
                        
                        for speaker_label, speaker_id in speaker_mapping.items():
                            # speaker_label: "Speaker 1", "Speaker 2"
                            # speaker_id: "speaker_linyudong", "speaker_lanweiyi"
                            # 使用真实姓名（如果存在），否则使用声纹 ID
                            speaker_name = display_names.get(speaker_id, speaker_id)
                            
                            self.speaker_mappings.create_or_update(
                                task_id=task_id,
                                speaker_label=speaker_label,
                                speaker_name=speaker_name,  # 存储真实姓名
                                speaker_id=speaker_id,
                                confidence=None,  # TODO: 从识别结果获取置信度
                            )
                        logger.info(
                            f"Task {task_id}: Speaker mappings saved to database with real names: "
                            f"{[(label, display_names.get(sid, sid)) for label, sid in speaker_mapping.items()]}"
                        )
                    except Exception as e:
                        logger.warning(f"Task {task_id}: Failed to save speaker mappings: {e}")
                
                # 记录实际声纹识别使用
                actual_usage["voiceprint_samples"] = len(speaker_mapping)
                # 假设每个说话人样本 5 秒
                actual_usage["voiceprint_duration"] = len(speaker_mapping) * 5.0
            else:
                logger.info(f"Task {task_id}: Skipping speaker recognition")
            
            # 3. 修正阶段 (60-70%)
            if speaker_mapping:
                logger.info(f"Task {task_id}: Starting correction phase")
                self._update_task_status(
                    task_id, 
                    TaskState.CORRECTING, 
                    progress=60.0,
                    audio_duration=audio_duration,
                )
                
                # 构建真实姓名映射：Speaker 1 -> 林煜东
                real_name_mapping = {}
                if self.speakers is not None:
                    try:
                        # 获取声纹 ID 列表
                        speaker_ids = list(speaker_mapping.values())
                        
                        # 批量查询真实姓名
                        display_names = self.speakers.get_display_names_batch(speaker_ids)
                        
                        # 构建映射：Speaker 1 -> 林煜东
                        for speaker_label, speaker_id in speaker_mapping.items():
                            real_name = display_names.get(speaker_id, speaker_id)
                            real_name_mapping[speaker_label] = real_name
                        
                        logger.info(
                            f"Task {task_id}: Real name mapping constructed: {real_name_mapping}"
                        )
                    except Exception as e:
                        logger.warning(f"Task {task_id}: Failed to get real names, using voiceprint IDs: {e}")
                        # 如果查询失败，使用声纹 ID
                        real_name_mapping = speaker_mapping
                else:
                    # 如果没有 speakers repository，使用声纹 ID
                    real_name_mapping = speaker_mapping
                
                # 应用真实姓名映射到 transcript
                transcript = await self.correction.correct_speakers(transcript, real_name_mapping)
                logger.info(f"Task {task_id}: Speaker correction completed with real names")
                
                # 更新数据库中的 transcript segments（已包含真实姓名）
                if self.transcripts is not None:
                    try:
                        self.transcripts.update_segments(
                            task_id=task_id,
                            segments=[seg.model_dump() for seg in transcript.segments],
                        )
                        logger.info(f"Task {task_id}: Transcript segments updated with real names in database")
                    except Exception as e:
                        logger.warning(f"Task {task_id}: Failed to update transcript segments: {e}")
                
                # 检查任务是否被取消
                if cancellation_check and cancellation_check(task_id):
                    logger.info(f"Task {task_id}: Cancelled after speaker correction")
                    self._update_task_status(task_id, TaskState.CANCELLED)
                    raise Exception("Task cancelled by user")
                
                # 更新进度：修正完成 (70%)
                self._update_task_status(
                    task_id,
                    TaskState.CORRECTING,
                    progress=70.0,
                    audio_duration=audio_duration,
                )
            else:
                logger.info(f"Task {task_id}: No speaker mapping, skipping correction phase")
            
            # 4. 生成衍生内容阶段 (70-100%)
            logger.info(f"Task {task_id}: Starting artifact generation phase")
            self._update_task_status(
                task_id, 
                TaskState.SUMMARIZING, 
                progress=70.0,  # 统一使用 70% 作为总结阶段起始进度
                audio_duration=audio_duration,
            )
            
            try:
                artifact = await self.artifact_generation.generate_artifact(
                    task_id=task_id,
                    transcript=transcript,
                    artifact_type="meeting_minutes",
                    prompt_instance=prompt_instance,
                    output_language=output_language,
                    user_id=user_id,
                    template=template,
                    meeting_date=meeting_date,  # 传入会议日期
                    meeting_time=meeting_time,  # 传入会议时间
                    display_name="纪要",  # 添加默认 display_name
                )
            except Exception as e:
                # LLM 生成阶段错误
                logger.error(f"Task {task_id}: LLM generation failed: {e}", exc_info=True)
                error = classify_exception(e, context="LLM")
                self._update_task_error(task_id, error)
                self._update_task_status(task_id, TaskState.FAILED, progress=70.0)
                raise
            
            logger.info(
                f"Task {task_id}: Artifact generation completed, "
                f"artifact_id={artifact.artifact_id}, version={artifact.version}"
            )
            
            # 记录实际 LLM 使用
            if artifact.metadata:
                actual_usage["llm_model"] = artifact.metadata.get("llm_model", "gemini-flash")
                actual_usage["llm_tokens"] = artifact.metadata.get("token_count", 0)
            
            # 5. 计算并记录实际成本
            await self._calculate_and_log_actual_cost(task_id, actual_usage, user_id, tenant_id)
            
            # 6. 更新任务状态为成功 (100%)
            self._update_task_status(
                task_id, 
                TaskState.SUCCESS, 
                progress=100.0,
                audio_duration=audio_duration,
            )
            
            # 7. 发送企微通知（任务成功）
            try:
                # 获取用户账号和任务信息
                user_account = None
                task_name = None
                if self.tasks:
                    from src.database.repositories import UserRepository
                    from src.database.session import session_scope
                    with session_scope() as session:
                        user_repo = UserRepository(session)
                        user = user_repo.get_by_id(user_id)
                        if user:
                            user_account = user.username
                        
                        # 获取任务名称（字段名是 name 不是 task_name）
                        task = self.tasks.get_by_id(task_id)
                        if task:
                            task_name = task.name
                            # 如果 task.name 为 None，使用原始文件名（去掉扩展名）
                            if not task_name and original_filenames:
                                import os
                                filename = original_filenames[0] if original_filenames else None
                                if filename:
                                    # 去掉文件扩展名
                                    task_name = os.path.splitext(filename)[0]
                
                if user_account:
                    wecom_service = get_wecom_service()
                    success = wecom_service.send_artifact_success_notification(
                        user_account=user_account,
                        task_id=task_id,
                        task_name=task_name,
                        meeting_date=meeting_date,
                        meeting_time=meeting_time,
                        artifact_id=artifact.artifact_id,
                        artifact_type="meeting_minutes",
                        display_name="纪要",
                    )
                    if success:
                        logger.info(f"Task {task_id}: WeCom notification sent successfully to {user_account}")
                    else:
                        logger.warning(f"Task {task_id}: WeCom notification failed to send to {user_account}")
                else:
                    logger.warning(f"Task {task_id}: Cannot send WeCom notification - user account not found")
            except Exception as e:
                # 通知失败不影响任务成功
                logger.error(f"Task {task_id}: Failed to send WeCom notification: {e}", exc_info=True)
            
            logger.info(f"Task {task_id}: Pipeline completed successfully")
            
            return artifact
            
        except Exception as e:
            # 记录错误并更新任务状态
            logger.error(
                f"Task {task_id}: Pipeline failed at current stage: {e}",
                exc_info=True,
            )
            
            # 如果还没有设置错误码，则分类并设置
            # (如果已经在上面的 try-except 中设置过，这里就不会重复设置)
            try:
                task = self.tasks.get_by_id(task_id) if self.tasks else None
                if task and not task.error_code:
                    # 通用错误分类
                    error = classify_exception(e, context="Pipeline")
                    self._update_task_error(task_id, error)
            except Exception as classify_error:
                logger.warning(f"Failed to classify error for task {task_id}: {classify_error}")
            
            # 更新任务状态为失败
            self._update_task_status(
                task_id, TaskState.FAILED, error_details=str(e)
            )
            
            # 发送企微通知（任务失败）
            try:
                # 获取用户账号和任务信息
                user_account = None
                task_name = None
                if self.tasks:
                    from src.database.repositories import UserRepository
                    from src.database.session import session_scope
                    with session_scope() as session:
                        user_repo = UserRepository(session)
                        user = user_repo.get_by_id(user_id)
                        if user:
                            user_account = user.username
                        
                        # 获取任务信息（字段名是 name 不是 task_name）
                        task = self.tasks.get_by_id(task_id)
                        if task:
                            task_name = task.name
                            # 如果 task.name 为 None，使用原始文件名（去掉扩展名）
                            if not task_name:
                                filenames = task.get_original_filenames_list()
                                if filenames:
                                    import os
                                    task_name = os.path.splitext(filenames[0])[0]
                
                if user_account:
                    # 获取错误信息
                    task = self.tasks.get_by_id(task_id) if self.tasks else None
                    error_code = task.error_code if task else "UNKNOWN_ERROR"
                    error_message = task.error_message if task else str(e)
                    
                    wecom_service = get_wecom_service()
                    wecom_service.send_artifact_failure_notification(
                        user_account=user_account,
                        task_id=task_id,
                        task_name=task_name,
                        meeting_date=meeting_date if 'meeting_date' in locals() else None,
                        meeting_time=meeting_time if 'meeting_time' in locals() else None,
                        error_code=error_code,
                        error_message=error_message,
                    )
                    logger.info(f"Task {task_id}: WeCom failure notification sent to {user_account}")
                else:
                    logger.warning(f"Task {task_id}: Cannot send WeCom notification - user account not found")
            except Exception as notify_error:
                # 通知失败不影响错误处理
                logger.error(f"Task {task_id}: Failed to send WeCom failure notification: {notify_error}", exc_info=True)
            
            # 如果是 MeetingAgentError,直接抛出
            if isinstance(e, MeetingAgentError):
                raise
            
            # 否则包装为 MeetingAgentError
            raise MeetingAgentError(
                f"Pipeline processing failed: {e}",
                details={
                    "task_id": task_id,
                    "error": str(e),
                    "has_transcript": transcript is not None,
                },
            )
        finally:
            # 清理临时音频文件 (如果是拼接文件)
            if local_audio_path and len(audio_files) > 1:
                import os
                try:
                    if os.path.exists(local_audio_path):
                        os.remove(local_audio_path)
                        logger.info(f"Cleaned up temporary audio file: {local_audio_path}")
                except Exception as e:
                    logger.warning(f"Failed to cleanup temp file {local_audio_path}: {e}")

    def _update_task_status(
        self,
        task_id: str,
        state: TaskState,
        progress: float = 0.0,
        audio_duration: Optional[float] = None,
        error_details: Optional[str] = None,
    ) -> None:
        """
        更新任务状态
        
        Args:
            task_id: 任务 ID
            state: 任务状态
            progress: 进度百分比 (0-100)
            audio_duration: 音频总时长(秒)，用于计算预估时间
            error_details: 错误详情
        """
        if self.tasks is None:
            # 如果没有任务仓库,只记录日志
            logger.info(
                f"Task {task_id}: Status update - state={state.value}, "
                f"progress={progress}%"
            )
            return
        
        # 计算预估剩余时间
        estimated_time = None
        if audio_duration:
            if progress >= 100.0:
                # 任务完成，剩余时间为 0
                estimated_time = 0
            else:
                # 使用 25% 规则：总耗时 = 音频时长 * 0.25
                total_estimated_time = audio_duration * 0.25
                # 剩余时间 = 总耗时 * (1 - 进度百分比)
                estimated_time = int(total_estimated_time * (1 - progress / 100.0))
        
        try:
            self.tasks.update_status(
                task_id=task_id,
                state=state,
                progress=progress,
                estimated_time=estimated_time,
                error_details=error_details,
                updated_at=datetime.now(),
            )
            
            logger.info(
                f"Task {task_id}: Status updated - state={state.value}, "
                f"progress={progress}%, estimated_time={estimated_time}s"
            )
        except Exception as e:
            logger.warning(f"Failed to update task status: {e}")

    def _update_task_error(self, task_id: str, error: "TaskError") -> None:
        """
        更新任务错误信息
        
        Args:
            task_id: 任务 ID
            error: TaskError 对象（来自 classify_exception）
        """
        if self.tasks is None:
            logger.warning(f"Task {task_id}: Cannot update error - no task repository")
            return
        
        try:
            self.tasks.update_error(
                task_id=task_id,
                error_code=error.error_code.value,
                error_message=error.error_message,
                error_details=error.error_details,
                retryable=error.retryable,
            )
            logger.info(
                f"Task {task_id}: Error updated - code={error.error_code.value}, "
                f"message={error.error_message}, retryable={error.retryable}"
            )
        except Exception as e:
            logger.warning(f"Failed to update task error for {task_id}: {e}")

    async def get_status(self, task_id: str) -> dict:
        """
        获取任务状态
        
        Args:
            task_id: 任务 ID
            
        Returns:
            dict: 任务状态信息
        """
        if self.tasks is None:
            return {
                "task_id": task_id,
                "state": "unknown",
                "message": "Task repository not configured",
            }
        
        try:
            task = self.tasks.get_by_id(task_id)
            if not task:
                return {
                    "task_id": task_id,
                    "state": "not_found",
                    "message": "Task not found",
                }
            
            return {
                "task_id": task_id,
                "state": task.state,
                "progress": task.progress,
                "estimated_time": task.estimated_time,
                "error_details": task.error_details,
                "updated_at": task.updated_at.isoformat(),
            }
        except Exception as e:
            logger.error(f"Failed to get task status: {e}")
            return {
                "task_id": task_id,
                "state": "error",
                "message": f"Failed to get status: {e}",
            }

    async def _calculate_and_log_actual_cost(
        self,
        task_id: str,
        actual_usage: dict,
        user_id: str,
        tenant_id: str,
    ) -> None:
        """
        计算并记录实际成本
        
        Args:
            task_id: 任务 ID
            actual_usage: 实际使用情况
            user_id: 用户 ID
            tenant_id: 租户 ID
        """
        try:
            # 1. 计算各项成本
            asr_cost = self.cost_tracker.calculate_asr_cost(
                duration=actual_usage["asr_duration"],
                provider=actual_usage["asr_provider"] or "volcano"
            )
            
            voiceprint_cost = 0.0
            if actual_usage["voiceprint_samples"] > 0:
                # 声纹识别按次计费，每个说话人识别一次
                voiceprint_cost = self.cost_tracker.calculate_voiceprint_cost(
                    speaker_count=actual_usage["voiceprint_samples"]
                )
            
            llm_cost = 0.0
            if actual_usage["llm_tokens"] > 0:
                # 从模型名称推断是 flash 还是 pro
                model_type = "gemini-pro" if "pro" in (actual_usage["llm_model"] or "").lower() else "gemini-flash"
                llm_cost = self.cost_tracker.calculate_llm_cost(
                    token_count=actual_usage["llm_tokens"],
                    model=model_type
                )
            
            total_cost = asr_cost + voiceprint_cost + llm_cost
            
            # 2. 构建成本详情
            cost_breakdown = {
                "asr": asr_cost,
                "voiceprint": voiceprint_cost,
                "llm": llm_cost,
                "total": total_cost,
            }
            
            logger.info(
                f"Task {task_id}: Actual cost calculated - "
                f"ASR: ¥{asr_cost:.4f}, "
                f"Voiceprint: ¥{voiceprint_cost:.4f}, "
                f"LLM: ¥{llm_cost:.4f}, "
                f"Total: ¥{total_cost:.4f}"
            )
            
            # 3. 记录到审计日志
            if self.audit_logger:
                await self.audit_logger.log_cost_usage(
                    task_id=task_id,
                    user_id=user_id,
                    tenant_id=tenant_id,
                    cost_amount=total_cost,
                    details={
                        "cost_breakdown": cost_breakdown,
                        "actual_usage": actual_usage,
                    }
                )
                logger.info(f"Task {task_id}: Cost logged to audit")
            
        except Exception as e:
            logger.warning(f"Failed to calculate/log actual cost for task {task_id}: {e}")


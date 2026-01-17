# Task 39 部分完成总结 - 成本预估优化

## 任务概述

**任务**: 39. 成本预估优化 (P1 - 中等)  
**状态**: ⏳ 部分完成 (39.1 完成, 39.2 待实施)  
**完成时间**: 2026-01-15  
**实际工作量**: 1 小时 (仅 39.1)

## 已完成部分

### Task 39.1: 配置化价格表 ✅

**完成内容**:
- ✅ 添加 `PricingConfig` 类到 `src/config/models.py`
- ✅ 重构 `CostTracker` 使用配置化价格
- ✅ 更新所有配置文件添加 pricing 配置节
- ✅ 所有 226 个单元测试通过

**优势**:
- 价格可通过配置文件调整，无需修改代码
- 支持不同环境使用不同价格
- 支持不同 LLM 模型的价格差异
- 配置验证确保价格有效

**详细文档**: `docs/summaries/TASK_39.1_COMPLETION_SUMMARY.md`

## 待实施部分

### Task 39.2: 根据实际模型计算成本 ⏳

**目标**:
- 在任务完成后记录实际使用的模型和成本
- 对比预估成本和实际成本
- 提供成本分析报告

**实施计划**:

#### 1. 在 PipelineService 中跟踪实际使用

```python
class PipelineService:
    async def process_meeting(self, ...):
        # 跟踪实际使用的服务
        actual_usage = {
            "asr_provider": None,
            "asr_duration": 0.0,
            "voiceprint_samples": 0,
            "voiceprint_duration": 0.0,
            "llm_model": None,
            "llm_tokens": 0,
        }
        
        try:
            # 1. 转写阶段 - 记录实际 ASR 提供商和时长
            transcript, audio_url, local_audio_path = await self.transcription.transcribe(...)
            actual_usage["asr_provider"] = transcript.provider
            actual_usage["asr_duration"] = transcript.duration
            
            # 2. 说话人识别阶段 - 记录样本数和时长
            if not skip_speaker_recognition:
                speaker_mapping = await self.speaker_recognition.recognize_speakers(...)
                actual_usage["voiceprint_samples"] = len(speaker_mapping)
                actual_usage["voiceprint_duration"] = len(speaker_mapping) * 5.0  # 假设每个样本 5 秒
            
            # 3. 生成衍生内容阶段 - 记录实际 LLM 模型和 Token 数
            artifact = await self.artifact_generation.generate_artifact(...)
            actual_usage["llm_model"] = artifact.metadata.get("llm_model", "gemini-flash")
            actual_usage["llm_tokens"] = artifact.metadata.get("token_count", 0)
            
            # 4. 计算实际成本
            actual_cost = await self._calculate_actual_cost(actual_usage)
            
            # 5. 记录到审计日志
            await self._log_actual_cost(task_id, actual_cost, actual_usage)
            
        except Exception as e:
            ...
```

#### 2. 添加实际成本计算方法

```python
async def _calculate_actual_cost(self, actual_usage: dict) -> dict:
    """
    根据实际使用计算成本
    
    Args:
        actual_usage: 实际使用情况
        
    Returns:
        dict: 成本拆分
    """
    cost_tracker = CostTracker(self.config.pricing)
    
    # ASR 成本
    asr_cost = cost_tracker.calculate_asr_cost(
        duration=actual_usage["asr_duration"],
        provider=actual_usage["asr_provider"]
    )
    
    # 声纹识别成本
    voiceprint_cost = cost_tracker.calculate_voiceprint_cost(
        sample_count=actual_usage["voiceprint_samples"],
        sample_duration=actual_usage["voiceprint_duration"] / actual_usage["voiceprint_samples"]
            if actual_usage["voiceprint_samples"] > 0 else 0
    )
    
    # LLM 成本
    llm_cost = cost_tracker.calculate_llm_cost(
        token_count=actual_usage["llm_tokens"],
        model=actual_usage["llm_model"]
    )
    
    total_cost = asr_cost + voiceprint_cost + llm_cost
    
    return {
        "asr": asr_cost,
        "voiceprint": voiceprint_cost,
        "llm": llm_cost,
        "total": total_cost,
    }
```

#### 3. 记录实际成本到审计日志

```python
async def _log_actual_cost(
    self,
    task_id: str,
    actual_cost: dict,
    actual_usage: dict
) -> None:
    """
    记录实际成本到审计日志
    
    Args:
        task_id: 任务 ID
        actual_cost: 实际成本
        actual_usage: 实际使用情况
    """
    if self.audit_logger:
        await self.audit_logger.log_cost_usage(
            task_id=task_id,
            cost_amount=actual_cost["total"],
            details={
                "cost_breakdown": actual_cost,
                "actual_usage": actual_usage,
            }
        )
```

#### 4. 添加成本对比 API

```python
# src/api/routes/tasks.py

@router.get("/api/v1/tasks/{task_id}/cost-analysis")
async def get_cost_analysis(
    task_id: str,
    current_user: dict = Depends(verify_jwt_token),
    db: Session = Depends(get_db),
):
    """
    获取任务的成本分析
    
    对比预估成本和实际成本
    """
    # 1. 获取任务信息
    task = task_repo.get_by_id(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    # 2. 获取预估成本 (从任务创建时的估算)
    estimated_cost = task.metadata.get("estimated_cost", {})
    
    # 3. 获取实际成本 (从审计日志)
    audit_logs = audit_repo.get_by_resource("task", task_id)
    actual_cost = {}
    for log in audit_logs:
        if log.action == "cost_usage":
            actual_cost = log.get_details_dict().get("cost_breakdown", {})
            break
    
    # 4. 计算差异
    cost_diff = {
        "asr": actual_cost.get("asr", 0) - estimated_cost.get("asr", 0),
        "voiceprint": actual_cost.get("voiceprint", 0) - estimated_cost.get("voiceprint", 0),
        "llm": actual_cost.get("llm", 0) - estimated_cost.get("llm", 0),
        "total": actual_cost.get("total", 0) - estimated_cost.get("total", 0),
    }
    
    return {
        "task_id": task_id,
        "estimated_cost": estimated_cost,
        "actual_cost": actual_cost,
        "cost_difference": cost_diff,
        "accuracy_percentage": (
            (1 - abs(cost_diff["total"]) / estimated_cost["total"]) * 100
            if estimated_cost.get("total", 0) > 0 else 0
        ),
    }
```

#### 5. 更新 ArtifactGenerationService 返回 Token 数

```python
# src/services/artifact_generation.py

async def generate_artifact(self, ...) -> GeneratedArtifact:
    """生成衍生内容"""
    # ... 现有代码 ...
    
    # 调用 LLM
    response = await self.llm_provider.call_gemini_api(...)
    
    # 提取 Token 数 (从 Gemini API 响应)
    token_count = response.get("usageMetadata", {}).get("totalTokenCount", 0)
    
    # 存储到 metadata
    metadata = {
        "llm_model": self.llm_provider.model,
        "token_count": token_count,
        "regenerated": regenerated,
    }
    
    # 创建 GeneratedArtifact
    artifact = GeneratedArtifact(
        artifact_id=artifact_id,
        task_id=task_id,
        artifact_type=artifact_type,
        version=version,
        prompt_instance=prompt_instance,
        content=content_json,
        metadata=metadata,  # 包含 token_count
        created_at=datetime.now(),
        created_by=user_id,
    )
    
    return artifact
```

**预计工作量**: 2-3 小时

**依赖**:
- 需要 `AuditLogger` 实例注入到 `PipelineService`
- 需要 Gemini API 返回 Token 使用信息
- 需要更新 `GeneratedArtifact.metadata` 存储 Token 数

## 当前状态

### 已实现 ✅
- 价格配置化
- 成本估算 API
- 配置验证

### 待实现 ⏳
- 实际成本跟踪
- 成本对比分析
- Token 数统计

## 优先级建议

Task 39.2 (实际成本跟踪) 的优先级可以根据业务需求调整:

**高优先级场景**:
- 需要精确的成本核算
- 需要优化成本预估模型
- 需要向用户展示实际消费

**低优先级场景**:
- 成本预估已经足够准确
- 主要用于内部测试
- 暂时不需要精确的成本分析

## 相关文件

### 已修改
- `src/config/models.py` - PricingConfig
- `src/utils/cost.py` - CostTracker
- `config/*.yaml` - 价格配置

### 待修改 (Task 39.2)
- `src/services/pipeline.py` - 添加实际成本跟踪
- `src/services/artifact_generation.py` - 返回 Token 数
- `src/api/routes/tasks.py` - 添加成本分析 API
- `src/database/models.py` - 可能需要添加 Task.metadata 字段

## 总结

Task 39.1 已成功完成，实现了价格配置化。系统现在可以通过配置文件灵活调整各个服务的价格。

Task 39.2 的实施计划已经制定，可以根据业务需求决定实施时机。建议在前端集成测试期间或生产部署前实施，以便提供准确的成本分析功能。

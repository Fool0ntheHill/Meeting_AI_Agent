# 实时进度更新 Async 问题修复

## 问题描述

Worker 日志显示错误：
```
RuntimeWarning: coroutine 'PipelineService._update_task_status' was never awaited
```

## 根本原因

在 `src/services/pipeline.py` 中：
1. `_update_task_status` 方法被定义为 `async def`，但内部调用的是同步方法
2. 所有调用 `_update_task_status` 的地方都使用了 `await`
3. `TaskRepository.update_status()` 是同步方法，不应该被 await

## 修复内容

### 1. 将 `_update_task_status` 改为同步方法

```python
# 修复前
async def _update_task_status(self, ...):
    ...
    await self.tasks.update_status(...)

# 修复后
def _update_task_status(self, ...):
    ...
    self.tasks.update_status(...)
```

### 2. 移除所有调用处的 `await`

修改了 9 处调用：
- 转写阶段开始 (0%)
- 转写完成 (40%)
- 说话人识别开始 (40%)
- 说话人识别完成 (60%)
- 修正阶段开始 (60%)
- 修正完成 (70%)
- 生成阶段开始 (70%)
- 任务成功 (100%)
- 任务失败

```python
# 修复前
await self._update_task_status(...)

# 修复后
self._update_task_status(...)
```

### 3. 修复 `get_status` 方法

`PipelineService.get_status()` 方法试图调用不存在的 `self.tasks.get_status()` 方法。

修复为使用 `self.tasks.get_by_id()` 方法：

```python
# 修复前
status = await self.tasks.get_status(task_id)

# 修复后
task = self.tasks.get_by_id(task_id)
if not task:
    return {"task_id": task_id, "state": "not_found", ...}
```

## 预估时间计算逻辑

确认了预估时间的计算逻辑正确：

```python
if audio_duration:
    if progress >= 100.0:
        # 任务完成，剩余时间为 0
        estimated_time = 0
    else:
        # 使用 25% 规则：总耗时 = 音频时长 * 0.25
        total_estimated_time = audio_duration * 0.25
        # 剩余时间 = 总耗时 * (1 - 进度百分比)
        estimated_time = int(total_estimated_time * (1 - progress / 100.0))
```

当任务完成时（progress=100.0），`estimated_time` 会被设置为 0。

## 进度更新机制

进度是**跳跃式**的，不是连续的：
- 0% - 转写开始
- 40% - 转写完成
- 60% - 说话人识别完成（如果启用）
- 70% - 修正完成（如果有说话人识别）
- 100% - 任务完成

## 前端集成建议

1. **轮询频率**：每 2 秒轮询一次任务状态
2. **禁用缓存**：确保获取最新状态
3. **平滑过渡**：使用 CSS transition 实现进度条的平滑动画
4. **预估时间**：直接使用后端返回的 `estimated_time` 字段（秒）

## Gemini API 网络问题

### 常见错误

1. **WinError 10054**: 远程主机强迫关闭连接
2. **SSL: UNEXPECTED_EOF_WHILE_READING**: SSL/TLS 握手失败

### 可能原因

1. **网络不稳定** - 连接到 Google 服务被中断
2. **GFW 干扰** - 访问 Google 服务被阻断
3. **请求过大** - 转写内容太长（479秒音频，125个片段）
4. **代理问题** - 如果使用代理访问 Google 服务

### 解决方案

1. **使用代理**（推荐）
   ```powershell
   # 设置环境变量
   $env:HTTP_PROXY="http://your-proxy:port"
   $env:HTTPS_PROXY="http://your-proxy:port"
   
   # 然后启动 worker
   python worker.py
   ```

2. **分段处理长文本**
   - 修改 `src/providers/gemini_llm.py` 添加文本分段逻辑
   - 将长转写内容分成多个小段处理

3. **增加重试次数和等待时间**
   - 当前是 3 次重试，间隔 1s, 2s
   - 可以增加到 5 次，间隔 2s, 4s, 8s, 16s

4. **使用更稳定的模型**
   - `gemini-2.0-flash-exp` 可能更稳定
   - `gemini-1.5-flash` 作为备用

5. **测试连接**
   ```powershell
   python scripts/test_gemini_connection.py
   ```

## 测试步骤

1. 重启 Worker：
   ```powershell
   # 停止现有 worker
   Get-Process python | Where-Object {$_.CommandLine -like "*worker.py*"} | Stop-Process -Force
   
   # 启动新 worker
   python worker.py
   ```

2. 创建新任务并监控进度：
   ```powershell
   python scripts/test_progress_tracking.py <task_id>
   ```

3. 验证：
   - 进度从 0% 跳到 40% → 60% → 70% → 100%
   - `estimated_time` 随进度递减
   - 任务完成时 `estimated_time` 为 0
   - 不再有 RuntimeWarning

## 相关文件

- `src/services/pipeline.py` - 修复了所有 async/await 问题
- `src/database/repositories.py` - TaskRepository.update_status 方法
- `scripts/test_gemini_connection.py` - Gemini API 连接测试脚本
- `docs/REALTIME_PROGRESS_FRONTEND_GUIDE.md` - 前端集成指南
- `docs/FRONTEND_PROGRESS_GUIDE.md` - 前端进度显示指南


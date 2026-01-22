# 进度更新问题修复指南

## 问题描述

你遇到的问题：
1. `progress` 一直是 0%，没有变化
2. `estimated_time` 一直是 4 分钟（或 None），不会递减
3. 8 分钟的音频应该预估 2 分钟（8 × 0.25 = 2），但显示 4 分钟

## 根本原因

**Worker 还在使用旧代码！**

我们刚才修改了：
- `src/services/pipeline.py` - 添加了进度更新逻辑
- `src/database/repositories.py` - 添加了 `estimated_time` 支持
- `src/queue/worker.py` - 添加了 `task_repo` 初始化

但是 **worker 进程还在运行旧代码**，所以：
- 进度不会更新（一直是 0%）
- 预估时间不会计算（一直是 None 或旧值）

## 解决方案

### 1. 重启 Worker（必须！）

```bash
# 停止旧的 worker（如果在运行）
# 按 Ctrl+C 或者找到进程并 kill

# 启动新的 worker
python worker.py
```

### 2. 创建新任务测试

```bash
# 创建一个测试任务
python scripts/create_test_task.py
```

### 3. 实时监控进度

```bash
# 监控任务进度（会每 2 秒刷新）
python scripts/test_progress_tracking.py <task_id>
```

或者使用诊断脚本：

```bash
# 诊断当前状态
python scripts/diagnose_progress_issue.py

# 检查特定任务
python scripts/check_task_progress.py <task_id>
```

## 预期行为

重启 worker 后，新任务应该：

### 进度更新时间线

```
时间    阶段          进度    预估剩余（8分钟音频）
0s      转写开始      0%      120秒 (2分钟)
30s     转写完成      40%     72秒 (1分12秒)
40s     识别开始      40%     72秒
50s     识别完成      60%     48秒
55s     修正完成      70%     36秒
60s     生成开始      70%     36秒
120s    完成          100%    0秒
```

### Worker 日志示例

重启后，你应该在 worker 日志中看到类似这样的输出：

```
Task task_xxx: Status updated - state=transcribing, progress=0.0%, estimated_time=None
Task task_xxx: Transcription completed, duration=479.09s
Task task_xxx: Status updated - state=transcribing, progress=40.0%, estimated_time=72s
Task task_xxx: Status updated - state=identifying, progress=40.0%, estimated_time=72s
Task task_xxx: Status updated - state=identifying, progress=60.0%, estimated_time=48s
Task task_xxx: Status updated - state=correcting, progress=60.0%, estimated_time=48s
Task task_xxx: Status updated - state=correcting, progress=70.0%, estimated_time=36s
Task task_xxx: Status updated - state=summarizing, progress=70.0%, estimated_time=36s
Task task_xxx: Status updated - state=success, progress=100.0%, estimated_time=0s
```

## 验证修复

### 1. 检查数据库

```bash
python scripts/check_task_progress.py
```

应该看到新任务的 `progress` 和 `estimated_time` 都有值。

### 2. 检查 API 响应

```bash
curl -H "Authorization: Bearer <token>" \
  http://localhost:8000/api/tasks/<task_id>/status
```

应该返回：
```json
{
  "task_id": "task_xxx",
  "state": "transcribing",
  "progress": 40.0,
  "estimated_time": 72,
  "error_details": null,
  "updated_at": "2026-01-22T16:30:00"
}
```

### 3. 前端轮询

前端每 2 秒轮询一次，应该看到：
- `progress` 从 0% 逐步增加到 100%
- `estimated_time` 从 120 秒逐步减少到 0
- `state` 从 `transcribing` 变化到 `success`

## 为什么之前显示 4 分钟？

如果你看到 `estimated_time` 是 240 秒（4 分钟），可能是：

1. **旧数据**：这是之前某个任务的缓存值
2. **错误计算**：如果音频时长是 960 秒（16 分钟），那么 960 × 0.25 = 240 秒

但你说音频只有 8 分钟（480 秒），那么：
- 正确的预估总时间 = 480 × 0.25 = **120 秒（2 分钟）**
- 进度 0% 时剩余 = 120 秒
- 进度 40% 时剩余 = 72 秒
- 进度 60% 时剩余 = 48 秒
- 进度 80% 时剩余 = 24 秒

## 常见问题

### Q: 重启 worker 后还是 0%？

A: 检查：
1. Worker 是否真的重启了（查看进程 ID）
2. Worker 日志是否有错误
3. 是否在查看旧任务（旧任务的进度不会更新）

### Q: 如何确认 worker 使用了新代码？

A: 查看 worker 日志，应该看到：
```
Task xxx: Status updated - state=transcribing, progress=40.0%, estimated_time=72s
```

如果没有这样的日志，说明还是旧代码。

### Q: 旧任务的进度能更新吗？

A: 不能。旧任务已经完成，进度永远是 0%。只有新创建的任务才会有正确的进度。

### Q: 前端还是显示 0%？

A: 检查：
1. 前端是否在轮询正确的任务 ID
2. 前端是否有缓存（清除浏览器缓存）
3. API 响应是否正确（用 curl 测试）

## 修改的文件

- ✅ `src/services/pipeline.py` - 添加进度更新
- ✅ `src/database/repositories.py` - 支持 estimated_time
- ✅ `src/queue/worker.py` - 初始化 task_repo
- ✅ `scripts/diagnose_progress_issue.py` - 诊断工具
- ✅ `scripts/test_progress_tracking.py` - 监控工具
- ✅ `scripts/check_task_progress.py` - 检查工具

## 下一步

1. **立即重启 worker**
2. 创建新任务测试
3. 使用监控脚本验证
4. 如果还有问题，查看 worker 日志并反馈

---

**重要提醒**：必须重启 worker 才能生效！旧的 worker 进程不会自动加载新代码。

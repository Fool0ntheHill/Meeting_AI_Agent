# Workspace 页面 API 集成指南

## 问题总结

Workspace 页面显示问题的根本原因：

1. ✅ **Artifact 保存** - 已修复（需要重启 worker）
2. ✅ **Artifact 详情 API** - 已添加 `GET /api/v1/artifacts/{artifact_id}`
3. ⚠️ **数据格式** - 需要前端适配

## API 响应格式

### 1. GET /api/v1/tasks/{task_id}

```json
{
  "task_id": "task_xxx",
  "audio_files": ["uploads/user_test_user/xxx.ogg"],  // 相对路径
  "duration": 479.09,  // 秒，不是毫秒
  "state": "success",
  ...
}
```

**前端需要处理：**
- `audio_files[0]` 是相对路径，需要拼接 `http://localhost:8000/` 前缀
- `duration` 单位是秒（float），不是毫秒

### 2. GET /api/v1/tasks/{task_id}/transcript

```json
{
  "task_id": "task_xxx",
  "segments": [  // 注意：是 segments，不是 paragraphs
    {
      "text": "...",
      "start_time": 2.73,
      "end_time": 14.53,
      "speaker": "Speaker 1",  // 原始标签
      "confidence": null
    }
  ],
  "speaker_mapping": {  // 新增：说话人姓名映射
    "Speaker 1": "林煜东",
    "Speaker 2": "蓝为一"
  },
  "full_text": "...",
  "duration": 479.09,
  "language": "zh-CN",
  "provider": "volcano"
}
```

**前端需要处理：**
- 字段名是 `segments`，不是 `paragraphs`
- 每个 segment 有 `start_time`, `end_time`, `speaker`, `text`
- **新增**：使用 `speaker_mapping` 自动替换 speaker 显示（前端已实现）

### 3. GET /api/v1/tasks/{task_id}/artifacts

```json
{
  "task_id": "task_xxx",
  "artifacts_by_type": {
    "meeting_minutes": [
      {
        "artifact_id": "art_task_xxx_meeting_minutes_v1",
        "version": 1,
        "created_at": "2026-01-20T06:36:16.742013",
        ...
      }
    ]
  },
  "total_count": 1
}
```

**前端需要处理：**
- 使用 `artifact_id` 调用详情 API 获取 content

### 4. GET /api/v1/artifacts/{artifact_id}

**新增的独立路由**，不需要 task_id。

```json
{
  "artifact": {
    "artifact_id": "art_task_xxx_meeting_minutes_v1",
    "task_id": "task_xxx",
    "artifact_type": "meeting_minutes",
    "version": 1,
    "content": "...",  // JSON 字符串或对象（取决于后端版本）
    "created_at": "2026-01-20T06:36:16.742013",
    "created_by": "user_test_user"
  }
}
```

**前端需要处理：**

#### 方案 A：后端已重启（推荐）
如果后端已重启，`content` 会是一个对象：
```typescript
const content = response.artifact.content;  // 直接是对象
console.log(content.会议概要);  // 可以直接访问
```

#### 方案 B：后端未重启（临时方案）
如果后端未重启，`content` 是 JSON 字符串：
```typescript
const content = typeof response.artifact.content === 'string' 
  ? JSON.parse(response.artifact.content)
  : response.artifact.content;
```

## 前端修改建议

### 1. 音频播放器
```typescript
// 当前可能的代码
const audioUrl = currentTask.audio_files[0];

// 修改为
const audioUrl = `http://localhost:8000/${currentTask.audio_files[0]}`;
// 或使用环境变量
const audioUrl = `${API_BASE_URL}/${currentTask.audio_files[0]}`;
```

### 2. Transcript 显示
```typescript
// 当前可能的代码
const paragraphs = transcriptData.paragraphs;

// 修改为
const segments = transcriptData.segments;
const speakerMapping = transcriptData.speaker_mapping;  // 新增

// 如果需要转换为 paragraphs 格式
const paragraphs = segments.map(seg => ({
  speaker: speakerMapping?.[seg.speaker] || seg.speaker,  // 使用真实姓名
  text: seg.text,
  startTime: seg.start_time,
  endTime: seg.end_time
}));
```

**注意**：前端已在 `task.ts` 中实现自动替换，无需额外修改。

### 3. Artifact 内容获取
```typescript
// 步骤 1: 获取 artifact 列表
const artifactsResponse = await fetch(`/api/v1/tasks/${taskId}/artifacts`);
const artifactsData = await artifactsResponse.json();

// 步骤 2: 获取第一个 meeting_minutes 的详情
const artifactId = artifactsData.artifacts_by_type.meeting_minutes[0].artifact_id;

// 步骤 3: 调用详情 API
const detailResponse = await fetch(`/api/v1/artifacts/${artifactId}`);
const detailData = await detailResponse.json();

// 步骤 4: 解析 content（兼容两种格式）
const content = typeof detailData.artifact.content === 'string'
  ? JSON.parse(detailData.artifact.content)
  : detailData.artifact.content;

// 步骤 5: 使用 content
console.log(content.会议概要);
console.log(content.讨论要点);
console.log(content.决策事项);
console.log(content.行动项);
```

## 后端状态

### 已完成
- ✅ Artifact 保存功能（需要重启 worker）
- ✅ 独立的 artifact 详情 API
- ✅ Content 字段解析（需要重启后端）

### 需要重启的服务
1. **Worker** - 使用新代码保存 artifacts
2. **Backend API** - 使用新代码返回解析后的 content

### 重启命令
```bash
# 重启 worker
python worker.py

# 重启 backend（如果使用 uvicorn）
python -m uvicorn src.api.app:app --reload --host 0.0.0.0 --port 8000
```

## 测试验证

### 测试脚本
```bash
# 测试 artifact 是否保存
python scripts/check_artifacts_in_db.py

# 测试 API 响应
python scripts/get_api_responses.py

# 测试 content 类型
python scripts/test_artifact_content_type.py
```

### 预期结果
- Artifact 数量 > 0
- GET /api/v1/artifacts/{artifact_id} 返回 200
- content 字段是对象（后端重启后）或字符串（后端未重启）

## 常见问题

### Q: 为什么 content 还是字符串？
A: 后端代码已修改，但需要重启才能生效。在重启前，前端可以使用 `JSON.parse()` 临时处理。

### Q: 音频无法播放？
A: 检查是否拼接了完整的 URL。后端返回的是相对路径 `uploads/...`，需要加上 `http://localhost:8000/` 前缀。

### Q: Transcript 显示为空？
A: 检查是否使用了正确的字段名 `segments` 而不是 `paragraphs`。

### Q: Artifact 列表为空？
A: 确保 worker 已重启并处理了新任务。旧任务的 artifacts 不会被自动生成。

## 联系方式

如有问题，请检查：
1. 后端日志（`python main.py` 的输出）
2. Worker 日志（`python worker.py` 的输出）
3. 浏览器开发者工具的 Network 标签

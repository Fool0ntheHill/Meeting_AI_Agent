# API 响应示例大全

**用途**: 前端开发时参考，了解每个 API 返回的真实数据结构

**说明**: 
- 所有示例都是真实的 API 响应
- 前端只需要关心这些响应数据，不需要了解数据库结构
- 数据库如何存储是后端的事，前端通过 API 获取处理好的数据

---

## 目录

1. [认证相关](#认证相关)
2. [文件上传](#文件上传)
3. [任务管理](#任务管理)
4. [转写记录](#转写记录)
5. [生成内容](#生成内容)
6. [模板管理](#模板管理)
7. [热词管理](#热词管理)
8. [修正记录](#修正记录)

---

## 认证相关

### POST /auth/dev/login - 开发环境登录

**请求**:
```json
{
  "username": "test_user"
}
```

**响应** (200):
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 86400,
  "user": {
    "user_id": "user_123abc",
    "username": "test_user",
    "tenant_id": "tenant_456def"
  }
}
```

**使用方式**:
```typescript
// 保存 token
localStorage.setItem('access_token', response.access_token);
localStorage.setItem('user_id', response.user.user_id);
localStorage.setItem('tenant_id', response.user.tenant_id);

// 后续请求带上 token
headers: {
  'Authorization': `Bearer ${access_token}`
}
```

---

## 文件上传

### POST /upload - 上传音频文件

**请求**:
```typescript
const formData = new FormData();
formData.append('file', audioFile);
```

**响应** (201):
```json
{
  "success": true,
  "file_path": "uploads/user_123abc/a1b2c3d4e5f6g7h8.wav",
  "file_size": 15728640,
  "duration": 180.5,
  "message": "文件上传成功: meeting_audio.wav"
}
```

**前端使用**:
```typescript
// 保存 file_path，用于创建任务
const uploadedFiles = [
  {
    file_path: response.file_path,
    speaker_id: "speaker_0"
  }
];
```

---

## 任务管理

### POST /tasks - 创建任务

**请求**:
```json
{
  "audio_files": [
    {
      "file_path": "uploads/user_123abc/a1b2c3d4e5f6g7h8.wav",
      "speaker_id": "speaker_0"
    }
  ],
  "meeting_type": "internal",
  "asr_language": "zh-CN+en-US",
  "output_language": "zh-CN",
  "prompt_instance": {
    "template_id": "meeting_minutes_default",
    "language": "zh-CN",
    "parameters": {
      "focus_areas": ["决策", "行动项"]
    }
  },
  "skip_speaker_recognition": false
}
```

**响应** (201):
```json
{
  "task_id": "task_789xyz",
  "state": "pending",
  "message": "任务创建成功"
}
```

### GET /tasks/{task_id} - 获取任务详情

**响应** (200):
```json
{
  "task_id": "task_789xyz",
  "user_id": "user_123abc",
  "tenant_id": "tenant_456def",
  "meeting_type": "internal",
  "audio_files": [
    {
      "file_path": "uploads/user_123abc/a1b2c3d4e5f6g7h8.wav",
      "speaker_id": "speaker_0"
    }
  ],
  "file_order": [0],
  "asr_language": "zh-CN+en-US",
  "output_language": "zh-CN",
  "skip_speaker_recognition": false,
  "hotword_set_id": null,
  "preferred_asr_provider": "volcano",
  "state": "running",
  "progress": 45.5,
  "estimated_time": 120,
  "error_details": null,
  "is_confirmed": false,
  "confirmed_by": null,
  "confirmed_by_name": null,
  "confirmed_at": null,
  "confirmation_items": null,
  "created_at": "2026-01-16T10:30:00Z",
  "updated_at": "2026-01-16T10:32:15Z",
  "completed_at": null
}
```

**任务状态变化**:
```
pending -> queued -> running -> transcribing -> identifying -> 
correcting -> summarizing -> success
                                              ↓
                                           failed
```

### GET /tasks - 获取任务列表

**请求参数**:
```
?state=success&limit=20&offset=0&sort_by=created_at&sort_order=desc
```

**响应** (200):
```json
{
  "tasks": [
    {
      "task_id": "task_789xyz",
      "meeting_type": "internal",
      "state": "success",
      "progress": 100.0,
      "is_confirmed": false,
      "created_at": "2026-01-16T10:30:00Z",
      "updated_at": "2026-01-16T10:35:00Z",
      "completed_at": "2026-01-16T10:35:00Z"
    },
    {
      "task_id": "task_456abc",
      "meeting_type": "client",
      "state": "success",
      "progress": 100.0,
      "is_confirmed": true,
      "created_at": "2026-01-15T14:20:00Z",
      "updated_at": "2026-01-15T14:28:00Z",
      "completed_at": "2026-01-15T14:28:00Z"
    }
  ],
  "total": 42,
  "limit": 20,
  "offset": 0
}
```

### POST /tasks/{task_id}/confirm - 确认任务

**请求**:
```json
{
  "confirmed_by_name": "张三",
  "confirmation_items": {
    "key_conclusions": true,
    "responsible_persons": true,
    "action_items": true,
    "timeline": false
  }
}
```

**响应** (200):
```json
{
  "task_id": "task_789xyz",
  "is_confirmed": true,
  "confirmed_by": "user_123abc",
  "confirmed_by_name": "张三",
  "confirmed_at": "2026-01-16T11:00:00Z",
  "confirmation_items": {
    "key_conclusions": true,
    "responsible_persons": true,
    "action_items": true,
    "timeline": false
  }
}
```

---

## 转写记录

### GET /tasks/{task_id}/transcript - 获取转写记录

**响应** (200):
```json
{
  "transcript_id": "transcript_abc123",
  "task_id": "task_789xyz",
  "segments": [
    {
      "text": "大家好，今天我们讨论一下项目进度。",
      "start_time": 0.0,
      "end_time": 3.5,
      "speaker_label": "Speaker 0",
      "speaker_name": "张三",
      "confidence": 0.95
    },
    {
      "text": "好的，我先汇报一下我这边的情况。",
      "start_time": 3.8,
      "end_time": 6.2,
      "speaker_label": "Speaker 1",
      "speaker_name": "李四",
      "confidence": 0.92
    },
    {
      "text": "我们已经完成了第一阶段的开发。",
      "start_time": 6.5,
      "end_time": 9.0,
      "speaker_label": "Speaker 1",
      "speaker_name": "李四",
      "confidence": 0.94
    }
  ],
  "full_text": "大家好，今天我们讨论一下项目进度。好的，我先汇报一下我这边的情况。我们已经完成了第一阶段的开发。",
  "duration": 180.5,
  "language": "zh-CN",
  "provider": "volcano",
  "is_corrected": false,
  "created_at": "2026-01-16T10:32:00Z"
}
```

**前端使用场景**:
- 显示逐字稿列表
- 点击时间戳跳转音频播放位置
- 高亮当前播放的文本
- 按说话人筛选

---

## 生成内容

### GET /tasks/{task_id}/artifacts - 获取所有生成内容

**响应** (200):
```json
{
  "task_id": "task_789xyz",
  "artifacts_by_type": {
    "meeting_minutes": [
      {
        "artifact_id": "artifact_001",
        "task_id": "task_789xyz",
        "artifact_type": "meeting_minutes",
        "version": 2,
        "prompt_instance": {
          "template_id": "meeting_minutes_default",
          "language": "zh-CN",
          "parameters": {}
        },
        "created_at": "2026-01-16T10:40:00Z",
        "created_by": "user_123abc"
      },
      {
        "artifact_id": "artifact_002",
        "task_id": "task_789xyz",
        "artifact_type": "meeting_minutes",
        "version": 1,
        "prompt_instance": {
          "template_id": "meeting_minutes_default",
          "language": "zh-CN",
          "parameters": {}
        },
        "created_at": "2026-01-16T10:35:00Z",
        "created_by": "system"
      }
    ],
    "action_items": [
      {
        "artifact_id": "artifact_003",
        "task_id": "task_789xyz",
        "artifact_type": "action_items",
        "version": 1,
        "prompt_instance": {
          "template_id": "action_items_default",
          "language": "zh-CN",
          "parameters": {}
        },
        "created_at": "2026-01-16T10:35:00Z",
        "created_by": "system"
      }
    ]
  },
  "total_count": 3
}
```

### GET /artifacts/{artifact_id} - 获取生成内容详情

**响应** (200):
```json
{
  "artifact_id": "artifact_001",
  "task_id": "task_789xyz",
  "artifact_type": "meeting_minutes",
  "version": 2,
  "prompt_instance": {
    "template_id": "meeting_minutes_default",
    "language": "zh-CN",
    "parameters": {}
  },
  "content": {
    "title": "项目进度讨论会议纪要",
    "date": "2026-01-16",
    "participants": ["张三", "李四", "王五"],
    "summary": "本次会议主要讨论了项目第一阶段的完成情况和第二阶段的计划安排。",
    "key_points": [
      {
        "topic": "第一阶段完成情况",
        "content": "已完成核心功能开发，测试覆盖率达到 85%。",
        "speaker": "李四"
      },
      {
        "topic": "第二阶段计划",
        "content": "预计在下月初启动，重点是性能优化和用户体验改进。",
        "speaker": "张三"
      }
    ],
    "decisions": [
      {
        "decision": "第一阶段验收通过",
        "rationale": "功能完整，质量达标",
        "decided_by": "张三"
      }
    ],
    "action_items": [
      {
        "task": "准备第二阶段需求文档",
        "assignee": "李四",
        "deadline": "2026-01-20",
        "priority": "high"
      },
      {
        "task": "组织用户体验评审会",
        "assignee": "王五",
        "deadline": "2026-01-25",
        "priority": "medium"
      }
    ],
    "next_steps": [
      "完成第一阶段文档归档",
      "启动第二阶段需求评审"
    ]
  },
  "metadata": {
    "regenerated": true,
    "regeneration_reason": "用户要求增加决策依据"
  },
  "created_at": "2026-01-16T10:40:00Z",
  "created_by": "user_123abc"
}
```

**注意**: `content` 字段是 JSON 对象，不是字符串！后端已经解析好了。

### GET /tasks/{task_id}/artifacts/{artifact_type}/versions - 获取版本列表

**响应** (200):
```json
{
  "task_id": "task_789xyz",
  "artifact_type": "meeting_minutes",
  "versions": [
    {
      "artifact_id": "artifact_001",
      "version": 2,
      "created_at": "2026-01-16T10:40:00Z",
      "created_by": "user_123abc",
      "prompt_instance": {
        "template_id": "meeting_minutes_default",
        "language": "zh-CN"
      }
    },
    {
      "artifact_id": "artifact_002",
      "version": 1,
      "created_at": "2026-01-16T10:35:00Z",
      "created_by": "system",
      "prompt_instance": {
        "template_id": "meeting_minutes_default",
        "language": "zh-CN"
      }
    }
  ],
  "total_versions": 2
}
```

### POST /artifacts/{artifact_id}/regenerate - 重新生成

**请求**:
```json
{
  "prompt_instance": {
    "template_id": "meeting_minutes_detailed",
    "language": "zh-CN",
    "parameters": {
      "focus_areas": ["决策依据", "风险分析"]
    }
  }
}
```

**响应** (201):
```json
{
  "artifact_id": "artifact_004",
  "task_id": "task_789xyz",
  "artifact_type": "meeting_minutes",
  "version": 3,
  "message": "重新生成成功，新版本号: 3"
}
```

---

## 模板管理

### GET /templates - 获取模板列表

**请求参数**:
```
?artifact_type=meeting_minutes&scope=global&language=zh-CN
```

**响应** (200):
```json
{
  "templates": [
    {
      "template_id": "meeting_minutes_default",
      "title": "标准会议纪要",
      "description": "适用于一般内部会议，包含摘要、关键点、决策和行动项。",
      "artifact_type": "meeting_minutes",
      "supported_languages": ["zh-CN", "en-US"],
      "parameter_schema": {
        "focus_areas": {
          "type": "array",
          "description": "重点关注的领域",
          "items": {
            "type": "string"
          },
          "optional": true
        }
      },
      "is_system": true,
      "scope": "global",
      "scope_id": null,
      "created_at": "2026-01-01T00:00:00Z",
      "updated_at": "2026-01-01T00:00:00Z"
    },
    {
      "template_id": "meeting_minutes_detailed",
      "title": "详细会议纪要",
      "description": "包含更详细的讨论过程、决策依据和风险分析。",
      "artifact_type": "meeting_minutes",
      "supported_languages": ["zh-CN"],
      "parameter_schema": {},
      "is_system": true,
      "scope": "global",
      "scope_id": null,
      "created_at": "2026-01-01T00:00:00Z",
      "updated_at": "2026-01-01T00:00:00Z"
    }
  ],
  "total": 2
}
```

### GET /templates/{template_id} - 获取模板详情

**响应** (200):
```json
{
  "template_id": "meeting_minutes_default",
  "title": "标准会议纪要",
  "description": "适用于一般内部会议，包含摘要、关键点、决策和行动项。",
  "prompt_body": "请根据以下会议转写内容，生成一份结构化的会议纪要...",
  "artifact_type": "meeting_minutes",
  "supported_languages": ["zh-CN", "en-US"],
  "parameter_schema": {
    "focus_areas": {
      "type": "array",
      "description": "重点关注的领域",
      "items": {
        "type": "string"
      },
      "optional": true
    }
  },
  "is_system": true,
  "scope": "global",
  "scope_id": null,
  "created_at": "2026-01-01T00:00:00Z",
  "updated_at": "2026-01-01T00:00:00Z"
}
```

### POST /templates - 创建私有模板

**请求**:
```json
{
  "title": "技术评审会议纪要",
  "description": "专门用于技术评审会议，重点记录技术决策和架构讨论。",
  "prompt_body": "请根据以下技术评审会议的转写内容...",
  "artifact_type": "meeting_minutes",
  "supported_languages": ["zh-CN"],
  "parameter_schema": {
    "tech_stack": {
      "type": "string",
      "description": "技术栈",
      "optional": true
    }
  }
}
```

**响应** (201):
```json
{
  "template_id": "template_user_001",
  "title": "技术评审会议纪要",
  "scope": "private",
  "scope_id": "user_123abc",
  "message": "模板创建成功"
}
```

### PUT /templates/{template_id} - 更新模板

**请求**:
```json
{
  "title": "技术评审会议纪要（更新版）",
  "description": "增加了性能指标和安全考虑的记录。"
}
```

**响应** (200):
```json
{
  "template_id": "template_user_001",
  "message": "模板更新成功"
}
```

### DELETE /templates/{template_id} - 删除模板

**响应** (204):
```
无响应体
```

---

## 热词管理

### GET /hotwords - 获取热词集列表

**请求参数**:
```
?scope=global&provider=volcano
```

**响应** (200):
```json
{
  "hotword_sets": [
    {
      "hotword_set_id": "hotword_global_001",
      "name": "全局通用热词",
      "provider": "volcano",
      "provider_resource_id": "boost_table_123",
      "scope": "global",
      "scope_id": null,
      "asr_language": "zh-CN+en-US",
      "description": "包含常用的技术术语和公司名称",
      "word_count": 150,
      "word_size": 2500,
      "created_at": "2026-01-01T00:00:00Z",
      "updated_at": "2026-01-10T00:00:00Z"
    }
  ],
  "total": 1
}
```

### GET /hotwords/{hotword_set_id} - 获取热词集详情

**响应** (200):
```json
{
  "hotword_set_id": "hotword_global_001",
  "name": "全局通用热词",
  "provider": "volcano",
  "provider_resource_id": "boost_table_123",
  "scope": "global",
  "scope_id": null,
  "asr_language": "zh-CN+en-US",
  "description": "包含常用的技术术语和公司名称",
  "word_count": 150,
  "word_size": 2500,
  "created_at": "2026-01-01T00:00:00Z",
  "updated_at": "2026-01-10T00:00:00Z"
}
```

---

## 修正记录

### GET /tasks/{task_id}/corrections - 获取修正记录

**响应** (200):
```json
{
  "task_id": "task_789xyz",
  "corrections": [
    {
      "correction_id": "correction_001",
      "correction_type": "speaker_name",
      "target_id": "mapping_001",
      "original_value": "Speaker 0",
      "corrected_value": "张三",
      "corrected_by": "user_123abc",
      "corrected_at": "2026-01-16T10:38:00Z"
    },
    {
      "correction_id": "correction_002",
      "correction_type": "transcript_text",
      "target_id": "segment_005",
      "original_value": "我们需要加快进度",
      "corrected_value": "我们需要加快进度，确保按时交付",
      "corrected_by": "user_123abc",
      "corrected_at": "2026-01-16T10:39:00Z"
    }
  ],
  "total": 2
}
```

### POST /tasks/{task_id}/corrections - 提交修正

**请求**:
```json
{
  "correction_type": "speaker_name",
  "target_id": "mapping_002",
  "corrected_value": "李四"
}
```

**响应** (201):
```json
{
  "correction_id": "correction_003",
  "message": "修正已保存"
}
```

---

## 错误响应

### 400 Bad Request - 请求参数错误

```json
{
  "detail": "audio_files 不能为空"
}
```

### 401 Unauthorized - 未认证

```json
{
  "detail": "未认证，请先登录"
}
```

### 403 Forbidden - 无权限

```json
{
  "detail": "无权访问此资源"
}
```

### 404 Not Found - 资源不存在

```json
{
  "detail": "任务不存在: task_999"
}
```

### 413 Payload Too Large - 文件过大

```json
{
  "detail": "文件过大: 520.5MB，最大支持 500MB"
}
```

### 415 Unsupported Media Type - 不支持的文件格式

```json
{
  "detail": "不支持的文件格式: .mp4，支持的格式: .wav, .opus, .mp3, .m4a"
}
```

### 422 Unprocessable Entity - 验证错误

```json
{
  "detail": [
    {
      "loc": ["body", "meeting_type"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```

### 429 Too Many Requests - 请求过于频繁

```json
{
  "detail": "请求过于频繁，请稍后再试"
}
```

### 500 Internal Server Error - 服务器错误

```json
{
  "detail": "服务器内部错误，请联系管理员"
}
```

---

## 前端开发建议

### 1. 不需要关心数据库结构

前端开发者**不需要知道**：
- 数据库用的是 SQLite 还是 PostgreSQL
- 表结构是什么样的
- 字段类型是什么
- 索引怎么建的

前端只需要知道：
- API 返回什么数据（看本文档）
- 数据的结构是什么（看 `frontend-types.ts`）
- 如何调用 API（看 `FRONTEND_DEVELOPMENT_GUIDE.md`）

### 2. 使用 TypeScript 类型定义

```typescript
// 从 frontend-types.ts 导入类型
import type { 
  Task, 
  TaskStatus, 
  Artifact, 
  TranscriptSegment 
} from '@/types/frontend-types';

// 使用类型
const task: Task = await api.getTask(taskId);
const artifacts: Artifact[] = await api.getArtifacts(taskId);
```

### 3. 使用 Swagger UI 测试

访问 http://localhost:8000/docs 可以：
- 查看所有 API 端点
- 在线测试 API
- 查看请求/响应示例
- 下载 OpenAPI 规范

### 4. 使用 Postman 集合

导入 `docs/api_references/postman_collection.json` 可以：
- 快速测试所有 API
- 保存测试用例
- 分享给团队成员

---

## 总结

**前端开发的关键文档**：

1. **本文档** (`API_RESPONSE_EXAMPLES.md`) - 了解 API 返回什么数据
2. **`FRONTEND_DEVELOPMENT_GUIDE.md`** - 了解如何调用 API
3. **`frontend-types.ts`** - TypeScript 类型定义
4. **`BACKEND_API_INFO.md`** - 后端地址和认证信息
5. **Swagger UI** (http://localhost:8000/docs) - 在线测试

**不需要看的文档**：
- `src/database/models.py` - 数据库模型（后端的事）
- `database_migration_guide.md` - 数据库迁移（后端的事）
- 任何包含 "database" 的文档（后端的事）

**记住**：前端通过 API 获取数据，不需要关心后端如何存储！

# 前端 API 缺口分析与待办事项

**更新日期**: 2026-01-16  
**状态**: 关键缺口已补齐 ✅

---

## 📊 当前状态总结

### ✅ 已实现的核心接口

| 功能 | 接口 | 状态 |
|------|------|------|
| 用户认证 | POST /api/v1/auth/dev/login | ✅ 完成 |
| **音频上传** | **POST /api/v1/upload** | **✅ 新增** |
| **删除上传** | **DELETE /api/v1/upload/{file_path}** | **✅ 新增** |
| 创建任务 | POST /api/v1/tasks | ✅ 完成 |
| 查询状态 | GET /api/v1/tasks/{id}/status | ✅ 完成 |
| 任务详情 | GET /api/v1/tasks/{id} | ✅ 完成 |
| **任务列表** | **GET /api/v1/tasks?state=xxx** | **✅ 增强** |
| **获取转写** | **GET /api/v1/tasks/{id}/transcript** | **✅ 新增** |
| 删除任务 | DELETE /api/v1/tasks/{id} | ✅ 完成 |
| 成本预估 | POST /api/v1/tasks/estimate | ✅ 完成 |
| 列出衍生内容 | GET /api/v1/tasks/{id}/artifacts | ✅ 完成 |
| 衍生内容详情 | GET /api/v1/tasks/{id}/artifacts/{aid} | ✅ 完成 |
| 生成新版本 | POST /api/v1/tasks/{id}/artifacts/{type}/generate | ✅ 完成 |
| 版本列表 | GET /api/v1/tasks/{id}/artifacts/{type}/versions | ✅ 完成 |
| 修正转写 | PUT /api/v1/tasks/{id}/transcript | ✅ 完成 |
| 修正说话人 | PATCH /api/v1/tasks/{id}/speakers | ✅ 完成 |
| 任务确认 | POST /api/v1/tasks/{id}/confirm | ✅ 完成 |
| 列出模板 | GET /api/v1/prompt-templates | ✅ 完成 |
| 模板详情 | GET /api/v1/prompt-templates/{id} | ✅ 完成 |
| 创建模板 | POST /api/v1/prompt-templates | ✅ 完成 |
| 更新模板 | PUT /api/v1/prompt-templates/{id} | ✅ 完成 |
| 删除模板 | DELETE /api/v1/prompt-templates/{id} | ✅ 完成 |
| 热词管理 | POST/GET/DELETE /api/v1/hotword-sets | ✅ 完成 |

---

## ✅ 已解决的关键缺口

### 1. 音频文件上传 ✅

**接口**: `POST /api/v1/upload`

**功能**:
- 支持上传 .wav, .opus, .mp3, .m4a 格式
- 最大文件大小 500MB
- 自动获取音频时长
- 用户隔离 (uploads/{user_id}/)

**请求**:
```bash
POST /api/v1/upload
Content-Type: multipart/form-data

file: <audio_file>
```

**响应**:
```json
{
  "success": true,
  "file_path": "uploads/user_123/meeting_20260116.wav",
  "file_size": 1024000,
  "duration": 300.5
}
```

**前端使用**:
```typescript
const formData = new FormData();
formData.append('file', audioFile);

const response = await fetch('/api/v1/upload', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${token}`
  },
  body: formData
});

const { file_path, duration } = await response.json();
```

---

### 2. 任务列表状态筛选 ✅

**接口**: `GET /api/v1/tasks?state={state}`

**新增参数**:
- `state`: 按状态筛选 (pending/running/success/failed)

**前端使用**:
```typescript
// 只显示进行中的任务
GET /api/v1/tasks?state=running&limit=20

// 只显示已完成的任务
GET /api/v1/tasks?state=success&limit=20

// 只显示失败的任务
GET /api/v1/tasks?state=failed&limit=20
```

---

### 3. 获取转写文本 ✅

**接口**: `GET /api/v1/tasks/{task_id}/transcript`

**响应**:
```json
{
  "task_id": "task_abc123",
  "segments": [
    {
      "text": "大家好",
      "start_time": 0.0,
      "end_time": 1.5,
      "speaker": "张三",
      "confidence": 0.95
    }
  ],
  "full_text": "大家好，今天我们讨论...",
  "duration": 300.5,
  "language": "zh-CN",
  "provider": "volcano"
}
```

**前端使用**:
```typescript
// 获取转写文本用于显示和编辑
const transcript = await api.getTranscript(taskId);

// 显示逐字稿
transcript.segments.forEach(seg => {
  console.log(`[${seg.start_time}s] ${seg.speaker}: ${seg.text}`);
});
```

---

## 📝 剩余待办事项

### P2 - 文档完善
- [ ] **补充错误码文档**
  - 文件: `docs/FRONTEND_DEVELOPMENT_GUIDE.md`
  - 内容: 文件上传、超时等错误说明
  - 预计工时: 0.5 小时

---

## 🎯 完成情况

| 优先级 | 任务 | 状态 |
|--------|------|------|
| P0 | 音频上传接口 | ✅ 已完成 |
| P1 | 任务列表状态筛选 | ✅ 已完成 |
| P1 | 获取转写文本接口 | ✅ 已完成 |
| P2 | 错误码文档 | ⏳ 待完成 |

---

## 🔗 相关文档

- **完整开发指南**: `docs/FRONTEND_DEVELOPMENT_GUIDE.md`
- **功能清单**: `docs/FRONTEND_FEATURE_CHECKLIST.md`
- **快速参考**: `docs/FRONTEND_QUICK_REFERENCE.md`
- **类型定义**: `docs/frontend-types.ts`

---

## 📞 联系方式

如有问题或需要讨论优先级，请联系后端团队。

**维护者**: 后端开发团队  
**最后更新**: 2026-01-16

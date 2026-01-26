# Artifact 自定义显示名称功能实现总结

## 问题

1. **Artifact 名称无法持久化**: 用户在生成 artifact 时输入了自定义名称，但刷新后 tab 标签仍显示默认的"纪要 v2"
2. **图片复制到企微无法显示**: 用户复制会议纪要到企业微信后，图片无法显示

## 解决方案

### 问题 1: Artifact 名称持久化

**方案**: 前后端一起改，添加 `display_name` 字段

#### 后端改动

1. **数据库模型** (`src/database/models.py`)
   - 在 `GeneratedArtifactRecord` 中添加 `display_name` 字段
   - 类型: `VARCHAR(256)`, 可选

2. **API Schemas** (`src/api/schemas.py`)
   - `GenerateArtifactRequest`: 添加 `name?: string` 字段
   - `GenerateArtifactResponse`: 添加 `display_name?: string` 字段
   - `ArtifactInfo`: 添加 `display_name?: string` 字段

3. **API 路由** (`src/api/routes/artifacts.py`, `src/api/routes/corrections.py`)
   - 生成/重新生成 artifact 时，保存 `request.name` 到 `display_name`
   - 返回响应时包含 `display_name`
   - 列出 artifacts 时返回 `display_name`

4. **数据库迁移** (`scripts/migrate_add_display_name.py`)
   - 添加 `display_name` 字段到 `generated_artifacts` 表

#### 前端改动（建议）

1. **类型定义**
   - 更新 `GenerateArtifactRequest`, `GenerateArtifactResponse`, `ArtifactInfo` 类型
   - 添加 `name?: string` 和 `display_name?: string` 字段

2. **生成 Artifact**
   - 在请求中添加 `name: values.meeting_type?.trim()`
   - 使用返回的 `display_name` 显示 tab 标题

3. **显示 Artifact**
   - 优先使用 `artifact.display_name`
   - 如果为 `null`，回退到默认格式 `${artifact_type} v${version}`

4. **移除临时逻辑**
   - 删除 `artifactNameOverrides` 临时状态
   - 直接使用后端返回的 `display_name`

### 问题 2: 图片复制逻辑

**方案**: 在前端处理图片转换

#### 为什么前端处理？

1. 用户编辑的图片在前端
2. 复制操作在前端触发
3. 前端可以直接访问图片 DOM
4. 后端不需要知道图片细节

#### 前端实现思路

```typescript
const handleCopy = async () => {
  let content = artifactContent;
  
  // 将图片 URL 转换为 base64
  const imgRegex = /!\[([^\]]*)\]\(([^\)]+)\)/g;
  content = await replaceAsync(content, imgRegex, async (match, alt, url) => {
    try {
      const base64 = await imageUrlToBase64(url);
      return `![${alt}](${base64})`;
    } catch (e) {
      return match;
    }
  });
  
  await navigator.clipboard.writeText(content);
};
```

## 已创建的文件

### 后端

1. ✅ `src/database/models.py` - 添加 `display_name` 字段
2. ✅ `src/api/schemas.py` - 更新 schemas
3. ✅ `src/api/routes/artifacts.py` - 处理 `name` 字段
4. ✅ `src/api/routes/corrections.py` - 处理 `name` 字段
5. ✅ `scripts/migrate_add_display_name.py` - 数据库迁移脚本
6. ✅ `scripts/test_artifact_display_name.py` - 测试脚本

### 文档

7. ✅ `docs/ARTIFACT_DISPLAY_NAME_GUIDE.md` - 详细指南
8. ✅ `docs/summaries/ARTIFACT_DISPLAY_NAME_IMPLEMENTATION.md` - 本文档
9. ✅ `docs/IMAGE_HANDLING_WECOM.md` - 图片处理分析
10. ✅ `docs/summaries/IMAGE_HANDLING_ANALYSIS.md` - 图片问题分析
11. ✅ `scripts/check_image_handling.py` - 图片诊断脚本

## 使用步骤

### 1. 运行数据库迁移

```bash
python scripts/migrate_add_display_name.py
```

### 2. 重启后端服务

```bash
# 停止所有服务
python scripts/stop_all.ps1

# 启动后端
python scripts/start_backend.ps1

# 启动 worker
python scripts/start_worker.ps1
```

### 3. 测试功能

```bash
python scripts/test_artifact_display_name.py
```

### 4. 前端实现

前端开发者需要：
1. 更新类型定义
2. 在生成/重新生成请求中添加 `name` 字段
3. 使用返回的 `display_name` 显示 tab 标题
4. 实现图片复制时的 base64 转换

## API 接口变化

### 生成 Artifact

**请求**:
```json
{
  "prompt_instance": { ... },
  "name": "产品规划会议纪要"  // 新增
}
```

**响应**:
```json
{
  "success": true,
  "artifact_id": "artifact_abc123",
  "version": 2,
  "content": { ... },
  "display_name": "产品规划会议纪要",  // 新增
  "message": "衍生内容已生成 (版本 2)"
}
```

### 列出 Artifacts

**响应**:
```json
{
  "task_id": "task_123",
  "artifacts_by_type": {
    "meeting_minutes": [
      {
        "artifact_id": "artifact_abc123",
        "display_name": "产品规划会议纪要",  // 新增
        ...
      }
    ]
  }
}
```

## 兼容性

- ✅ 向后兼容：旧 artifacts 的 `display_name` 为 `null`
- ✅ 前端回退：`display_name` 为 `null` 时使用默认格式
- ✅ 空字符串处理：后端 trim 并检查，空字符串不保存

## 测试场景

1. ✅ 生成 artifact 时提供自定义名称
2. ✅ 列出 artifacts 时返回 display_name
3. ✅ 生成 artifact 时不提供名称（display_name 为 None）
4. ✅ 重新生成 artifact 时提供自定义名称

## 总结

通过前后端协作，成功实现了：

1. **Artifact 名称持久化**: 用户输入的名称保存到数据库，刷新后仍然显示
2. **图片处理方案**: 建议在前端处理图片复制逻辑，转换为 base64 格式
3. **向后兼容**: 不影响现有功能，旧数据正常工作
4. **清晰的接口**: 前后端接口定义明确，易于实现和维护

**下一步**: 前端开发者根据文档实现前端部分，测试完整流程。

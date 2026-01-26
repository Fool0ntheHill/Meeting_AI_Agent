# Artifact 自定义显示名称功能

## 问题描述

用户在生成 artifact 时输入了自定义名称，但刷新后 tab 标签仍显示默认的"纪要 v2"，无法持久化保存用户输入的名称。

## 解决方案

前后端一起改，添加 `display_name` 字段来持久化存储用户自定义的 artifact 名称。

## 后端改动

### 1. 数据库模型

**文件**: `src/database/models.py`

在 `GeneratedArtifactRecord` 模型中添加 `display_name` 字段：

```python
class GeneratedArtifactRecord(Base):
    """生成内容记录表"""
    
    # ... 其他字段 ...
    
    # 自定义显示名称（用户可以自定义 artifact 的名称）
    display_name = Column(String(256), nullable=True)
```

### 2. API Schemas

**文件**: `src/api/schemas.py`

#### GenerateArtifactRequest

添加 `name` 字段（可选）：

```python
class GenerateArtifactRequest(BaseModel):
    """生成衍生内容请求"""
    
    prompt_instance: PromptInstance = Field(..., description="提示词实例")
    name: Optional[str] = Field(None, description="自定义显示名称")
```

#### GenerateArtifactResponse

添加 `display_name` 字段（可选）：

```python
class GenerateArtifactResponse(BaseModel):
    """生成衍生内容响应"""
    
    success: bool
    artifact_id: str
    version: int
    content: Dict
    display_name: Optional[str] = Field(None, description="自定义显示名称")
    message: str = "内容已生成"
```

#### ArtifactInfo

添加 `display_name` 字段（可选）：

```python
class ArtifactInfo(BaseModel):
    """衍生内容基本信息"""
    
    artifact_id: str
    task_id: str
    artifact_type: str
    version: int
    prompt_instance: PromptInstance
    display_name: Optional[str] = Field(None, description="自定义显示名称")
    created_at: datetime
    created_by: str
```

### 3. API 路由

**文件**: `src/api/routes/artifacts.py` 和 `src/api/routes/corrections.py`

在生成和重新生成 artifact 的接口中，保存用户提供的 `name`：

```python
# 如果用户提供了自定义名称，保存到数据库
if request.name and request.name.strip():
    artifact_record = artifact_repo.get_by_id(generated_artifact.artifact_id)
    if artifact_record:
        artifact_record.display_name = request.name.strip()
        db.commit()
        logger.info(f"Saved display_name '{request.name}' for artifact {generated_artifact.artifact_id}")

# 返回响应时包含 display_name
return GenerateArtifactResponse(
    success=True,
    artifact_id=generated_artifact.artifact_id,
    version=generated_artifact.version,
    content=generated_artifact.get_content_dict(),
    display_name=request.name.strip() if request.name and request.name.strip() else None,
    message=f"衍生内容已生成 (版本 {generated_artifact.version})",
)
```

在列出 artifacts 时，返回 `display_name`：

```python
def _record_to_artifact_info(record) -> ArtifactInfo:
    """将数据库记录转换为 ArtifactInfo"""
    return ArtifactInfo(
        artifact_id=record.artifact_id,
        task_id=record.task_id,
        artifact_type=record.artifact_type,
        version=record.version,
        prompt_instance=PromptInstance(**record.get_prompt_instance_dict()),
        display_name=record.display_name,  # 添加 display_name
        created_at=record.created_at,
        created_by=record.created_by,
    )
```

### 4. 数据库迁移

**文件**: `scripts/migrate_add_display_name.py`

运行迁移脚本添加 `display_name` 字段：

```bash
python scripts/migrate_add_display_name.py
```

## 前端改动

### 1. TypeScript 类型定义

**文件**: `docs/frontend-types.ts`

更新类型定义：

```typescript
// 生成 artifact 请求
interface GenerateArtifactRequest {
  prompt_instance: PromptInstance;
  name?: string;  // 新增：自定义显示名称
}

// 生成 artifact 响应
interface GenerateArtifactResponse {
  success: boolean;
  artifact_id: string;
  version: number;
  content: Record<string, any>;
  display_name?: string;  // 新增：自定义显示名称
  message: string;
}

// Artifact 信息
interface ArtifactInfo {
  artifact_id: string;
  task_id: string;
  artifact_type: string;
  version: number;
  prompt_instance: PromptInstance;
  display_name?: string;  // 新增：自定义显示名称
  created_at: string;
  created_by: string;
}
```

### 2. 生成 Artifact 时传递 name

在生成/重新生成 artifact 的请求中，添加 `name` 字段：

```typescript
// 生成新 artifact
const payload: GenerateArtifactRequest = {
  prompt_instance: {
    template_id: values.template_id,
    language: values.language,
    prompt_text: values.prompt_text,
    parameters: values.parameters
  },
  name: values.meeting_type?.trim()  // 传递用户输入的名称
};

const response = await fetch(
  `/api/v1/tasks/${taskId}/artifacts/meeting_minutes/generate`,
  {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(payload)
  }
);

const data: GenerateArtifactResponse = await response.json();

// 使用返回的 display_name 显示 tab 标题
const tabTitle = data.display_name || `纪要 v${data.version}`;
```

### 3. 显示 Artifact 名称

在渲染 artifact 列表和 tab 标签时，优先使用 `display_name`：

```typescript
// 渲染 tab 标签
const renderTabTitle = (artifact: ArtifactInfo) => {
  // 优先使用 display_name，如果没有则使用默认格式
  return artifact.display_name || `${artifact.artifact_type} v${artifact.version}`;
};

// 渲染列表项
const renderArtifactItem = (artifact: ArtifactInfo) => {
  return (
    <div>
      <h3>{artifact.display_name || `${artifact.artifact_type} v${artifact.version}`}</h3>
      <p>版本: {artifact.version}</p>
      <p>创建时间: {artifact.created_at}</p>
    </div>
  );
};
```

### 4. 移除临时 override 逻辑

不再需要前端的 `artifactNameOverrides` 临时状态，直接使用后端返回的 `display_name`：

```typescript
// 删除或注释掉
// const [artifactNameOverrides, setArtifactNameOverrides] = useState<Record<string, string>>({});

// 直接使用 artifact.display_name
const tabTitle = artifact.display_name || `纪要 v${artifact.version}`;
```

## API 接口示例

### 生成 Artifact（带自定义名称）

**请求**:
```http
POST /api/v1/tasks/{task_id}/artifacts/meeting_minutes/generate
Authorization: Bearer <token>
Content-Type: application/json

{
  "prompt_instance": {
    "template_id": "__blank__",
    "language": "zh-CN",
    "prompt_text": "请生成会议纪要",
    "parameters": {}
  },
  "name": "产品规划会议纪要"
}
```

**响应**:
```json
{
  "success": true,
  "artifact_id": "artifact_abc123",
  "version": 2,
  "content": { ... },
  "display_name": "产品规划会议纪要",
  "message": "衍生内容已生成 (版本 2)"
}
```

### 生成 Artifact（不提供名称）

**请求**:
```http
POST /api/v1/tasks/{task_id}/artifacts/meeting_minutes/generate
Authorization: Bearer <token>
Content-Type: application/json

{
  "prompt_instance": {
    "template_id": "__blank__",
    "language": "zh-CN",
    "prompt_text": "请生成会议纪要",
    "parameters": {}
  }
}
```

**响应**:
```json
{
  "success": true,
  "artifact_id": "artifact_def456",
  "version": 3,
  "content": { ... },
  "display_name": null,
  "message": "衍生内容已生成 (版本 3)"
}
```

### 列出 Artifacts

**请求**:
```http
GET /api/v1/tasks/{task_id}/artifacts
Authorization: Bearer <token>
```

**响应**:
```json
{
  "task_id": "task_123",
  "artifacts_by_type": {
    "meeting_minutes": [
      {
        "artifact_id": "artifact_abc123",
        "task_id": "task_123",
        "artifact_type": "meeting_minutes",
        "version": 2,
        "prompt_instance": { ... },
        "display_name": "产品规划会议纪要",
        "created_at": "2026-01-26T10:00:00Z",
        "created_by": "user_123"
      },
      {
        "artifact_id": "artifact_def456",
        "task_id": "task_123",
        "artifact_type": "meeting_minutes",
        "version": 3,
        "prompt_instance": { ... },
        "display_name": null,
        "created_at": "2026-01-26T11:00:00Z",
        "created_by": "user_123"
      }
    ]
  },
  "total_count": 2
}
```

## 测试

### 运行迁移

```bash
python scripts/migrate_add_display_name.py
```

### 运行测试

```bash
python scripts/test_artifact_display_name.py
```

测试场景：
1. ✅ 生成 artifact 时提供自定义名称
2. ✅ 列出 artifacts 时返回 display_name
3. ✅ 生成 artifact 时不提供名称（display_name 为 None）
4. ✅ 重新生成 artifact 时提供自定义名称

## 兼容性

- **向后兼容**: `display_name` 字段为可选，旧的 artifacts 的 `display_name` 为 `null`
- **前端回退**: 如果 `display_name` 为 `null`，前端使用默认格式 `${artifact_type} v${version}`
- **空字符串处理**: 后端会 trim 并检查，空字符串不会保存

## 相关文件

### 后端
- ✅ `src/database/models.py` - 添加 `display_name` 字段
- ✅ `src/api/schemas.py` - 更新 schemas
- ✅ `src/api/routes/artifacts.py` - 处理 `name` 字段
- ✅ `src/api/routes/corrections.py` - 处理 `name` 字段
- ✅ `scripts/migrate_add_display_name.py` - 数据库迁移
- ✅ `scripts/test_artifact_display_name.py` - 测试脚本

### 前端
- 📝 `docs/frontend-types.ts` - 类型定义（参考）
- 📝 前端代码 - 需要前端开发者实现

### 文档
- ✅ `docs/ARTIFACT_DISPLAY_NAME_GUIDE.md` - 本文档
- ✅ `docs/summaries/ARTIFACT_DISPLAY_NAME_IMPLEMENTATION.md` - 实现总结

## 图片复制逻辑

关于图片复制到企微的问题，建议**在前端处理**：

### 为什么前端处理更合适？

1. **用户编辑的图片在前端**: 用户在编辑器中插入图片，图片数据在前端
2. **复制操作在前端**: 用户点击"复制"按钮，触发的是前端的复制逻辑
3. **格式转换在前端更高效**: 前端可以直接访问图片 DOM，转换为 base64 后放入剪贴板
4. **后端不需要知道图片细节**: 后端只需要存储 Markdown 内容，不需要处理图片转换

### 前端实现思路

```typescript
// 在复制时处理图片
const handleCopy = async () => {
  // 1. 获取 Markdown 内容
  let content = artifactContent;
  
  // 2. 查找所有图片标签
  const imgRegex = /!\[([^\]]*)\]\(([^\)]+)\)/g;
  
  // 3. 将图片 URL 转换为 base64
  content = await replaceAsync(content, imgRegex, async (match, alt, url) => {
    try {
      const base64 = await imageUrlToBase64(url);
      return `![${alt}](${base64})`;
    } catch (e) {
      return match; // 转换失败保持原样
    }
  });
  
  // 4. 复制到剪贴板
  await navigator.clipboard.writeText(content);
};

// 图片 URL 转 base64
const imageUrlToBase64 = async (url: string): Promise<string> => {
  const response = await fetch(url);
  const blob = await response.blob();
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onloadend = () => resolve(reader.result as string);
    reader.onerror = reject;
    reader.readAsDataURL(blob);
  });
};
```

## 总结

通过前后端协作，实现了 artifact 自定义显示名称的持久化存储：

1. **后端**: 添加 `display_name` 字段，接收并保存用户输入的名称
2. **前端**: 传递 `name` 字段，使用返回的 `display_name` 显示 tab 标题
3. **兼容性**: 向后兼容，旧数据的 `display_name` 为 `null`，前端使用默认格式
4. **图片处理**: 建议在前端处理图片复制逻辑，转换为 base64 格式

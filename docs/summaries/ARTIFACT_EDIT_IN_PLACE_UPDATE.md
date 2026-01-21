# Artifact 原地更新功能完成

## 任务概述

实现 artifact 的原地更新（in-place update）功能，允许用户直接修改会议纪要内容，而不创建新版本。

## 实现内容

### 1. API 接口

**接口**: `PUT /api/v1/artifacts/{artifact_id}`

**功能**: 直接更新现有 artifact 的内容（原地更新）

**特点**:
- artifact_id 和 version 保持不变
- 直接替换 content 字段
- 自动添加元数据标记
- 更新任务的 last_content_modified_at

### 2. 元数据标记

更新时自动添加以下元数据：
- `manually_edited: true` - 标记为手动编辑
- `last_edited_at` - 最后编辑时间
- `last_edited_by` - 编辑者 user_id

### 3. 代码修改

#### src/api/routes/artifacts.py
- 修改 `PUT /artifacts/{artifact_id}` 端点
- 直接更新 artifact.content
- 使用 `set_metadata_dict()` 添加元数据
- 更新 task.last_content_modified_at

#### src/database/repositories.py
- 修复 `to_generated_artifact()` 方法
- 添加 metadata 字段的转换
- 确保元数据正确返回给前端

#### docs/FRONTEND_EDIT_GUIDE.md
- 更新文档说明原地更新行为
- 添加与 LLM 重新生成的对比表格
- 更新前端示例代码

#### scripts/test_artifact_update.py
- 更新测试脚本验证原地更新
- 验证 artifact_id 和 version 不变
- 验证 content 被更新
- 验证元数据正确保存

## 测试结果

```
✅ 更新成功！
   - artifact_id: artifact_6274c1eeb377462b (应该与原 ID 相同)
   - 消息: 内容已更新
   ✓ 确认：artifact_id 未变化（原地更新）

✓ 内容获取成功
   - 版本号: v2 (应该与原版本相同: v2)
   - 会议概要: 【已修改】【已修改】【已修改】本次会议主要评审了...
   - 其他: 这是通过 API 手动修改的测试
   ✓ 确认：版本号未变化（原地更新）
   ✓ 确认：内容已成功更新
   - 元数据: manually_edited=True
   - 元数据: last_edited_at=2026-01-20T08:44:58.009449
   - 元数据: last_edited_by=user_test_user
   ✓ 确认：已标记为手动编辑
```

## 两种修改方式对比

| 操作 | 接口 | 是否创建新版本 | 用途 |
|------|------|---------------|------|
| 手动编辑 | `PUT /artifacts/{artifact_id}` | ❌ 否（原地更新） | 用户直接修改内容 |
| LLM 重新生成 | `POST /corrections/{task_id}/artifacts/{type}/regenerate` | ✅ 是 | 使用修改后的 transcript 重新生成 |

## 前端集成指南

### 调用示例

```typescript
async function updateArtifact(artifactId: string, content: Record<string, any>) {
  const response = await fetch(
    `/api/v1/artifacts/${artifactId}`,
    {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      },
      body: JSON.stringify(content)  // 直接发送 content 对象
    }
  );
  
  return await response.json();
}
```

### 响应格式

```typescript
interface UpdateArtifactResponse {
  success: boolean;
  artifact_id: string;  // 相同的 artifact_id（原地更新）
  message: string;
}
```

### 保存后处理

```typescript
async function handleSaveArtifact() {
  try {
    const result = await updateArtifact(currentArtifactId, artifactContent);
    
    if (result.success) {
      toast.success('已保存修改');
      setIsEditing(false);
      
      // 刷新当前 artifact（artifact_id 不变）
      await refreshCurrentArtifact();
    }
  } catch (error) {
    toast.error('保存失败');
  }
}
```

## 完整的编辑接口

后端现在提供 4 个编辑接口：

1. ✅ `PUT /corrections/{task_id}/transcript` - 修改逐字稿
2. ✅ `PATCH /corrections/{task_id}/speakers` - 修改说话人
3. ✅ `POST /corrections/{task_id}/artifacts/{type}/regenerate` - 重新生成（创建新版本）
4. ✅ `PUT /artifacts/{artifact_id}` - 直接修改会议纪要内容（原地更新）

## 文件清单

- ✅ `src/api/routes/artifacts.py` - 更新 PUT 端点
- ✅ `src/database/repositories.py` - 修复 metadata 转换
- ✅ `docs/FRONTEND_EDIT_GUIDE.md` - 更新文档
- ✅ `scripts/test_artifact_update.py` - 更新测试脚本

## 状态

✅ **完成** - 原地更新功能已实现并测试通过

# 删除 Artifact API 前端集成指南

## 概述

本文档说明如何在前端调用删除 artifact 的 API。

## API 端点

```
DELETE /api/v1/tasks/{task_id}/artifacts/{artifact_id}
```

## 功能说明

- 删除指定的 artifact（会议纪要、摘要等衍生内容）
- 自动验证用户权限（只能删除自己任务的 artifact）
- 删除成功后更新任务的最后修改时间

## 请求参数

### 路径参数

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| task_id | string | 是 | 任务 ID |
| artifact_id | string | 是 | Artifact ID |

### 请求头

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| Authorization | string | 是 | Bearer Token（JWT） |

## 响应格式

### 成功响应 (200)

```json
{
  "success": true,
  "message": "Artifact artifact_abc123 已删除",
  "artifact_id": "artifact_abc123"
}
```

### 错误响应

#### 404 - Artifact 不存在

```json
{
  "detail": "Artifact 不存在: artifact_abc123"
}
```

#### 403 - 无权删除

```json
{
  "detail": "无权删除此 artifact"
}
```

#### 401 - 未认证

```json
{
  "detail": "未登录"
}
```

## 前端实现示例

### TypeScript/Axios 实现

```typescript
// api/artifacts.ts

import apiClient from './client';

/**
 * 删除 artifact
 * 
 * @param taskId 任务 ID
 * @param artifactId Artifact ID
 * @returns 删除结果
 */
export async function deleteArtifact(
  taskId: string,
  artifactId: string
): Promise<{
  success: boolean;
  message: string;
  artifactId: string;
}> {
  const response = await apiClient.delete(
    `/tasks/${taskId}/artifacts/${artifactId}`
  );
  return response.data;
}
```

### React 组件示例

```typescript
// components/ArtifactList.tsx

import React, { useState } from 'react';
import { deleteArtifact } from '../api/artifacts';

interface ArtifactItemProps {
  taskId: string;
  artifact: {
    artifactId: string;
    artifactType: string;
    version: number;
    createdAt: string;
  };
  onDeleted: () => void;
}

const ArtifactItem: React.FC<ArtifactItemProps> = ({
  taskId,
  artifact,
  onDeleted
}) => {
  const [deleting, setDeleting] = useState(false);

  const handleDelete = async () => {
    // 确认删除
    if (!window.confirm(`确定要删除此 artifact (版本 ${artifact.version}) 吗？`)) {
      return;
    }

    setDeleting(true);

    try {
      const result = await deleteArtifact(taskId, artifact.artifactId);
      
      console.log('删除成功:', result.message);
      
      // 通知父组件刷新列表
      onDeleted();
      
      // 显示成功提示
      alert('删除成功');
      
    } catch (error: any) {
      console.error('删除失败:', error);
      
      // 处理不同的错误
      if (error.response?.status === 404) {
        alert('Artifact 不存在');
      } else if (error.response?.status === 403) {
        alert('无权删除此 artifact');
      } else {
        alert(`删除失败: ${error.response?.data?.detail || error.message}`);
      }
    } finally {
      setDeleting(false);
    }
  };

  return (
    <div className="artifact-item">
      <div className="artifact-info">
        <span>类型: {artifact.artifactType}</span>
        <span>版本: {artifact.version}</span>
        <span>创建时间: {new Date(artifact.createdAt).toLocaleString()}</span>
      </div>
      
      <button
        onClick={handleDelete}
        disabled={deleting}
        className="delete-button"
      >
        {deleting ? '删除中...' : '删除'}
      </button>
    </div>
  );
};

export default ArtifactItem;
```

### Vue 组件示例

```vue
<!-- components/ArtifactItem.vue -->

<template>
  <div class="artifact-item">
    <div class="artifact-info">
      <span>类型: {{ artifact.artifactType }}</span>
      <span>版本: {{ artifact.version }}</span>
      <span>创建时间: {{ formatDate(artifact.createdAt) }}</span>
    </div>
    
    <button
      @click="handleDelete"
      :disabled="deleting"
      class="delete-button"
    >
      {{ deleting ? '删除中...' : '删除' }}
    </button>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import { deleteArtifact } from '../api/artifacts';

interface Props {
  taskId: string;
  artifact: {
    artifactId: string;
    artifactType: string;
    version: number;
    createdAt: string;
  };
}

const props = defineProps<Props>();
const emit = defineEmits<{
  deleted: [];
}>();

const deleting = ref(false);

const handleDelete = async () => {
  // 确认删除
  if (!confirm(`确定要删除此 artifact (版本 ${props.artifact.version}) 吗？`)) {
    return;
  }

  deleting.value = true;

  try {
    const result = await deleteArtifact(props.taskId, props.artifact.artifactId);
    
    console.log('删除成功:', result.message);
    
    // 通知父组件刷新列表
    emit('deleted');
    
    // 显示成功提示
    alert('删除成功');
    
  } catch (error: any) {
    console.error('删除失败:', error);
    
    // 处理不同的错误
    if (error.response?.status === 404) {
      alert('Artifact 不存在');
    } else if (error.response?.status === 403) {
      alert('无权删除此 artifact');
    } else {
      alert(`删除失败: ${error.response?.data?.detail || error.message}`);
    }
  } finally {
    deleting.value = false;
  }
};

const formatDate = (dateStr: string) => {
  return new Date(dateStr).toLocaleString('zh-CN');
};
</script>

<style scoped>
.artifact-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px;
  border: 1px solid #e0e0e0;
  border-radius: 4px;
  margin-bottom: 8px;
}

.artifact-info {
  display: flex;
  gap: 16px;
}

.delete-button {
  padding: 6px 12px;
  background-color: #f44336;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}

.delete-button:hover:not(:disabled) {
  background-color: #d32f2f;
}

.delete-button:disabled {
  background-color: #ccc;
  cursor: not-allowed;
}
</style>
```

## 使用场景

### 1. Artifact 列表页面

用户可以查看所有 artifacts 并删除不需要的版本：

```typescript
// pages/ArtifactList.tsx

const ArtifactList: React.FC<{ taskId: string }> = ({ taskId }) => {
  const [artifacts, setArtifacts] = useState([]);

  const loadArtifacts = async () => {
    const data = await getArtifacts(taskId);
    setArtifacts(data.artifacts);
  };

  const handleArtifactDeleted = () => {
    // 重新加载列表
    loadArtifacts();
  };

  return (
    <div>
      {artifacts.map(artifact => (
        <ArtifactItem
          key={artifact.artifactId}
          taskId={taskId}
          artifact={artifact}
          onDeleted={handleArtifactDeleted}
        />
      ))}
    </div>
  );
};
```

### 2. 版本管理页面

用户可以管理同一类型的多个版本，删除旧版本：

```typescript
// pages/VersionManager.tsx

const VersionManager: React.FC<{ taskId: string; artifactType: string }> = ({
  taskId,
  artifactType
}) => {
  const [versions, setVersions] = useState([]);

  const loadVersions = async () => {
    const data = await getArtifactVersions(taskId, artifactType);
    setVersions(data.versions);
  };

  const handleDeleteVersion = async (artifactId: string) => {
    try {
      await deleteArtifact(taskId, artifactId);
      loadVersions(); // 刷新列表
    } catch (error) {
      console.error('删除失败:', error);
    }
  };

  return (
    <div>
      <h2>{artifactType} 版本管理</h2>
      {versions.map(version => (
        <div key={version.artifactId}>
          <span>版本 {version.version}</span>
          <button onClick={() => handleDeleteVersion(version.artifactId)}>
            删除
          </button>
        </div>
      ))}
    </div>
  );
};
```

## 注意事项

### 1. 权限验证

- API 会自动验证用户权限
- 只能删除自己任务的 artifacts
- 如果尝试删除其他用户的 artifact，会返回 403 错误

### 2. 确认提示

建议在删除前显示确认对话框，避免误删：

```typescript
const handleDelete = async () => {
  if (!window.confirm('确定要删除此 artifact 吗？此操作不可恢复。')) {
    return;
  }
  // 执行删除...
};
```

### 3. 错误处理

需要处理以下错误情况：

- **404**: Artifact 不存在（可能已被删除）
- **403**: 无权删除（不是自己的任务）
- **401**: 未登录（Token 过期）
- **500**: 服务器错误

### 4. UI 反馈

- 删除过程中显示加载状态
- 删除成功后刷新列表
- 删除失败时显示错误信息

### 5. 批量删除

如果需要批量删除多个 artifacts，建议：

```typescript
const handleBatchDelete = async (artifactIds: string[]) => {
  const results = await Promise.allSettled(
    artifactIds.map(id => deleteArtifact(taskId, id))
  );
  
  const succeeded = results.filter(r => r.status === 'fulfilled').length;
  const failed = results.filter(r => r.status === 'rejected').length;
  
  alert(`删除完成: 成功 ${succeeded} 个，失败 ${failed} 个`);
  
  // 刷新列表
  loadArtifacts();
};
```

## 完整工作流程

```
1. 用户点击删除按钮
   ↓
2. 显示确认对话框
   ↓
3. 用户确认删除
   ↓
4. 调用 DELETE API
   ↓
5. 显示加载状态
   ↓
6. 收到响应
   ├─ 成功 (200)
   │  ├─ 显示成功提示
   │  └─ 刷新 artifact 列表
   │
   └─ 失败 (4xx/5xx)
      ├─ 显示错误信息
      └─ 保持当前状态
```

## 相关 API

- `GET /api/v1/tasks/{task_id}/artifacts` - 列出所有 artifacts
- `GET /api/v1/tasks/{task_id}/artifacts/{artifact_type}/versions` - 列出特定类型的版本
- `GET /api/v1/tasks/{task_id}/artifacts/{artifact_id}` - 获取 artifact 详情
- `POST /api/v1/tasks/{task_id}/artifacts/{artifact_type}/generate` - 生成新版本
- `DELETE /api/v1/tasks/{task_id}/artifacts/{artifact_id}` - 删除 artifact（本文档）

## 测试建议

### 单元测试

```typescript
// __tests__/deleteArtifact.test.ts

import { deleteArtifact } from '../api/artifacts';
import apiClient from '../api/client';

jest.mock('../api/client');

describe('deleteArtifact', () => {
  it('should delete artifact successfully', async () => {
    const mockResponse = {
      data: {
        success: true,
        message: 'Artifact deleted',
        artifactId: 'artifact_123'
      }
    };
    
    (apiClient.delete as jest.Mock).mockResolvedValue(mockResponse);
    
    const result = await deleteArtifact('task_123', 'artifact_123');
    
    expect(result.success).toBe(true);
    expect(apiClient.delete).toHaveBeenCalledWith(
      '/tasks/task_123/artifacts/artifact_123'
    );
  });
  
  it('should handle 404 error', async () => {
    (apiClient.delete as jest.Mock).mockRejectedValue({
      response: { status: 404, data: { detail: 'Not found' } }
    });
    
    await expect(
      deleteArtifact('task_123', 'artifact_123')
    ).rejects.toThrow();
  });
});
```

### 集成测试

```typescript
// __tests__/ArtifactItem.integration.test.tsx

import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import ArtifactItem from '../components/ArtifactItem';
import * as api from '../api/artifacts';

jest.mock('../api/artifacts');

describe('ArtifactItem Integration', () => {
  it('should delete artifact when confirmed', async () => {
    const mockDelete = jest.spyOn(api, 'deleteArtifact')
      .mockResolvedValue({
        success: true,
        message: 'Deleted',
        artifactId: 'artifact_123'
      });
    
    const mockOnDeleted = jest.fn();
    
    window.confirm = jest.fn(() => true);
    
    render(
      <ArtifactItem
        taskId="task_123"
        artifact={{
          artifactId: 'artifact_123',
          artifactType: 'meeting_minutes',
          version: 1,
          createdAt: '2024-01-23T10:00:00Z'
        }}
        onDeleted={mockOnDeleted}
      />
    );
    
    const deleteButton = screen.getByText('删除');
    fireEvent.click(deleteButton);
    
    await waitFor(() => {
      expect(mockDelete).toHaveBeenCalledWith('task_123', 'artifact_123');
      expect(mockOnDeleted).toHaveBeenCalled();
    });
  });
});
```

## 总结

删除 artifact 功能已完全实现，前端只需：

1. 调用 `DELETE /api/v1/tasks/{task_id}/artifacts/{artifact_id}`
2. 传递正确的 JWT Token
3. 处理成功和错误响应
4. 刷新 UI

如有问题，请参考本文档或联系后端团队。

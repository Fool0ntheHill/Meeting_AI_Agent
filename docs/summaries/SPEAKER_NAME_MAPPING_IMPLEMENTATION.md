# 说话人姓名映射功能实现总结

## 问题

逐字稿显示 `Speaker 1`、`Speaker 2`，而不是真实姓名 `林煜东`、`蓝为一`。

## 解决方案

### 后端修改

1. **新增 speakers 表**
   - 存储声纹 ID 到真实姓名的映射
   - 例如：`speaker_linyudong` -> `林煜东`

2. **Pipeline 保存 speaker mapping**
   - 声纹识别后自动保存到 `speaker_mappings` 表
   - 记录：`Speaker 1` -> `speaker_linyudong`

3. **API 返回真实姓名**
   - `GET /api/v1/tasks/{task_id}/transcript` 新增 `speaker_mapping` 字段
   - 自动关联 speakers 表，返回真实姓名
   - 格式：`{"Speaker 1": "林煜东", "Speaker 2": "蓝为一"}`

### 前端适配

**前端无需修改**！

前端已经在 `task.ts` 中实现了自动替换逻辑：
- 读取 `speaker_mapping` 字段
- 自动替换 segments 中的 speaker 显示
- 支持多种字段名：`speaker_mapping`、`speaker_map`、`speakerMap`

### API 响应示例

```json
{
  "task_id": "task_xxx",
  "segments": [
    {
      "text": "大家好",
      "speaker": "Speaker 1",  // 原始标签
      ...
    }
  ],
  "speaker_mapping": {
    "Speaker 1": "林煜东",  // 真实姓名
    "Speaker 2": "蓝为一"
  },
  ...
}
```

### 部署步骤

1. **运行数据库迁移**
   ```bash
   python scripts/migrate_add_speakers_table.py
   ```

2. **重启 Worker**
   ```bash
   python worker.py
   ```

3. **重启 Backend**（如果已运行）
   ```bash
   python main.py
   ```

4. **创建新任务测试**
   - 旧任务没有 speaker mapping 数据
   - 新任务会自动保存并返回真实姓名

### 测试验证

```bash
python scripts/test_speaker_mapping.py
```

预期结果：
- ✅ speakers 表包含测试数据
- ✅ API 返回 `speaker_mapping` 字段
- ✅ 前端自动显示真实姓名

### 文件修改清单

#### 新增文件
- `src/database/models.py` - 添加 Speaker 模型
- `src/database/repositories.py` - 添加 SpeakerRepository
- `scripts/migrate_add_speakers_table.py` - 数据库迁移脚本
- `scripts/test_speaker_mapping.py` - 测试脚本
- `docs/SPEAKER_NAME_MAPPING_GUIDE.md` - 完整指南

#### 修改文件
- `src/services/pipeline.py` - 保存 speaker mapping
- `src/queue/worker.py` - 传递 speaker_mapping_repo
- `src/api/routes/tasks.py` - 返回 speaker_mapping
- `src/api/schemas.py` - 添加 speaker_mapping 字段

### 注意事项

1. **旧任务无法显示真实姓名**
   - 旧任务没有 speaker mapping 数据
   - 需要重新运行任务

2. **speakers 表需要预先配置**
   - 迁移脚本已插入测试数据
   - 生产环境需要导入真实的说话人数据

3. **前端已完成适配**
   - 无需修改前端代码
   - 只要后端返回 `speaker_mapping` 即可

## 总结

✅ 后端实现完成
✅ 前端已适配（无需修改）
✅ 数据库迁移脚本已准备
⚠️ 需要重启服务
⚠️ 旧任务无法显示真实姓名

**前端开发者无需任何操作**，只要后端部署完成，新任务会自动显示真实姓名。

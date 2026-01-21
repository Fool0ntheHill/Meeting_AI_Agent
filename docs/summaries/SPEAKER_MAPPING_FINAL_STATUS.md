# 说话人姓名映射 - 最终状态

## 问题诊断

任务 `task_ab07a64f9e8d4f69` 前端无法显示真实姓名的原因：

1. ✅ **后端代码已完成** - API 返回 `speaker_mapping` 字段
2. ✅ **前端代码已完成** - 自动读取并替换显示
3. ❌ **旧任务缺少数据** - 数据库中没有 speaker mapping 记录

## 解决方案

已为旧任务手动添加 speaker mapping 数据：

```bash
python scripts/add_speaker_mapping_for_old_task.py
```

添加的映射：
- `Speaker 1` -> `speaker_linyudong` -> `林煜东`
- `Speaker 2` -> `speaker_lanweiyi` -> `蓝为一`

## 验证结果

```bash
python scripts/test_task_with_correct_user.py
```

输出：
```
1. 登录...
   user_id: user_test_user
   tenant_id: tenant_test_user

2. 获取 transcript...
   Status: 200

3. speaker_mapping:
   类型: <class 'dict'>
   Speaker 1 -> 林煜东
   Speaker 2 -> 蓝为一

✅ 成功！前端应该能看到真实姓名了
```

## 前端使用说明

### 登录

前端应该使用 `username: "test_user"` 登录：

```typescript
const response = await fetch('/api/v1/auth/dev/login', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ username: 'test_user' })
});

const data = await response.json();
// data.user_id = "user_test_user"
// data.tenant_id = "tenant_test_user"
```

**注意**：不要用 `username: "user_test_user"`，这会导致 user_id 变成 `user_user_test_user`（多了一个 user_ 前缀）。

### API 响应

`GET /api/v1/tasks/{task_id}/transcript` 返回：

```json
{
  "segments": [
    {"speaker": "Speaker 1", "text": "..."}
  ],
  "speaker_mapping": {
    "Speaker 1": "林煜东",
    "Speaker 2": "蓝为一"
  }
}
```

### 前端显示

前端已在 `task.ts` 中实现自动替换，无需修改：

```typescript
// 自动读取 speaker_mapping
const speakerMap = response.speaker_mapping;

// 自动替换 segments 中的 speaker
segments.map(seg => ({
  ...seg,
  speaker: speakerMap?.[seg.speaker] || seg.speaker
}));
```

## 测试任务

### 已修复的旧任务

- `task_ab07a64f9e8d4f69` - ✅ 已添加 speaker mapping
- `task_07cb88970c3848c4` - ✅ 已添加 speaker mapping

这两个任务现在都能正常显示真实姓名。

### 新任务

新创建的任务会自动保存 speaker mapping，无需手动处理。

## 常见问题

### Q: 前端还是看不到真实姓名？

检查：

1. **登录用户名是否正确**
   - 应该用 `username: "test_user"`
   - 不要用 `username: "user_test_user"`

2. **浏览器是否刷新**
   - 刷新页面重新获取数据

3. **浏览器控制台是否有错误**
   - 检查 Network 标签，查看 API 响应
   - 检查 Console 标签，查看 JavaScript 错误

4. **API 响应是否包含 speaker_mapping**
   - 在 Network 标签中查看 `/transcript` 的响应
   - 应该包含 `speaker_mapping` 字段

### Q: 其他旧任务怎么办？

使用脚本手动添加：

```bash
# 修改 scripts/add_speaker_mapping_for_old_task.py 中的 task_id
# 然后运行
python scripts/add_speaker_mapping_for_old_task.py
```

### Q: 新任务会自动保存吗？

是的，只要：
1. Worker 已重启（加载新代码）
2. Backend 已重启（加载新代码）
3. 数据库已运行迁移（创建 speakers 表）

## 部署检查清单

- [x] 数据库迁移已运行（`python scripts/migrate_add_speakers_table.py`）
- [x] speakers 表已创建并包含测试数据
- [x] 旧任务已手动添加 speaker mapping
- [x] Backend 代码已更新（返回 speaker_mapping）
- [x] Worker 代码已更新（保存 speaker mapping）
- [x] 前端代码已更新（自动替换显示）
- [ ] Worker 需要重启（加载新代码）
- [ ] Backend 需要重启（加载新代码）

## 下一步

1. **重启 Worker**
   ```bash
   python worker.py
   ```

2. **重启 Backend**（如果已运行）
   ```bash
   python main.py
   ```

3. **前端测试**
   - 登录：`username: "test_user"`
   - 访问任务：`task_ab07a64f9e8d4f69`
   - 检查逐字稿是否显示真实姓名

4. **创建新任务测试**
   - 上传音频创建新任务
   - 等待处理完成
   - 检查是否自动显示真实姓名

## 总结

✅ **后端完成** - API 返回 speaker_mapping
✅ **前端完成** - 自动替换显示
✅ **数据完成** - 旧任务已添加映射
⚠️ **需要重启** - Worker 和 Backend
📝 **前端登录** - 使用 `username: "test_user"`

**现在前端应该能正常显示真实姓名了！**

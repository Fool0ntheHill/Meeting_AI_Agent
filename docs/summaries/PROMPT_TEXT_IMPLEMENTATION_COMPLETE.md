# 提示词文本传递与存储功能实现完成

## 实现日期
2026-01-23

## 问题背景

后端存在严重设计缺陷：
1. **完全忽略用户编辑的提示词** - 总是使用数据库模板原文
2. **无法回溯历史提示词** - 不知道某个 artifact 是用什么提示词生成的
3. **空白模板失败** - `template_id="__blank__"` 会报错"模板不存在"

## 实现内容

### 1. 修复 `PromptInstance` 模型

**文件**: `src/core/models.py`

**新增字段**:
```python
class PromptInstance(BaseModel):
    template_id: str
    language: str = "zh-CN"
    prompt_text: Optional[str] = None  # 新增：用户编辑的完整提示词
    parameters: Dict[str, Any] = {}
    custom_instructions: Optional[str] = None  # 新增：补充指令
```

### 2. 修复提示词构建逻辑

**文件**: `src/providers/gemini_llm.py`

**修改**: `_build_prompt()` 方法

**逻辑**:
```python
# 优先使用用户编辑的 prompt_text
if prompt_instance.prompt_text:
    prompt_body = prompt_instance.prompt_text  # 用户版本
else:
    prompt_body = template.prompt_body  # 模板原文
```

### 3. 修复空白模板支持

**文件**: `src/services/artifact_generation.py`

**新增方法**: `_create_blank_template()`

**逻辑**:
```python
if prompt_instance.template_id == "__blank__":
    # 使用用户的 prompt_text 创建临时模板
    template = self._create_blank_template(artifact_type, prompt_instance)
```

### 4. 实现提示词存储

**文件**: `src/providers/gemini_llm.py`

**修改**: 在生成 artifact 时保存提示词信息到 `metadata.prompt`

**存储结构**:
```python
metadata["prompt"] = {
    "template_id": prompt_instance.template_id,
    "language": prompt_instance.language,
    "parameters": prompt_instance.parameters,
    "prompt_text": prompt_text,  # 实际使用的提示词
    "is_user_edited": bool(prompt_instance.prompt_text),
    "custom_instructions": prompt_instance.custom_instructions
}
```

### 5. API 自动返回提示词信息

**文件**: 无需修改

**说明**: `GET /api/v1/tasks/{task_id}/artifacts/{artifact_id}` 已经返回完整的 `metadata`，包含新增的 `prompt` 字段

## 使用场景

### 场景 1: 使用模板，不编辑

**前端传递**:
```json
{
  "template_id": "tpl_001",
  "language": "zh-CN",
  "parameters": {}
}
```

**后端行为**: 使用模板原文

**存储**: `is_user_edited: false`, `prompt_text: 模板原文`

### 场景 2: 使用模板，用户编辑

**前端传递**:
```json
{
  "template_id": "tpl_001",
  "language": "zh-CN",
  "prompt_text": "用户编辑的提示词...",
  "parameters": {}
}
```

**后端行为**: 使用用户编辑的提示词

**存储**: `is_user_edited: true`, `prompt_text: 用户编辑的提示词`

### 场景 3: 空白模板

**前端传递**:
```json
{
  "template_id": "__blank__",
  "language": "zh-CN",
  "prompt_text": "完全自定义的提示词...",
  "parameters": {}
}
```

**后端行为**: 使用用户的完整提示词

**存储**: `is_user_edited: true`, `prompt_text: 用户提示词`

## 向后兼容

### 旧数据
- `metadata.prompt` 为 `null` 或不存在
- 前端显示"此 artifact 没有提示词信息"
- 不影响正常使用

### 新数据
- 完整保存提示词信息
- 支持查看和重新生成

## 文档

### 前端集成文档
- `docs/PROMPT_TEXT_FRONTEND_GUIDE.md` - 前端如何传递提示词
- `docs/ARTIFACT_PROMPT_STORAGE_GUIDE.md` - 提示词存储与回溯

### 关键点
1. **前端**: 用户编辑提示词后，传递 `prompt_text` 字段
2. **后端**: 优先使用 `prompt_text`，否则使用模板原文
3. **存储**: 自动保存到 `artifact.metadata.prompt`
4. **查看**: GET artifact API 自动返回提示词信息
5. **重新生成**: 可以使用相同提示词重新生成

## 测试建议

### 1. 测试空白模板
```bash
# 创建使用空白模板的任务
python scripts/test_blank_template.py
```

### 2. 测试提示词存储
```bash
# 检查 artifact 的 metadata.prompt 字段
python scripts/check_task_prompt.py task_xxx
```

### 3. 测试前端集成
- 创建任务时传递 `prompt_text`
- 查看 artifact 详情，检查 `metadata.prompt`
- 验证 `is_user_edited` 标记正确

## 影响范围

### 修改的文件
1. `src/core/models.py` - 添加 `prompt_text` 和 `custom_instructions` 字段
2. `src/providers/gemini_llm.py` - 修改提示词构建和存储逻辑
3. `src/services/artifact_generation.py` - 添加空白模板支持

### 新增的文件
1. `docs/PROMPT_TEXT_FRONTEND_GUIDE.md` - 前端集成指南
2. `docs/ARTIFACT_PROMPT_STORAGE_GUIDE.md` - 存储与回溯指南
3. `scripts/test_blank_template.py` - 空白模板测试脚本
4. `scripts/check_task_prompt.py` - 提示词检查脚本

### 不需要修改的部分
- API 路由（已经返回完整 metadata）
- 数据库表结构（metadata 是 JSON 字段）
- 前端 API 调用（只需添加 `prompt_text` 字段）

## 部署注意事项

### 1. 无需数据库迁移
- `metadata` 是 JSON 字段，可以直接添加新字段
- 旧数据保持不变，不影响使用

### 2. 需要重启服务
- Worker 需要重启以应用新逻辑
- Backend API 需要重启（如果有修改）

### 3. 前端更新
- 前端需要更新以传递 `prompt_text` 字段
- 可以逐步更新，旧版本仍然可以工作

## 总结

✅ **空白模板支持** - `template_id="__blank__"` 现在可以正常工作  
✅ **用户编辑支持** - 完全使用用户编辑的提示词  
✅ **提示词存储** - 每个 artifact 保存完整提示词信息  
✅ **历史回溯** - 可以查看任何版本使用的提示词  
✅ **向后兼容** - 旧数据不受影响  
✅ **重新生成** - 可以使用相同提示词重新生成  

现在后端完全支持用户自定义提示词，并且可以完整回溯历史！

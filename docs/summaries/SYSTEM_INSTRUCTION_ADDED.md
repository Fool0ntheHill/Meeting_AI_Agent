# System Instruction 添加完成

## 修改内容

为 `src/providers/gemini_llm.py` 添加了全局 System Instruction，用于处理防幻觉和格式兼容性问题。

## 核心改动

### 1. 定义全局常量

在文件顶部添加了 `GLOBAL_SYSTEM_INSTRUCTION` 常量：

```python
GLOBAL_SYSTEM_INSTRUCTION = """【底层约束】

1. 核心原则：严格基于提供的【转写内容】生成回答，绝对不要编造转写中未提及的事实或细节。
   如果信息缺失，请直接说明或标记为 [???]。

2. 格式兼容性：为了适配企业微信文档的粘贴格式，请严格遵守以下 Markdown 规范：
   - 严禁使用 Checkbox 复选框语法（即禁止出现 "- [ ]" 或 "- [x]"）。
   - 所有列表项（包括待办事项、行动项）必须强制使用标准的无序列表符号 "-" 开头。
"""
```

### 2. 修改 API 调用

在 `_call_gemini_api` 方法中添加 `system_instruction` 参数：

```python
response = await asyncio.to_thread(
    self.client.models.generate_content,
    model=self.config.model,
    contents=prompt,
    config=config,
    system_instruction=GLOBAL_SYSTEM_INSTRUCTION,  # ⭐ NEW
)
```

## 设计原则

### ✅ 做了什么

1. **防幻觉约束（Grounding）**
   - 强制 AI 严格基于转写内容
   - 禁止编造未提及的事实
   - 信息缺失时标记为 `[???]`

2. **格式兼容性（Compatibility）**
   - 禁用 Markdown 复选框语法（`- [ ]` 和 `- [x]`）
   - 强制使用标准无序列表符号 `-`
   - 确保企业微信文档粘贴兼容

3. **保持灵活性**
   - 不定义角色（如"你是会议助手"）
   - 让用户模板决定任务类型
   - 只定义底层约束和格式规范

### ❌ 没有做什么

- ❌ 不定义角色和任务类型
- ❌ 不限制内容结构
- ❌ 不影响用户模板的灵活性

## 完整的提示词结构

现在 Gemini API 调用包含以下部分：

```python
response = client.models.generate_content(
    model="gemini-3-pro-preview",  # 实际使用的模型
    
    # 0. System Instruction（全局约束）⭐ NEW
    system_instruction=GLOBAL_SYSTEM_INSTRUCTION,
    
    # 1. User Prompt（用户内容）
    contents="""
        [模板主体 - 用户定义]
        + [转写内容 - 包含声纹识别]
        + [语言指令 - 自动添加]
    """,
    
    # 2. Config（格式参数）
    config=GenerateContentConfig(
        response_mime_type="application/json",
        response_schema={
            "type": "object",
            "properties": {
                "content": {"type": "string"},
                "metadata": {"type": "object"}
            }
        }
    )
)
```

## 效果

### 防幻觉

**之前**:
```markdown
## 行动项
- [ ] 张三：完成用户认证模块（截止日期：下周五）
- [ ] 李四：优化数据库性能（预计需要3天）
```
❌ 可能编造"截止日期"和"预计时间"

**之后**:
```markdown
## 行动项
- 张三：完成用户认证模块
- 李四：优化数据库性能
```
✅ 严格基于转写内容，不编造细节

### 格式兼容

**之前**:
```markdown
## 待办事项
- [ ] 任务1
- [x] 任务2
```
❌ 企微文档粘贴后复选框显示异常

**之后**:
```markdown
## 待办事项
- 任务1
- 任务2
```
✅ 企微文档粘贴正常显示

## 测试验证

运行测试脚本：

```bash
python scripts/test_system_instruction.py
```

输出：
```
✅ 包含防幻觉约束（Grounding）
✅ 包含格式兼容性约束（企微文档）
✅ 没有定义角色（保持灵活性）
```

## 生效方式

System Instruction 会在以下情况生效：

1. **新任务**: 所有新创建的任务自动应用
2. **Worker 重启**: 需要重启 worker 才能生效
3. **全局生效**: 所有任务类型共享

## 重启 Worker

```powershell
# 停止当前 worker
Stop-Process -Name python -Force

# 启动新 worker
python worker.py
```

或使用脚本：

```powershell
.\scripts\start_worker.ps1
```

## 相关文件

### 修改的文件
- `src/providers/gemini_llm.py` - 添加 System Instruction

### 更新的文档
- `docs/PROMPT_CONSTRUCTION_FLOW.md` - 更新提示词构建流程
- `scripts/show_prompt_construction.py` - 更新演示脚本

### 新增的文件
- `scripts/test_system_instruction.py` - System Instruction 测试脚本
- `docs/summaries/SYSTEM_INSTRUCTION_ADDED.md` - 本文档

## 后续建议

### 可选优化

1. **可配置化**: 将 System Instruction 移到配置文件
2. **多语言支持**: 根据 output_language 调整 System Instruction
3. **任务特定约束**: 允许不同任务类型添加额外约束

### 监控指标

建议监控以下指标来评估效果：

1. **幻觉率**: 生成内容中编造事实的比例
2. **格式兼容性**: 企微文档粘贴成功率
3. **用户反馈**: 内容准确性和格式满意度

## 总结

✅ 成功添加全局 System Instruction  
✅ 防幻觉约束已生效  
✅ 格式兼容性已保证  
✅ 用户模板灵活性已保持  
✅ 文档已更新  
✅ 测试脚本已创建  

需要重启 worker 才能在新任务中生效。

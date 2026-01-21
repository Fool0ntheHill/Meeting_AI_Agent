# System Instruction 快速参考

## 📍 位置

**文件**: `src/providers/gemini_llm.py`  
**常量**: `GLOBAL_SYSTEM_INSTRUCTION`

## 📝 内容

```
【底层约束】

1. 核心原则：严格基于提供的【转写内容】生成回答，绝对不要编造转写中未提及的事实或细节。
   如果信息缺失，请直接说明或标记为 [???]。

2. 格式兼容性：为了适配企业微信文档的粘贴格式，请严格遵守以下 Markdown 规范：
   - 严禁使用 Checkbox 复选框语法（即禁止出现 "- [ ]" 或 "- [x]"）。
   - 所有列表项（包括待办事项、行动项）必须强制使用标准的无序列表符号 "-" 开头。
```

**注意**: 实际使用的模型是 `gemini-3-pro-preview`（从配置文件读取），文档中的示例可能显示其他模型名称仅作演示。

## 🎯 作用

| 功能 | 说明 |
|------|------|
| **防幻觉** | 强制 AI 基于转写内容，不编造事实 |
| **格式兼容** | 禁用复选框，确保企微文档粘贴正常 |
| **保持灵活** | 不定义角色，让用户模板决定任务类型 |

## 🔄 与其他部分的关系

```
┌─────────────────────────────────────────────────────┐
│  Gemini API 调用                                     │
├─────────────────────────────────────────────────────┤
│                                                     │
│  system_instruction = GLOBAL_SYSTEM_INSTRUCTION     │
│  ↓                                                  │
│  【全局约束】防幻觉 + 格式兼容                        │
│                                                     │
│  contents = prompt                                  │
│  ↓                                                  │
│  【用户内容】模板 + 转写 + 语言指令                   │
│                                                     │
│  config = GenerateContentConfig(...)                │
│  ↓                                                  │
│  【格式参数】response_schema                         │
│                                                     │
└─────────────────────────────────────────────────────┘
```

## ✅ 设计原则

### 做什么
- ✅ 定义负向约束（不要做什么）
- ✅ 定义格式规范（必须遵守什么）
- ✅ 全局生效（所有任务共享）

### 不做什么
- ❌ 不定义角色（如"你是会议助手"）
- ❌ 不限制内容结构
- ❌ 不影响用户模板灵活性

## 🚀 生效方式

1. **自动生效**: 所有新任务自动应用
2. **需要重启**: 修改后需要重启 worker
3. **全局共享**: 所有任务类型共享

## 🧪 测试

```bash
# 验证 System Instruction
python scripts/test_system_instruction.py

# 查看提示词构建过程
python scripts/show_prompt_construction.py
```

## 📚 相关文档

- [提示词构建流程](./PROMPT_CONSTRUCTION_FLOW.md)
- [Markdown 统一格式](./MARKDOWN_UNIFIED_FORMAT.md)
- [System Instruction 添加总结](./summaries/SYSTEM_INSTRUCTION_ADDED.md)

## 💡 示例效果

### 防幻觉

**之前**: 可能编造"截止日期：下周五"  
**之后**: 只记录转写中提到的内容

### 格式兼容

**之前**: `- [ ] 任务` → 企微粘贴异常  
**之后**: `- 任务` → 企微粘贴正常

## 🔧 修改建议

如需修改 System Instruction：

1. 编辑 `src/providers/gemini_llm.py` 中的 `GLOBAL_SYSTEM_INSTRUCTION`
2. 重启 worker: `python worker.py`
3. 测试验证: `python scripts/test_system_instruction.py`

## ⚠️ 注意事项

- System Instruction 优先级高于 User Prompt
- 过于严格的约束可能影响输出质量
- 建议保持简洁，只定义核心约束

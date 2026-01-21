#!/usr/bin/env python3
"""展示提示词的构建过程和最终效果"""

import sqlite3
import json

# 1. 获取模板
conn = sqlite3.connect("meeting_agent.db")
cursor = conn.cursor()

cursor.execute("""
    SELECT template_id, title, prompt_body
    FROM prompt_templates
    WHERE template_id = 'meeting_minutes_detailed_summary'
""")

template = cursor.fetchone()
conn.close()

if not template:
    print("❌ 模板不存在")
    exit(1)

template_id, title, prompt_body = template

print("=" * 100)
print("提示词构建过程展示（包含 System Instruction）")
print("=" * 100)

print("\n" + "─" * 100)
print("第 0 部分：System Instruction（全局底层约束）⭐ NEW")
print("─" * 100)
print("""
这是 Gemini API 的 system_instruction 参数，不是 prompt 的一部分。
全局生效，所有任务类型共享。

【底层约束】

1. 核心原则：严格基于提供的【转写内容】生成回答，绝对不要编造转写中未提及的事实或细节。
   如果信息缺失，请直接说明或标记为 [???]。

2. 格式兼容性：为了适配企业微信文档的粘贴格式，请严格遵守以下 Markdown 规范：
   - 严禁使用 Checkbox 复选框语法（即禁止出现 "- [ ]" 或 "- [x]"）。
   - 所有列表项（包括待办事项、行动项）必须强制使用标准的无序列表符号 "-" 开头。

设计原则：
✅ 防幻觉：强制基于转写内容
✅ 格式兼容：禁用复选框，确保企微文档兼容
✅ 不定义角色：保持用户模板的灵活性
""")

print("\n" + "─" * 100)
print("第 1 部分：模板主体 (prompt_body)")
print("─" * 100)
print(prompt_body)

print("\n" + "─" * 100)
print("第 2 部分：转写内容占位符")
print("─" * 100)
print("""
模板中的 {transcript} 会被替换为实际的转写内容，格式如下：

[蓝为一] 今天我们讨论一下新功能的设计方案 (00:00:05 - 00:00:10)
[张三] 我觉得可以采用微服务架构 (00:00:11 - 00:00:15)
[李四] 需要考虑性能问题 (00:00:16 - 00:00:20)
...
""")

print("\n" + "─" * 100)
print("第 3 部分：输出语言指令")
print("─" * 100)
print("""
根据 output_language 参数添加：

- zh-CN: "请使用中文生成会议纪要。"
- en-US: "Please generate the meeting minutes in English."
- ja-JP: "日本語で議事録を作成してください。"
- ko-KR: "한국어로 회의록을 작성해 주세요。"
""")

print("\n" + "─" * 100)
print("第 4 部分：JSON Schema (强制输出格式)")
print("─" * 100)

schema = {
    "type": "object",
    "properties": {
        "content": {
            "type": "string",
            "description": "Markdown 格式的内容，可以包含任意结构的文本、列表、表格等"
        },
        "metadata": {
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "标题"},
                "summary": {"type": "string", "description": "简短摘要"}
            },
            "description": "可选的元数据"
        }
    },
    "required": ["content"]
}

print("Gemini API 配置:")
print(json.dumps({
    "response_mime_type": "application/json",
    "response_schema": schema
}, indent=2, ensure_ascii=False))

print("\n" + "=" * 100)
print("最终发送给 Gemini 的完整提示词示例")
print("=" * 100)

final_prompt = f"""{prompt_body}

## 转写内容
[蓝为一] 今天我们讨论一下新功能的设计方案，主要是关于用户认证模块 (00:00:05 - 00:00:12)
[张三] 我建议采用 JWT 方案，这样可以实现无状态认证 (00:00:13 - 00:00:18)
[李四] JWT 有安全风险，需要考虑 token 刷新机制 (00:00:19 - 00:00:25)
[蓝为一] 那我们就采用 JWT + Refresh Token 的方案 (00:00:26 - 00:00:30)
[张三] 好的，我负责实现这个功能 (00:00:31 - 00:00:33)

请使用中文生成会议纪要。"""

print(final_prompt)

print("\n" + "=" * 100)
print("Gemini 返回的 JSON (保证格式)")
print("=" * 100)

example_response = {
    "content": """## 会议基本信息

**会议标题**: 用户认证模块设计讨论
**参与者**: 蓝为一、张三、李四

## 会议概要

本次会议讨论了新功能中用户认证模块的技术方案，最终决定采用 JWT + Refresh Token 的方案来实现无状态认证。

## 讨论要点

### 认证方案选择

- **JWT 方案**: 张三建议采用 JWT 实现无状态认证
- **安全考虑**: 李四指出 JWT 存在安全风险，需要考虑 token 刷新机制
- **最终方案**: 采用 JWT + Refresh Token 的组合方案

## 决策事项

- ✅ 采用 JWT + Refresh Token 认证方案
- ✅ 需要实现 token 刷新机制

## 行动项

- [ ] **[张三]**: 实现 JWT + Refresh Token 认证功能

## 其他

无
""",
    "metadata": {
        "title": "用户认证模块设计讨论",
        "summary": "讨论并决定了用户认证模块的技术方案"
    }
}

print(json.dumps(example_response, indent=2, ensure_ascii=False))

print("\n" + "=" * 100)
print("存储到数据库")
print("=" * 100)
print("""
数据库 generated_artifacts 表中存储：

- artifact_id: art_xxx
- task_id: task_xxx
- artifact_type: meeting_minutes
- version: 1
- content: (上面的 JSON，序列化为字符串)
- prompt_instance: {"template_id": "meeting_minutes_detailed_summary", "language": "zh-CN", ...}
""")

print("\n" + "=" * 100)
print("前端获取时的转换")
print("=" * 100)
print("""
API 返回给前端：

{
  "artifact_id": "art_xxx",
  "display_type": "markdown",
  "data": {
    "title": "用户认证模块设计讨论",
    "content": "## 会议基本信息\\n\\n**会议标题**: 用户认证模块设计讨论\\n..."
  }
}

前端只需要：
1. 显示 data.title 作为标题
2. 用 Markdown 渲染器渲染 data.content
3. 完成！
""")

print("\n" + "=" * 100)
print("总结")
print("=" * 100)
print("""
提示词组成部分：
0. ✅ System Instruction（全局约束）- 防幻觉 + 格式兼容 ⭐ NEW
1. ✅ 模板主体 (prompt_body) - 定义内容要求和格式说明
2. ✅ 转写内容 ({transcript}) - 实际的会议对话
3. ✅ 输出语言指令 - 根据 output_language 添加
4. ✅ JSON Schema - 通过 Gemini API 配置强制输出格式

关键优势：
- System Instruction 全局生效，防止幻觉和格式问题
- 用户只需要修改模板主体（内容要求）
- 输出格式由 Schema 保证，100% 统一
- 前端永远收到相同格式，不会白屏
- 历史数据通过转换器统一为 Markdown
- 企微文档粘贴兼容（无复选框）
""")

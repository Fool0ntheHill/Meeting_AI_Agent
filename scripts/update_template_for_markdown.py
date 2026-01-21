#!/usr/bin/env python3
"""更新提示词模板，使用 Markdown 输出格式"""

import sqlite3

# 新的提示词模板（Markdown 格式）
new_prompt_body = """请根据以下会议转写内容，生成一份详细的会议摘要。

## 要求

请以 Markdown 格式输出，包含以下章节：

### 1. 会议基本信息
- 会议标题
- 会议时间和日期
- 参与者列表

### 2. 会议概要
简要总结整个会议的主要内容和目的

### 3. 讨论要点
按照讨论顺序列出各个议题，每个议题包括：
- 议题标题
- 关键要点（使用列表）
- 参与讨论的人员
- 重要的原话引述（如果有）
- 相关决策
- 发现的问题或挑战

### 4. 决策事项
列出会议中做出的所有决策

### 5. 行动项
列出所有待办事项，格式：
- **[负责人]**: 任务描述 (截止日期)

### 6. 其他
其他需要记录的信息

## 注意事项
1. 所有内容必须经过校对以确保准确和完整
2. 不应补充缺失的细节
3. 不清楚的内容必须标记为 [???]
4. 确保摘要中包含转录内容的所有重要议题
5. 使用清晰的 Markdown 格式，便于阅读

## 转写内容
{transcript}

## 输出格式
请以 JSON 格式输出，结构如下：
```json
{
  "content": "Markdown 格式的完整会议纪要内容",
  "metadata": {
    "title": "会议标题",
    "summary": "简短摘要（1-2句话）"
  }
}
```
"""

conn = sqlite3.connect("meeting_agent.db")
cursor = conn.cursor()

# 更新模板
cursor.execute("""
    UPDATE prompt_templates
    SET prompt_body = ?,
        updated_at = CURRENT_TIMESTAMP
    WHERE template_id = 'meeting_minutes_detailed_summary'
""", (new_prompt_body,))

affected = cursor.rowcount
conn.commit()
conn.close()

print(f"✅ 已更新 {affected} 个模板")
print("新的输出格式：Markdown (content + metadata)")

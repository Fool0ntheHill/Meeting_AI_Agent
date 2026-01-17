# -*- coding: utf-8 -*-
"""添加详细摘要模板到数据库

使用方法:
    python scripts/add_detailed_summary_template.py
"""

import sys
from pathlib import Path
from datetime import datetime

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.database.session import get_session
from src.database.models import PromptTemplateRecord
from src.config.loader import get_config


def add_detailed_summary_template():
    """添加详细摘要模板"""
    
    # 模板信息
    template_id = "meeting_minutes_detailed_summary"
    title = "详细摘要"
    description = "通话或会议的详细摘要概览，包含完整的议题讨论、决策和行动项"
    
    # 提示词
    prompt_body = """请根据以下会议转写内容，生成一份详细的会议摘要。

## 要求

### 1. 基本信息
- 标题：会议主题
- 时间：会议时间
- 日期：会议日期
- 参与者：所有参与者姓名
- 整体总结：会议的总体概述

### 2. 议题详情
按照讨论顺序列出各个议题，每个议题包括：
- 议题标题
- 要点列表
- 参与者
- 关键观点（带引号的原话）
- 决策
- 发现的问题
- 挑战
- 反馈
- 计划的行动

### 3. 行动项
每个行动项必须包括：
- 标题
- 任务描述
- 负责人
- 截止日期
- 备注

## 注意事项
1. 所有笔记必须经过校对以确保准确和完整
2. 不应补充缺失的细节
3. 不清楚的原始引述必须标记为 [???]
4. 确保摘要中包含转录内容的所有议题

## 转写内容
{transcript}

## 输出格式
请以 JSON 格式输出，结构如下：
```json
{
  "title": "会议标题",
  "date": "YYYY-MM-DD",
  "time": "HH:MM",
  "participants": ["参与者1", "参与者2"],
  "overall_summary": "整体会议总结",
  "topics": [
    {
      "title": "议题标题",
      "order": 1,
      "key_points": ["要点1", "要点2"],
      "participants": ["参与者1"],
      "key_quotes": [
        {
          "speaker": "参与者1",
          "quote": "原话内容"
        }
      ],
      "decisions": ["决策1", "决策2"],
      "issues": ["问题1"],
      "challenges": ["挑战1"],
      "feedback": ["反馈1"],
      "planned_actions": ["计划行动1"]
    }
  ],
  "action_items": [
    {
      "title": "行动项标题",
      "description": "任务描述",
      "assignee": "负责人",
      "deadline": "YYYY-MM-DD",
      "notes": "备注"
    }
  ]
}
```
"""
    
    # 参数定义
    parameter_schema = {
        "focus_areas": {
            "type": "array",
            "description": "重点关注的领域（可选）",
            "items": {
                "type": "string"
            },
            "optional": True
        }
    }
    
    # 创建模板记录
    template = PromptTemplateRecord(
        template_id=template_id,
        title=title,
        description=description,
        prompt_body=prompt_body,
        artifact_type="meeting_minutes",
        is_system=True,
        scope="global",
        scope_id=None,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    
    # 设置支持的语言和参数
    template.set_supported_languages_list(["zh-CN", "en-US"])
    template.set_parameter_schema_dict(parameter_schema)
    
    # 保存到数据库
    session = get_session()
    try:
        # 检查是否已存在
        existing = session.query(PromptTemplateRecord).filter_by(
            template_id=template_id
        ).first()
        
        if existing:
            print(f"⚠️  模板已存在: {template_id}")
            print(f"   是否更新？(yes/no): ", end="")
            confirm = input().strip().lower()
            
            if confirm == "yes":
                # 更新现有模板
                existing.title = title
                existing.description = description
                existing.prompt_body = prompt_body
                existing.set_supported_languages_list(["zh-CN", "en-US"])
                existing.set_parameter_schema_dict(parameter_schema)
                existing.updated_at = datetime.utcnow()
                
                session.commit()
                print(f"✅ 模板已更新: {template_id}")
            else:
                print("❌ 已取消")
                return
        else:
            # 添加新模板
            session.add(template)
            session.commit()
            print(f"✅ 模板已添加: {template_id}")
        
        # 显示模板信息
        print("\n" + "=" * 60)
        print("模板信息:")
        print("=" * 60)
        print(f"ID: {template_id}")
        print(f"标题: {title}")
        print(f"描述: {description}")
        print(f"类型: meeting_minutes")
        print(f"语言: zh-CN, en-US")
        print(f"作用域: global (系统模板)")
        print("=" * 60)
        
    except Exception as e:
        session.rollback()
        print(f"❌ 添加失败: {e}")
        raise
    finally:
        session.close()


if __name__ == "__main__":
    print("添加详细摘要模板...")
    print()
    
    try:
        add_detailed_summary_template()
        print("\n✅ 完成！")
    except KeyboardInterrupt:
        print("\n\n⚠️  用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 失败: {e}")
        sys.exit(1)

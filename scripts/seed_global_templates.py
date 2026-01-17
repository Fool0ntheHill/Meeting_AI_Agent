"""
初始化全局提示词模板

创建系统预置的全局模板,供所有用户使用。

运行方式:
    python scripts/seed_global_templates.py
"""

import sys
import os

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.database.session import get_session, init_db
from src.database.repositories import PromptTemplateRepository
from src.utils.logger import get_logger

logger = get_logger(__name__)


# 全局模板定义
GLOBAL_TEMPLATES = [
    {
        "template_id": "tpl_standard_minutes",
        "title": "标准会议纪要",
        "description": "生成包含摘要、关键要点和行动项的标准会议纪要",
        "prompt_body": """你是一个专业的会议纪要助手。

会议信息:
{meeting_description}

请根据以下会议转写生成结构化的会议纪要:

会议转写:
{transcript}

请按以下格式生成会议纪要:

# 会议纪要

## 会议概要
[简要概述会议的主要内容和目的]

## 关键要点
1. [要点 1]
2. [要点 2]
3. [要点 3]
...

## 讨论详情
[详细记录会议中的重要讨论内容,包括不同观点和决策过程]

## 行动项
- [ ] [行动项 1] - 负责人: [姓名] - 截止日期: [日期]
- [ ] [行动项 2] - 负责人: [姓名] - 截止日期: [日期]
...

## 下次会议
[如有安排,说明下次会议的时间和议题]""",
        "artifact_type": "meeting_minutes",
        "supported_languages": ["zh-CN", "en-US"],
        "parameter_schema": {
            "meeting_description": {
                "type": "string",
                "required": False,
                "default": "",
                "description": "会议描述信息(标题、主题、背景等)"
            }
        },
    },
    {
        "template_id": "tpl_action_items",
        "title": "行动项提取",
        "description": "从会议中提取行动项和待办事项",
        "prompt_body": """你是一个专业的会议助手,擅长从会议讨论中提取行动项。

会议信息:
{meeting_description}

请从以下会议转写中提取所有行动项:

会议转写:
{transcript}

请按以下格式列出所有行动项:

# 行动项清单

## 高优先级
- [ ] [行动项描述] - 负责人: [姓名] - 截止日期: [日期] - 备注: [相关上下文]

## 中优先级
- [ ] [行动项描述] - 负责人: [姓名] - 截止日期: [日期] - 备注: [相关上下文]

## 低优先级
- [ ] [行动项描述] - 负责人: [姓名] - 截止日期: [日期] - 备注: [相关上下文]

注意:
- 明确标注每个行动项的负责人
- 如果会议中提到了截止日期,请标注
- 如果没有明确的负责人或截止日期,请标注为"待定"
- 按优先级分类(根据会议中的讨论语气和紧急程度判断)""",
        "artifact_type": "action_items",
        "supported_languages": ["zh-CN", "en-US"],
        "parameter_schema": {
            "meeting_description": {
                "type": "string",
                "required": False,
                "default": "",
                "description": "会议描述信息"
            }
        },
    },
    {
        "template_id": "tpl_summary_notes",
        "title": "会议摘要笔记",
        "description": "生成简洁的会议摘要笔记",
        "prompt_body": """你是一个专业的会议记录助手,擅长提炼会议要点。

会议信息:
{meeting_description}

请根据以下会议转写生成简洁的摘要笔记:

会议转写:
{transcript}

请按以下格式生成摘要笔记:

# 会议摘要

**会议时间**: [从转写中提取]
**参与人员**: [列出所有说话人]

## 核心要点
- [要点 1]
- [要点 2]
- [要点 3]

## 重要决策
- [决策 1]
- [决策 2]

## 待跟进事项
- [事项 1]
- [事项 2]

注意:
- 保持简洁,每个要点不超过一句话
- 突出最重要的信息
- 使用清晰的结构化格式""",
        "artifact_type": "summary_notes",
        "supported_languages": ["zh-CN", "en-US"],
        "parameter_schema": {
            "meeting_description": {
                "type": "string",
                "required": False,
                "default": "",
                "description": "会议描述信息"
            }
        },
    },
    {
        "template_id": "tpl_technical_minutes",
        "title": "技术会议纪要",
        "description": "适用于技术团队的会议纪要,重点关注技术决策和实现细节",
        "prompt_body": """你是一个专业的技术会议记录助手。

会议信息:
{meeting_description}

请根据以下会议转写生成技术导向的会议纪要:

会议转写:
{transcript}

请按以下格式生成技术会议纪要:

# 技术会议纪要

## 会议概要
[简要概述会议的技术主题和目的]

## 技术决策
1. **[决策 1]**
   - 背景: [为什么需要这个决策]
   - 方案: [选择的技术方案]
   - 理由: [为什么选择这个方案]
   - 影响: [对系统的影响]

2. **[决策 2]**
   ...

## 技术讨论
### [主题 1]
- 讨论内容: [详细记录技术讨论]
- 不同观点: [如有分歧,记录不同观点]
- 结论: [最终结论]

### [主题 2]
...

## 技术风险与挑战
- [风险 1]: [描述] - 应对措施: [措施]
- [风险 2]: [描述] - 应对措施: [措施]

## 行动项
- [ ] [技术任务 1] - 负责人: [姓名] - 截止日期: [日期]
- [ ] [技术任务 2] - 负责人: [姓名] - 截止日期: [日期]

## 技术参考
[如有提到的技术文档、API、工具等,列出链接或名称]

注意:
- 重点关注技术决策和实现细节
- 明确记录技术方案的选择理由
- 突出技术风险和挑战
- 使用技术术语,但保持清晰易懂""",
        "artifact_type": "meeting_minutes",
        "supported_languages": ["zh-CN", "en-US"],
        "parameter_schema": {
            "meeting_description": {
                "type": "string",
                "required": False,
                "default": "",
                "description": "会议描述信息"
            }
        },
    },
]


def seed_templates():
    """初始化全局模板"""
    logger.info("开始初始化全局提示词模板...")
    
    # 初始化数据库
    init_db()
    
    db = get_session()
    repo = PromptTemplateRepository(db)
    
    created_count = 0
    skipped_count = 0
    
    for template_data in GLOBAL_TEMPLATES:
        template_id = template_data["template_id"]
        
        # 检查模板是否已存在
        existing = repo.get_by_id(template_id)
        if existing:
            logger.info(f"模板已存在,跳过: {template_id}")
            skipped_count += 1
            continue
        
        # 创建模板
        try:
            repo.create(
                template_id=template_data["template_id"],
                title=template_data["title"],
                description=template_data["description"],
                prompt_body=template_data["prompt_body"],
                artifact_type=template_data["artifact_type"],
                supported_languages=template_data["supported_languages"],
                parameter_schema=template_data["parameter_schema"],
                is_system=True,
                scope="global",
                scope_id=None,
            )
            db.commit()
            logger.info(f"✅ 模板已创建: {template_id} - {template_data['title']}")
            created_count += 1
        
        except Exception as e:
            db.rollback()
            logger.error(f"❌ 创建模板失败: {template_id} - {e}")
    
    logger.info(f"\n初始化完成:")
    logger.info(f"  - 创建: {created_count} 个模板")
    logger.info(f"  - 跳过: {skipped_count} 个模板")
    logger.info(f"  - 总计: {len(GLOBAL_TEMPLATES)} 个模板")


if __name__ == "__main__":
    seed_templates()

# -*- coding: utf-8 -*-
"""查看模板详情

使用方法:
    python scripts/view_template.py meeting_minutes_detailed_summary
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.database.session import get_session
from src.database.models import PromptTemplateRecord


def view_template(template_id: str):
    """查看模板详情"""
    session = get_session()
    
    try:
        template = session.query(PromptTemplateRecord).filter_by(
            template_id=template_id
        ).first()
        
        if not template:
            print(f"❌ 模板不存在: {template_id}")
            return
        
        print("=" * 80)
        print(f"模板详情: {template_id}")
        print("=" * 80)
        print(f"标题: {template.title}")
        print(f"描述: {template.description}")
        print(f"类型: {template.artifact_type}")
        print(f"语言: {', '.join(template.get_supported_languages_list())}")
        print(f"系统模板: {'是' if template.is_system else '否'}")
        print(f"作用域: {template.scope}")
        print(f"创建时间: {template.created_at}")
        print(f"更新时间: {template.updated_at}")
        print("\n" + "-" * 80)
        print("提示词:")
        print("-" * 80)
        print(template.prompt_body)
        print("\n" + "-" * 80)
        print("参数定义:")
        print("-" * 80)
        import json
        print(json.dumps(template.get_parameter_schema_dict(), indent=2, ensure_ascii=False))
        print("=" * 80)
        
    finally:
        session.close()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python scripts/view_template.py <template_id>")
        print("示例: python scripts/view_template.py meeting_minutes_detailed_summary")
        sys.exit(1)
    
    template_id = sys.argv[1]
    view_template(template_id)

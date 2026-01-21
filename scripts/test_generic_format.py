#!/usr/bin/env python3
"""测试通用格式的智能映射"""

import json
from src.utils.artifact_normalizer import ArtifactNormalizer

# 测试用户自定义的格式
custom_formats = [
    # 格式 1: 中文键名
    {
        "会议主题": "产品设计评审",
        "会议概要": "讨论了新产品的UI设计方案",
        "讨论要点": [
            "界面布局需要优化",
            "颜色方案待确认",
            "交互流程需要简化"
        ],
        "决策事项": [
            "采用方案A的布局",
            "下周完成原型"
        ],
        "待办事项": [
            {
                "任务": "完成UI原型",
                "负责人": "张三",
                "截止日期": "2024-01-30"
            }
        ],
        "参与者": ["张三", "李四", "王五"]
    },
    
    # 格式 2: 英文键名
    {
        "subject": "Weekly Team Meeting",
        "overview": "Discussed project progress and next steps",
        "discussions": [
            "Backend API development is on track",
            "Frontend needs more resources"
        ],
        "resolutions": [
            "Hire 2 more frontend developers",
            "Extend deadline by 1 week"
        ],
        "todos": [
            {
                "description": "Post job openings",
                "assignee": "HR Team"
            }
        ]
    },
    
    # 格式 3: 混合格式
    {
        "标题": "技术分享会",
        "总结": "分享了最新的AI技术趋势",
        "要点": "AI在各行业的应用案例",
        "行动项": [
            "研究GPT-4的应用场景",
            "准备下次分享的PPT"
        ]
    }
]

print("=" * 80)
print("测试通用格式的智能映射")
print("=" * 80)

for i, custom_format in enumerate(custom_formats, 1):
    print(f"\n{'='*80}")
    print(f"测试格式 {i}")
    print(f"{'='*80}\n")
    
    print("原始格式:")
    print(json.dumps(custom_format, ensure_ascii=False, indent=2))
    
    print(f"\n{'─'*80}")
    print("标准化处理...")
    print(f"{'─'*80}\n")
    
    try:
        result = ArtifactNormalizer.normalize(custom_format, "meeting_minutes")
        
        print(f"✅ 标准化成功!")
        print(f"格式版本: {result['format_version']}")
        print(f"原始格式: {result['original_format']}")
        print(f"\n标准化后的内容:")
        print(json.dumps(result['normalized'], ensure_ascii=False, indent=2))
        
    except Exception as e:
        print(f"❌ 标准化失败: {e}")
        import traceback
        traceback.print_exc()

print(f"\n{'='*80}")
print("测试完成")
print(f"{'='*80}")

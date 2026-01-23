"""
查看任务的 artifacts 及其提示词信息

显示每个 artifact 使用的提示词详情
"""

import asyncio
import sys
import json
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.database.session import get_session
from src.database.repositories import TaskRepository, ArtifactRepository
from sqlalchemy import text


async def check_artifact_prompts(task_id: str):
    """查看任务的 artifacts 提示词"""
    
    print("=" * 80)
    print(f"查看任务 artifacts 提示词: {task_id}")
    print("=" * 80)
    
    with get_session() as session:
        task_repo = TaskRepository(session)
        
        # 获取任务
        task = task_repo.get_by_id(task_id)
        if not task:
            print(f"✗ 任务不存在: {task_id}")
            return
        
        print(f"\n【任务信息】")
        print(f"  任务 ID: {task.task_id}")
        print(f"  状态: {task.state}")
        print(f"  用户 ID: {task.user_id}")
        print(f"  创建时间: {task.created_at}")
        
        # 直接查询 generated_artifacts 表
        result = session.execute(
            text("""
                SELECT artifact_id, artifact_type, version, artifact_metadata, content, created_at, created_by
                FROM generated_artifacts
                WHERE task_id = :task_id
                ORDER BY version ASC
            """),
            {"task_id": task_id}
        ).fetchall()
        
        if not result:
            print(f"\n✗ 没有找到 artifacts")
            return
        
        print(f"\n【Artifacts 列表】")
        print(f"  找到 {len(result)} 个 artifacts\n")
        
        for i, row in enumerate(result, 1):
            artifact_id, artifact_type, version, metadata_str, content, created_at, created_by = row
            
            print("=" * 80)
            print(f"Artifact #{i}")
            print("=" * 80)
            
            print(f"\n  Artifact ID: {artifact_id}")
            print(f"  类型: {artifact_type}")
            print(f"  版本: {version}")
            print(f"  创建时间: {created_at}")
            print(f"  创建者: {created_by}")
            
            # 解析 metadata
            if metadata_str:
                try:
                    metadata = json.loads(metadata_str)
                    
                    print(f"\n  【Metadata 信息】")
                    print(f"    LLM 模型: {metadata.get('llm_model', 'N/A')}")
                    print(f"    Token 总数: {metadata.get('token_count', 'N/A')}")
                    
                    # 检查提示词信息
                    prompt_info = metadata.get('prompt')
                    
                    if prompt_info:
                        print(f"\n  【提示词信息】 ✓ 已保存")
                        print(f"    模板 ID: {prompt_info.get('template_id', 'N/A')}")
                        print(f"    语言: {prompt_info.get('language', 'N/A')}")
                        print(f"    是否用户编辑: {prompt_info.get('is_user_edited', 'N/A')}")
                        
                        # 显示参数
                        parameters = prompt_info.get('parameters', {})
                        if parameters:
                            print(f"    参数:")
                            for key, value in parameters.items():
                                value_str = str(value)[:100]
                                print(f"      - {key}: {value_str}")
                        else:
                            print(f"    参数: (无)")
                        
                        # 显示补充指令
                        custom_inst = prompt_info.get('custom_instructions')
                        if custom_inst:
                            print(f"    补充指令: {custom_inst}")
                        
                        # 显示提示词文本
                        prompt_text = prompt_info.get('prompt_text', '')
                        print(f"\n  【提示词文本】")
                        print("  " + "-" * 76)
                        # 显示前800个字符
                        if len(prompt_text) > 800:
                            print(f"  {prompt_text[:800]}")
                            print(f"  ... (还有 {len(prompt_text) - 800} 个字符)")
                        else:
                            print(f"  {prompt_text}")
                        print("  " + "-" * 76)
                    else:
                        print(f"\n  【提示词信息】 ✗ 未保存（旧版本数据）")
                        
                except json.JSONDecodeError:
                    print(f"\n  【Metadata】 ✗ JSON 解析失败")
            else:
                print(f"\n  【Metadata】 ✗ 无 metadata")
            
            # 显示内容预览
            print(f"\n  【内容预览】")
            print("  " + "-" * 76)
            if content:
                content_preview = content[:300]
                print(f"  {content_preview}")
                if len(content) > 300:
                    print(f"  ... (还有 {len(content) - 300} 个字符)")
            else:
                print("  (无内容)")
            print("  " + "-" * 76)
            
            print()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python scripts/check_artifact_prompts.py <task_id>")
        print("示例: python scripts/check_artifact_prompts.py task_d0342ccb5de44548")
        sys.exit(1)
    
    task_id = sys.argv[1]
    asyncio.run(check_artifact_prompts(task_id))

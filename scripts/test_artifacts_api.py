"""
测试衍生内容管理 API

测试场景:
1. 创建测试任务
2. 生成不同类型的衍生内容
3. 列出所有衍生内容(按类型分组)
4. 列出特定类型的所有版本
5. 获取特定版本的详情
6. 生成同一类型的多个版本

运行前提:
- API 服务器已启动: python main.py
- 数据库已初始化
- 全局模板已初始化: python scripts/seed_global_templates.py
"""

import requests
import json
from typing import Dict, Any
from auth_helper import get_auth_headers, BASE_URL

# 测试用户名
USERNAME = "test_user_001"


def print_section(title: str):
    """打印测试章节标题"""
    print(f"\n{'=' * 80}")
    print(f"  {title}")
    print(f"{'=' * 80}\n")


def print_response(response: requests.Response):
    """打印响应信息"""
    print(f"状态码: {response.status_code}")
    try:
        data = response.json()
        print(f"响应: {json.dumps(data, indent=2, ensure_ascii=False)}")
    except:
        print(f"响应: {response.text}")
    print()


def create_test_task() -> str:
    """创建测试任务"""
    print_section("创建测试任务")
    
    # 注意: 这里需要实际的音频文件和完整的任务创建流程
    # 为了测试,我们假设已经有一个完成的任务
    # 实际使用时需要先创建任务并等待处理完成
    
    print("⚠️ 注意: 此测试需要一个已完成的任务 ID")
    print("请先运行完整的任务处理流程,或使用现有的任务 ID")
    print()
    
    # 返回一个示例任务 ID (需要替换为实际的任务 ID)
    return "task_example_001"


def generate_artifact(task_id: str, artifact_type: str, template_id: str, description: str = "") -> Dict:
    """生成衍生内容"""
    print(f"生成 {artifact_type} (模板: {template_id})...")
    
    request_data = {
        "prompt_instance": {
            "template_id": template_id,
            "language": "zh-CN",
            "parameters": {
                "meeting_description": description or f"测试会议 - {artifact_type}"
            }
        }
    }
    
    response = requests.post(
        f"{BASE_URL}/tasks/{task_id}/artifacts/{artifact_type}/generate",
        headers=get_auth_headers(USERNAME),
        json=request_data
    )
    
    print_response(response)
    
    if response.status_code == 201:
        data = response.json()
        print(f"✅ 衍生内容已生成: {data['artifact_id']} (版本 {data['version']})")
        return data
    else:
        print(f"❌ 生成失败")
        return {}


def list_all_artifacts(task_id: str):
    """列出所有衍生内容(按类型分组)"""
    print_section("列出所有衍生内容(按类型分组)")
    
    response = requests.get(
        f"{BASE_URL}/tasks/{task_id}/artifacts",
        headers=get_auth_headers(USERNAME)
    )
    
    print_response(response)
    
    if response.status_code == 200:
        data = response.json()
        artifacts_by_type = data.get("artifacts_by_type", {})
        total = data.get("total_count", 0)
        
        print(f"✅ 找到 {total} 个衍生内容,分为 {len(artifacts_by_type)} 种类型:")
        for artifact_type, artifacts in artifacts_by_type.items():
            print(f"  - {artifact_type}: {len(artifacts)} 个版本")
        
        return artifacts_by_type
    else:
        print("❌ 列出失败")
        return {}


def list_artifact_versions(task_id: str, artifact_type: str):
    """列出特定类型的所有版本"""
    print_section(f"列出 {artifact_type} 的所有版本")
    
    response = requests.get(
        f"{BASE_URL}/tasks/{task_id}/artifacts/{artifact_type}/versions",
        headers=get_auth_headers(USERNAME)
    )
    
    print_response(response)
    
    if response.status_code == 200:
        data = response.json()
        versions = data.get("versions", [])
        print(f"✅ 找到 {len(versions)} 个版本")
        
        for version_info in versions:
            print(f"  - 版本 {version_info['version']}: {version_info['artifact_id']}")
            print(f"    模板: {version_info['prompt_instance']['template_id']}")
            print(f"    创建时间: {version_info['created_at']}")
        
        return versions
    else:
        print("❌ 列出失败")
        return []


def get_artifact_detail(task_id: str, artifact_id: str):
    """获取特定版本的详情"""
    print_section(f"获取衍生内容详情: {artifact_id}")
    
    response = requests.get(
        f"{BASE_URL}/tasks/{task_id}/artifacts/{artifact_id}",
        headers=get_auth_headers(USERNAME)
    )
    
    print_response(response)
    
    if response.status_code == 200:
        data = response.json()
        artifact = data.get("artifact", {})
        print(f"✅ 获取成功:")
        print(f"  - 类型: {artifact.get('artifact_type')}")
        print(f"  - 版本: {artifact.get('version')}")
        print(f"  - 模板: {artifact.get('prompt_instance', {}).get('template_id')}")
        print(f"  - 内容: {json.dumps(artifact.get('content', {}), ensure_ascii=False)[:200]}...")
        
        return artifact
    else:
        print("❌ 获取失败")
        return {}


def test_version_management(task_id: str):
    """测试版本管理"""
    print_section("测试版本管理 - 生成同一类型的多个版本")
    
    # 使用不同的模板生成多个版本
    templates = [
        ("tpl_standard_minutes", "标准会议纪要"),
        ("tpl_technical_minutes", "技术会议纪要"),
    ]
    
    for template_id, description in templates:
        generate_artifact(
            task_id,
            "meeting_minutes",
            template_id,
            f"使用{description}模板"
        )
    
    # 列出所有版本
    versions = list_artifact_versions(task_id, "meeting_minutes")
    
    if len(versions) >= 2:
        print(f"\n✅ 版本管理测试通过: 成功创建了 {len(versions)} 个版本")
    else:
        print(f"\n❌ 版本管理测试失败: 只有 {len(versions)} 个版本")


def main():
    """运行所有测试"""
    print("\n" + "=" * 80)
    print("  衍生内容管理 API 测试")
    print("=" * 80)
    
    # 注意: 这个测试需要一个已完成的任务
    # 实际使用时需要先创建任务并等待处理完成
    task_id = create_test_task()
    
    print(f"\n使用任务 ID: {task_id}")
    print("⚠️ 如果任务不存在或未完成,测试将失败")
    print("请确保:")
    print("1. 任务已创建并处理完成")
    print("2. 任务状态为 SUCCESS 或 PARTIAL_SUCCESS")
    print("3. 任务有转写结果")
    
    input("\n按 Enter 继续测试...")
    
    try:
        # 测试 1: 生成不同类型的衍生内容
        print_section("测试 1: 生成不同类型的衍生内容")
        
        # 生成会议纪要
        generate_artifact(task_id, "meeting_minutes", "tpl_standard_minutes", "技术评审会议")
        
        # 生成行动项
        generate_artifact(task_id, "action_items", "tpl_action_items", "技术评审会议")
        
        # 生成摘要笔记
        generate_artifact(task_id, "summary_notes", "tpl_summary_notes", "技术评审会议")
        
        # 测试 2: 列出所有衍生内容
        artifacts_by_type = list_all_artifacts(task_id)
        
        # 测试 3: 列出特定类型的所有版本
        if "meeting_minutes" in artifacts_by_type:
            list_artifact_versions(task_id, "meeting_minutes")
        
        # 测试 4: 获取特定版本的详情
        if artifacts_by_type:
            # 获取第一个类型的第一个版本
            first_type = list(artifacts_by_type.keys())[0]
            first_artifact = artifacts_by_type[first_type][0]
            get_artifact_detail(task_id, first_artifact["artifact_id"])
        
        # 测试 5: 版本管理
        test_version_management(task_id)
        
        print_section("测试完成")
        print("✅ 所有测试已执行完成")
        print("\n注意: 当前为 Phase 1 实现,生成的内容为占位符")
        print("Phase 2 将实现实际的 LLM 内容生成")
        
    except Exception as e:
        print(f"\n❌ 测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()

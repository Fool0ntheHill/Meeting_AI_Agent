"""
测试提示词模板管理 API

测试场景:
1. 列出全局模板
2. 创建私有模板
3. 获取模板详情
4. 更新私有模板
5. 删除私有模板
6. 权限验证

运行前提:
- API 服务器已启动: python main.py
- 数据库已初始化
"""

import requests
import json
from typing import Dict, Any

# API 基础 URL
BASE_URL = "http://localhost:8000/api/v1"

# 测试用户 ID
USER_ID_1 = "user_001"
USER_ID_2 = "user_002"


def print_section(title: str):
    """打印测试章节标题"""
    print(f"\n{'=' * 80}")
    print(f"  {title}")
    print(f"{'=' * 80}\n")


def print_response(response: requests.Response):
    """打印响应信息"""
    print(f"Status: {response.status_code}")
    try:
        data = response.json()
        print(f"Response: {json.dumps(data, indent=2, ensure_ascii=False)}")
    except:
        print(f"Response: {response.text}")
    print()


def test_list_global_templates():
    """测试 1: 列出全局模板"""
    print_section("测试 1: 列出全局模板")
    
    response = requests.get(f"{BASE_URL}/prompt-templates", params={"scope": "global"})
    print_response(response)
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ 找到 {len(data['templates'])} 个全局模板")
        return data["templates"]
    else:
        print("❌ 列出全局模板失败")
        return []


def test_create_private_template(user_id: str) -> str:
    """测试 2: 创建私有模板"""
    print_section(f"测试 2: 创建私有模板 (用户: {user_id})")
    
    template_data = {
        "title": f"用户 {user_id} 的自定义会议纪要模板",
        "description": "适用于技术团队的会议纪要模板",
        "prompt_body": """你是一个专业的会议纪要助手。

会议信息:
{meeting_description}

请根据以下会议转写生成技术导向的会议纪要:
- 重点关注技术决策和实现细节
- 明确列出行动项和负责人
- 突出技术风险和挑战

会议转写:
{transcript}

请生成结构化的会议纪要。""",
        "artifact_type": "meeting_minutes",
        "supported_languages": ["zh-CN", "en-US"],
        "parameter_schema": {
            "meeting_description": {
                "type": "string",
                "required": False,
                "default": "",
                "description": "会议描述信息(标题、主题、背景等)"
            }
        }
    }
    
    response = requests.post(
        f"{BASE_URL}/prompt-templates",
        params={"user_id": user_id},
        json=template_data
    )
    print_response(response)
    
    if response.status_code == 201:
        data = response.json()
        template_id = data["template_id"]
        print(f"✅ 私有模板已创建: {template_id}")
        return template_id
    else:
        print("❌ 创建私有模板失败")
        return ""


def test_get_template_detail(template_id: str, user_id: str):
    """测试 3: 获取模板详情"""
    print_section(f"测试 3: 获取模板详情 (模板: {template_id}, 用户: {user_id})")
    
    response = requests.get(
        f"{BASE_URL}/prompt-templates/{template_id}",
        params={"user_id": user_id}
    )
    print_response(response)
    
    if response.status_code == 200:
        print(f"✅ 成功获取模板详情")
    else:
        print(f"❌ 获取模板详情失败")


def test_list_user_templates(user_id: str):
    """测试 4: 列出用户的所有模板 (全局 + 私有)"""
    print_section(f"测试 4: 列出用户的所有模板 (用户: {user_id})")
    
    response = requests.get(
        f"{BASE_URL}/prompt-templates",
        params={"user_id": user_id}
    )
    print_response(response)
    
    if response.status_code == 200:
        data = response.json()
        templates = data["templates"]
        global_count = sum(1 for t in templates if t["scope"] == "global")
        private_count = sum(1 for t in templates if t["scope"] == "private")
        print(f"✅ 找到 {len(templates)} 个模板 (全局: {global_count}, 私有: {private_count})")
    else:
        print("❌ 列出模板失败")


def test_update_template(template_id: str, user_id: str):
    """测试 5: 更新私有模板"""
    print_section(f"测试 5: 更新私有模板 (模板: {template_id}, 用户: {user_id})")
    
    update_data = {
        "title": f"用户 {user_id} 的自定义会议纪要模板 (已更新)",
        "description": "更新后的描述: 适用于技术团队的会议纪要模板 v2"
    }
    
    response = requests.put(
        f"{BASE_URL}/prompt-templates/{template_id}",
        params={"user_id": user_id},
        json=update_data
    )
    print_response(response)
    
    if response.status_code == 200:
        print(f"✅ 私有模板已更新")
    else:
        print(f"❌ 更新私有模板失败")


def test_access_control(template_id: str, owner_id: str, other_user_id: str):
    """测试 6: 权限控制 - 其他用户不能访问私有模板"""
    print_section(f"测试 6: 权限控制 (模板: {template_id}, 所有者: {owner_id}, 访问者: {other_user_id})")
    
    # 尝试用其他用户访问
    print(f"尝试用用户 {other_user_id} 访问用户 {owner_id} 的私有模板...")
    response = requests.get(
        f"{BASE_URL}/prompt-templates/{template_id}",
        params={"user_id": other_user_id}
    )
    print_response(response)
    
    if response.status_code == 403:
        print(f"✅ 权限控制正常: 其他用户无法访问私有模板")
    else:
        print(f"❌ 权限控制失败: 其他用户不应该能访问私有模板")
    
    # 尝试用其他用户更新
    print(f"尝试用用户 {other_user_id} 更新用户 {owner_id} 的私有模板...")
    response = requests.put(
        f"{BASE_URL}/prompt-templates/{template_id}",
        params={"user_id": other_user_id},
        json={"title": "尝试恶意修改"}
    )
    print_response(response)
    
    if response.status_code == 403:
        print(f"✅ 权限控制正常: 其他用户无法更新私有模板")
    else:
        print(f"❌ 权限控制失败: 其他用户不应该能更新私有模板")
    
    # 尝试用其他用户删除
    print(f"尝试用用户 {other_user_id} 删除用户 {owner_id} 的私有模板...")
    response = requests.delete(
        f"{BASE_URL}/prompt-templates/{template_id}",
        params={"user_id": other_user_id}
    )
    print_response(response)
    
    if response.status_code == 403:
        print(f"✅ 权限控制正常: 其他用户无法删除私有模板")
    else:
        print(f"❌ 权限控制失败: 其他用户不应该能删除私有模板")


def test_delete_template(template_id: str, user_id: str):
    """测试 7: 删除私有模板"""
    print_section(f"测试 7: 删除私有模板 (模板: {template_id}, 用户: {user_id})")
    
    response = requests.delete(
        f"{BASE_URL}/prompt-templates/{template_id}",
        params={"user_id": user_id}
    )
    print_response(response)
    
    if response.status_code == 200:
        print(f"✅ 私有模板已删除")
    else:
        print(f"❌ 删除私有模板失败")


def test_filter_by_artifact_type():
    """测试 8: 按内容类型过滤"""
    print_section("测试 8: 按内容类型过滤")
    
    response = requests.get(
        f"{BASE_URL}/prompt-templates",
        params={"artifact_type": "meeting_minutes"}
    )
    print_response(response)
    
    if response.status_code == 200:
        data = response.json()
        templates = data["templates"]
        print(f"✅ 找到 {len(templates)} 个 meeting_minutes 类型的模板")
        
        # 验证所有模板都是 meeting_minutes 类型
        all_correct = all(t["artifact_type"] == "meeting_minutes" for t in templates)
        if all_correct:
            print("✅ 所有模板类型正确")
        else:
            print("❌ 存在类型不匹配的模板")
    else:
        print("❌ 按类型过滤失败")


def main():
    """运行所有测试"""
    print("\n" + "=" * 80)
    print("  提示词模板管理 API 测试")
    print("=" * 80)
    
    try:
        # 测试 1: 列出全局模板
        global_templates = test_list_global_templates()
        
        # 测试 2: 创建私有模板 (用户 1)
        template_id_1 = test_create_private_template(USER_ID_1)
        
        if template_id_1:
            # 测试 3: 获取模板详情
            test_get_template_detail(template_id_1, USER_ID_1)
            
            # 测试 4: 列出用户的所有模板
            test_list_user_templates(USER_ID_1)
            
            # 测试 5: 更新私有模板
            test_update_template(template_id_1, USER_ID_1)
            
            # 测试 6: 权限控制
            test_access_control(template_id_1, USER_ID_1, USER_ID_2)
            
            # 测试 7: 删除私有模板
            test_delete_template(template_id_1, USER_ID_1)
        
        # 测试 8: 按内容类型过滤
        test_filter_by_artifact_type()
        
        print_section("测试完成")
        print("✅ 所有测试已执行完成")
        
    except Exception as e:
        print(f"\n❌ 测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()

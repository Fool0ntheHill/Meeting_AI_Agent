"""
测试企业微信 Markdown 消息发送
"""
import requests
import json

# 企业微信消息服务地址
WECOM_API_BASE = "http://gsmsg.gs.com:24905"

def send_wecom_markdown(to_users: list, message: str):
    """
    发送企业微信 Markdown 消息
    
    Args:
        to_users: 收件人列表（企业微信英文名）
        message: Markdown 格式的消息内容
    """
    url = f"{WECOM_API_BASE}/msg/send_wecom_markdown"
    
    payload = {
        "to": to_users,
        "msg": message
    }
    
    headers = {
        "Content-Type": "application/json"
    }
    
    print(f"发送企业微信消息到: {to_users}")
    print(f"消息内容:\n{message}")
    print(f"\n请求 URL: {url}")
    print(f"请求体: {json.dumps(payload, ensure_ascii=False, indent=2)}")
    print("\n发送中...")
    
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        
        print(f"\n响应状态码: {response.status_code}")
        print(f"响应内容: {response.text}")
        
        if response.status_code == 200:
            print("\n✅ 消息发送成功！")
            return True
        else:
            print(f"\n❌ 消息发送失败: HTTP {response.status_code}")
            return False
            
    except requests.exceptions.Timeout:
        print("\n❌ 请求超时")
        return False
    except requests.exceptions.ConnectionError:
        print("\n❌ 连接失败，请检查网络或服务地址")
        return False
    except Exception as e:
        print(f"\n❌ 发送失败: {e}")
        return False


def test_simple_message():
    """测试简单消息"""
    print("=" * 60)
    print("测试 1: 发送简单文本消息")
    print("=" * 60)
    
    message = "这是一条测试消息"
    send_wecom_markdown(["lorenzolin"], message)


def test_markdown_message():
    """测试 Markdown 格式消息"""
    print("\n" + "=" * 60)
    print("测试 2: 发送 Markdown 格式消息")
    print("=" * 60)
    
    message = """# 会议纪要生成通知

## 任务信息
- **任务 ID**: task_1c8f2c5d561048db
- **状态**: 生成中
- **进度**: 50%

## 详情
您的会议纪要正在生成中，请稍候...

---
*Meeting AI Agent*"""
    
    send_wecom_markdown(["lorenzolin"], message)


def test_meeting_notification():
    """测试会议纪要生成通知"""
    print("\n" + "=" * 60)
    print("测试 3: 发送会议纪要生成完成通知")
    print("=" * 60)
    
    message = """# ✅ 会议纪要生成完成

## 会议信息
- **会议标题**: 产品规划会议
- **会议时间**: 2026-01-26 15:30
- **参与人员**: 张三、李四、王五

## 生成结果
- **任务 ID**: task_1c8f2c5d561048db
- **生成时间**: 2026-01-26 21:30
- **状态**: ✅ 成功

## 生成内容
- 📝 会议纪要
- 📋 行动项
- 📊 会议摘要

点击查看详情 👉 [查看会议纪要](http://localhost:5173/tasks/task_1c8f2c5d561048db)

---
*由 Meeting AI Agent 自动生成*"""
    
    send_wecom_markdown(["lorenzolin"], message)


if __name__ == "__main__":
    print("企业微信 Markdown 消息测试")
    print("=" * 60)
    print()
    
    # 测试 1: 简单消息
    test_simple_message()
    
    # 等待用户确认
    input("\n按 Enter 继续测试 Markdown 格式消息...")
    
    # 测试 2: Markdown 消息
    test_markdown_message()
    
    # 等待用户确认
    input("\n按 Enter 继续测试会议通知...")
    
    # 测试 3: 会议通知
    test_meeting_notification()
    
    print("\n" + "=" * 60)
    print("测试完成！")
    print("=" * 60)

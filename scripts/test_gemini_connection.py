"""测试 Gemini API 连接和 SSL 问题"""

import asyncio
import sys
import os

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.config.loader import load_config
from src.providers.gemini_llm import GeminiLLMProvider


async def test_simple_request():
    """测试简单的 Gemini API 请求"""
    print("=" * 80)
    print("测试 Gemini API 连接")
    print("=" * 80)
    
    # 加载配置
    config = load_config()
    
    # 创建 LLM provider
    llm = GeminiLLMProvider(
        api_key=config.llm.api_key,
        model=config.llm.model,
    )
    
    # 测试 1: 非常简单的请求
    print("\n1. 测试简单请求（10个字）...")
    try:
        simple_prompt = "请用一句话介绍 Python 编程语言。"
        response = await llm.client.generate_content_async(simple_prompt)
        print(f"✓ 成功: {response.text[:100]}...")
    except Exception as e:
        print(f"✗ 失败: {e}")
        return False
    
    # 测试 2: 中等长度请求
    print("\n2. 测试中等长度请求（100个字）...")
    try:
        medium_prompt = "请详细介绍 Python 编程语言的特点，包括语法、应用场景、优缺点等。" * 5
        response = await llm.client.generate_content_async(medium_prompt)
        print(f"✓ 成功: {response.text[:100]}...")
    except Exception as e:
        print(f"✗ 失败: {e}")
        return False
    
    # 测试 3: 较长请求（模拟会议转写）
    print("\n3. 测试较长请求（1000个字）...")
    try:
        long_prompt = """
        以下是一段会议转写内容，请总结要点：
        
        """ + ("这是一段会议讨论内容。" * 200)
        
        response = await llm.client.generate_content_async(long_prompt)
        print(f"✓ 成功: {response.text[:100]}...")
    except Exception as e:
        print(f"✗ 失败: {e}")
        print("\n可能的原因：")
        print("- 请求内容过长")
        print("- 网络连接不稳定")
        print("- SSL/TLS 握手失败")
        return False
    
    print("\n" + "=" * 80)
    print("✓ 所有测试通过！Gemini API 连接正常")
    print("=" * 80)
    return True


async def test_with_retry():
    """测试带重试的请求"""
    print("\n" + "=" * 80)
    print("测试带重试机制的请求")
    print("=" * 80)
    
    config = load_config()
    llm = GeminiLLMProvider(
        api_key=config.llm.api_key,
        model=config.llm.model,
    )
    
    max_retries = 3
    for attempt in range(1, max_retries + 1):
        try:
            print(f"\n尝试 {attempt}/{max_retries}...")
            prompt = "请用一句话介绍 Python。"
            response = await llm.client.generate_content_async(prompt)
            print(f"✓ 成功: {response.text[:100]}...")
            return True
        except Exception as e:
            print(f"✗ 失败: {e}")
            if attempt < max_retries:
                wait_time = attempt * 2
                print(f"等待 {wait_time} 秒后重试...")
                await asyncio.sleep(wait_time)
    
    print("\n所有重试都失败了")
    return False


def print_network_suggestions():
    """打印网络问题的建议"""
    print("\n" + "=" * 80)
    print("网络问题排查建议")
    print("=" * 80)
    print("""
1. 检查网络连接
   - 确保可以访问 Google 服务
   - 尝试访问 https://generativelanguage.googleapis.com

2. 使用代理（如果在中国大陆）
   - 设置环境变量：
     set HTTP_PROXY=http://your-proxy:port
     set HTTPS_PROXY=http://your-proxy:port
   
   - 或在代码中配置代理

3. 减少请求大小
   - 将长文本分段处理
   - 使用流式输出
   - 压缩转写内容

4. 检查 API Key
   - 确认 API Key 有效
   - 检查配额限制

5. 尝试其他模型
   - gemini-2.0-flash-exp (更快，更稳定)
   - gemini-1.5-flash (备用)
""")


if __name__ == "__main__":
    print("开始测试 Gemini API 连接...\n")
    
    # 运行测试
    success = asyncio.run(test_simple_request())
    
    if not success:
        # 如果失败，尝试带重试的测试
        print("\n简单测试失败，尝试带重试机制...")
        success = asyncio.run(test_with_retry())
    
    if not success:
        print_network_suggestions()
        sys.exit(1)
    
    print("\n✓ 测试完成")

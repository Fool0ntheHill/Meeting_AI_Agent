# -*- coding: utf-8 -*-
"""
测试错误分类系统

验证各种异常能否正确映射到错误码
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.utils.error_handler import classify_exception
from src.core.error_codes import ErrorCode


def test_error_classification():
    """测试错误分类"""
    
    print("=" * 80)
    print("测试错误分类系统")
    print("=" * 80)
    
    # 测试用例
    test_cases = [
        # (异常, 上下文, 预期错误码)
        (TimeoutError("Connection timed out"), "ASR", ErrorCode.NETWORK_TIMEOUT),
        (Exception("SSL: UNEXPECTED_EOF_WHILE_READING"), "LLM", ErrorCode.NETWORK_TIMEOUT),
        (Exception("Authentication failed: Invalid API key"), "ASR", ErrorCode.ASR_AUTH_ERROR),
        (Exception("Authentication failed: Invalid API key"), "LLM", ErrorCode.LLM_AUTH_ERROR),
        (Exception("Rate limit exceeded"), "LLM", ErrorCode.RATE_LIMITED),
        (FileNotFoundError("Audio file not found"), "ASR", ErrorCode.INPUT_MISSING_FILE),
        (Exception("Unsupported audio format"), "ASR", ErrorCode.INPUT_UNSUPPORTED_FORMAT),
        (Exception("Content blocked by safety filter"), "LLM", ErrorCode.LLM_CONTENT_BLOCKED),
        (Exception("SQLite database is locked"), "Pipeline", ErrorCode.DB_ERROR),
        (Exception("Unknown error"), "Pipeline", ErrorCode.INTERNAL_ERROR),
    ]
    
    passed = 0
    failed = 0
    
    for i, (exception, context, expected_code) in enumerate(test_cases, 1):
        print(f"\n测试 {i}: {type(exception).__name__}: {str(exception)[:50]}")
        print(f"  上下文: {context}")
        print(f"  预期错误码: {expected_code.value}")
        
        try:
            task_error = classify_exception(exception, context=context)
            
            print(f"  实际错误码: {task_error.error_code.value}")
            print(f"  错误消息: {task_error.error_message}")
            print(f"  可重试: {task_error.retryable}")
            
            if task_error.error_code == expected_code:
                print("  ✓ 通过")
                passed += 1
            else:
                print(f"  ✗ 失败: 预期 {expected_code.value}, 实际 {task_error.error_code.value}")
                failed += 1
        
        except Exception as e:
            print(f"  ✗ 异常: {e}")
            failed += 1
    
    print("\n" + "=" * 80)
    print(f"测试结果: {passed} 通过, {failed} 失败")
    print("=" * 80)
    
    if failed == 0:
        print("\n✓ 所有测试通过！")
    else:
        print(f"\n✗ {failed} 个测试失败")
    
    return failed == 0


if __name__ == "__main__":
    success = test_error_classification()
    sys.exit(0 if success else 1)

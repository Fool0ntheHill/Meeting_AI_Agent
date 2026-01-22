"""检查 Worker 状态和代码版本"""
import subprocess
import sys

print("=" * 80)
print("检查 Worker 状态")
print("=" * 80)

# 1. 检查 Worker 进程是否在运行
print("\n1. 检查 Worker 进程...")
try:
    result = subprocess.run(
        ["powershell", "-Command", "Get-Process | Where-Object {$_.CommandLine -like '*worker.py*'} | Select-Object Id, ProcessName, StartTime"],
        capture_output=True,
        text=True,
        timeout=5
    )
    if result.stdout.strip():
        print("✓ Worker 进程正在运行:")
        print(result.stdout)
    else:
        print("✗ 未找到 Worker 进程")
        print("\n请运行: python worker.py")
except Exception as e:
    print(f"✗ 检查失败: {e}")

# 2. 检查 pipeline.py 中的 _update_task_status 方法
print("\n2. 检查 pipeline.py 代码版本...")
try:
    with open("src/services/pipeline.py", "r", encoding="utf-8") as f:
        content = f.read()
        
    # 检查是否是 async def
    if "async def _update_task_status" in content:
        print("✗ 代码版本：旧版本（async def）")
        print("  问题：_update_task_status 是 async def，但调用的是同步方法")
        print("  需要修复：将 'async def _update_task_status' 改为 'def _update_task_status'")
    elif "def _update_task_status" in content:
        print("✓ 代码版本：新版本（def）")
        
        # 检查是否还有 await 调用
        if "await self._update_task_status" in content:
            print("✗ 警告：代码中仍有 'await self._update_task_status' 调用")
            print("  需要移除所有 await 关键字")
        else:
            print("✓ 所有 await 关键字已移除")
    else:
        print("✗ 未找到 _update_task_status 方法")
        
except Exception as e:
    print(f"✗ 检查失败: {e}")

# 3. 检查 repositories.py 中的缓存清除
print("\n3. 检查 repositories.py 缓存清除...")
try:
    with open("src/database/repositories.py", "r", encoding="utf-8") as f:
        content = f.read()
        
    if "_clear_task_cache" in content:
        print("✓ 缓存清除方法已添加")
        
        if "self._clear_task_cache(task_id)" in content:
            print("✓ update_state 方法中已调用缓存清除")
        else:
            print("✗ update_state 方法中未调用缓存清除")
    else:
        print("✗ 缓存清除方法未添加")
        
except Exception as e:
    print(f"✗ 检查失败: {e}")

print("\n" + "=" * 80)
print("建议:")
print("=" * 80)
print("1. 如果 Worker 正在运行且使用旧代码，请重启 Worker:")
print("   - 按 Ctrl+C 停止当前 Worker")
print("   - 运行: python worker.py")
print("\n2. 如果代码仍是旧版本，请确认修复已保存")
print("\n3. 创建新任务测试，观察完整的进度更新流程")

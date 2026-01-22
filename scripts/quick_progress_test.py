"""
快速测试进度 - 3 步判断前端还是后端问题

使用方法:
    python scripts/quick_progress_test.py <task_id>
"""

import sys
import os
import requests
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scripts.auth_helper import get_jwt_token


def quick_test(task_id: str):
    token = get_jwt_token()
    
    print("=" * 60)
    print("快速进度测试")
    print("=" * 60)
    
    # 步骤 1: 测试 API
    print("\n[步骤 1] 测试 API 响应...")
    try:
        response = requests.get(
            f"http://localhost:8000/api/v1/tasks/{task_id}/status",
            headers={
                "Authorization": f"Bearer {token}",
                "Cache-Control": "no-cache",
            },
            timeout=5,
        )
        
        if response.status_code != 200:
            print(f"✗ API 错误: HTTP {response.status_code}")
            print("→ 后端问题：API 无法访问")
            return
        
        api_data = response.json()
        print(f"✓ API 正常")
        print(f"  state: {api_data.get('state')}")
        print(f"  progress: {api_data.get('progress')}%")
        print(f"  estimated_time: {api_data.get('estimated_time')}s")
        
    except Exception as e:
        print(f"✗ API 请求失败: {e}")
        print("→ 后端问题：服务不可用")
        return
    
    # 步骤 2: 检查数据库
    print("\n[步骤 2] 检查数据库...")
    try:
        from src.database.session import session_scope
        from src.database.repositories import TaskRepository
        
        with session_scope() as db:
            repo = TaskRepository(db)
            task = repo.get_by_id(task_id)
            
            if not task:
                print(f"✗ 任务不存在")
                print("→ 后端问题：任务未创建或已删除")
                return
            
            # 获取音频时长（从转写记录）
            audio_duration = None
            try:
                from src.database.repositories import TranscriptRepository
                transcript_repo = TranscriptRepository(db)
                transcript_record = transcript_repo.get_by_task_id(task_id)
                if transcript_record:
                    audio_duration = transcript_record.duration
            except Exception:
                pass
            
            print(f"✓ 数据库正常")
            print(f"  state: {task.state}")
            print(f"  progress: {task.progress}%")
            print(f"  estimated_time: {task.estimated_time}s")
            if audio_duration:
                print(f"  audio_duration: {audio_duration}s")
            
            # 对比
            if (api_data.get('state') != task.state or 
                api_data.get('progress') != task.progress):
                print("\n✗ API 和数据库不一致")
                print("→ 后端问题：缓存问题（等待 60 秒或清除缓存）")
                return
            
    except Exception as e:
        print(f"✗ 数据库查询失败: {e}")
        print("→ 后端问题：数据库连接失败")
        return
    
    # 步骤 3: 验证逻辑
    print("\n[步骤 3] 验证进度逻辑...")
    
    state = api_data.get('state')
    progress = api_data.get('progress')
    estimated_time = api_data.get('estimated_time')
    
    issues = []
    
    # 检查 progress 存在
    if progress is None:
        issues.append(f"progress 字段缺失 (state={state})")
    
    # 检查完成状态
    if state in ['success', 'partial_success']:
        if progress != 100:
            issues.append(f"任务完成但 progress={progress}% (应该是 100%)")
        if estimated_time != 0:
            issues.append(f"任务完成但 estimated_time={estimated_time}s (应该是 0)")
    
    if issues:
        print("✗ 发现逻辑问题:")
        for issue in issues:
            print(f"  - {issue}")
        print("→ 后端问题：进度更新逻辑错误")
        return
    
    print("✓ 逻辑正常")
    
    # 结论
    print("\n" + "=" * 60)
    print("✓ 后端完全正常！")
    print("=" * 60)
    print("\n如果前端仍显示不正确，是前端问题。")
    print("\n前端检查:")
    print("  1. 打开浏览器 DevTools → Network 面板")
    print("  2. 筛选 'status' 请求")
    print("  3. 查看响应数据是否和上面一致")
    print("  4. 检查前端代码:")
    print("     - 是否正确解析 progress 字段")
    print("     - 状态映射是否正确（summarizing → 70%，不是 90%）")
    print("     - 是否有单调递增逻辑导致进度卡住")
    print("\n添加调试日志:")
    print("""
    fetch('/api/v1/tasks/{task_id}/status')
      .then(res => res.json())
      .then(data => {
        console.log('收到数据:', data);
        console.log('progress:', data.progress);
        console.log('state:', data.state);
      });
    """)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("使用方法: python scripts/quick_progress_test.py <task_id>")
        sys.exit(1)
    
    quick_test(sys.argv[1])

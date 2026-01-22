"""
诊断进度同步问题 - 判断是前端还是后端问题

使用方法:
    python scripts/diagnose_progress_sync.py <task_id>
"""

import sys
import os
import time
import json
import requests
from datetime import datetime
from typing import Optional, Dict, Any

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.auth_helper import get_jwt_token


class ProgressDiagnostics:
    def __init__(self, task_id: str):
        self.task_id = task_id
        self.token = get_jwt_token()
        self.base_url = "http://localhost:8000"
        
    def print_section(self, title: str):
        """打印分隔线"""
        print("\n" + "=" * 80)
        print(f"  {title}")
        print("=" * 80)
    
    def check_api_response(self) -> Optional[Dict[str, Any]]:
        """检查 API 响应"""
        self.print_section("1. 检查 API 响应")
        
        try:
            response = requests.get(
                f"{self.base_url}/api/v1/tasks/{self.task_id}/status",
                headers={
                    "Authorization": f"Bearer {self.token}",
                    "Cache-Control": "no-cache",
                },
                timeout=5,
            )
            
            print(f"✓ HTTP Status: {response.status_code}")
            
            if response.status_code != 200:
                print(f"✗ 错误: {response.text}")
                return None
            
            # 检查响应头
            print("\n响应头:")
            important_headers = ['cache-control', 'content-type', 'x-cache', 'age']
            for header in important_headers:
                value = response.headers.get(header, 'N/A')
                print(f"  {header}: {value}")
            
            # 解析响应体
            data = response.json()
            print("\n响应体:")
            print(json.dumps(data, indent=2, ensure_ascii=False))
            
            return data
            
        except requests.exceptions.RequestException as e:
            print(f"✗ 请求失败: {e}")
            return None
    
    def check_database(self) -> Optional[Dict[str, Any]]:
        """检查数据库实际值"""
        self.print_section("2. 检查数据库实际值")
        
        try:
            from src.database.session import session_scope
            from src.database.repositories import TaskRepository
            
            with session_scope() as db:
                repo = TaskRepository(db)
                task = repo.get_by_id(self.task_id)
                
                if not task:
                    print(f"✗ 任务不存在: {self.task_id}")
                    return None
                
                db_data = {
                    "task_id": task.task_id,
                    "state": task.state,
                    "progress": task.progress,
                    "estimated_time": task.estimated_time,
                    "error_details": task.error_details,
                    "updated_at": task.updated_at.isoformat() if task.updated_at else None,
                    "created_at": task.created_at.isoformat() if task.created_at else None,
                }
                
                # 尝试获取音频时长（从转写记录）
                try:
                    from src.database.repositories import TranscriptRepository
                    transcript_repo = TranscriptRepository(db)
                    transcript_record = transcript_repo.get_by_task_id(task_id)
                    if transcript_record:
                        db_data["audio_duration"] = transcript_record.duration
                    else:
                        db_data["audio_duration"] = None
                except Exception:
                    db_data["audio_duration"] = None
                
                print("数据库记录:")
                print(json.dumps(db_data, indent=2, ensure_ascii=False))
                
                return db_data
                
        except Exception as e:
            print(f"✗ 数据库查询失败: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def compare_data(self, api_data: Dict, db_data: Dict):
        """对比 API 和数据库数据"""
        self.print_section("3. 对比 API vs 数据库")
        
        fields = ['state', 'progress', 'estimated_time', 'error_details']
        all_match = True
        
        for field in fields:
            api_value = api_data.get(field)
            db_value = db_data.get(field)
            
            match = api_value == db_value
            symbol = "✓" if match else "✗"
            
            print(f"{symbol} {field}:")
            print(f"    API:  {api_value}")
            print(f"    DB:   {db_value}")
            
            if not match:
                all_match = False
                print(f"    ⚠️  不一致！")
        
        if all_match:
            print("\n✓ API 和数据库数据一致")
        else:
            print("\n✗ API 和数据库数据不一致 - 可能是缓存问题")
        
        return all_match
    
    def validate_progress_logic(self, data: Dict):
        """验证进度逻辑"""
        self.print_section("4. 验证进度逻辑")
        
        state = data.get('state')
        progress = data.get('progress')
        estimated_time = data.get('estimated_time')
        audio_duration = data.get('audio_duration')
        
        issues = []
        
        # 检查 1: progress 字段存在性
        if progress is None:
            issues.append(f"⚠️  progress 字段缺失 (state={state})")
        else:
            print(f"✓ progress 字段存在: {progress}%")
        
        # 检查 2: progress 范围
        if progress is not None and not (0 <= progress <= 100):
            issues.append(f"✗ progress 超出范围: {progress}% (应该在 0-100)")
        
        # 检查 3: state 和 progress 的对应关系
        expected_progress = {
            'pending': 0,
            'running': 0,
            'transcribing': (0, 40),  # 范围
            'identifying': (40, 60),
            'correcting': (60, 70),
            'summarizing': 70,
            'success': 100,
            'partial_success': 100,
            'failed': None,  # 失败时进度可能是任意值
        }
        
        if state in expected_progress:
            expected = expected_progress[state]
            if isinstance(expected, tuple):
                min_p, max_p = expected
                if progress is not None and not (min_p <= progress <= max_p):
                    issues.append(
                        f"⚠️  state={state} 时 progress={progress}% 不在预期范围 [{min_p}, {max_p}]"
                    )
                else:
                    print(f"✓ state={state}, progress={progress}% 在预期范围内")
            elif expected is not None:
                if progress != expected:
                    issues.append(
                        f"⚠️  state={state} 时 progress={progress}% 不等于预期值 {expected}%"
                    )
                else:
                    print(f"✓ state={state}, progress={progress}% 符合预期")
        
        # 检查 4: estimated_time 逻辑
        if state in ['success', 'partial_success']:
            if estimated_time != 0:
                issues.append(
                    f"✗ 任务已完成但 estimated_time={estimated_time} (应该是 0)"
                )
            else:
                print(f"✓ 任务完成，estimated_time=0")
        elif progress == 100:
            if estimated_time != 0:
                issues.append(
                    f"✗ progress=100% 但 estimated_time={estimated_time} (应该是 0)"
                )
        
        # 检查 5: estimated_time 计算
        if audio_duration and progress is not None and 0 < progress < 100:
            expected_time = int(audio_duration * 0.25 * (1 - progress / 100.0))
            if estimated_time != expected_time:
                issues.append(
                    f"⚠️  estimated_time={estimated_time}s 不等于计算值 {expected_time}s "
                    f"(audio_duration={audio_duration}s, progress={progress}%)"
                )
            else:
                print(f"✓ estimated_time={estimated_time}s 计算正确")
        
        # 打印问题
        if issues:
            print("\n发现的问题:")
            for issue in issues:
                print(f"  {issue}")
        else:
            print("\n✓ 所有逻辑检查通过")
        
        return len(issues) == 0
    
    def test_cache_behavior(self):
        """测试缓存行为"""
        self.print_section("5. 测试缓存行为")
        
        print("连续请求 3 次，观察缓存...")
        
        for i in range(3):
            print(f"\n请求 #{i+1}:")
            start = time.time()
            
            response = requests.get(
                f"{self.base_url}/api/v1/tasks/{self.task_id}/status",
                headers={
                    "Authorization": f"Bearer {self.token}",
                    "Cache-Control": "no-cache",
                },
            )
            
            latency = (time.time() - start) * 1000
            data = response.json()
            
            print(f"  延迟: {latency:.1f}ms")
            print(f"  progress: {data.get('progress')}%")
            print(f"  updated_at: {data.get('updated_at')}")
            
            if i < 2:
                time.sleep(1)
        
        print("\n提示:")
        print("  - 如果 3 次请求的 updated_at 相同，说明命中了缓存")
        print("  - 如果延迟都很低 (<10ms)，说明从 Redis 缓存返回")
        print("  - 如果延迟较高 (>50ms)，说明查询了数据库")
    
    def check_worker_status(self):
        """检查 Worker 状态"""
        self.print_section("6. 检查 Worker 状态")
        
        try:
            import redis
            r = redis.from_url("redis://localhost:6379/0", decode_responses=True)
            
            # 检查队列
            queue_length = r.llen("meeting_agent:queue")
            print(f"队列长度: {queue_length}")
            
            # 检查任务是否在队列中
            queue_items = r.lrange("meeting_agent:queue", 0, -1)
            task_in_queue = any(self.task_id in item for item in queue_items)
            
            if task_in_queue:
                print(f"⚠️  任务 {self.task_id} 仍在队列中，尚未被 Worker 处理")
            else:
                print(f"✓ 任务不在队列中（已被 Worker 处理或已完成）")
            
        except Exception as e:
            print(f"⚠️  无法连接 Redis: {e}")
    
    def generate_diagnosis(self, api_data: Dict, db_data: Dict, data_match: bool, logic_valid: bool):
        """生成诊断结论"""
        self.print_section("诊断结论")
        
        if not api_data:
            print("✗ 后端问题: API 无法访问或返回错误")
            print("\n建议:")
            print("  1. 检查后端服务是否运行")
            print("  2. 检查任务 ID 是否正确")
            print("  3. 检查用户权限")
            return
        
        if not db_data:
            print("✗ 后端问题: 数据库中没有该任务")
            print("\n建议:")
            print("  1. 确认任务 ID 正确")
            print("  2. 检查任务是否已被删除")
            return
        
        if not data_match:
            print("✗ 后端问题: API 返回的数据与数据库不一致")
            print("\n可能原因:")
            print("  1. Redis 缓存了旧数据（TTL 60秒）")
            print("  2. 数据库更新后缓存未失效")
            print("\n建议:")
            print("  1. 等待 60 秒让缓存自然过期")
            print("  2. 或手动清除 Redis 缓存:")
            print(f"     redis-cli DEL task_status:{self.task_id}")
            return
        
        if not logic_valid:
            print("✗ 后端问题: 进度逻辑不正确")
            print("\n可能原因:")
            print("  1. Pipeline 更新进度的代码有 bug")
            print("  2. Worker 没有正确更新数据库")
            print("  3. estimated_time 计算错误")
            print("\n建议:")
            print("  1. 检查 Worker 日志")
            print("  2. 检查 src/services/pipeline.py 的 _update_task_status 方法")
            print("  3. 确认 Worker 已重启（加载最新代码）")
            return
        
        # 如果后端都正常
        print("✓ 后端数据正常")
        print("\n如果前端仍显示不正确，可能是前端问题:")
        print("\n前端检查清单:")
        print("  1. 确认轮询正在运行（每 2 秒）")
        print("  2. 检查浏览器 Network 面板:")
        print("     - 请求是否发送成功")
        print("     - 响应数据是否正确")
        print("     - 是否有浏览器缓存（应该看到 Cache-Control: no-cache）")
        print("  3. 检查前端状态映射:")
        print("     - running → 0%")
        print("     - transcribing → 40%")
        print("     - identifying → 60%")
        print("     - correcting → 70%")
        print("     - summarizing → 70% (不是 90%!)")
        print("     - success → 100%")
        print("  4. 检查前端是否保持单调递增")
        print("  5. 添加 console.log 查看实际收到的数据")
        print("\n前端调试代码:")
        print("""
  fetch('/api/v1/tasks/{task_id}/status', {
    headers: {
      'Authorization': 'Bearer ' + token,
      'Cache-Control': 'no-cache',
    }
  })
  .then(res => res.json())
  .then(data => {
    console.log('[Progress Debug]', {
      state: data.state,
      progress: data.progress,
      estimated_time: data.estimated_time,
      updated_at: data.updated_at,
    });
  });
        """)
    
    def run(self):
        """运行完整诊断"""
        print("=" * 80)
        print(f"  进度同步诊断工具")
        print(f"  任务 ID: {self.task_id}")
        print(f"  时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 80)
        
        # 1. 检查 API
        api_data = self.check_api_response()
        if not api_data:
            print("\n✗ 无法继续诊断（API 请求失败）")
            return
        
        # 2. 检查数据库
        db_data = self.check_database()
        if not db_data:
            print("\n✗ 无法继续诊断（数据库查询失败）")
            return
        
        # 3. 对比数据
        data_match = self.compare_data(api_data, db_data)
        
        # 4. 验证逻辑
        logic_valid = self.validate_progress_logic(db_data)
        
        # 5. 测试缓存
        self.test_cache_behavior()
        
        # 6. 检查 Worker
        self.check_worker_status()
        
        # 7. 生成诊断
        self.generate_diagnosis(api_data, db_data, data_match, logic_valid)


def main():
    if len(sys.argv) < 2:
        print("使用方法: python scripts/diagnose_progress_sync.py <task_id>")
        print("\n示例:")
        print("  python scripts/diagnose_progress_sync.py task_abc123")
        sys.exit(1)
    
    task_id = sys.argv[1]
    
    diagnostics = ProgressDiagnostics(task_id)
    diagnostics.run()


if __name__ == "__main__":
    main()

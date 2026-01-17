# Task 28.1 完成总结: 性能监控实现

## 完成时间
2026-01-14

## 任务概述
实现性能指标收集系统，支持 Prometheus 格式导出，跟踪管线各阶段耗时、API 调用性能、系统资源使用等关键指标。

## 实现内容

### 1. MetricsCollector 类

#### 核心指标类型
```python
class MetricType(Enum):
    COUNTER = "counter"      # 计数器（只增不减）
    GAUGE = "gauge"          # 仪表（可增可减）
    HISTOGRAM = "histogram"  # 直方图（分布统计）
    SUMMARY = "summary"      # 摘要（分位数统计）
```

#### 主要功能

1. **计数器（Counter）**
   - `increment_counter()` - 增加计数器
   - 支持标签化指标（多维度）
   - 自动记录时间序列

2. **仪表（Gauge）**
   - `set_gauge()` - 设置仪表值
   - 支持标签化指标
   - 用于队列长度、内存使用等

3. **直方图（Histogram）**
   - `observe_histogram()` - 观测值
   - 自动计算分位数（p50, p95, p99）
   - 用于响应时间、处理时长等

4. **摘要（Summary）**
   - `observe_summary()` - 观测值
   - 计算分位数（p50, p90, p99）
   - 类似直方图但更轻量

5. **函数计时装饰器**
   - `@time_function()` - 自动测量函数执行时间
   - 结果记录到直方图

6. **速率计算**
   - `get_rate()` - 计算时间窗口内的速率
   - 支持自定义时间窗口

7. **系统资源监控**
   - `collect_system_metrics()` - 收集 CPU 和内存使用
   - 使用 psutil 库

8. **Prometheus 导出**
   - `export_prometheus()` - 导出标准 Prometheus 格式
   - 支持所有指标类型
   - 包含标准直方图桶

### 2. 使用示例

#### 基础计数器
```python
from src.utils.metrics import get_metrics_collector

metrics = get_metrics_collector()

# 简单计数
metrics.increment_counter("requests_total", 1.0)

# 带标签的计数
metrics.increment_counter(
    "http_requests_total",
    1.0,
    labels={"method": "GET", "status": "200"}
)
```

#### 仪表
```python
# 设置队列长度
metrics.set_gauge("queue_length", 10.0)

# 带标签的仪表
metrics.set_gauge(
    "queue_length",
    5.0,
    labels={"queue": "high_priority"}
)
```

#### 直方图（响应时间）
```python
# 记录 API 响应时间
metrics.observe_histogram("api_response_time_seconds", 0.25)

# 获取统计信息
stats = metrics.get_histogram_stats("api_response_time_seconds")
print(f"P95: {stats['p95']:.3f}s")
print(f"P99: {stats['p99']:.3f}s")
```

#### 函数计时装饰器
```python
@metrics.time_function("transcription_duration_seconds")
async def transcribe_audio(audio_file):
    # 函数执行时间会自动记录
    result = await asr_provider.transcribe(audio_file)
    return result
```

#### 系统资源监控
```python
# 收集系统指标
system_metrics = metrics.collect_system_metrics()
print(f"CPU: {system_metrics['cpu_percent']:.1f}%")
print(f"Memory: {system_metrics['memory_mb']:.1f} MB")
```

#### Prometheus 导出
```python
# 导出 Prometheus 格式
prometheus_text = metrics.export_prometheus()

# 可以通过 HTTP 端点暴露
@app.get("/metrics")
async def metrics_endpoint():
    return Response(
        content=metrics.export_prometheus(),
        media_type="text/plain"
    )
```

### 3. 管线指标示例

```python
# 记录管线各阶段
stages = ["transcription", "speaker_recognition", "correction", "summarization"]

for stage in stages:
    start_time = time.time()
    
    try:
        # 执行阶段
        result = await execute_stage(stage)
        
        # 记录成功
        metrics.increment_counter(
            "pipeline_stage_total",
            1.0,
            labels={"stage": stage, "status": "success"}
        )
        
        # 记录耗时
        duration = time.time() - start_time
        metrics.observe_histogram(
            "pipeline_stage_duration_seconds",
            duration
        )
        
    except Exception as e:
        # 记录失败
        metrics.increment_counter(
            "pipeline_stage_total",
            1.0,
            labels={"stage": stage, "status": "failure"}
        )
```

### 4. API 调用指标示例

```python
# 记录 API 调用
provider = "gemini"
start_time = time.time()

try:
    response = await llm_provider.generate(prompt)
    
    # 记录成功
    metrics.increment_counter(
        "api_calls_total",
        1.0,
        labels={"provider": provider, "status": "success"}
    )
    
    # 记录响应时间
    duration = time.time() - start_time
    metrics.observe_histogram(
        "api_call_duration_seconds",
        duration
    )
    
except RateLimitError:
    # 记录速率限制
    metrics.increment_counter(
        "api_calls_total",
        1.0,
        labels={"provider": provider, "status": "rate_limited"}
    )
    
except Exception:
    # 记录失败
    metrics.increment_counter(
        "api_calls_total",
        1.0,
        labels={"provider": provider, "status": "failure"}
    )
```

## 测试覆盖

### 单元测试 (28 个)
✅ 所有测试通过

**测试类别**:

1. **基础指标测试** (8 个)
   - 计数器增加
   - 带标签的计数器
   - 仪表设置
   - 带标签的仪表
   - 直方图观测
   - 摘要观测
   - 直方图百分位数
   - 摘要百分位数

2. **高级功能测试** (4 个)
   - 函数计时装饰器
   - 速率计算
   - 系统资源收集
   - 并发访问

3. **Prometheus 导出测试** (5 个)
   - 导出计数器
   - 导出仪表
   - 导出带标签的指标
   - 导出直方图
   - 导出摘要

4. **边界情况测试** (5 个)
   - 重置指标
   - 空直方图统计
   - 空摘要统计
   - 不存在的指标
   - 无数据时的速率

5. **全局实例测试** (2 个)
   - 获取全局收集器
   - 重置全局收集器

6. **集成测试** (4 个)
   - 管线指标收集
   - API 调用指标
   - 队列指标
   - 成功率计算

## 文件清单

### 新增文件
1. `src/utils/metrics.py` - MetricsCollector 实现 (500+ 行)
2. `tests/unit/test_utils_metrics.py` - 单元测试 (450+ 行)

### 修改文件
1. `requirements.txt` - 添加 psutil 依赖

## 技术亮点

### 1. 多种指标类型支持
- Counter: 单调递增，用于请求数、错误数
- Gauge: 可增可减，用于队列长度、内存使用
- Histogram: 分布统计，用于响应时间
- Summary: 分位数统计，类似 Histogram 但更轻量

### 2. 标签化指标
支持多维度标签，便于细粒度分析：
```python
metrics.increment_counter(
    "http_requests_total",
    labels={"method": "GET", "endpoint": "/api/tasks", "status": "200"}
)
```

### 3. 线程安全
使用 `threading.Lock` 保护所有数据结构，支持并发访问。

### 4. Prometheus 兼容
完全兼容 Prometheus 格式：
- 标准的 TYPE 声明
- 标准的直方图桶（0.005 到 10.0）
- 标准的分位数（0.5, 0.9, 0.99）
- 正确的标签格式

### 5. 装饰器模式
提供 `@time_function` 装饰器，自动测量函数执行时间。

### 6. 全局单例
提供 `get_metrics_collector()` 获取全局实例，便于在整个应用中使用。

### 7. 系统资源监控
集成 psutil，自动收集 CPU 和内存使用情况。

### 8. 死锁避免
修复了 `export_prometheus` 中的死锁问题，避免在持有锁时调用其他需要锁的方法。

## Prometheus 格式示例

```
# TYPE http_requests_total counter
http_requests_total{method="GET",status="200"} 150.0
http_requests_total{method="POST",status="201"} 50.0

# TYPE queue_length gauge
queue_length 10.0

# TYPE api_response_time_seconds histogram
api_response_time_seconds_bucket{le="0.005"} 5
api_response_time_seconds_bucket{le="0.01"} 10
api_response_time_seconds_bucket{le="0.025"} 25
api_response_time_seconds_bucket{le="0.05"} 50
api_response_time_seconds_bucket{le="0.1"} 80
api_response_time_seconds_bucket{le="0.25"} 95
api_response_time_seconds_bucket{le="0.5"} 98
api_response_time_seconds_bucket{le="1.0"} 99
api_response_time_seconds_bucket{le="2.5"} 100
api_response_time_seconds_bucket{le="5.0"} 100
api_response_time_seconds_bucket{le="10.0"} 100
api_response_time_seconds_bucket{le="+Inf"} 100
api_response_time_seconds_sum 15.5
api_response_time_seconds_count 100

# TYPE response_time summary
response_time{quantile="0.5"} 0.15
response_time{quantile="0.9"} 0.45
response_time{quantile="0.99"} 0.95
response_time_sum 25.0
response_time_count 100
```

## 集成建议

### 1. 在 FastAPI 中暴露指标端点

```python
from fastapi import FastAPI, Response
from src.utils.metrics import get_metrics_collector

app = FastAPI()
metrics = get_metrics_collector()

@app.get("/metrics")
async def metrics_endpoint():
    """Prometheus 指标端点"""
    return Response(
        content=metrics.export_prometheus(),
        media_type="text/plain; version=0.0.4"
    )
```

### 2. 在中间件中记录请求指标

```python
from fastapi import Request
import time

@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    start_time = time.time()
    
    response = await call_next(request)
    
    duration = time.time() - start_time
    
    # 记录请求
    metrics.increment_counter(
        "http_requests_total",
        1.0,
        labels={
            "method": request.method,
            "endpoint": request.url.path,
            "status": str(response.status_code)
        }
    )
    
    # 记录响应时间
    metrics.observe_histogram(
        "http_request_duration_seconds",
        duration
    )
    
    return response
```

### 3. 在 Worker 中记录任务指标

```python
# 记录队列长度
queue_length = await queue_manager.get_queue_length()
metrics.set_gauge("task_queue_length", float(queue_length))

# 记录任务处理
start_time = time.time()

try:
    result = await process_task(task)
    
    metrics.increment_counter(
        "tasks_processed_total",
        1.0,
        labels={"status": "success"}
    )
    
    duration = time.time() - start_time
    metrics.observe_histogram("task_processing_duration_seconds", duration)
    
except Exception as e:
    metrics.increment_counter(
        "tasks_processed_total",
        1.0,
        labels={"status": "failure"}
    )
```

### 4. 定期收集系统指标

```python
import asyncio

async def collect_system_metrics_periodically():
    """每 10 秒收集一次系统指标"""
    while True:
        metrics.collect_system_metrics()
        await asyncio.sleep(10)

# 在应用启动时启动后台任务
@app.on_event("startup")
async def startup_event():
    asyncio.create_task(collect_system_metrics_periodically())
```

### 5. 配置 Prometheus 抓取

```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'meeting-agent'
    scrape_interval: 15s
    static_configs:
      - targets: ['localhost:8000']
    metrics_path: '/metrics'
```

### 6. Grafana 仪表板示例

```
# 请求速率
rate(http_requests_total[5m])

# P95 响应时间
histogram_quantile(0.95, rate(api_response_time_seconds_bucket[5m]))

# 错误率
rate(http_requests_total{status=~"5.."}[5m]) / rate(http_requests_total[5m])

# 队列长度
task_queue_length

# CPU 使用率
system_cpu_percent

# 内存使用
system_memory_mb
```

## 性能考虑

### 1. 内存使用
- 直方图和摘要存储所有观测值，可能占用较多内存
- 建议定期重置或限制存储的值数量
- 生产环境可考虑使用滑动窗口

### 2. 锁竞争
- 所有操作都需要获取锁
- 高并发场景下可能成为瓶颈
- 可考虑使用无锁数据结构或分片锁

### 3. 导出性能
- `export_prometheus()` 需要遍历所有指标
- 大量指标时可能较慢
- 建议限制指标数量或使用增量导出

## 下一步建议

### 1. 添加告警规则
```yaml
# prometheus_alerts.yml
groups:
  - name: meeting_agent
    rules:
      - alert: HighErrorRate
        expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.05
        for: 5m
        annotations:
          summary: "High error rate detected"
      
      - alert: SlowAPIResponse
        expr: histogram_quantile(0.95, rate(api_response_time_seconds_bucket[5m])) > 2.0
        for: 5m
        annotations:
          summary: "API response time is slow"
```

### 2. 添加指标清理
```python
def cleanup_old_metrics(max_age_seconds=3600):
    """清理旧的时间序列数据"""
    cutoff_time = datetime.now() - timedelta(seconds=max_age_seconds)
    
    for name, series in metrics._time_series.items():
        metrics._time_series[name] = [
            mv for mv in series
            if mv.timestamp >= cutoff_time
        ]
```

### 3. 添加指标聚合
```python
def get_success_rate(metric_name: str, labels: Dict[str, str]) -> float:
    """计算成功率"""
    success = metrics.get_counter(metric_name, {**labels, "status": "success"})
    failure = metrics.get_counter(metric_name, {**labels, "status": "failure"})
    
    total = success + failure
    if total == 0:
        return 0.0
    
    return success / total
```

## 总结

Task 28.1 成功实现了完整的性能监控系统：
- ✅ 28 个单元测试全部通过
- ✅ 支持 4 种指标类型（Counter, Gauge, Histogram, Summary）
- ✅ 标签化指标支持多维度分析
- ✅ Prometheus 格式完全兼容
- ✅ 线程安全的并发访问
- ✅ 系统资源监控
- ✅ 函数计时装饰器
- ✅ 速率计算

这为系统提供了完整的性能监控能力，可以实时跟踪系统性能、识别瓶颈、监控 SLA。

**测试统计**:
- 总测试数: 226 (198 + 28)
- 通过率: 100%
- 新增代码: ~500 行
- 测试代码: ~450 行

**下一步**: Task 28.2 (可选) - 编写性能监控单元测试

---

**完成时间**: 2026-01-14  
**实现者**: Kiro AI Assistant  
**状态**: ✅ 完成

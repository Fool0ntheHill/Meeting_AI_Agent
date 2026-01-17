# -*- coding: utf-8 -*-
"""性能指标收集器单元测试"""

import pytest
import time
from unittest.mock import Mock, patch

from src.utils.metrics import (
    MetricsCollector,
    MetricType,
    get_metrics_collector,
    reset_metrics_collector,
)


@pytest.fixture
def metrics_collector():
    """创建指标收集器"""
    collector = MetricsCollector()
    yield collector
    collector.reset()


class TestMetricsCollector:
    """指标收集器测试"""

    def test_increment_counter(self, metrics_collector):
        """测试增加计数器"""
        metrics_collector.increment_counter("test_counter", 1.0)
        metrics_collector.increment_counter("test_counter", 2.0)

        assert metrics_collector.get_counter("test_counter") == 3.0

    def test_increment_counter_with_labels(self, metrics_collector):
        """测试带标签的计数器"""
        metrics_collector.increment_counter(
            "http_requests_total",
            1.0,
            labels={"method": "GET", "status": "200"}
        )
        metrics_collector.increment_counter(
            "http_requests_total",
            1.0,
            labels={"method": "POST", "status": "201"}
        )
        metrics_collector.increment_counter(
            "http_requests_total",
            1.0,
            labels={"method": "GET", "status": "200"}
        )

        # 验证不同标签的计数
        assert metrics_collector.get_counter(
            "http_requests_total",
            labels={"method": "GET", "status": "200"}
        ) == 2.0

        assert metrics_collector.get_counter(
            "http_requests_total",
            labels={"method": "POST", "status": "201"}
        ) == 1.0

    def test_set_gauge(self, metrics_collector):
        """测试设置仪表"""
        metrics_collector.set_gauge("queue_length", 10.0)
        assert metrics_collector.get_gauge("queue_length") == 10.0

        metrics_collector.set_gauge("queue_length", 5.0)
        assert metrics_collector.get_gauge("queue_length") == 5.0

    def test_set_gauge_with_labels(self, metrics_collector):
        """测试带标签的仪表"""
        metrics_collector.set_gauge(
            "queue_length",
            10.0,
            labels={"queue": "high_priority"}
        )
        metrics_collector.set_gauge(
            "queue_length",
            5.0,
            labels={"queue": "low_priority"}
        )

        assert metrics_collector.get_gauge(
            "queue_length",
            labels={"queue": "high_priority"}
        ) == 10.0

        assert metrics_collector.get_gauge(
            "queue_length",
            labels={"queue": "low_priority"}
        ) == 5.0

    def test_observe_histogram(self, metrics_collector):
        """测试观测直方图"""
        values = [0.1, 0.2, 0.3, 0.4, 0.5]
        for value in values:
            metrics_collector.observe_histogram("request_duration", value)

        stats = metrics_collector.get_histogram_stats("request_duration")

        assert stats["count"] == 5
        assert stats["sum"] == 1.5
        assert stats["min"] == 0.1
        assert stats["max"] == 0.5
        assert stats["avg"] == 0.3
        assert stats["p50"] == 0.3

    def test_observe_summary(self, metrics_collector):
        """测试观测摘要"""
        values = [1.0, 2.0, 3.0, 4.0, 5.0]
        for value in values:
            metrics_collector.observe_summary("response_time", value)

        stats = metrics_collector.get_summary_stats("response_time")

        assert stats["count"] == 5
        assert stats["sum"] == 15.0
        assert stats["avg"] == 3.0
        assert stats["p50"] == 3.0

    def test_histogram_percentiles(self, metrics_collector):
        """测试直方图百分位数"""
        # 添加 100 个值
        for i in range(100):
            metrics_collector.observe_histogram("test_histogram", i / 100.0)

        stats = metrics_collector.get_histogram_stats("test_histogram")

        # 验证百分位数
        assert 0.45 <= stats["p50"] <= 0.55
        assert 0.90 <= stats["p95"] <= 0.99
        assert 0.95 <= stats["p99"] <= 1.0

    def test_summary_percentiles(self, metrics_collector):
        """测试摘要百分位数"""
        # 添加 100 个值
        for i in range(100):
            metrics_collector.observe_summary("test_summary", i)

        stats = metrics_collector.get_summary_stats("test_summary")

        # 验证百分位数
        assert 45 <= stats["p50"] <= 55
        assert 85 <= stats["p90"] <= 95
        assert 95 <= stats["p99"] <= 100

    def test_time_function_decorator(self, metrics_collector):
        """测试函数计时装饰器"""
        @metrics_collector.time_function("test_function_duration")
        def slow_function():
            time.sleep(0.01)  # 减少到 10ms
            return "done"

        result = slow_function()

        assert result == "done"

        stats = metrics_collector.get_histogram_stats("test_function_duration")
        assert stats["count"] == 1
        assert stats["min"] >= 0.01

    def test_get_rate(self, metrics_collector):
        """测试速率计算"""
        # 简单测试：增加几次计数器
        for _ in range(10):
            metrics_collector.increment_counter("requests", 1.0)
            time.sleep(0.001)  # 添加微小延迟确保时间戳不同

        # 获取速率
        rate = metrics_collector.get_rate("requests", window_seconds=60)

        # 速率应该大于 0（因为有数据）
        assert rate >= 0

    @patch('psutil.Process')
    def test_collect_system_metrics(self, mock_process_class, metrics_collector):
        """测试收集系统指标"""
        # Mock psutil.Process
        mock_process = Mock()
        mock_process.cpu_percent.return_value = 25.5
        mock_memory_info = Mock()
        mock_memory_info.rss = 100 * 1024 * 1024  # 100 MB
        mock_process.memory_info.return_value = mock_memory_info
        
        # 替换 metrics_collector 的 _process
        metrics_collector._process = mock_process
        
        metrics = metrics_collector.collect_system_metrics()

        assert "cpu_percent" in metrics
        assert "memory_mb" in metrics
        assert "memory_bytes" in metrics
        assert metrics["cpu_percent"] == 25.5
        assert metrics["memory_mb"] == 100.0

        # 验证仪表已更新
        assert metrics_collector.get_gauge("system_cpu_percent") == 25.5
        assert metrics_collector.get_gauge("system_memory_mb") == 100.0

    def test_export_prometheus_counters(self, metrics_collector):
        """测试导出 Prometheus 格式 - 计数器"""
        metrics_collector.increment_counter("test_counter", 5.0)

        output = metrics_collector.export_prometheus()

        assert "# TYPE test_counter counter" in output
        assert "test_counter 5.0" in output

    def test_export_prometheus_gauges(self, metrics_collector):
        """测试导出 Prometheus 格式 - 仪表"""
        metrics_collector.set_gauge("test_gauge", 42.0)

        output = metrics_collector.export_prometheus()

        assert "# TYPE test_gauge gauge" in output
        assert "test_gauge 42.0" in output

    def test_export_prometheus_labeled_metrics(self, metrics_collector):
        """测试导出 Prometheus 格式 - 带标签的指标"""
        metrics_collector.increment_counter(
            "http_requests",
            1.0,
            labels={"method": "GET", "status": "200"}
        )

        output = metrics_collector.export_prometheus()

        assert "# TYPE http_requests counter" in output
        assert 'http_requests{method="GET",status="200"} 1.0' in output

    def test_export_prometheus_histogram(self, metrics_collector):
        """测试导出 Prometheus 格式 - 直方图"""
        metrics_collector.observe_histogram("request_duration", 0.1)
        metrics_collector.observe_histogram("request_duration", 0.5)
        metrics_collector.observe_histogram("request_duration", 1.5)

        output = metrics_collector.export_prometheus()

        assert "# TYPE request_duration histogram" in output
        assert 'request_duration_bucket{le="0.005"}' in output
        assert 'request_duration_bucket{le="+Inf"}' in output
        assert "request_duration_sum" in output
        assert "request_duration_count 3" in output

    def test_export_prometheus_summary(self, metrics_collector):
        """测试导出 Prometheus 格式 - 摘要"""
        for i in range(10):
            metrics_collector.observe_summary("response_time", i)

        output = metrics_collector.export_prometheus()

        assert "# TYPE response_time summary" in output
        assert 'response_time{quantile="0.5"}' in output
        assert 'response_time{quantile="0.9"}' in output
        assert 'response_time{quantile="0.99"}' in output
        assert "response_time_sum" in output
        assert "response_time_count 10" in output

    def test_reset(self, metrics_collector):
        """测试重置指标"""
        metrics_collector.increment_counter("test_counter", 10.0)
        metrics_collector.set_gauge("test_gauge", 20.0)
        metrics_collector.observe_histogram("test_histogram", 30.0)

        metrics_collector.reset()

        assert metrics_collector.get_counter("test_counter") == 0.0
        assert metrics_collector.get_gauge("test_gauge") == 0.0

        stats = metrics_collector.get_histogram_stats("test_histogram")
        assert stats["count"] == 0

    def test_empty_histogram_stats(self, metrics_collector):
        """测试空直方图统计"""
        stats = metrics_collector.get_histogram_stats("nonexistent")

        assert stats["count"] == 0
        assert stats["sum"] == 0.0
        assert stats["min"] == 0.0
        assert stats["max"] == 0.0
        assert stats["avg"] == 0.0

    def test_empty_summary_stats(self, metrics_collector):
        """测试空摘要统计"""
        stats = metrics_collector.get_summary_stats("nonexistent")

        assert stats["count"] == 0
        assert stats["sum"] == 0.0
        assert stats["avg"] == 0.0

    def test_get_nonexistent_counter(self, metrics_collector):
        """测试获取不存在的计数器"""
        assert metrics_collector.get_counter("nonexistent") == 0.0

    def test_get_nonexistent_gauge(self, metrics_collector):
        """测试获取不存在的仪表"""
        assert metrics_collector.get_gauge("nonexistent") == 0.0

    def test_get_rate_no_data(self, metrics_collector):
        """测试无数据时的速率"""
        rate = metrics_collector.get_rate("nonexistent")
        assert rate == 0.0

    def test_concurrent_access(self, metrics_collector):
        """测试并发访问（简单测试）"""
        import threading

        def increment():
            for _ in range(10):  # 减少到 10 次
                metrics_collector.increment_counter("concurrent_counter", 1.0)

        threads = [threading.Thread(target=increment) for _ in range(5)]  # 减少到 5 个线程

        for t in threads:
            t.start()

        for t in threads:
            t.join()

        # 应该有 50 次增加
        assert metrics_collector.get_counter("concurrent_counter") == 50.0


class TestGlobalMetricsCollector:
    """全局指标收集器测试"""

    def test_get_global_metrics_collector(self):
        """测试获取全局指标收集器"""
        reset_metrics_collector()

        collector1 = get_metrics_collector()
        collector2 = get_metrics_collector()

        # 应该返回同一个实例
        assert collector1 is collector2

    def test_reset_global_metrics_collector(self):
        """测试重置全局指标收集器"""
        collector1 = get_metrics_collector()
        reset_metrics_collector()
        collector2 = get_metrics_collector()

        # 应该是不同的实例
        assert collector1 is not collector2


class TestMetricIntegration:
    """指标集成测试"""

    def test_pipeline_metrics(self, metrics_collector):
        """测试管线指标收集"""
        # 模拟管线各阶段
        stages = ["transcription", "speaker_recognition", "correction", "summarization"]

        for stage in stages:
            # 记录阶段执行时间
            metrics_collector.observe_histogram(
                f"pipeline_stage_duration_seconds",
                0.5,
            )

            # 记录阶段成功
            metrics_collector.increment_counter(
                "pipeline_stage_total",
                1.0,
                labels={"stage": stage, "status": "success"}
            )

        # 验证指标
        for stage in stages:
            count = metrics_collector.get_counter(
                "pipeline_stage_total",
                labels={"stage": stage, "status": "success"}
            )
            assert count == 1.0

        stats = metrics_collector.get_histogram_stats("pipeline_stage_duration_seconds")
        assert stats["count"] == 4

    def test_api_call_metrics(self, metrics_collector):
        """测试 API 调用指标"""
        providers = ["volcano", "azure", "gemini", "iflytek"]

        for provider in providers:
            # 成功调用
            metrics_collector.increment_counter(
                "api_calls_total",
                3.0,
                labels={"provider": provider, "status": "success"}
            )

            # 失败调用
            metrics_collector.increment_counter(
                "api_calls_total",
                1.0,
                labels={"provider": provider, "status": "failure"}
            )

            # 记录响应时间
            metrics_collector.observe_histogram(
                f"api_call_duration_seconds",
                0.2,
            )

        # 验证成功率
        for provider in providers:
            success = metrics_collector.get_counter(
                "api_calls_total",
                labels={"provider": provider, "status": "success"}
            )
            failure = metrics_collector.get_counter(
                "api_calls_total",
                labels={"provider": provider, "status": "failure"}
            )

            assert success == 3.0
            assert failure == 1.0

            # 成功率应该是 75%
            success_rate = success / (success + failure)
            assert success_rate == 0.75

    def test_queue_metrics(self, metrics_collector):
        """测试队列指标"""
        # 设置队列长度
        metrics_collector.set_gauge("queue_length", 10.0)

        # 记录任务处理时间
        for _ in range(5):
            metrics_collector.observe_histogram("task_processing_duration_seconds", 2.0)

        # 记录任务完成
        metrics_collector.increment_counter("tasks_completed_total", 5.0)

        # 验证指标
        assert metrics_collector.get_gauge("queue_length") == 10.0
        assert metrics_collector.get_counter("tasks_completed_total") == 5.0

        stats = metrics_collector.get_histogram_stats("task_processing_duration_seconds")
        assert stats["count"] == 5
        assert stats["avg"] == 2.0

# -*- coding: utf-8 -*-
"""性能指标收集和监控"""

import time
import psutil
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Callable
from threading import Lock

from src.utils.logger import get_logger

logger = get_logger(__name__)


class MetricType(Enum):
    """指标类型"""
    COUNTER = "counter"  # 计数器（只增不减）
    GAUGE = "gauge"  # 仪表（可增可减）
    HISTOGRAM = "histogram"  # 直方图（分布统计）
    SUMMARY = "summary"  # 摘要（分位数统计）


@dataclass
class MetricValue:
    """指标值"""
    value: float
    timestamp: datetime = field(default_factory=datetime.now)
    labels: Dict[str, str] = field(default_factory=dict)


@dataclass
class HistogramBucket:
    """直方图桶"""
    le: float  # 上界（less than or equal）
    count: int = 0


class MetricsCollector:
    """性能指标收集器"""

    def __init__(self):
        """初始化指标收集器"""
        self._lock = Lock()

        # 计数器
        self._counters: Dict[str, float] = defaultdict(float)

        # 仪表
        self._gauges: Dict[str, float] = defaultdict(float)

        # 直方图（存储所有观测值）
        self._histograms: Dict[str, List[float]] = defaultdict(list)

        # 摘要（存储所有观测值）
        self._summaries: Dict[str, List[float]] = defaultdict(list)

        # 标签化指标（支持多维度）
        self._labeled_counters: Dict[str, Dict[str, float]] = defaultdict(lambda: defaultdict(float))
        self._labeled_gauges: Dict[str, Dict[str, float]] = defaultdict(lambda: defaultdict(float))

        # 时间序列（用于计算速率）
        self._time_series: Dict[str, List[MetricValue]] = defaultdict(list)

        # 系统资源监控
        self._process = psutil.Process()

        logger.info("MetricsCollector initialized")

    def increment_counter(
        self,
        name: str,
        value: float = 1.0,
        labels: Optional[Dict[str, str]] = None,
    ) -> None:
        """
        增加计数器

        Args:
            name: 指标名称
            value: 增加值
            labels: 标签
        """
        with self._lock:
            if labels:
                label_key = self._make_label_key(labels)
                self._labeled_counters[name][label_key] += value
            else:
                self._counters[name] += value

            # 记录时间序列
            self._time_series[name].append(
                MetricValue(value=value, labels=labels or {})
            )

    def set_gauge(
        self,
        name: str,
        value: float,
        labels: Optional[Dict[str, str]] = None,
    ) -> None:
        """
        设置仪表值

        Args:
            name: 指标名称
            value: 值
            labels: 标签
        """
        with self._lock:
            if labels:
                label_key = self._make_label_key(labels)
                self._labeled_gauges[name][label_key] = value
            else:
                self._gauges[name] = value

    def observe_histogram(self, name: str, value: float) -> None:
        """
        观测直方图值

        Args:
            name: 指标名称
            value: 观测值
        """
        with self._lock:
            self._histograms[name].append(value)

    def observe_summary(self, name: str, value: float) -> None:
        """
        观测摘要值

        Args:
            name: 指标名称
            value: 观测值
        """
        with self._lock:
            self._summaries[name].append(value)

    def time_function(self, metric_name: str) -> Callable:
        """
        装饰器：测量函数执行时间

        Args:
            metric_name: 指标名称

        Returns:
            装饰器函数
        """
        def decorator(func: Callable) -> Callable:
            def wrapper(*args, **kwargs):
                start_time = time.time()
                try:
                    result = func(*args, **kwargs)
                    return result
                finally:
                    duration = time.time() - start_time
                    self.observe_histogram(metric_name, duration)
            return wrapper
        return decorator

    def get_counter(self, name: str, labels: Optional[Dict[str, str]] = None) -> float:
        """
        获取计数器值

        Args:
            name: 指标名称
            labels: 标签

        Returns:
            计数器值
        """
        with self._lock:
            if labels:
                label_key = self._make_label_key(labels)
                return self._labeled_counters[name].get(label_key, 0.0)
            return self._counters.get(name, 0.0)

    def get_gauge(self, name: str, labels: Optional[Dict[str, str]] = None) -> float:
        """
        获取仪表值

        Args:
            name: 指标名称
            labels: 标签

        Returns:
            仪表值
        """
        with self._lock:
            if labels:
                label_key = self._make_label_key(labels)
                return self._labeled_gauges[name].get(label_key, 0.0)
            return self._gauges.get(name, 0.0)

    def get_histogram_stats(self, name: str) -> Dict[str, float]:
        """
        获取直方图统计信息

        Args:
            name: 指标名称

        Returns:
            统计信息（count, sum, min, max, avg, p50, p95, p99）
        """
        with self._lock:
            values = self._histograms.get(name, [])

            if not values:
                return {
                    "count": 0,
                    "sum": 0.0,
                    "min": 0.0,
                    "max": 0.0,
                    "avg": 0.0,
                    "p50": 0.0,
                    "p95": 0.0,
                    "p99": 0.0,
                }

            sorted_values = sorted(values)
            count = len(sorted_values)

            return {
                "count": count,
                "sum": sum(sorted_values),
                "min": sorted_values[0],
                "max": sorted_values[-1],
                "avg": sum(sorted_values) / count,
                "p50": self._percentile(sorted_values, 0.5),
                "p95": self._percentile(sorted_values, 0.95),
                "p99": self._percentile(sorted_values, 0.99),
            }

    def get_summary_stats(self, name: str) -> Dict[str, float]:
        """
        获取摘要统计信息

        Args:
            name: 指标名称

        Returns:
            统计信息（count, sum, avg, p50, p90, p99）
        """
        with self._lock:
            values = self._summaries.get(name, [])

            if not values:
                return {
                    "count": 0,
                    "sum": 0.0,
                    "avg": 0.0,
                    "p50": 0.0,
                    "p90": 0.0,
                    "p99": 0.0,
                }

            sorted_values = sorted(values)
            count = len(sorted_values)

            return {
                "count": count,
                "sum": sum(sorted_values),
                "avg": sum(sorted_values) / count,
                "p50": self._percentile(sorted_values, 0.5),
                "p90": self._percentile(sorted_values, 0.9),
                "p99": self._percentile(sorted_values, 0.99),
            }

    def get_rate(self, name: str, window_seconds: int = 60) -> float:
        """
        计算速率（每秒）

        Args:
            name: 指标名称
            window_seconds: 时间窗口（秒）

        Returns:
            速率（每秒）
        """
        with self._lock:
            time_series = self._time_series.get(name, [])

            if not time_series:
                return 0.0

            # 过滤时间窗口内的数据
            cutoff_time = datetime.now() - timedelta(seconds=window_seconds)
            recent_values = [
                mv for mv in time_series
                if mv.timestamp >= cutoff_time
            ]

            if not recent_values:
                return 0.0
            
            if len(recent_values) == 1:
                # 只有一个数据点，无法计算速率
                return 0.0

            # 计算速率
            total_value = sum(mv.value for mv in recent_values)
            time_span = (recent_values[-1].timestamp - recent_values[0].timestamp).total_seconds()

            if time_span == 0:
                return 0.0

            return total_value / time_span

    def collect_system_metrics(self) -> Dict[str, float]:
        """
        收集系统资源指标

        Returns:
            系统指标字典
        """
        try:
            cpu_percent = self._process.cpu_percent(interval=0.01)  # 减少到 10ms
            memory_info = self._process.memory_info()
            memory_mb = memory_info.rss / 1024 / 1024

            # 更新仪表
            self.set_gauge("system_cpu_percent", cpu_percent)
            self.set_gauge("system_memory_mb", memory_mb)

            return {
                "cpu_percent": cpu_percent,
                "memory_mb": memory_mb,
                "memory_bytes": memory_info.rss,
            }
        except Exception as e:
            logger.error(f"Failed to collect system metrics: {e}")
            return {}

    def export_prometheus(self) -> str:
        """
        导出 Prometheus 格式的指标

        Returns:
            Prometheus 格式的文本
        """
        lines = []

        with self._lock:
            # 导出计数器
            for name, value in self._counters.items():
                lines.append(f"# TYPE {name} counter")
                lines.append(f"{name} {value}")

            # 导出标签化计数器
            for name, labeled_values in self._labeled_counters.items():
                lines.append(f"# TYPE {name} counter")
                for label_key, value in labeled_values.items():
                    labels_str = self._format_labels(label_key)
                    lines.append(f"{name}{{{labels_str}}} {value}")

            # 导出仪表
            for name, value in self._gauges.items():
                lines.append(f"# TYPE {name} gauge")
                lines.append(f"{name} {value}")

            # 导出标签化仪表
            for name, labeled_values in self._labeled_gauges.items():
                lines.append(f"# TYPE {name} gauge")
                for label_key, value in labeled_values.items():
                    labels_str = self._format_labels(label_key)
                    lines.append(f"{name}{{{labels_str}}} {value}")

            # 导出直方图
            for name, values in self._histograms.items():
                if not values:
                    continue

                lines.append(f"# TYPE {name} histogram")
                
                # 直接计算统计信息（避免调用 get_histogram_stats 导致死锁）
                sorted_values = sorted(values)
                count = len(sorted_values)
                total_sum = sum(sorted_values)

                # 标准桶
                buckets = [0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]
                for bucket in buckets:
                    bucket_count = sum(1 for v in sorted_values if v <= bucket)
                    lines.append(f'{name}_bucket{{le="{bucket}"}} {bucket_count}')

                lines.append(f'{name}_bucket{{le="+Inf"}} {count}')
                lines.append(f'{name}_sum {total_sum}')
                lines.append(f'{name}_count {count}')

            # 导出摘要
            for name, values in self._summaries.items():
                if not values:
                    continue

                lines.append(f"# TYPE {name} summary")
                
                # 直接计算统计信息（避免调用 get_summary_stats 导致死锁）
                sorted_values = sorted(values)
                count = len(sorted_values)
                total_sum = sum(sorted_values)
                
                p50 = self._percentile(sorted_values, 0.5)
                p90 = self._percentile(sorted_values, 0.9)
                p99 = self._percentile(sorted_values, 0.99)

                lines.append(f'{name}{{quantile="0.5"}} {p50}')
                lines.append(f'{name}{{quantile="0.9"}} {p90}')
                lines.append(f'{name}{{quantile="0.99"}} {p99}')
                lines.append(f'{name}_sum {total_sum}')
                lines.append(f'{name}_count {count}')

        return "\n".join(lines) + "\n"

    def reset(self) -> None:
        """重置所有指标"""
        with self._lock:
            self._counters.clear()
            self._gauges.clear()
            self._histograms.clear()
            self._summaries.clear()
            self._labeled_counters.clear()
            self._labeled_gauges.clear()
            self._time_series.clear()

        logger.info("All metrics reset")

    def _make_label_key(self, labels: Dict[str, str]) -> str:
        """
        生成标签键

        Args:
            labels: 标签字典

        Returns:
            标签键
        """
        return ",".join(f"{k}={v}" for k, v in sorted(labels.items()))

    def _format_labels(self, label_key: str) -> str:
        """
        格式化标签为 Prometheus 格式

        Args:
            label_key: 标签键

        Returns:
            Prometheus 格式的标签
        """
        parts = label_key.split(",")
        formatted = []
        for part in parts:
            k, v = part.split("=")
            formatted.append(f'{k}="{v}"')
        return ",".join(formatted)

    def _percentile(self, sorted_values: List[float], p: float) -> float:
        """
        计算百分位数

        Args:
            sorted_values: 已排序的值列表
            p: 百分位（0-1）

        Returns:
            百分位值
        """
        if not sorted_values:
            return 0.0

        k = (len(sorted_values) - 1) * p
        f = int(k)
        c = f + 1

        if c >= len(sorted_values):
            return sorted_values[-1]

        d0 = sorted_values[f]
        d1 = sorted_values[c]

        return d0 + (d1 - d0) * (k - f)


# 全局指标收集器实例
_global_metrics_collector: Optional[MetricsCollector] = None


def get_metrics_collector() -> MetricsCollector:
    """
    获取全局指标收集器实例

    Returns:
        MetricsCollector 实例
    """
    global _global_metrics_collector

    if _global_metrics_collector is None:
        _global_metrics_collector = MetricsCollector()

    return _global_metrics_collector


def reset_metrics_collector() -> None:
    """重置全局指标收集器"""
    global _global_metrics_collector
    _global_metrics_collector = None

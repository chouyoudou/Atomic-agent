"""
性能监控和指标收集
"""

import time
import asyncio
import psutil
import threading
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from collections import defaultdict, deque
from dataclasses import dataclass
import json


@dataclass
class Metric:
    """指标数据类"""
    name: str
    value: float
    timestamp: datetime
    tags: Dict[str, str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            'name': self.name,
            'value': self.value,
            'timestamp': self.timestamp.isoformat(),
            'tags': self.tags or {}
        }


class MetricsCollector:
    """指标收集器"""

    def __init__(self, max_history: int = 1000):
        self.max_history = max_history
        self.metrics: Dict[str, deque] = defaultdict(lambda: deque(maxlen=max_history))
        self.counters: Dict[str, int] = defaultdict(int)
        self.gauges: Dict[str, float] = defaultdict(float)
        self.timers: Dict[str, deque] = defaultdict(lambda: deque(maxlen=100))
        self._lock = threading.Lock()

    def increment(self, name: str, value: int = 1, tags: Dict[str, str] = None):
        """增加计数器"""
        with self._lock:
            self.counters[name] += value
            metric = Metric(name, self.counters[name], datetime.now(), tags)
            self.metrics[name].append(metric)

    def gauge(self, name: str, value: float, tags: Dict[str, str] = None):
        """设置仪表值"""
        with self._lock:
            self.gauges[name] = value
            metric = Metric(name, value, datetime.now(), tags)
            self.metrics[name].append(metric)

    def timer(self, name: str, duration: float, tags: Dict[str, str] = None):
        """记录时间"""
        with self._lock:
            self.timers[name].append(duration)
            metric = Metric(name, duration, datetime.now(), tags)
            self.metrics[name].append(metric)

    def histogram(self, name: str, value: float, tags: Dict[str, str] = None):
        """记录直方图值"""
        metric = Metric(name, value, datetime.now(), tags)
        with self._lock:
            self.metrics[name].append(metric)

    def get_metrics(self, name: Optional[str] = None) -> Dict[str, Any]:
        """获取指标数据"""
        with self._lock:
            if name:
                return {
                    'metrics': [m.to_dict() for m in self.metrics.get(name, [])],
                    'current_value': self.gauges.get(name) or self.counters.get(name, 0)
                }

            result = {}
            for metric_name, metric_list in self.metrics.items():
                result[metric_name] = {
                    'metrics': [m.to_dict() for m in metric_list],
                    'current_value': self.gauges.get(metric_name) or self.counters.get(metric_name, 0)
                }
            return result

    def get_summary(self) -> Dict[str, Any]:
        """获取指标摘要"""
        with self._lock:
            summary = {
                'timestamp': datetime.now().isoformat(),
                'counters': dict(self.counters),
                'gauges': dict(self.gauges),
                'timers': {}
            }

            # 计算时间指标统计
            for name, times in self.timers.items():
                if times:
                    times_list = list(times)
                    summary['timers'][name] = {
                        'count': len(times_list),
                        'min': min(times_list),
                        'max': max(times_list),
                        'avg': sum(times_list) / len(times_list),
                        'p95': sorted(times_list)[int(len(times_list) * 0.95)] if len(times_list) > 1 else times_list[0]
                    }

            return summary


class PerformanceMonitor:
    """性能监控器"""

    def __init__(self, collector: MetricsCollector):
        self.collector = collector
        self.running = False
        self._monitor_task = None

    async def start(self, interval: float = 10.0):
        """启动监控"""
        if self.running:
            return

        self.running = True
        self._monitor_task = asyncio.create_task(self._monitor_loop(interval))

    async def stop(self):
        """停止监控"""
        self.running = False
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass

    async def _monitor_loop(self, interval: float):
        """监控循环"""
        while self.running:
            try:
                await self._collect_system_metrics()
                await asyncio.sleep(interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"监控错误: {e}")
                await asyncio.sleep(interval)

    async def _collect_system_metrics(self):
        """收集系统指标"""
        # CPU使用率
        cpu_percent = psutil.cpu_percent(interval=1)
        self.collector.gauge('system.cpu.usage', cpu_percent, {'unit': 'percent'})

        # 内存使用率
        memory = psutil.virtual_memory()
        self.collector.gauge('system.memory.usage', memory.percent, {'unit': 'percent'})
        self.collector.gauge('system.memory.used', memory.used / 1024 / 1024, {'unit': 'MB'})
        self.collector.gauge('system.memory.available', memory.available / 1024 / 1024, {'unit': 'MB'})

        # 磁盘使用率
        disk = psutil.disk_usage('/')
        self.collector.gauge('system.disk.usage', (disk.used / disk.total) * 100, {'unit': 'percent'})
        self.collector.gauge('system.disk.free', disk.free / 1024 / 1024 / 1024, {'unit': 'GB'})

        # 网络IO
        network = psutil.net_io_counters()
        self.collector.gauge('system.network.bytes_sent', network.bytes_sent / 1024 / 1024, {'unit': 'MB'})
        self.collector.gauge('system.network.bytes_recv', network.bytes_recv / 1024 / 1024, {'unit': 'MB'})


class Timer:
    """计时器上下文管理器"""

    def __init__(self, collector: MetricsCollector, name: str, tags: Dict[str, str] = None):
        self.collector = collector
        self.name = name
        self.tags = tags
        self.start_time = None

    def __enter__(self):
        self.start_time = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.start_time:
            duration = time.time() - self.start_time
            self.collector.timer(self.name, duration, self.tags)


# 全局指标收集器
metrics_collector = MetricsCollector()
performance_monitor = PerformanceMonitor(metrics_collector)


def timer(name: str, tags: Dict[str, str] = None):
    """计时器装饰器"""
    def decorator(func):
        if asyncio.iscoroutinefunction(func):
            async def async_wrapper(*args, **kwargs):
                with Timer(metrics_collector, name, tags):
                    return await func(*args, **kwargs)
            return async_wrapper
        else:
            def sync_wrapper(*args, **kwargs):
                with Timer(metrics_collector, name, tags):
                    return func(*args, **kwargs)
            return sync_wrapper
    return decorator


def increment_counter(name: str, value: int = 1, tags: Dict[str, str] = None):
    """增加计数器的便捷函数"""
    metrics_collector.increment(name, value, tags)


def set_gauge(name: str, value: float, tags: Dict[str, str] = None):
    """设置仪表值的便捷函数"""
    metrics_collector.gauge(name, value, tags)


def record_histogram(name: str, value: float, tags: Dict[str, str] = None):
    """记录直方图值的便捷函数"""
    metrics_collector.histogram(name, value, tags)


# 应用特定指标
class ASEMetrics:
    """ASE特定指标"""

    @staticmethod
    def record_structure_created(structure_type: str, atoms_count: int):
        """记录结构创建"""
        increment_counter('ase.structure.created', tags={'type': structure_type})
        record_histogram('ase.structure.atoms_count', atoms_count, tags={'type': structure_type})

    @staticmethod
    def record_structure_modified(operation: str):
        """记录结构修改"""
        increment_counter('ase.structure.modified', tags={'operation': operation})

    @staticmethod
    def record_calculation(calculator: str, duration: float, success: bool):
        """记录计算"""
        increment_counter('ase.calculation.total', tags={'calculator': calculator})
        if success:
            increment_counter('ase.calculation.success', tags={'calculator': calculator})
            metrics_collector.timer('ase.calculation.duration', duration, {'calculator': calculator})
        else:
            increment_counter('ase.calculation.failed', tags={'calculator': calculator})

    @staticmethod
    def record_session_activity(action: str):
        """记录会话活动"""
        increment_counter('ase.session.activity', tags={'action': action})

    @staticmethod
    def record_websocket_connection(action: str):
        """记录WebSocket连接"""
        increment_counter('ase.websocket.connections', tags={'action': action})

    @staticmethod
    def set_active_sessions(count: int):
        """设置活跃会话数"""
        set_gauge('ase.sessions.active', count)

    @staticmethod
    def set_websocket_clients(count: int):
        """设置WebSocket客户端数"""
        set_gauge('ase.websocket.clients', count)


# 导出主要组件
__all__ = [
    'metrics_collector',
    'performance_monitor',
    'Timer',
    'timer',
    'increment_counter',
    'set_gauge',
    'record_histogram',
    'ASEMetrics'
]
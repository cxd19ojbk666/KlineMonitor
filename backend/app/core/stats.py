"""
统计收集器
用于收集和汇总同步和监控结果
"""
from typing import Dict, List
from dataclasses import dataclass, field
from datetime import datetime

from .timezone import now_beijing


@dataclass
class SyncResult:
    """单个同步结果"""
    symbol: str
    interval: str
    success: bool
    inserted: int = 0
    updated: int = 0
    error: str = ""


@dataclass
class SyncStats:
    """同步统计汇总"""
    start_time: datetime = field(default_factory=now_beijing)
    end_time: datetime = None
    success_count: int = 0
    failed_count: int = 0
    total_inserted: int = 0
    total_updated: int = 0
    failed_symbols: List[Dict[str, str]] = field(default_factory=list)
    interval_stats: Dict[str, Dict[str, int]] = field(default_factory=dict)
    
    def add_result(self, result: SyncResult):
        """添加同步结果"""
        if result.success:
            self.success_count += 1
            self.total_inserted += result.inserted
            self.total_updated += result.updated
            
            if result.interval not in self.interval_stats:
                self.interval_stats[result.interval] = {
                    "success": 0,
                    "failed": 0,
                    "inserted": 0,
                    "updated": 0
                }
            self.interval_stats[result.interval]["success"] += 1
            self.interval_stats[result.interval]["inserted"] += result.inserted
            self.interval_stats[result.interval]["updated"] += result.updated
        else:
            self.failed_count += 1
            self.failed_symbols.append({
                "symbol": result.symbol,
                "interval": result.interval,
                "error": result.error
            })
            
            if result.interval not in self.interval_stats:
                self.interval_stats[result.interval] = {
                    "success": 0,
                    "failed": 0,
                    "inserted": 0,
                    "updated": 0
                }
            self.interval_stats[result.interval]["failed"] += 1
    
    def finish(self):
        """标记统计完成"""
        self.end_time = now_beijing()
    
    def get_duration(self) -> float:
        """获取耗时（秒）"""
        if self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return (now_beijing() - self.start_time).total_seconds()
    
    def format_summary(self) -> str:
        """格式化汇总信息"""
        duration = self.get_duration()
        lines = [
            "=" * 60,
            "数据同步汇总",
            "=" * 60,
            f"总耗时: {duration:.2f}秒",
        ]
        
        if self.interval_stats:
            lines.append("-" * 60)
            lines.append("分周期统计:")
            interval_order = ["1m", "3m", "5m", "15m", "30m", "1h", "2h", "4h", "6h", "8h", "12h", "1d", "3d", "1w", "1M"]
            sorted_intervals = sorted(
                self.interval_stats.keys(),
                key=lambda x: interval_order.index(x) if x in interval_order else 999
            )
            for interval in sorted_intervals:
                stats = self.interval_stats[interval]
                lines.append(f"  [{interval}]")
                lines.append(f"    成功: {stats['success']}个交易对")
                lines.append(f"    失败: {stats['failed']}个交易对")
                lines.append(f"    新增K线: {stats['inserted']}条")
                lines.append(f"    更新K线: {stats['updated']}条")
        
        if self.failed_symbols:
            lines.append("-" * 60)
            lines.append("失败详情:")
            for item in self.failed_symbols:
                lines.append(f"  交易对: {item['symbol']} ({item['interval']})")
                lines.append(f"  原因: {item['error']}")
        
        lines.append("=" * 60)
        return "\n".join(lines)


class SyncStatsCollector:
    """同步统计收集器（单例）"""
    
    def __init__(self):
        self._current_stats: SyncStats = None
    
    def start_batch(self) -> SyncStats:
        """开始新的批次统计"""
        self._current_stats = SyncStats()
        return self._current_stats
    
    def add_result(self, result: SyncResult):
        """添加同步结果"""
        if self._current_stats:
            self._current_stats.add_result(result)
    
    def finish_batch(self) -> SyncStats:
        """完成当前批次并返回统计"""
        if self._current_stats:
            self._current_stats.finish()
        stats = self._current_stats
        self._current_stats = None
        return stats
    
    def get_current_stats(self) -> SyncStats:
        """获取当前统计"""
        return self._current_stats


@dataclass
class MonitorResult:
    """单个监控结果"""
    symbol: str
    volume_alert: bool = False
    rise_alert: bool = False
    open_price_alerts: Dict[str, bool] = field(default_factory=dict)
    error: str = ""


@dataclass
class MonitorStats:
    """监控统计汇总"""
    start_time: datetime = field(default_factory=now_beijing)
    end_time: datetime = None
    total_checked: int = 0
    volume_triggered: int = 0
    rise_triggered: int = 0
    open_price_triggered: Dict[str, int] = field(default_factory=dict)
    error_count: int = 0
    error_symbols: List[Dict[str, str]] = field(default_factory=list)
    triggered_symbols: List[str] = field(default_factory=list)
    
    def add_result(self, result: MonitorResult):
        """添加监控结果"""
        self.total_checked += 1
        
        if result.error:
            self.error_count += 1
            self.error_symbols.append({
                "symbol": result.symbol,
                "error": result.error
            })
            return
        
        has_alert = False
        
        if result.volume_alert:
            self.volume_triggered += 1
            has_alert = True
        
        if result.rise_alert:
            self.rise_triggered += 1
            has_alert = True
        
        for timeframe, triggered in result.open_price_alerts.items():
            if triggered:
                if timeframe not in self.open_price_triggered:
                    self.open_price_triggered[timeframe] = 0
                self.open_price_triggered[timeframe] += 1
                has_alert = True
        
        if has_alert:
            self.triggered_symbols.append(result.symbol)
    
    def finish(self):
        """标记统计完成"""
        self.end_time = now_beijing()
    
    def get_duration(self) -> float:
        """获取耗时（秒）"""
        if self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return (now_beijing() - self.start_time).total_seconds()
    
    def format_summary(self) -> str:
        """格式化汇总信息"""
        duration = self.get_duration()
        total_alerts = self.volume_triggered + self.rise_triggered + sum(self.open_price_triggered.values())
        
        lines = [
            "=" * 60,
            "监控检查汇总",
            "=" * 60,
            f"总耗时: {duration:.2f}秒",
            f"检查交易对: {self.total_checked}个",
            f"触发提醒: {total_alerts}次 ({len(self.triggered_symbols)}个交易对)",
            f"  - 成交量提醒: {self.volume_triggered}次",
            f"  - 涨幅提醒: {self.rise_triggered}次",
            f"  - 开盘价匹配提醒: {sum(self.open_price_triggered.values())}次",
        ]
        
        if self.open_price_triggered:
            for timeframe, count in sorted(self.open_price_triggered.items()):
                lines.append(f"    - {timeframe}: {count}次")
        
        if self.triggered_symbols:
            lines.append(f"触发交易对: {', '.join(self.triggered_symbols[:10])}")
            if len(self.triggered_symbols) > 10:
                lines.append(f"  ... 还有 {len(self.triggered_symbols) - 10} 个")
        
        if self.error_count > 0:
            lines.append("-" * 60)
            lines.append(f"异常: {self.error_count}个交易对")
            for item in self.error_symbols[:5]:
                lines.append(f"  交易对: {item['symbol']}")
                lines.append(f"  原因: {item['error']}")
            if len(self.error_symbols) > 5:
                lines.append(f"  ... 还有 {len(self.error_symbols) - 5} 个异常")
        
        lines.append("=" * 60)
        return "\n".join(lines)


class MonitorStatsCollector:
    """监控统计收集器（单例）"""
    
    def __init__(self):
        self._current_stats: MonitorStats = None
    
    def start_batch(self) -> MonitorStats:
        """开始新的批次统计"""
        self._current_stats = MonitorStats()
        return self._current_stats
    
    def add_result(self, result: MonitorResult):
        """添加监控结果"""
        if self._current_stats:
            self._current_stats.add_result(result)
    
    def finish_batch(self) -> MonitorStats:
        """完成当前批次并返回统计"""
        if self._current_stats:
            self._current_stats.finish()
        stats = self._current_stats
        self._current_stats = None
        return stats
    
    def get_current_stats(self) -> MonitorStats:
        """获取当前统计"""
        return self._current_stats


# 全局实例
sync_stats_collector = SyncStatsCollector()
monitor_stats_collector = MonitorStatsCollector()

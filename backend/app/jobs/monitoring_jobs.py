"""
监控调度任务
===========
包含K线同步、监控检查、数据清理等定时任务

任务：
- sync_klines_task: 统一K线数据同步任务（每分钟执行）
- cleanup_klines_task: 清理过期K线数据（每天执行）
- run_monitor_task: 主监控任务
"""
import asyncio
from datetime import datetime
from typing import List

from ..core.database import SessionLocal
from ..core.events import event_broadcaster
from ..core.scheduler import is_scheduler_running
from ..core.stats import sync_stats_collector, monitor_stats_collector
from ..core.logger import logger
from ..models.symbol import Symbol
from ..services.binance_client import binance_client
from ..services.monitor_service import monitor_service

# 并发控制常量
SYNC_CONCURRENCY = 600  # K线同步最大并发数
MONITOR_CONCURRENCY = 50  # 监控任务最大并发数


async def get_active_symbols() -> List[str]:
    """
    获取所有启用的监控币种
    
    Returns:
        启用的币种名称列表
    """
    db = SessionLocal()
    try:
        symbols = db.query(Symbol).filter(Symbol.is_active == True).all()
        return [s.symbol for s in symbols]
    finally:
        db.close()


def get_intervals_to_sync(trigger_time: datetime = None) -> List[str]:
    """
    智能获取需要同步的K线周期
    
    - 1m、15m：00分同步
    - 30m：+1分（01分、31分）
    - 1h：+2分（02分）
    - 4h：+3分（03分）
    - 1d：+4分（04分）
    - 3d：+5分（05分）
    
    Args:
        trigger_time: 触发时间，默认为当前时间
    
    Returns:
        需要同步的周期列表
    """
    if trigger_time is None:
        trigger_time = datetime.now()
    
    minute = trigger_time.minute
    hour = trigger_time.hour
    
    # 1m每分钟都同步
    intervals = ["1m"]
    
    # 15m：每15分钟的00分同步（00、15、30、45分）
    if minute % 15 == 0:
        intervals.append("15m")
    
    # 30m：+1分（01分和31分）
    if minute == 1 or minute == 31:
        intervals.append("30m")
    
    # 1h：+2分（02分）
    if minute == 2:
        intervals.append("1h")
    
    # 4h：+3分（03分，在0、4、8、12、16、20点）
    if minute == 3 and hour % 4 == 0:
        intervals.append("4h")
    
    # 1d：+4分（每天0点04分）
    if minute == 4 and hour == 0:
        intervals.append("1d")
    
    # 3d：+5分（每天0点05分）
    if minute == 5 and hour == 0:
        intervals.append("3d")
    
    return intervals


async def sync_single_interval(symbol: str, interval: str, semaphore: asyncio.Semaphore) -> tuple:
    """
    同步单个币种单个周期的K线（带信号量控制）
    
    Args:
        symbol: 交易对
        interval: K线周期
        semaphore: 并发控制信号量
    
    Returns:
        (symbol, interval, result, error) 元组
    """
    async with semaphore:
        try:
            result = await binance_client.sync_klines(symbol, interval=interval, force=True)
            return (symbol, interval, result if result else 0, None)
        except Exception as e:
            return (symbol, interval, 0, str(e))


async def sync_klines_task():
    """
    统一K线数据同步任务
    
    根据当前时间判断需要同步的周期，使用信号量控制并发度，最大化网络带宽利用
    同步完成后自动触发监控任务
    """
    if not is_scheduler_running():
        return
    
    trigger_time = datetime.now()
    
    try:
        symbols = await get_active_symbols()
        
        if not symbols:
            return
        
        intervals = get_intervals_to_sync(trigger_time)
        
        logger.info(f"[K线同步] 开始 - {trigger_time.strftime('%Y-%m-%d %H:%M:%S')} | 周期: {', '.join(intervals)} | 交易对: {len(symbols)}个")
        
        # 启动统计收集
        sync_stats_collector.start_batch()
        
        semaphore = asyncio.Semaphore(SYNC_CONCURRENCY)
        
        # 创建所有同步任务
        tasks = [
            sync_single_interval(symbol, interval, semaphore)
            for symbol in symbols
            for interval in intervals
        ]
        
        # 并发执行所有任务
        await asyncio.gather(*tasks, return_exceptions=True)
        
        # 完成统计并输出汇总
        stats = sync_stats_collector.finish_batch()
        if stats:
            logger.info("\n" + stats.format_summary())
        
        # 广播K线同步完成事件
        await event_broadcaster.broadcast("sync_complete", {
            "success_count": stats.success_count if stats else 0,
            "fail_count": stats.failed_count if stats else 0,
            "intervals": intervals,
            "elapsed": stats.get_duration() if stats else 0
        })
        
        # 触发监控任务
        if stats and stats.success_count > 0:
            await run_monitor_task(symbols)
        
    except Exception as e:
        logger.error(f"[K线同步] 任务异常: {e}", exc_info=True)


async def cleanup_klines_task():
    """
    清理过期K线数据任务
    
    每天执行一次，按周期区分保留天数：
    - 1m: 1天
    - 15m, 30m, 1h: 30天
    - 4h, 1d, 3d: 90天
    """
    try:
        result = await binance_client.cleanup_old_klines()  # 使用按周期配置
        total = result.get("total", 0)
        details = {k: v for k, v in result.items() if k != "total"}
        print(f"[Scheduler] 清理了 {total} 条过期K线数据: {details}")
    except Exception as e:
        print(f"[Scheduler] K线清理任务异常: {e}")


async def run_single_monitor(symbol: str, semaphore: asyncio.Semaphore) -> tuple:
    """
    执行单个币种的监控检查（带信号量控制）
    
    Args:
        symbol: 交易对
        semaphore: 并发控制信号量
    
    Returns:
        (symbol, result) 元组
    """
    async with semaphore:
        try:
            result = await monitor_service.run_all_checks(symbol)
            return (symbol, result)
        except Exception as e:
            return (symbol, e)


async def run_monitor_task(symbols: List[str] = None):
    """
    主监控任务
    
    在K线同步成功后触发，遍历指定的币种执行监控检查
    
    Args:
        symbols: 要监控的交易对列表，默认获取所有启用的币种
    """
    if not is_scheduler_running():
        return
    
    try:
        # 如果未指定交易对，则获取所有启用的币种
        if symbols is None:
            symbols = await get_active_symbols()
        
        if not symbols:
            return
        
        logger.info(f"[监控检查] 开始 - 交易对: {len(symbols)}个")
        
        # 启动监控统计收集
        monitor_stats_collector.start_batch()
        
        # 使用信号量控制并发度
        semaphore = asyncio.Semaphore(MONITOR_CONCURRENCY)
        
        # 创建所有监控任务
        tasks = [run_single_monitor(symbol, semaphore) for symbol in symbols]
        
        # 并发执行所有任务（不输出详细日志）
        await asyncio.gather(*tasks, return_exceptions=True)
        
        # 完成统计并输出汇总
        stats = monitor_stats_collector.finish_batch()
        if stats:
            logger.info("\n" + stats.format_summary())
        
        # 广播监控任务完成事件
        await event_broadcaster.broadcast("monitor_complete", {
            "symbols_count": len(symbols),
            "duration": stats.get_duration() if stats else 0
        })
        
    except Exception as e:
        logger.error(f"[监控检查] 任务异常: {e}", exc_info=True)


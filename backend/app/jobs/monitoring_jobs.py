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
from typing import List

from ..core.database import SessionLocal
from ..core.events import event_broadcaster
from ..core.scheduler import is_scheduler_running
from ..core.stats import sync_stats_collector, monitor_stats_collector
from ..core.logger import logger
from ..core.timezone import now_beijing
from ..models.symbol import Symbol
from ..services.binance_client import binance_client
from ..services.monitor_service import monitor_service

# 并发控制常量
SYNC_CONCURRENCY = 600  # K线同步最大并发数（已初始化的增量同步）
INITIAL_SYNC_CONCURRENCY = 20  # 初始同步最大并发数（控制API请求量）
INITIAL_SYNC_BATCH_SIZE = 5  # 每分钟最多初始化的新交易对数量
MONITOR_CONCURRENCY = 100  # 监控任务最大并发数（提升到100，因为主要是数据库查询）


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


async def get_synced_and_unsynced_symbols() -> tuple:
    """
    获取已初始化和未初始化的活跃交易对
    
    Returns:
        (已初始化列表, 未初始化列表)
    """
    db = SessionLocal()
    try:
        synced = db.query(Symbol).filter(
            Symbol.is_active == True,
            Symbol.initial_synced == True
        ).all()
        unsynced = db.query(Symbol).filter(
            Symbol.is_active == True,
            Symbol.initial_synced == False
        ).all()
        return ([s.symbol for s in synced], [s.symbol for s in unsynced])
    finally:
        db.close()


def mark_symbol_synced(symbol: str):
    """
    标记交易对已完成初始同步
    
    Args:
        symbol: 交易对名称
    """
    db = SessionLocal()
    try:
        db.query(Symbol).filter(Symbol.symbol == symbol).update(
            {"initial_synced": True}
        )
        db.commit()
    finally:
        db.close()


def get_intervals_to_sync(trigger_time = None):
    """
    智能获取需要同步的K线周期
    
    - 1m、15m：00分同步
    - 30m：+1分（01分、31分）
    - 1h：+2分（02分）
    - 4h：+3分（03分）
    - 1d：+4分（04分）
    - 3d：+5分（05分）
    
    Args:
        trigger_time: 触发时间，默认为当前北京时间
    
    Returns:
        需要同步的周期列表
    """
    if trigger_time is None:
        trigger_time = now_beijing()
    
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


async def sync_initial_symbol(symbol: str, intervals: List[str], semaphore: asyncio.Semaphore) -> bool:
    """
    对单个交易对执行初始同步（所有周期）
    
    Args:
        symbol: 交易对
        intervals: 需要同步的周期列表
        semaphore: 并发控制信号量
    
    Returns:
        是否全部成功
    """
    success = True
    async with semaphore:
        for interval in intervals:
            try:
                await binance_client.sync_klines(symbol, interval=interval, force=True)
            except Exception as e:
                logger.debug(f"[初始同步] {symbol} {interval} 失败: {e}")
                success = False
    return success


async def sync_klines_task():
    """
    统一K线数据同步任务（支持渐进式初始化）
    
    - 已初始化的交易对：正常增量同步，高并发
    - 未初始化的交易对：每分钟只处理N个，低并发，完成后标记为已初始化
    """
    if not is_scheduler_running():
        return
    
    trigger_time = now_beijing()
    
    try:
        # 区分已初始化和未初始化的交易对
        synced_symbols, unsynced_symbols = await get_synced_and_unsynced_symbols()
        
        if not synced_symbols and not unsynced_symbols:
            return
        
        intervals = get_intervals_to_sync(trigger_time)
        # 初始同步使用所有周期
        all_intervals = ["1m", "15m", "30m", "1h", "4h", "1d", "3d"]
        
        # 本次要初始化的交易对（限制数量）
        to_initialize = unsynced_symbols[:INITIAL_SYNC_BATCH_SIZE]
        
        logger.info(
            f"[K线同步] 开始 - {trigger_time.strftime('%Y-%m-%d %H:%M:%S')} | "
            f"周期: {', '.join(intervals)} | "
            f"增量同步: {len(synced_symbols)}个 | "
            f"初始同步: {len(to_initialize)}/{len(unsynced_symbols)}个"
        )
        
        # 启动统计收集
        sync_stats_collector.start_batch()
        
        # ===== 1. 已初始化交易对的增量同步（高并发） =====
        if synced_symbols:
            semaphore = asyncio.Semaphore(SYNC_CONCURRENCY)
            tasks = [
                sync_single_interval(symbol, interval, semaphore)
                for symbol in synced_symbols
                for interval in intervals
            ]
            await asyncio.gather(*tasks, return_exceptions=True)
        
        # ===== 2. 未初始化交易对的初始同步（低并发，限量） =====
        if to_initialize:
            logger.info(f"[初始同步] 开始初始化 {len(to_initialize)} 个新交易对: {', '.join(to_initialize)}")
            init_semaphore = asyncio.Semaphore(INITIAL_SYNC_CONCURRENCY)
            
            init_tasks = [
                sync_initial_symbol(symbol, all_intervals, init_semaphore)
                for symbol in to_initialize
            ]
            results = await asyncio.gather(*init_tasks, return_exceptions=True)
            
            # 标记成功初始化的交易对
            initialized_count = 0
            for symbol, result in zip(to_initialize, results):
                if result is True:
                    mark_symbol_synced(symbol)
                    initialized_count += 1
            
            remaining = len(unsynced_symbols) - len(to_initialize)
            logger.info(f"[初始同步] 完成 {initialized_count}/{len(to_initialize)} 个，剩余待初始化: {remaining} 个")
        
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
        
        # 触发监控任务（仅对已初始化的交易对）
        if synced_symbols and stats and stats.success_count > 0:
            await run_monitor_task(synced_symbols)
        
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


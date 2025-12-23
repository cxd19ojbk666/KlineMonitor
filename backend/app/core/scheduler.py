"""
APScheduler 调度器封装
=====================
负责调度器启停控制和任务管理
"""
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

# 调度器实例
scheduler = AsyncIOScheduler()

# 调度器运行状态
scheduler_running = False


def start_scheduler():
    """
    启动调度器
    
    添加K线同步任务和清理任务
    """
    global scheduler_running
    
    if scheduler.running:
        print("[Scheduler] 调度器已在运行")
        return
    
    # 延迟导入避免循环依赖
    from ..jobs.monitoring_jobs import sync_klines_task, cleanup_klines_task
    
    # 添加统一K线同步任务：每分钟第0秒执行，同步完成后自动触发监控任务
    scheduler.add_job(
        sync_klines_task,
        CronTrigger(second=0),
        id="sync_klines_unified",
        name="K线同步与监控",
        replace_existing=True
    )
    
    # 添加K线清理任务：每天定时执行
    scheduler.add_job(
        cleanup_klines_task,
        CronTrigger(hour=1, minute=10),
        id="cleanup_klines_task",
        name="K线数据清理任务",
        replace_existing=True
    )
    
    scheduler.start()
    scheduler_running = True
    print("[Scheduler] 调度器已启动")


def stop_scheduler():
    """停止调度器"""
    global scheduler_running
    
    if scheduler.running:
        scheduler.shutdown(wait=False)
    
    scheduler_running = False
    print("[Scheduler] 调度器已停止")


def pause_scheduler():
    """暂停调度器"""
    global scheduler_running
    
    if scheduler.running:
        scheduler.pause()
    
    scheduler_running = False
    print("[Scheduler] 调度器已暂停")


def resume_scheduler():
    """恢复调度器"""
    global scheduler_running
    
    if scheduler.running:
        scheduler.resume()
    
    scheduler_running = True
    print("[Scheduler] 调度器已恢复")


def get_scheduler_status() -> dict:
    """
    获取调度器状态
    
    Returns:
        包含运行状态、暂停状态和任务列表的字典
    """
    return {
        "is_running": scheduler_running,
        "is_paused": not scheduler_running,
        "scheduler_running": scheduler.running if scheduler else False,
        "jobs": [
            {
                "id": job.id,
                "name": job.name,
                "next_run_time": str(job.next_run_time) if job.next_run_time else None
            }
            for job in scheduler.get_jobs()
        ] if scheduler.running else []
    }


def is_scheduler_running() -> bool:
    """
    检查调度器是否运行中
    
    Returns:
        调度器运行状态
    """
    return scheduler_running

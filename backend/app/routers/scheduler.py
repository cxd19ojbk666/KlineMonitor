"""
调度器控制路由
=============
提供调度器状态查询和控制接口
"""
from fastapi import APIRouter

from ..core.scheduler import get_scheduler_status, pause_scheduler, resume_scheduler

router = APIRouter(prefix="/scheduler", tags=["调度器"])


@router.get("/status")
def scheduler_status():
    """
    获取调度器状态
    
    返回调度器运行状态、暂停状态和任务列表
    """
    return get_scheduler_status()


@router.post("/pause")
def scheduler_pause():
    """
    暂停调度器
    
    暂停后监控任务将不再执行
    """
    pause_scheduler()
    return {"message": "调度器已暂停", "status": get_scheduler_status()}


@router.post("/resume")
def scheduler_resume():
    """
    恢复调度器
    
    恢复后监控任务将继续执行
    """
    resume_scheduler()
    return {"message": "调度器已恢复", "status": get_scheduler_status()}


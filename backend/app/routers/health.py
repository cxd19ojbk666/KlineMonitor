"""
健康检查路由
===========
提供系统健康检查和根路由
"""
from fastapi import APIRouter

router = APIRouter(tags=["系统"])


@router.get("/")
def root():
    """
    根路由
    返回系统基本信息
    """
    return {
        "name": "币安合约K线监控系统",
        "version": "1.0.0",
        "status": "running"
    }


@router.get("/health")
def health_check():
    """
    健康检查接口
    返回系统运行状态
    """
    return {"status": "healthy"}


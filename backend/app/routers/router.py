"""
API路由聚合
==========
聚合所有API路由到统一入口
"""
from fastapi import APIRouter

from .health import router as health_router
from .alert import router as alert_router
from .config import router as config_router
from .symbol import router as symbol_router
from .monitoring import router as monitor_router
from .scheduler import router as scheduler_router
from .events import router as events_router
from .logs import router as logs_router

# 聚合API路由
api_router = APIRouter()

# 系统路由
api_router.include_router(scheduler_router)
api_router.include_router(events_router)

# 业务模块路由（prefix和tags已在各路由文件中定义）
api_router.include_router(alert_router)
api_router.include_router(config_router)
api_router.include_router(symbol_router)
api_router.include_router(monitor_router)
api_router.include_router(logs_router)


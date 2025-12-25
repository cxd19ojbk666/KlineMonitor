"""
FastAPI 主入口
=============
应用初始化、生命周期管理、中间件配置
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routers.router import api_router
from .routers.health import router as health_router
from .core.config import settings
from .core.database import init_db
from .core.scheduler import start_scheduler, stop_scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    应用生命周期管理
    
    启动时：初始化数据库、根据配置启动调度器
    关闭时：停止调度器
    """
    # 启动时
    print("正在初始化数据库...")
    init_db()
    print("数据库初始化完成")
    
    # 根据配置决定是否启动调度器
    if settings.ENABLE_SCHEDULER:
        print("正在启动调度器...")
        start_scheduler()
        print("调度器启动完成")
    else:
        print("调度器已禁用（ENABLE_SCHEDULER=false）")
    
    yield
    
    # 关闭时
    if settings.ENABLE_SCHEDULER:
        print("正在停止调度器...")
        stop_scheduler()
        print("调度器已停止")


# 创建FastAPI应用
app = FastAPI(
    title="币安合约K线监控系统",
    description="监控币安所有合约的成交量、涨幅和开盘价匹配",
    version="1.0.0",
    lifespan=lifespan
)

# 配置CORS
cors_origins = settings.CORS_ALLOW_ORIGINS.split(",") if settings.CORS_ALLOW_ORIGINS != "*" else ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(health_router)  # 根路由和健康检查
app.include_router(api_router, prefix="/api")  # API路由


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.BACKEND_HOST,
        port=settings.BACKEND_PORT,
        reload=settings.BACKEND_RELOAD
    )

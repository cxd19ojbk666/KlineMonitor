"""
Worker 入口
===========
独立运行调度任务的 Worker 进程
与 API 服务分离，避免监控任务阻塞 API 响应
"""
import asyncio
import signal
import sys

from .core.config import settings
from .core.database import init_db
from .core.scheduler import start_scheduler, stop_scheduler


# 优雅退出标志
shutdown_event = asyncio.Event()


def signal_handler(signum, frame):
    """处理退出信号"""
    print(f"\n[Worker] 收到信号 {signum}，准备退出...")
    shutdown_event.set()


async def main():
    """Worker 主函数"""
    print("=" * 60)
    print("[Worker] K线监控 Worker 启动")
    print("=" * 60)
    
    # 初始化数据库
    print("[Worker] 正在初始化数据库...")
    init_db()
    print("[Worker] 数据库初始化完成")
    
    # 启动调度器
    print("[Worker] 正在启动调度器...")
    start_scheduler()
    print("[Worker] 调度器启动完成")
    print("[Worker] Worker 运行中，按 Ctrl+C 退出")
    
    # 等待退出信号
    await shutdown_event.wait()
    
    # 清理
    print("[Worker] 正在停止调度器...")
    stop_scheduler()
    print("[Worker] Worker 已退出")


if __name__ == "__main__":
    # 注册信号处理
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # 运行主函数
    asyncio.run(main())

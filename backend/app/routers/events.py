"""
SSE事件流路由
=============
提供实时事件推送接口
"""
import asyncio
import json

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from ..core.events import event_broadcaster

router = APIRouter(tags=["事件"])


@router.get("/events")
async def sse_events():
    """
    SSE 事件流
    
    用于实时推送调度器状态变化和监控事件
    
    事件类型:
    - connected: 连接成功
    - sync_complete: K线同步完成
    - monitor_complete: 监控任务完成
    - scheduler_status: 调度器状态变化
    """
    async def event_generator():
        queue = await event_broadcaster.subscribe()
        try:
            # 发送初始连接成功事件
            yield f"data: {json.dumps({'type': 'connected', 'data': {}})}\n\n"
            
            while True:
                try:
                    # 等待事件，超时30秒发送心跳
                    event = await asyncio.wait_for(queue.get(), timeout=30.0)
                    yield f"data: {json.dumps(event)}\n\n"
                except asyncio.TimeoutError:
                    # 发送心跳保持连接
                    yield ": heartbeat\n\n"
        except asyncio.CancelledError:
            pass
        finally:
            await event_broadcaster.unsubscribe(queue)
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


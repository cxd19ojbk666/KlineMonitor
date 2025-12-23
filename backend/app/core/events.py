"""事件广播器 - 用于 SSE 推送通知前端刷新"""
import asyncio
from typing import Set, Dict, Any
from datetime import datetime
import json


class EventBroadcaster:
    """SSE 事件广播器"""
    
    def __init__(self):
        self._subscribers: Set[asyncio.Queue] = set()
        self._lock = asyncio.Lock()
    
    async def subscribe(self) -> asyncio.Queue:
        """订阅事件流"""
        queue = asyncio.Queue()
        async with self._lock:
            self._subscribers.add(queue)
        return queue
    
    async def unsubscribe(self, queue: asyncio.Queue):
        """取消订阅"""
        async with self._lock:
            self._subscribers.discard(queue)
    
    async def broadcast(self, event_type: str, data: Dict[str, Any] = None):
        """广播事件到所有订阅者"""
        event = {
            "type": event_type,
            "data": data or {},
            "timestamp": datetime.now().isoformat()
        }
        
        async with self._lock:
            dead_queues = set()
            for queue in self._subscribers:
                try:
                    queue.put_nowait(event)
                except asyncio.QueueFull:
                    dead_queues.add(queue)
            
            # 清理满队列的订阅者
            self._subscribers -= dead_queues
    
    @property
    def subscriber_count(self) -> int:
        """当前订阅者数量"""
        return len(self._subscribers)


# 全局事件广播器实例
event_broadcaster = EventBroadcaster()

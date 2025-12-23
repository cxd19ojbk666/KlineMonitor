"""
提醒相关 Pydantic 模式
=====================
"""
from datetime import datetime
from typing import List, Optional, Any, Dict

from pydantic import BaseModel


class AlertResponse(BaseModel):
    """提醒响应模式"""
    id: int
    symbol: str
    alert_type: int
    data: Dict[str, Any]
    created_at: datetime
    
    class Config:
        from_attributes = True


class AlertListResponse(BaseModel):
    """提醒列表响应模式"""
    total: int
    items: List[AlertResponse]


class DashboardStats(BaseModel):
    """仪表盘统计数据模式"""
    total_alerts_today: int
    alert_type_1_count: int
    alert_type_2_count: int
    alert_type_3_count: int
    active_symbols_count: int
    active_symbols: List[str]
    is_running: bool
    recent_alerts: List[AlertResponse]

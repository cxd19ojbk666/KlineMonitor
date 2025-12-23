"""
币种相关 Pydantic 模式
=====================
包含监控币种的数据验证模型
"""
from datetime import datetime
from typing import List

from pydantic import BaseModel


class SymbolBase(BaseModel):
    """币种基础模式"""
    symbol: str  # 交易对（如 BTCUSDT）


class SymbolCreate(SymbolBase):
    """币种创建模式"""
    pass


class SymbolResponse(SymbolBase):
    """币种响应模式"""
    id: int  # 记录ID
    is_active: bool  # 是否启用监控
    created_at: datetime  # 添加时间
    
    class Config:
        from_attributes = True


class SymbolListResponse(BaseModel):
    """币种列表响应模式"""
    total: int  # 总数
    items: List[SymbolResponse]  # 币种列表


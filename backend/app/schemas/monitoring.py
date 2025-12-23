"""
监控相关 Pydantic 模式
=====================
包含K线数据和监控指标的数据验证模型
"""
from typing import Optional, List

from pydantic import BaseModel


class KlineData(BaseModel):
    """K线数据模式"""
    open_time: str  # 开盘时间（格式化字符串）
    open: float  # 开盘价
    high: float  # 最高价
    low: float  # 最低价
    close: float  # 收盘价
    volume: float  # 成交量
    quote_volume: float  # 成交额
    close_time: str  # 收盘时间（格式化字符串）


class MonitorMetrics(BaseModel):
    """监控指标数据模式"""
    # 需求一：成交量监控
    volume_15m: float  # 15分钟成交量
    volume_8h: float  # 8小时成交量
    volume_percent: float  # 成交量比例配置
    volume_threshold: float  # 成交量阈值
    volume_triggered: bool  # 是否触发成交量提醒
    
    # 需求二：涨幅监控
    rise_percent: float  # 当前涨幅
    rise_threshold: float  # 涨幅阈值
    rise_triggered: bool  # 是否触发涨幅提醒
    rise_start_time: Optional[str] = None  # 涨幅计算开始时间
    rise_start_price: Optional[float] = None  # 涨幅计算开始价格
    rise_end_time: Optional[str] = None  # 涨幅计算结束时间
    rise_end_price: Optional[float] = None  # 涨幅计算结束价格
    
    # 需求三：开盘价匹配状态
    price_error_config: float  # 价格误差配置
    fake_count_n_config: int  # 中间K线数量配置
    open_price_triggered: bool = False  # 是否触发开盘价匹配
    open_price_match_info: Optional[str] = None  # 匹配信息
    open_price_d: Optional[float] = None  # D点开盘价（最新K线）
    open_price_d_time: Optional[str] = None  # D点时间
    open_price_e: Optional[float] = None  # E点开盘价（匹配的历史K线）
    open_price_e_time: Optional[str] = None  # E点时间
    open_price_error: Optional[float] = None  # 实际误差百分比
    open_price_middle_count: Optional[int] = None  # 实际间隔K线数量


class SymbolMonitorData(BaseModel):
    """币种监控数据模式"""
    symbol: str  # 交易对
    timestamp: str  # 数据时间戳
    current_price: float  # 当前价格
    metrics: MonitorMetrics  # 监控指标
    klines: List[KlineData]  # K线数据列表


class SymbolMonitorListResponse(BaseModel):
    """币种监控列表响应模式"""
    total: int  # 总数
    items: List[SymbolMonitorData]  # 监控数据列表


"""
K线数据模型
===========
包含多周期K线数据的数据库表定义
"""
from datetime import datetime
from sqlalchemy import Column, DateTime, Float, Integer, String, UniqueConstraint, Index

from ..core.database import Base


class PriceKline(Base):
    """
    多周期K线数据表
    存储所有周期的价格数据（1m, 15m, 30m, 1h, 4h, 1d, 3d）
    """
    __tablename__ = "price_klines"
    
    # 主键
    id = Column(Integer, primary_key=True, index=True)
    # 交易对
    symbol = Column(String(50), nullable=False, index=True)
    # K线周期: 1m, 15m, 30m, 1h, 4h, 1d, 3d
    interval = Column(String(10), nullable=False, index=True)
    # K线开盘时间
    open_time = Column(DateTime, nullable=False, index=True)
    # 开盘价
    open = Column(Float, nullable=False)
    # 最高价
    high = Column(Float, nullable=False)
    # 最低价
    low = Column(Float, nullable=False)
    # 收盘价
    close = Column(Float, nullable=False)
    # 成交量
    volume = Column(Float, nullable=False)
    # K线收盘时间
    close_time = Column(DateTime, nullable=False)
    # 成交额(USDT)
    quote_volume = Column(Float, nullable=False)
    # 成交笔数
    trades = Column(Integer, nullable=False)
    # 主动买入成交量
    taker_buy_volume = Column(Float, nullable=False)
    # 主动买入成交额
    taker_buy_quote_volume = Column(Float, nullable=False)
    
    # 联合唯一约束和索引
    __table_args__ = (
        # 同一交易对、周期、开盘时间唯一
        UniqueConstraint('symbol', 'interval', 'open_time', name='uix_price_kline'),
        # 联合索引，用于快速查询
        Index('ix_price_kline_lookup', 'symbol', 'interval', 'open_time'),
        # 优化涨跌K线查询（需求三：开盘价匹配）
        Index('ix_kline_bullish', 'symbol', 'interval', 'open_time', 'close', 'open'),
    )


"""
提醒相关数据模型
===============
包含提醒记录和去重记录的数据库表定义
"""
from datetime import datetime
from sqlalchemy import Column, DateTime, Integer, String, JSON, Index

from ..core.database import Base


class Alert(Base):
    """
    提醒记录表
    存储所有触发的提醒信息
    
    data 字段 JSON 结构：
    类型1(成交量): {
        "volume_15m": float,      # 15分钟成交量
        "volume_8h": float,       # 8小时成交量
        "volume_ratio": float,    # 占比百分比
        "volume_threshold": float # 触发阈值百分比
    }
    类型2(涨幅): {
        "rise_percent": float,     # 涨幅百分比
        "rise_threshold": float,   # 涨幅阈值
        "rise_start_price": float, # 起始价格
        "rise_end_price": float    # 结束价格
    }
    类型3(开盘价匹配): {
        "timeframe": str,              # K线周期
        "price_d": float,              # 最新开盘价D
        "price_e": float,              # 匹配开盘价E
        "time_d": str,                 # D的时间 (ISO格式)
        "time_e": str,                 # E的时间 (ISO格式)
        "price_error": float,          # 价格误差百分比
        "price_error_threshold": float,# 误差阈值
        "middle_count": int,           # 中间K线数量
        "middle_count_threshold": int  # 中间K线阈值
    }
    """
    __tablename__ = "alerts"
    
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(50), nullable=False, index=True)
    alert_type = Column(Integer, nullable=False)
    data = Column(JSON, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class AlertDedup(Base):
    """提醒去重记录表"""
    __tablename__ = "alert_dedups"
    
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(50), nullable=False, index=True)
    alert_type = Column(Integer, nullable=False, index=True)
    dedup_key = Column(String(200), nullable=True, index=True)
    last_alert_time = Column(DateTime, nullable=False)
    
    __table_args__ = (
        Index('ix_alert_dedup_lookup', 'symbol', 'alert_type', 'dedup_key'),
    )

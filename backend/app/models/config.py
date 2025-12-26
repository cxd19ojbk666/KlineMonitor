"""
配置相关数据模型
===============
包含全局配置和币种个性化配置的数据库表定义
"""
from datetime import datetime
from sqlalchemy import Column, DateTime, Float, Integer, String, Index

from ..core.database import Base


class Config(Base):
    """
    可调参数配置表
    存储系统全局配置参数
    """
    __tablename__ = "configs"
    
    # 主键
    id = Column(Integer, primary_key=True, index=True)
    # 参数名（唯一）
    key = Column(String(100), nullable=False, unique=True, index=True)
    # 参数值
    value = Column(String(500), nullable=False)


class SymbolConfig(Base):
    """
    币种个性化配置表
    存储每个币种+K线间隔的独立配置（优先级高于全局配置）
    """
    __tablename__ = "symbol_configs"
    
    # 主键
    id = Column(Integer, primary_key=True, index=True)
    # 交易对
    symbol = Column(String(50), nullable=False, index=True)
    # K线间隔（如：1m, 5m, 15m, 1h, 4h, 1d等）
    interval = Column(String(10), nullable=False, index=True)
    # 开盘价误差阈值（%），null表示使用全局配置
    price_error = Column(Float, nullable=True)
    # D和E之间最少间隔K线数，null表示使用全局配置
    middle_kline_cnt = Column(Integer, nullable=True)
    # 中间最多N个假K线，null表示使用全局配置
    fake_kline_cnt = Column(Integer, nullable=True)
    # 创建时间（北京时间）
    created_at = Column(DateTime, default=now_beijing)
    # 更新时间（北京时间）
    updated_at = Column(DateTime, default=now_beijing, onupdate=now_beijing)
    
    # 联合唯一约束：同一币种+间隔只能有一条配置
    __table_args__ = (
        Index('ix_symbol_interval', 'symbol', 'interval', unique=True),
    )


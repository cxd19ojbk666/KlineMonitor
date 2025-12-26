"""
币种相关数据模型
===============
包含监控币种的数据库表定义
"""
from sqlalchemy import Boolean, Column, DateTime, Integer, String

from ..core.database import Base
from ..core.timezone import now_beijing


class Symbol(Base):
    """
    监控币种表
    存储所有需要监控的交易对信息
    """
    __tablename__ = "symbols"
    
    # 主键
    id = Column(Integer, primary_key=True, index=True)
    # 交易对（如 BTCUSDT，唯一）
    symbol = Column(String(50), unique=True, nullable=False, index=True)
    # 是否启用监控
    is_active = Column(Boolean, default=True)
    # 是否已完成初始同步（用于渐进式初始化）
    initial_synced = Column(Boolean, default=False)
    # 添加时间（北京时间）
    created_at = Column(DateTime, default=now_beijing)


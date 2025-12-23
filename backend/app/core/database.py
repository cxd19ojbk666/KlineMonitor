"""
数据库连接模块
=============
提供 SQLAlchemy 数据库连接和会话管理
"""
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from .config import settings

# 创建数据库引擎
engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False}, 
    poolclass=StaticPool,   # 使用静态池，单连接复用
)

# 创建会话工厂
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 创建基类
Base = declarative_base()


def init_db():
    """
    初始化数据库表
    
    导入所有模型并创建表结构
    """
    # 导入所有模型以注册到 Base.metadata
    from ..models.alert import Alert, AlertDedup
    from ..models.config import Config, SymbolConfig
    from ..models.symbol import Symbol
    from ..models.kline import PriceKline
    
    # 创建所有表
    Base.metadata.create_all(bind=engine)

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
    
    # 迁移：添加 initial_synced 列（如果不存在）
    _migrate_add_initial_synced_column()


def _migrate_add_initial_synced_column():
    """
    迁移：为 symbols 表添加 initial_synced 列
    并将已有K线数据的交易对标记为已初始化
    """
    from sqlalchemy import text
    
    with engine.connect() as conn:
        # 检查列是否存在
        result = conn.execute(text("PRAGMA table_info(symbols)"))
        columns = [row[1] for row in result.fetchall()]
        
        if "initial_synced" not in columns:
            # 添加列
            conn.execute(text("ALTER TABLE symbols ADD COLUMN initial_synced BOOLEAN DEFAULT 0"))
            conn.commit()
            print("[Migration] 已添加 initial_synced 列")
            
            # 将已有K线数据的交易对标记为已初始化
            conn.execute(text("""
                UPDATE symbols SET initial_synced = 1 
                WHERE symbol IN (SELECT DISTINCT symbol FROM price_klines)
            """))
            conn.commit()
            print("[Migration] 已将现有交易对标记为已初始化")

"""依赖注入模块 - 统一管理公共依赖"""
from contextlib import contextmanager
from typing import Generator
from sqlalchemy.orm import Session

from .database import SessionLocal
from .config import settings, Settings


def get_db_session() -> Generator[Session, None, None]:
    """获取数据库会话依赖（用于FastAPI Depends）"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_settings() -> Settings:
    """获取应用配置依赖"""
    return settings


@contextmanager
def get_db_context() -> Generator[Session, None, None]:
    """获取数据库会话上下文管理器（用于非FastAPI场景）
    
    使用示例:
        with get_db_context() as db:
            # 执行数据库操作
            result = db.query(Model).all()
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

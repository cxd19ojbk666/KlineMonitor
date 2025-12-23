"""
配置服务
=======
提供配置相关的业务逻辑：默认值初始化、配置查询辅助

功能：
- 初始化默认配置：在系统启动时填充默认配置值
- 配置值查询：提供便捷的配置值获取方法
- 币种个性化配置：获取币种特定的配置值
"""
from typing import List

from sqlalchemy.orm import Session

from ..core.config import settings
from ..models.config import Config


# 默认配置项列表
DEFAULT_CONFIGS = [
    {"key": "1_volume_percent", "value": str(settings.DEFAULT_1_VOLUME_PERCENT)},
    {"key": "1_reminder_interval", "value": str(settings.DEFAULT_1_REMINDER_INTERVAL)},
    {"key": "2_rise_percent", "value": str(settings.DEFAULT_2_RISE_PERCENT)},
    {"key": "2_reminder_interval", "value": str(settings.DEFAULT_2_REMINDER_INTERVAL)},
    {"key": "3_price_error", "value": str(settings.DEFAULT_3_PRICE_ERROR)},
    {"key": "3_middle_kline_cnt", "value": str(settings.DEFAULT_3_MIDDLE_KLINE_CNT)},
    {"key": "3_fake_kline_cnt", "value": str(settings.DEFAULT_3_FAKE_KLINE_CNT)},
    {"key": "3_dedup_enabled", "value": str(settings.DEFAULT_3_DEDUP_ENABLED).lower()},
]


class ConfigService:
    """配置管理服务"""
    
    def init_default_configs(self, db: Session):
        """
        初始化默认配置
        如果配置不存在则创建，已存在则跳过
        
        Args:
            db: 数据库会话
        """
        for config_data in DEFAULT_CONFIGS:
            existing = db.query(Config).filter(Config.key == config_data["key"]).first()
            if not existing:
                config = Config(**config_data)
                db.add(config)
        db.commit()
    
    def get_config_value(self, db: Session, key: str, default: str = "") -> str:
        """
        获取配置值（字符串）
        
        Args:
            db: 数据库会话
            key: 配置键名
            default: 默认值
        
        Returns:
            配置值字符串
        """
        config = db.query(Config).filter(Config.key == key).first()
        return config.value if config else default
    
    def get_config_float(self, db: Session, key: str, default: float = 0.0) -> float:
        """
        获取配置值（浮点数）
        
        Args:
            db: 数据库会话
            key: 配置键名
            default: 默认值
        
        Returns:
            配置值（浮点数）
        """
        config = db.query(Config).filter(Config.key == key).first()
        return float(config.value) if config else default
    
    def get_all_configs(self, db: Session) -> List[Config]:
        """
        获取所有配置
        如果没有配置则先初始化默认配置
        
        Args:
            db: 数据库会话
        
        Returns:
            配置列表
        """
        configs = db.query(Config).all()
        
        # 如果没有配置，初始化默认配置
        if not configs:
            self.init_default_configs(db)
            configs = db.query(Config).all()
        
        return configs


# 全局实例
config_service = ConfigService()


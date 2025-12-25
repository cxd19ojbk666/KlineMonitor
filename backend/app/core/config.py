"""配置管理模块"""
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """应用配置"""
    # 数据库配置
    DATABASE_URL: str = "sqlite:///./database.db"
    
    # 币安API配置
    BINANCE_BASE_URL: str = "https://fapi.binance.com"
    BINANCE_API_KEY: str = ""
    BINANCE_API_SECRET: str = ""
    
    # 微信机器人配置
    WECHAT_WEBHOOK_URL: str = ""
    
    # 默认监控参数
    DEFAULT_1_VOLUME_PERCENT: float = 12.5  # 需求一：A >= B * percent / 100
    DEFAULT_2_RISE_PERCENT: float = 10.0  # 需求二：涨幅阈值(%)
    DEFAULT_1_REMINDER_INTERVAL: int = 60  # 需求一：提醒间隔（分钟）
    DEFAULT_2_REMINDER_INTERVAL: int = 60  # 需求二：提醒间隔（分钟）
    DEFAULT_3_PRICE_ERROR: float = 1.0  # 需求三：开盘价误差(%)
    DEFAULT_3_MIDDLE_KLINE_CNT: int = 3  # 需求三：D和E之间最少间隔K线数
    DEFAULT_3_FAKE_KLINE_CNT: int = 5  # 需求三：中间最多N个假K线
    DEFAULT_3_DEDUP_ENABLED: bool = True  # 需求三：同一匹配对(D,E)是否只提醒一次
    
    # 时间配置
    MAX_LOOKBACK_DAYS: int = 30  # 需求三：最大回溯天数
    
    # 后端服务配置
    BACKEND_HOST: str = "0.0.0.0"
    BACKEND_PORT: int = 8000
    BACKEND_RELOAD: bool = False
    
    # CORS配置
    CORS_ALLOW_ORIGINS: str = "*"
    
    # Worker 配置
    ENABLE_SCHEDULER: bool = True  # 是否启用调度器（API服务设为False）
    
    class Config:
        env_file = ".env"


settings = Settings()

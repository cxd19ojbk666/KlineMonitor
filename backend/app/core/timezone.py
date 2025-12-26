"""
时区工具
=======
统一处理北京时间（UTC+8）
"""
from datetime import datetime, timedelta, timezone

# 北京时区 UTC+8
BEIJING_TZ = timezone(timedelta(hours=8))


def now_beijing() -> datetime:
    """
    获取当前北京时间（带时区信息）
    
    Returns:
        当前北京时间的 datetime 对象
    """
    return datetime.now(BEIJING_TZ)


def utc_to_beijing(dt: datetime) -> datetime:
    """
    将 UTC 时间转换为北京时间
    
    Args:
        dt: UTC 时间（可以是 naive 或 aware）
    
    Returns:
        北京时间的 datetime 对象
    """
    if dt.tzinfo is None:
        # 如果是 naive datetime，假设它是 UTC
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(BEIJING_TZ)


def beijing_to_utc(dt: datetime) -> datetime:
    """
    将北京时间转换为 UTC 时间
    
    Args:
        dt: 北京时间（可以是 naive 或 aware）
    
    Returns:
        UTC 时间的 datetime 对象
    """
    if dt.tzinfo is None:
        # 如果是 naive datetime，假设它是北京时间
        dt = dt.replace(tzinfo=BEIJING_TZ)
    return dt.astimezone(timezone.utc)


def remove_timezone(dt: datetime) -> datetime:
    """
    移除时区信息，返回 naive datetime
    
    Args:
        dt: 带时区信息的 datetime
    
    Returns:
        不带时区信息的 datetime
    """
    return dt.replace(tzinfo=None)

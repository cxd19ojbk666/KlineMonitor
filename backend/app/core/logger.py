"""
日志系统
========
提供统一的日志管理功能

功能：
- 日志分级（DEBUG/INFO/WARNING/ERROR）
- 日志轮转和归档
- 控制台和文件双输出
"""
import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path


def setup_logger(name: str = "kline_monitor", log_dir: str = "logs") -> logging.Logger:
    """
    配置日志系统
    
    Args:
        name: 日志器名称
        log_dir: 日志目录
    
    Returns:
        配置好的日志器
    """
    # 创建日志目录
    log_path = Path(log_dir)
    log_path.mkdir(exist_ok=True)
    
    # 创建日志器
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    
    # 避免重复添加处理器
    if logger.handlers:
        return logger
    
    # 日志格式
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    app_log_file = log_path / "app.log"
    file_handler = RotatingFileHandler(
        app_log_file,
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    error_log_file = log_path / "error.log"
    error_handler = RotatingFileHandler(
        error_log_file,
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(formatter)
    logger.addHandler(error_handler)
    
    # 控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    return logger


# 全局日志器实例
logger = setup_logger()


import time
from collections import defaultdict
from typing import Dict, Tuple
from functools import wraps


class LogOptimizer:
    """日志优化器 - 用于聚合和采样日志"""
    
    def __init__(self):
        # 日志采样缓存: key -> (last_time, count)
        self._sampling_cache: Dict[str, Tuple[float, int]] = {}
        # 日志聚合缓存: 用于批量输出
        self._aggregation_cache: Dict[str, list] = defaultdict(list)
        # 最大缓存大小
        self._max_cache_size = 1000
    
    def should_log(self, key: str, sampling_seconds: int = 30) -> bool:
        """
        判断是否应该记录日志（采样机制）
        
        Args:
            key: 日志唯一标识
            sampling_seconds: 采样间隔（秒）
        
        Returns:
            是否应该记录
        """
        now = time.time()
        
        if key in self._sampling_cache:
            last_time, count = self._sampling_cache[key]
            if now - last_time < sampling_seconds:
                # 在采样间隔内，增加计数但不记录
                self._sampling_cache[key] = (last_time, count + 1)
                return False
        
        # 清理过期缓存
        if len(self._sampling_cache) > self._max_cache_size:
            self._cleanup_cache()
        
        # 记录本次日志
        self._sampling_cache[key] = (now, 1)
        return True
    
    def get_skip_count(self, key: str) -> int:
        """获取跳过的日志数量"""
        if key in self._sampling_cache:
            return self._sampling_cache[key][1] - 1
        return 0
    
    def aggregate_log(self, category: str, message: str):
        """
        聚合日志消息
        
        Args:
            category: 日志分类
            message: 日志消息
        """
        self._aggregation_cache[category].append(message)
    
    def flush_aggregated_logs(self, category: str) -> list:
        """
        获取并清空聚合的日志
        
        Args:
            category: 日志分类
        
        Returns:
            聚合的日志列表
        """
        logs = self._aggregation_cache.get(category, [])
        if category in self._aggregation_cache:
            self._aggregation_cache[category] = []
        return logs
    
    def _cleanup_cache(self):
        """清理过期的采样缓存"""
        now = time.time()
        expired_keys = [
            key for key, (last_time, _) in self._sampling_cache.items()
            if now - last_time > 300  # 5分钟未使用的缓存
        ]
        for key in expired_keys:
            del self._sampling_cache[key]


# 全局实例
log_optimizer = LogOptimizer()


def log_sampled(sampling_seconds: int = 30):
    """
    日志采样装饰器
    
    Args:
        sampling_seconds: 采样间隔（秒）
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # 使用函数名和参数作为缓存key
            key = f"{func.__name__}:{args}:{kwargs}"
            if log_optimizer.should_log(key, sampling_seconds):
                skip_count = log_optimizer.get_skip_count(key)
                if skip_count > 0:
                    # 如果跳过了日志，在下次记录时说明
                    return func(*args, skip_count=skip_count, **kwargs)
                return func(*args, **kwargs)
        return wrapper
    return decorator

"""
日志系统
========
提供统一的日志管理功能

功能：
- 结构化JSON日志（便于ELK/Loki解析）
- 异步写入（不阻塞业务逻辑）
- 日志分级（DEBUG/INFO/WARNING/ERROR）
- 日志轮转和归档
- 请求上下文追踪
- 日志采样和速率限制
"""
import atexit
import contextvars
import json
import logging
import os
import time
from collections import defaultdict
from functools import wraps
from logging.handlers import QueueHandler, QueueListener, RotatingFileHandler
from pathlib import Path
from queue import Queue
from typing import Any, Dict, Optional, Tuple


# ============== 上下文追踪 ==============
request_id_var: contextvars.ContextVar[str] = contextvars.ContextVar('request_id', default='-')
user_id_var: contextvars.ContextVar[str] = contextvars.ContextVar('user_id', default='-')


def set_request_context(request_id: str, user_id: str = '-'):
    """设置请求上下文"""
    request_id_var.set(request_id)
    user_id_var.set(user_id)


def clear_request_context():
    """清除请求上下文"""
    request_id_var.set('-')
    user_id_var.set('-')


# ============== JSON格式化器 ==============
class JsonFormatter(logging.Formatter):
    """JSON格式化器，便于日志分析系统解析"""
    
    def __init__(self, include_extra: bool = True):
        super().__init__()
        self.include_extra = include_extra
    
    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z",
            "level": record.levelname,
            "logger": record.name,
            "file": record.filename,
            "line": record.lineno,
            "func": record.funcName,
            "message": record.getMessage(),
            "request_id": getattr(record, 'request_id', '-'),
            "user_id": getattr(record, 'user_id', '-'),
        }
        
        # 添加异常信息
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        
        # 添加额外字段
        if self.include_extra and hasattr(record, 'extra_data'):
            log_data["extra"] = record.extra_data
        
        return json.dumps(log_data, ensure_ascii=False, default=str)


class ConsoleFormatter(logging.Formatter):
    """控制台彩色格式化器"""
    
    COLORS = {
        'DEBUG': '\033[36m',    # 青色
        'INFO': '\033[32m',     # 绿色
        'WARNING': '\033[33m',  # 黄色
        'ERROR': '\033[31m',    # 红色
        'CRITICAL': '\033[35m', # 紫色
    }
    RESET = '\033[0m'
    
    def format(self, record: logging.LogRecord) -> str:
        color = self.COLORS.get(record.levelname, self.RESET)
        request_id = getattr(record, 'request_id', '-')
        
        formatted = (
            f"{self.formatTime(record, '%Y-%m-%d %H:%M:%S')} "
            f"{color}{record.levelname:8}{self.RESET} "
            f"[{request_id}] "
            f"[{record.filename}:{record.lineno}] "
            f"{record.getMessage()}"
        )
        
        if record.exc_info:
            formatted += "\n" + self.formatException(record.exc_info)
        
        return formatted


# ============== 上下文过滤器 ==============
class ContextFilter(logging.Filter):
    """注入请求上下文到日志记录"""
    
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_var.get()
        record.user_id = user_id_var.get()
        return True


# ============== 级别过滤器 ==============
class LevelFilter(logging.Filter):
    """只允许特定级别的日志"""
    
    def __init__(self, level: int):
        super().__init__()
        self.level = level
    
    def filter(self, record: logging.LogRecord) -> bool:
        return record.levelno == self.level


# ============== 异步日志管理器 ==============
class AsyncLoggerManager:
    """异步日志管理器，管理QueueListener的生命周期"""
    
    _instance: Optional['AsyncLoggerManager'] = None
    _listeners: list = []
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._listeners = []
            atexit.register(cls._instance.shutdown)
        return cls._instance
    
    def add_listener(self, listener: QueueListener):
        """添加并启动监听器"""
        listener.start()
        self._listeners.append(listener)
    
    def shutdown(self):
        """关闭所有监听器"""
        for listener in self._listeners:
            try:
                listener.stop()
            except Exception:
                pass
        self._listeners.clear()


# ============== 日志设置 ==============
def setup_logger(
    name: str = "kline_monitor",
    log_dir: str = "logs",
    level: int = logging.INFO,
    json_format: bool = True,
    async_write: bool = True,
    max_bytes: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 5
) -> logging.Logger:
    """
    配置日志系统
    
    Args:
        name: 日志器名称
        log_dir: 日志目录
        level: 日志级别
        json_format: 是否使用JSON格式（文件）
        async_write: 是否异步写入
        max_bytes: 单个日志文件最大字节数
        backup_count: 保留的备份文件数量
    
    Returns:
        配置好的日志器
    """
    # 创建日志目录
    log_path = Path(log_dir)
    log_path.mkdir(exist_ok=True)
    
    # 创建日志器
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # 避免重复添加处理器
    if logger.handlers:
        return logger
    
    # 添加上下文过滤器
    context_filter = ContextFilter()
    logger.addFilter(context_filter)
    
    # 格式化器
    json_formatter = JsonFormatter()
    console_formatter = ConsoleFormatter()
    
    # 文件处理器配置: (文件名, 处理器级别, 级别过滤器)
    file_configs = [
        ("app.log", logging.INFO, None),              # 所有INFO及以上
        ("info.log", logging.INFO, logging.INFO),     # 仅INFO
        ("warning.log", logging.WARNING, logging.WARNING),  # 仅WARNING
        ("error.log", logging.ERROR, None),           # ERROR及以上
    ]
    
    file_handlers = []
    
    for filename, handler_level, level_filter in file_configs:
        handler = RotatingFileHandler(
            log_path / filename,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding='utf-8'
        )
        handler.setLevel(handler_level)
        handler.setFormatter(json_formatter if json_format else console_formatter)
        if level_filter is not None:
            handler.addFilter(LevelFilter(level_filter))
        file_handlers.append(handler)
    
    if async_write:
        # 异步写入：使用队列
        log_queue: Queue = Queue(-1)
        queue_handler = QueueHandler(log_queue)
        logger.addHandler(queue_handler)
        
        # 创建监听器处理实际写入
        listener = QueueListener(
            log_queue,
            *file_handlers,
            respect_handler_level=True
        )
        AsyncLoggerManager().add_listener(listener)
    else:
        # 同步写入
        for handler in file_handlers:
            logger.addHandler(handler)
    
    # 控制台处理器（始终同步，便于调试）
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    console_handler.setFormatter(console_formatter)
    console_handler.addFilter(context_filter)
    logger.addHandler(console_handler)
    
    return logger


# ============== 日志优化器 ==============
class LogOptimizer:
    """日志优化器 - 用于采样和速率限制"""
    
    def __init__(self):
        self._sampling_cache: Dict[str, Tuple[float, int]] = {}
        self._rate_cache: Dict[str, list] = defaultdict(list)
        self._max_cache_size = 1000
    
    def should_log(self, key: str, sampling_seconds: int = 30) -> Tuple[bool, int]:
        """
        判断是否应该记录日志（采样机制）
        
        Returns:
            (是否记录, 跳过的数量)
        """
        now = time.time()
        
        if key in self._sampling_cache:
            last_time, count = self._sampling_cache[key]
            if now - last_time < sampling_seconds:
                self._sampling_cache[key] = (last_time, count + 1)
                return False, 0
            
            skip_count = count - 1
            self._sampling_cache[key] = (now, 1)
            return True, skip_count
        
        if len(self._sampling_cache) > self._max_cache_size:
            self._cleanup_cache()
        
        self._sampling_cache[key] = (now, 1)
        return True, 0
    
    def rate_limited(self, key: str, max_per_minute: int = 10) -> bool:
        """基于速率的日志限制"""
        now = time.time()
        window_start = now - 60
        
        self._rate_cache[key] = [t for t in self._rate_cache[key] if t > window_start]
        
        if len(self._rate_cache[key]) >= max_per_minute:
            return False
        
        self._rate_cache[key].append(now)
        return True
    
    def _cleanup_cache(self):
        """清理过期缓存"""
        now = time.time()
        expired = [k for k, (t, _) in self._sampling_cache.items() if now - t > 300]
        for k in expired:
            del self._sampling_cache[k]


# ============== 全局实例 ==============
logger = setup_logger()
log_optimizer = LogOptimizer()


# ============== 便捷函数 ==============
def log_with_extra(level: int, message: str, **extra):
    """带额外字段的日志记录"""
    record = logger.makeRecord(
        logger.name, level, "", 0, message, (), None
    )
    record.extra_data = extra
    logger.handle(record)


def log_info(message: str, **extra):
    """INFO级别日志"""
    if extra:
        log_with_extra(logging.INFO, message, **extra)
    else:
        logger.info(message)


def log_error(message: str, **extra):
    """ERROR级别日志"""
    if extra:
        log_with_extra(logging.ERROR, message, **extra)
    else:
        logger.error(message)


def log_sampled(key: str, message: str, sampling_seconds: int = 30, level: int = logging.INFO):
    """采样日志"""
    should_log, skip_count = log_optimizer.should_log(key, sampling_seconds)
    if should_log:
        if skip_count > 0:
            message = f"{message} (skipped {skip_count} similar logs)"
        logger.log(level, message)

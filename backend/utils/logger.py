"""日志工具模块"""

import logging
import logging.handlers
import sys
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional
from functools import lru_cache

from backend.config.settings import get_settings


class JSONFormatter(logging.Formatter):
    """JSON 格式化器"""
    
    def format(self, record: logging.LogRecord) -> str:
        """格式化日志记录为 JSON"""
        log_entry = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
            "process_id": record.process,
            "thread_id": record.thread,
        }
        
        # 添加额外的字段
        if hasattr(record, "extra"):
            log_entry.update(record.extra)
        
        # 添加异常信息
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)
        
        # 添加堆栈信息
        if record.stack_info:
            log_entry["stack_info"] = record.stack_info
        
        return json.dumps(log_entry, ensure_ascii=False)


class ColoredFormatter(logging.Formatter):
    """彩色控制台格式化器"""
    
    # ANSI 颜色代码
    COLORS = {
        'DEBUG': '\033[36m',      # 青色
        'INFO': '\033[32m',       # 绿色
        'WARNING': '\033[33m',    # 黄色
        'ERROR': '\033[31m',      # 红色
        'CRITICAL': '\033[35m',   # 紫色
        'RESET': '\033[0m'        # 重置
    }
    
    def format(self, record: logging.LogRecord) -> str:
        """格式化日志记录为彩色文本"""
        color = self.COLORS.get(record.levelname, self.COLORS['RESET'])
        reset = self.COLORS['RESET']
        
        # 格式化时间
        timestamp = datetime.fromtimestamp(record.created).strftime('%Y-%m-%d %H:%M:%S')
        
        # 构建日志消息
        log_message = (
            f"{color}[{timestamp}] {record.levelname:8} "
            f"{record.name}:{record.lineno} - {record.getMessage()}{reset}"
        )
        
        # 添加异常信息
        if record.exc_info:
            log_message += f"\n{self.formatException(record.exc_info)}"
        
        return log_message


class ContextFilter(logging.Filter):
    """上下文过滤器，添加请求相关信息"""
    
    def filter(self, record: logging.LogRecord) -> bool:
        """过滤日志记录，添加上下文信息"""
        # 这里可以添加请求ID、用户ID等上下文信息
        # 在实际使用中，可以从 contextvars 或其他地方获取
        record.request_id = getattr(record, 'request_id', None)
        record.user_id = getattr(record, 'user_id', None)
        return True


class LoggerManager:
    """日志管理器"""
    
    def __init__(self):
        self.settings = get_settings()
        self._loggers: Dict[str, logging.Logger] = {}
        self._setup_root_logger()
    
    def _setup_root_logger(self):
        """设置根日志器"""
        root_logger = logging.getLogger()
        root_logger.setLevel(getattr(logging, self.settings.log_level.upper()))
        
        # 清除现有的处理器
        root_logger.handlers.clear()
        
        # 添加控制台处理器
        console_handler = self._create_console_handler()
        root_logger.addHandler(console_handler)
        
        # 添加文件处理器（如果配置了文件路径）
        if self.settings.log_file_path:
            file_handler = self._create_file_handler()
            root_logger.addHandler(file_handler)
    
    def _create_console_handler(self) -> logging.StreamHandler:
        """创建控制台处理器"""
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(getattr(logging, self.settings.log_level.upper()))
        
        if self.settings.log_format.lower() == "json":
            formatter = JSONFormatter()
        else:
            formatter = ColoredFormatter()
        
        handler.setFormatter(formatter)
        handler.addFilter(ContextFilter())
        
        return handler
    
    def _create_file_handler(self) -> logging.handlers.RotatingFileHandler:
        """创建文件处理器"""
        # 确保日志目录存在
        log_path = Path(self.settings.log_file_path)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        handler = logging.handlers.RotatingFileHandler(
            filename=self.settings.log_file_path,
            maxBytes=self.settings.log_max_size,
            backupCount=self.settings.log_backup_count,
            encoding='utf-8'
        )
        
        handler.setLevel(getattr(logging, self.settings.log_level.upper()))
        
        # 文件日志始终使用 JSON 格式
        formatter = JSONFormatter()
        handler.setFormatter(formatter)
        handler.addFilter(ContextFilter())
        
        return handler
    
    def get_logger(self, name: str) -> logging.Logger:
        """获取指定名称的日志器"""
        if name not in self._loggers:
            logger = logging.getLogger(name)
            self._loggers[name] = logger
        
        return self._loggers[name]
    
    def set_level(self, level: str):
        """设置日志级别"""
        log_level = getattr(logging, level.upper())
        
        # 更新根日志器级别
        root_logger = logging.getLogger()
        root_logger.setLevel(log_level)
        
        # 更新所有处理器级别
        for handler in root_logger.handlers:
            handler.setLevel(log_level)
    
    def add_handler(self, handler: logging.Handler):
        """添加处理器"""
        root_logger = logging.getLogger()
        root_logger.addHandler(handler)
    
    def remove_handler(self, handler: logging.Handler):
        """移除处理器"""
        root_logger = logging.getLogger()
        root_logger.removeHandler(handler)


# 全局日志管理器实例
_logger_manager: Optional[LoggerManager] = None


def get_logger_manager() -> LoggerManager:
    """获取日志管理器实例（单例模式）"""
    global _logger_manager
    if _logger_manager is None:
        _logger_manager = LoggerManager()
    return _logger_manager


@lru_cache(maxsize=128)
def get_logger(name: str) -> logging.Logger:
    """获取指定名称的日志器"""
    manager = get_logger_manager()
    return manager.get_logger(name)


def log_function_call(func):
    """函数调用日志装饰器"""
    def wrapper(*args, **kwargs):
        logger = get_logger(func.__module__)
        logger.debug(
            f"调用函数 {func.__name__}",
            extra={
                "function": func.__name__,
                "args": str(args)[:200],  # 限制参数长度
                "kwargs": str(kwargs)[:200]
            }
        )
        
        try:
            result = func(*args, **kwargs)
            logger.debug(
                f"函数 {func.__name__} 执行成功",
                extra={"function": func.__name__}
            )
            return result
        except Exception as e:
            logger.error(
                f"函数 {func.__name__} 执行失败: {str(e)}",
                extra={
                    "function": func.__name__,
                    "error": str(e)
                },
                exc_info=True
            )
            raise
    
    return wrapper


def log_async_function_call(func):
    """异步函数调用日志装饰器"""
    async def wrapper(*args, **kwargs):
        logger = get_logger(func.__module__)
        logger.debug(
            f"调用异步函数 {func.__name__}",
            extra={
                "function": func.__name__,
                "args": str(args)[:200],
                "kwargs": str(kwargs)[:200]
            }
        )
        
        try:
            result = await func(*args, **kwargs)
            logger.debug(
                f"异步函数 {func.__name__} 执行成功",
                extra={"function": func.__name__}
            )
            return result
        except Exception as e:
            logger.error(
                f"异步函数 {func.__name__} 执行失败: {str(e)}",
                extra={
                    "function": func.__name__,
                    "error": str(e)
                },
                exc_info=True
            )
            raise
    
    return wrapper


class LogContext:
    """日志上下文管理器"""
    
    def __init__(self, logger: logging.Logger, **context):
        self.logger = logger
        self.context = context
        self.old_context = {}
    
    def __enter__(self):
        # 保存旧的上下文
        for key in self.context:
            if hasattr(self.logger, key):
                self.old_context[key] = getattr(self.logger, key)
        
        # 设置新的上下文
        for key, value in self.context.items():
            setattr(self.logger, key, value)
        
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        # 恢复旧的上下文
        for key, value in self.old_context.items():
            setattr(self.logger, key, value)
        
        # 删除新添加的上下文
        for key in self.context:
            if key not in self.old_context:
                delattr(self.logger, key)


def with_log_context(logger: logging.Logger, **context):
    """创建日志上下文管理器"""
    return LogContext(logger, **context)


# 便捷函数
def debug(message: str, logger_name: str = "app", **extra):
    """记录调试日志"""
    logger = get_logger(logger_name)
    logger.debug(message, extra=extra)


def info(message: str, logger_name: str = "app", **extra):
    """记录信息日志"""
    logger = get_logger(logger_name)
    logger.info(message, extra=extra)


def warning(message: str, logger_name: str = "app", **extra):
    """记录警告日志"""
    logger = get_logger(logger_name)
    logger.warning(message, extra=extra)


def error(message: str, logger_name: str = "app", **extra):
    """记录错误日志"""
    logger = get_logger(logger_name)
    logger.error(message, extra=extra)


def critical(message: str, logger_name: str = "app", **extra):
    """记录严重错误日志"""
    logger = get_logger(logger_name)
    logger.critical(message, extra=extra)
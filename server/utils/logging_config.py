"""
日志配置和错误处理
"""

import os
import sys
import logging
import logging.handlers
from typing import Optional
from datetime import datetime
import traceback
import json
from pathlib import Path


class JSONFormatter(logging.Formatter):
    """JSON格式的日志格式器"""

    def format(self, record):
        log_entry = {
            'timestamp': datetime.fromtimestamp(record.created).isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
            'process': record.process,
            'thread': record.thread
        }

        # 添加异常信息
        if record.exc_info:
            log_entry['exception'] = self.formatException(record.exc_info)

        # 添加额外字段
        for key, value in record.__dict__.items():
            if key not in ['name', 'msg', 'args', 'levelname', 'levelno', 'pathname',
                          'filename', 'module', 'lineno', 'funcName', 'created',
                          'msecs', 'relativeCreated', 'thread', 'threadName',
                          'processName', 'process', 'getMessage', 'exc_info',
                          'exc_text', 'stack_info']:
                log_entry[key] = value

        return json.dumps(log_entry, ensure_ascii=False)


class ColoredFormatter(logging.Formatter):
    """彩色控制台日志格式器"""

    COLORS = {
        'DEBUG': '\033[36m',      # 青色
        'INFO': '\033[32m',       # 绿色
        'WARNING': '\033[33m',    # 黄色
        'ERROR': '\033[31m',      # 红色
        'CRITICAL': '\033[35m',   # 紫色
        'ENDC': '\033[0m'         # 结束颜色
    }

    def format(self, record):
        # 添加颜色
        if record.levelname in self.COLORS:
            record.levelname = (
                self.COLORS[record.levelname] +
                record.levelname +
                self.COLORS['ENDC']
            )

        return super().format(record)


def setup_logging(
    log_level: str = "INFO",
    log_file: Optional[str] = None,
    log_format: str = "standard",
    max_file_size: str = "10MB",
    backup_count: int = 5,
    enable_console: bool = True
) -> logging.Logger:
    """
    设置日志配置

    Args:
        log_level: 日志级别
        log_file: 日志文件路径
        log_format: 日志格式 ('standard', 'json', 'detailed')
        max_file_size: 日志文件最大大小
        backup_count: 备份文件数量
        enable_console: 是否启用控制台输出

    Returns:
        配置好的logger
    """

    # 获取根logger
    logger = logging.getLogger()
    logger.setLevel(getattr(logging, log_level.upper()))

    # 清除现有处理器
    logger.handlers.clear()

    # 格式器配置
    formats = {
        'standard': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        'detailed': '%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(funcName)s() - %(message)s',
        'json': None  # 使用JSONFormatter
    }

    # 控制台处理器
    if enable_console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(getattr(logging, log_level.upper()))

        if log_format == 'json':
            console_handler.setFormatter(JSONFormatter())
        else:
            formatter = ColoredFormatter(formats.get(log_format, formats['standard']))
            console_handler.setFormatter(formatter)

        logger.addHandler(console_handler)

    # 文件处理器
    if log_file:
        # 确保日志目录存在
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        # 解析文件大小
        size_multipliers = {'KB': 1024, 'MB': 1024**2, 'GB': 1024**3}
        max_bytes = 10 * 1024 * 1024  # 默认10MB

        if max_file_size:
            size_str = max_file_size.upper()
            for suffix, multiplier in size_multipliers.items():
                if size_str.endswith(suffix):
                    try:
                        max_bytes = int(size_str[:-len(suffix)]) * multiplier
                    except ValueError:
                        pass
                    break

        # 创建轮转文件处理器
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding='utf-8'
        )
        file_handler.setLevel(getattr(logging, log_level.upper()))

        if log_format == 'json':
            file_handler.setFormatter(JSONFormatter())
        else:
            formatter = logging.Formatter(formats.get(log_format, formats['standard']))
            file_handler.setFormatter(formatter)

        logger.addHandler(file_handler)

    # 添加异常钩子
    sys.excepthook = log_uncaught_exceptions

    return logger


def log_uncaught_exceptions(exc_type, exc_value, exc_traceback):
    """记录未捕获的异常"""
    if issubclass(exc_type, KeyboardInterrupt):
        # 对于Ctrl+C，使用默认处理
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return

    logger = logging.getLogger(__name__)
    logger.critical(
        "未捕获的异常",
        exc_info=(exc_type, exc_value, exc_traceback)
    )


class ASELogger:
    """ASE专用日志器"""

    def __init__(self, name: str = "ase_mcp"):
        self.logger = logging.getLogger(name)

    def log_operation(self, operation: str, session_id: str, details: dict = None):
        """记录操作日志"""
        self.logger.info(
            f"Operation: {operation}",
            extra={
                'operation': operation,
                'session_id': session_id,
                'details': details or {}
            }
        )

    def log_error(self, error: Exception, context: dict = None):
        """记录错误日志"""
        self.logger.error(
            f"Error: {str(error)}",
            exc_info=True,
            extra={
                'error_type': type(error).__name__,
                'context': context or {}
            }
        )

    def log_performance(self, operation: str, duration: float, details: dict = None):
        """记录性能日志"""
        self.logger.info(
            f"Performance: {operation} took {duration:.3f}s",
            extra={
                'performance': True,
                'operation': operation,
                'duration': duration,
                'details': details or {}
            }
        )

    def log_websocket_event(self, event: str, client_id: str, details: dict = None):
        """记录WebSocket事件"""
        self.logger.debug(
            f"WebSocket: {event}",
            extra={
                'websocket': True,
                'event': event,
                'client_id': client_id,
                'details': details or {}
            }
        )

    def log_session_event(self, event: str, session_id: str, details: dict = None):
        """记录会话事件"""
        self.logger.info(
            f"Session: {event}",
            extra={
                'session': True,
                'event': event,
                'session_id': session_id,
                'details': details or {}
            }
        )


class ErrorHandler:
    """错误处理器"""

    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)

    def handle_exception(self, exc: Exception, context: str = "",
                        session_id: str = None, reraise: bool = True):
        """统一异常处理"""
        error_info = {
            'error_type': type(exc).__name__,
            'error_message': str(exc),
            'context': context,
            'session_id': session_id,
            'traceback': traceback.format_exc()
        }

        self.logger.error(
            f"Exception in {context}: {str(exc)}",
            extra=error_info,
            exc_info=True
        )

        if reraise:
            raise exc

    def handle_validation_error(self, error: str, data: dict = None):
        """处理验证错误"""
        self.logger.warning(
            f"Validation error: {error}",
            extra={
                'validation_error': True,
                'error': error,
                'data': data
            }
        )

    def handle_websocket_error(self, error: Exception, client_id: str):
        """处理WebSocket错误"""
        self.logger.error(
            f"WebSocket error for client {client_id}: {str(error)}",
            extra={
                'websocket_error': True,
                'client_id': client_id,
                'error_type': type(error).__name__
            },
            exc_info=True
        )


# 创建全局实例
ase_logger = ASELogger()
error_handler = ErrorHandler()


def get_logger(name: str = None) -> logging.Logger:
    """获取logger实例"""
    return logging.getLogger(name) if name else logging.getLogger()


def setup_default_logging():
    """设置默认日志配置"""
    log_level = os.getenv("LOG_LEVEL", "INFO")
    log_file = os.getenv("LOG_FILE", "ase_mcp.log")
    log_format = os.getenv("LOG_FORMAT", "standard")

    return setup_logging(
        log_level=log_level,
        log_file=log_file,
        log_format=log_format
    )


# 自动设置默认配置
if not logging.getLogger().handlers:
    setup_default_logging()
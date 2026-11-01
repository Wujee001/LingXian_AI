# -*- coding: utf-8 -*-
"""
日志系统模块

提供彩色控制台输出、文件日志、文件日志持久化、热重载自动恢复。
基于 Python 官方 logging 库二次封装。

作者：
    @Wujee

创建日期：2026-9-21
版本：1.0.0

许可证：内部使用，未经许可不得传播。

"""

import logging
import sys
import os
import threading
from enum import Enum
from typing import Any, Optional


class LogLevel(Enum):
    """日志级别枚举"""
    DEBUG = 0
    INFO = 1
    WARN = 2
    ERROR = 3


LEVEL_MAP = {
    LogLevel.DEBUG: logging.DEBUG,
    LogLevel.INFO: logging.INFO,
    LogLevel.WARN: logging.WARNING,
    LogLevel.ERROR: logging.ERROR,
}


# ==============================================================================
# 环境变量配置
# ==============================================================================
ENV_LOG_FILE = "MLN_LOG_FILE"
ENV_LOG_LEVEL = "MLN_LOG_LEVEL"
ENV_LOG_CONSOLE = "MLN_LOG_CONSOLE"


def _get_env(key: str):
    return os.environ.get(key, None)


def _set_env(key: str, value: Any):
    os.environ[key] = str(value)


class ColoredConsoleHandler(logging.StreamHandler):
    """带颜色输出的控制台处理器"""

    COLORS = {
        logging.DEBUG: "\033[1;36m",     # 青色
        logging.INFO: "\033[1;32m",      # 绿色
        logging.WARNING: "\033[1;33m",   # 黄色
        logging.ERROR: "\033[1;31m",     # 红色
        logging.CRITICAL: "\033[1;35m",  # 紫色
    }

    RESET = "\033[0m"

    def emit(self, record):
        try:
            msg = self.format(record)
            color = self.COLORS.get(record.levelno, "")
            self.stream.write(f"{color}{msg}{self.RESET}\n")
            self.flush()
        except Exception:
            self.handleError(record)


class MlnLog:
    """单例日志类，全局统一配置"""

    _instance: Optional["MlnLog"] = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                obj = super().__new__(cls)
                cls._instance = obj
                obj._init_logger()
                obj.auto_initialize()
        return cls._instance

    def _init_logger(self):
        """初始化 logger 基础配置"""
        self.logger = logging.getLogger("MlnLog")
        self.logger.handlers.clear()

        # 默认 DEBUG，方便开发阶段看日志
        self.logger.setLevel(logging.DEBUG)

        # 防止日志继续往 root logger 传，避免 uvicorn 下重复输出
        self.logger.propagate = False

        self.console_enabled = True

        # 控制台 handler 对象
        self.console_handler = None

        # 文件 handler 对象，不是字符串
        self.file_handler = None

        # 当前日志文件路径，字符串
        self._log_file = None

        self.formatter = logging.Formatter(
            "[%(asctime)s] [%(levelname)s] [%(filename)s:%(lineno)d:%(funcName)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )

    def auto_initialize(self):
        """热重载自动恢复日志配置"""

        # 恢复日志级别
        level_str = _get_env(ENV_LOG_LEVEL)
        if level_str:
            try:
                self.logger.setLevel(int(level_str))
            except Exception:
                self.logger.setLevel(logging.DEBUG)
        else:
            self.logger.setLevel(logging.DEBUG)

        # 恢复控制台
        console_str = _get_env(ENV_LOG_CONSOLE)
        if console_str is None or console_str == "1":
            self._add_console_handler()
        else:
            self._remove_console_handler()

        # 恢复日志文件
        log_file = _get_env(ENV_LOG_FILE)
        if log_file:
            try:
                self.set_log_file(log_file)
            except Exception:
                pass

    @classmethod
    def get_instance(cls):
        return cls()

    @classmethod
    def initialize(cls, level: LogLevel = LogLevel.INFO, console: bool = True):
        """初始化日志系统"""
        instance = cls.get_instance()

        lv = LEVEL_MAP.get(level, logging.INFO)

        instance.logger.setLevel(lv)
        _set_env(ENV_LOG_LEVEL, lv)
        _set_env(ENV_LOG_CONSOLE, "1" if console else "0")

        if console:
            instance._add_console_handler()
        else:
            instance._remove_console_handler()

        return instance

    def _add_console_handler(self):
        """添加控制台日志 handler"""
        if self.console_handler is not None:
            return

        handler = ColoredConsoleHandler(stream=sys.stdout)
        handler.setFormatter(self.formatter)

        self.logger.addHandler(handler)
        self.console_handler = handler
        self.console_enabled = True

    def _remove_console_handler(self):
        """移除控制台日志 handler"""
        if self.console_handler:
            try:
                self.logger.removeHandler(self.console_handler)
                self.console_handler.close()
            except Exception:
                pass

        self.console_handler = None
        self.console_enabled = False

    def set_console_output(self, enable: bool):
        """开启或关闭控制台输出"""
        if enable:
            self._add_console_handler()
            _set_env(ENV_LOG_CONSOLE, "1")
        else:
            self._remove_console_handler()
            _set_env(ENV_LOG_CONSOLE, "0")

    def set_log_file(self, filename: str):
        """设置日志文件"""

        if not filename:
            return

        self._log_file = filename
        _set_env(ENV_LOG_FILE, filename)

        # 如果之前已经有文件 handler，先移除并关闭
        if self.file_handler:
            try:
                self.logger.removeHandler(self.file_handler)
                self.file_handler.close()
            except Exception:
                pass
            self.file_handler = None

        dir_name = os.path.dirname(filename)
        if dir_name:
            os.makedirs(dir_name, exist_ok=True)

        handler = logging.FileHandler(
            filename,
            encoding="utf-8",
            mode="a"
        )

        handler.setFormatter(self.formatter)

        self.logger.addHandler(handler)
        self.file_handler = handler

    def close_log_file(self):
        """关闭文件日志"""
        if self.file_handler:
            try:
                self.logger.removeHandler(self.file_handler)
                self.file_handler.close()
            except Exception:
                pass

        self.file_handler = None
        self._log_file = None
        _set_env(ENV_LOG_FILE, "")

    def set_log_level(self, level: LogLevel):
        """设置日志级别"""
        lv = LEVEL_MAP.get(level, logging.INFO)
        self.logger.setLevel(lv)
        _set_env(ENV_LOG_LEVEL, lv)

    def get_log_file(self):
        """获取当前日志文件路径"""
        return self._log_file

    def get_file_handler(self):
        """获取当前文件日志 handler"""
        return self.file_handler


# ==============================================================================
# 内部日志输出函数
# ==============================================================================
def _log(level: int, format_str: str, *args: Any) -> None:
    logger = MlnLog.get_instance().logger

    if not logger.isEnabledFor(level):
        return

    frame = sys._getframe(2)

    record = logging.LogRecord(
        name="MlnLog",
        level=level,
        pathname=frame.f_code.co_filename,
        lineno=frame.f_lineno,
        msg=format_str,
        args=args,
        exc_info=None,
        func=frame.f_code.co_name
    )

    logger.handle(record)


# ==============================================================================
# 对外日志输出函数
# ==============================================================================
def MLN_LOG_DEBUG(format_str: str, *args: Any) -> None:
    _log(logging.DEBUG, format_str, *args)


def MLN_LOG_INFO(format_str: str, *args: Any) -> None:
    _log(logging.INFO, format_str, *args)


def MLN_LOG_WARN(format_str: str, *args: Any) -> None:
    _log(logging.WARNING, format_str, *args)


def MLN_LOG_ERROR(format_str: str, *args: Any) -> None:
    _log(logging.ERROR, format_str, *args)


def MLN_LOG_EXCEPTION(format_str: str, *args: Any) -> None:
    """
    异常日志。

    推荐在 except 中使用：
        try:
            ...
        except Exception as e:
            MLN_LOG_EXCEPTION("注册异常：%s", e)
    """

    logger = MlnLog.get_instance().logger

    if not logger.isEnabledFor(logging.ERROR):
        return

    frame = sys._getframe(1)

    record = logging.LogRecord(
        name="MlnLog",
        level=logging.ERROR,
        pathname=frame.f_code.co_filename,
        lineno=frame.f_lineno,
        msg=format_str,
        args=args,
        exc_info=sys.exc_info(),
        func=frame.f_code.co_name
    )

    logger.handle(record)


# ==============================================================================
# 测试
# ==============================================================================
if __name__ == "__main__":
    MlnLog.initialize(LogLevel.DEBUG, console=True)

    log = MlnLog.get_instance()
    log.set_log_file("utils/logs/mlnlog.log")

    MLN_LOG_DEBUG("调试日志测试")
    MLN_LOG_INFO("信息日志测试")
    MLN_LOG_WARN("警告日志测试")
    MLN_LOG_ERROR("错误日志测试")

    try:
        a = 1 / 0
    except Exception as e:
        MLN_LOG_EXCEPTION("异常日志测试：%s", e)
"""
日志系统 - 企业级日志管理
记录程序运行的所有关键信息，便于调试和监控
"""

import logging
import os
from datetime import datetime


def setup_logger(
    log_dir="logs",
    log_file=None,
    level=logging.INFO,
    console_output=True
):
    """
    配置日志系统

    参数：
    log_dir: 日志文件夹
    log_file: 日志文件名（如果不指定，自动生成）
    level: 日志级别
    console_output: 是否同时输出到控制台
    """

    # 创建日志文件夹
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    # 生成日志文件名（如果未指定）
    if log_file is None:
        timestamp = datetime.now().strftime("%Y%m%d")
        log_file = f"app_{timestamp}.log"

    log_path = os.path.join(log_dir, log_file)

    # 配置日志格式
    log_format = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # 获取根日志记录器
    logger = logging.getLogger()
    logger.setLevel(level)

    # 清空已有处理器（避免重复）
    logger.handlers.clear()

    # 文件处理器
    file_handler = logging.FileHandler(log_path, encoding='utf-8')
    file_handler.setFormatter(log_format)
    logger.addHandler(file_handler)

    # 控制台处理器（如果启用）
    if console_output:
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(log_format)
        logger.addHandler(console_handler)

    logging.info(f"日志系统初始化成功，日志文件：{log_path}")

    return logger


# 默认日志实例
logger = setup_logger()


def get_logger(name=None):
    """
    获取指定名称的日志记录器
    """
    if name:
        return logging.getLogger(name)
    return logging.getLogger()


# 便捷函数
def info(msg):
    logging.info(msg)


def debug(msg):
    logging.debug(msg)


def warning(msg):
    logging.warning(msg)


def error(msg):
    logging.error(msg)


def critical(msg):
    logging.critical(msg)


if __name__ == "__main__":
    # 测试日志系统
    logger = setup_logger()
    logger.info("这是一条信息日志")
    logger.warning("这是一条警告日志")
    logger.error("这是一条错误日志")
    print("日志测试完成，请查看 logs/ 文件夹")
import os
import logging
from logging.handlers import RotatingFileHandler
from config_manager import config

def setup_logger():
    """初始化全局日志系统：支持自动滚动切割日志文件及控制台打印"""
    if not os.path.exists(config.LOG_DIR):
        os.makedirs(config.LOG_DIR)

    log_file_path = os.path.join(config.LOG_DIR, config.LOG_FILE_NAME)

    formatter = logging.Formatter(
        fmt='[%(asctime)s] [%(levelname)s] [%(filename)s:%(lineno)d] - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    file_handler = RotatingFileHandler(
        filename=log_file_path,
        maxBytes=config.LOG_MAX_BYTES,
        backupCount=config.LOG_BACKUP_COUNT,
        encoding='utf-8'
    )
    file_handler.setFormatter(formatter)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    logger = logging.getLogger("JavDBSystem")
    logger.setLevel(getattr(logging, config.LOG_LEVEL.upper(), logging.INFO))
    
    if not logger.handlers:
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)

    return logger, log_file_path

logger, LOG_FILE_PATH = setup_logger()
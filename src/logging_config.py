"""Logging configuration module."""
import logging
import sys
from typing import Optional


def setup_logging(log_path: Optional[str] = None) -> None:
    """
    Set up logging configuration.
    
    Args:
        log_path: Optional path to log file. If None, only console logging.
    """
    log_format = '%(asctime)s.%(msecs)03d %(levelname)s: %(message)s'
    date_format = '%Y-%m-%d %H:%M:%S'
    
    handlers = []
    
    # Console handler - DEBUG level (temporary for debugging)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG)
    handlers.append(console_handler)
    
    # File handler (if log path is provided) - WARNING level for warnings and errors
    if log_path:
        try:
            file_handler = logging.FileHandler(log_path, encoding='utf-8')
            file_handler.setLevel(logging.INFO)
            handlers.append(file_handler)
        except Exception as e:
            print(f"Warning: Could not set up file logging: {e}")
    
    # Set root logger to DEBUG to capture all messages (temporary for debugging)
    logging.basicConfig(
        level=logging.DEBUG,
        format=log_format,
        datefmt=date_format,
        handlers=handlers
    )
    
    # Configure specific loggers - all set to DEBUG level (temporary for debugging)
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)
    
    # Set external libraries to WARNING level (only warnings and errors)
    _configure_external_loggers()


def _configure_external_loggers() -> None:
    """Configure external library loggers to reduce noise."""
    external_loggers = ['aiogram', 'aiohttp', 'requests', 'urllib3']
    
    for logger_name in external_loggers:
        logger = logging.getLogger(logger_name)
        logger.setLevel(logging.WARNING)

"""
Logging Configuration Module

Centralized logging using Loguru with custom formatting and filtering.
All modules should use this logger instead of print statements.

Usage:
    from app.infrastructure.config.logger import get_logger
    
    logger = get_logger(__name__)
    logger.info("Processing query", query="What is the penalty?")
    logger.error("Failed to connect", error=str(e))
    
Author: AnhNN217-FHN
"""

import sys
from typing import Optional
from loguru import logger
from pathlib import Path


def setup_logger(
    log_level: str = "INFO",
    log_file: Optional[str] = None,
    json_format: bool = False,
    enable_backtrace: bool = True,
    enable_diagnose: bool = True
) -> None:
    """
    Configure the global logger instance.
    
    This function should be called once at application startup, typically
    from main.py or container.py.
    
    Args:
        log_level: Minimum log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional path to log file. If None, logs only to stderr
        json_format: If True, output logs in JSON format for structured logging
        enable_backtrace: Show full stack trace on errors
        enable_diagnose: Show variable values in stack traces
    
    Example:
        >>> setup_logger(log_level="DEBUG", log_file="logs/app.log")
    """
    # Remove default logger
    logger.remove()
    
    # Configure format based on json_format flag
    if json_format:
        # Structured JSON format for production/log aggregation
        log_format = (
            "{{\"time\": \"{time:YYYY-MM-DD HH:mm:ss.SSS}\", "
            "\"level\": \"{level}\", "
            "\"module\": \"{name}\", "
            "\"function\": \"{function}\", "
            "\"line\": {line}, "
            "\"message\": \"{message}\"}}"
        )
    else:
        # Human-readable format for development
        log_format = (
            "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
            "<level>{message}</level>"
        )
    
    # Add stderr handler
    logger.add(
        sys.stderr,
        format=log_format,
        level=log_level,
        colorize=not json_format,
        backtrace=enable_backtrace,
        diagnose=enable_diagnose,
        enqueue=True  # Thread-safe logging
    )
    
    # Add file handler if specified
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        logger.add(
            log_file,
            format=log_format if json_format else (
                "{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | "
                "{name}:{function}:{line} | {message}"
            ),
            level=log_level,
            rotation="100 MB",  # Rotate when file reaches 100 MB
            retention="30 days",  # Keep logs for 30 days
            compression="zip",  # Compress rotated logs
            backtrace=enable_backtrace,
            diagnose=enable_diagnose,
            enqueue=True
        )
    
    logger.info(
        "Logger initialized",
        level=log_level,
        json_format=json_format,
        log_file=log_file
    )


def get_logger(name: str):
    """
    Get a logger instance bound to a specific module name.
    
    This creates a contextualized logger that includes the module name
    in all log messages, making it easier to trace the source of logs.
    
    Args:
        name: Module name, typically __name__
    
    Returns:
        Contextualized logger instance
    
    Example:
        >>> logger = get_logger(__name__)
        >>> logger.info("Starting retrieval", query="example")
    """
    return logger.bind(name=name)

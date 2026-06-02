"""
Structured logging configuration for the trading system.
Provides JSON and text formatting with context preservation.
"""

import logging
import json
import sys
from typing import Any
from datetime import datetime
from pathlib import Path

from .config import settings


class JSONFormatter(logging.Formatter):
    """JSON log formatter for structured logging."""
    
    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        
        # Add extra fields
        if hasattr(record, "extra_fields"):
            log_data.update(record.extra_fields)
        
        return json.dumps(log_data)


class TextFormatter(logging.Formatter):
    """Human-readable text formatter."""
    
    COLORS = {
        "DEBUG": "\033[36m",      # Cyan
        "INFO": "\033[32m",       # Green
        "WARNING": "\033[33m",    # Yellow
        "ERROR": "\033[31m",      # Red
        "CRITICAL": "\033[35m",   # Magenta
        "RESET": "\033[0m",
    }
    
    def format(self, record: logging.LogRecord) -> str:
        level = record.levelname
        color = self.COLORS.get(level, "")
        reset = self.COLORS["RESET"]
        
        timestamp = datetime.fromtimestamp(record.created).isoformat()
        
        base_format = f"{color}[{timestamp}] [{level:8s}] {record.name}:{record.funcName}:{record.lineno} - {record.getMessage()}{reset}"
        
        if record.exc_info:
            base_format += f"\n{self.formatException(record.exc_info)}"
        
        return base_format


class ContextFilter(logging.Filter):
    """Add contextual information to logs."""
    
    def __init__(self, context: dict[str, Any] | None = None):
        super().__init__()
        self.context = context or {}
    
    def filter(self, record: logging.LogRecord) -> bool:
        record.extra_fields = self.context
        return True


def setup_logging(use_json: bool = False) -> logging.Logger:
    """
    Configure logging for the application.
    
    Args:
        use_json: Use JSON formatting if True, otherwise text formatting
        
    Returns:
        Configured logger instance
    """
    
    # Create logs directory
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    # Root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(settings.log_level)
    
    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Choose formatter
    if use_json:
        formatter = JSONFormatter()
    else:
        formatter = TextFormatter()
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # File handler (always text for readability)
    file_handler = logging.FileHandler(log_dir / "trading_system.log")
    file_handler.setFormatter(JSONFormatter() if use_json else TextFormatter())
    root_logger.addHandler(file_handler)
    
    # Error file handler
    error_handler = logging.FileHandler(log_dir / "errors.log")
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(JSONFormatter() if use_json else TextFormatter())
    root_logger.addHandler(error_handler)
    
    # Trade file handler
    trade_handler = logging.FileHandler(log_dir / "trades.log")
    trade_handler.setFormatter(JSONFormatter() if use_json else TextFormatter())
    root_logger.addHandler(trade_handler)
    
    return root_logger


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance with the given name."""
    return logging.getLogger(name)

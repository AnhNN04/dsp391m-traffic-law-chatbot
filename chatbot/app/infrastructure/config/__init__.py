from .logger import setup_logger, get_logger
from .settings import settings

# Export the logger instance for backward compatibility
__all__ = ["settings", "logger", "setup_logger", "get_logger"]

"""Logging configuration for SpecFlow."""

import logging
import sys
from typing import Any

from rich.console import Console
from rich.logging import RichHandler

from specflow.utils.config import get_settings


def setup_logging() -> logging.Logger:
    """Configure logging with Rich handler for beautiful console output.

    Returns:
        Configured logger instance for SpecFlow.
    """
    settings = get_settings()

    # Create console with error handling
    console = Console(stderr=True, force_terminal=True)

    # Configure rich handler
    rich_handler = RichHandler(
        console=console,
        rich_tracebacks=True,
        tracebacks_show_locals=settings.debug,
        show_time=True,
        show_path=settings.debug,
    )

    # Set format
    log_format = "%(message)s"
    rich_handler.setFormatter(logging.Formatter(log_format))

    # Configure root logger
    logging.basicConfig(
        level=settings.log_level,
        format=log_format,
        handlers=[rich_handler],
    )

    # Get logger for specflow
    logger = logging.getLogger("specflow")
    logger.setLevel(settings.log_level)

    # Reduce noise from third-party libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("atlassian").setLevel(logging.WARNING)

    return logger


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance for a specific module.

    Args:
        name: Name of the module requesting the logger.

    Returns:
        Logger instance configured for the module.
    """
    return logging.getLogger(f"specflow.{name}")


class LoggerMixin:
    """Mixin class to add logging capability to any class."""

    @property
    def logger(self) -> logging.Logger:
        """Get logger for this class."""
        return get_logger(self.__class__.__name__)

    def log_info(self, message: str, **kwargs: Any) -> None:
        """Log info level message with context."""
        self.logger.info(message, extra=kwargs)

    def log_error(self, message: str, exc_info: bool = False, **kwargs: Any) -> None:
        """Log error level message with context."""
        self.logger.error(message, exc_info=exc_info, extra=kwargs)

    def log_warning(self, message: str, **kwargs: Any) -> None:
        """Log warning level message with context."""
        self.logger.warning(message, extra=kwargs)

    def log_debug(self, message: str, **kwargs: Any) -> None:
        """Log debug level message with context."""
        self.logger.debug(message, extra=kwargs)

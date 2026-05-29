"""Structured logging utilities for CineVault."""

import logging


def setup_logger(name: str, level: int = logging.INFO) -> logging.Logger:
    """Configure and return a named logger.

    Args:
        name: Logger name (e.g., 'cinevault.videos')
        level: Logging level (default: logging.INFO)

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Avoid adding duplicate handlers
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setLevel(level)

        formatter = logging.Formatter(
            fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger


# Pre-configured logger instances
video_logger = setup_logger("cinevault.videos")
db_logger = setup_logger("cinevault.db")
auth_logger = setup_logger("cinevault.auth")
sync_logger = setup_logger("cinevault.sync")
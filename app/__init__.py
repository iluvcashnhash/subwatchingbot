"""
SubWatch Bot - A Telegram bot for tracking subscriptions with natural language support.
"""

import os
from pathlib import Path

# Package version
__version__ = "0.1.0"

# Setup logging
from .logging_config import setup_logging, get_logger

# Default log file path
LOG_DIR = Path("logs")
LOG_FILE = LOG_DIR / "bot.log"

# Ensure log directory exists
os.makedirs(LOG_DIR, exist_ok=True)

# Configure logging
setup_logging(log_level=os.getenv("LOG_LEVEL", "INFO"), log_file=str(LOG_FILE))

# Create package-level logger
logger = get_logger(__name__)
logger.info(f"SubWatch Bot v{__version__} starting...")

"""Custom logging utility with colored output and PST timezone support."""

import logging
import sys
import traceback
from datetime import datetime
from zoneinfo import ZoneInfo
from typing import Any

# ANSI Color Codes
RESET = "\033[0m"
BOLD = "\033[1m"
RED = "\033[31m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
BLUE = "\033[34m"
CYAN = "\033[36m"
WHITE = "\033[37m"

class PSTFormatter(logging.Formatter):
    """Formatter that enforces Pacific Time (US/Pacific) for timestamps."""

    def formatTime(self, record: logging.LogRecord, datefmt: str | None = None) -> str:
        """Overridden to convert the record timestamp to US/Pacific time."""
        # Convert record creation time to aware datetime in US/Pacific
        dt = datetime.fromtimestamp(record.created, tz=ZoneInfo("US/Pacific"))
        
        if datefmt:
            return dt.strftime(datefmt)
        return dt.isoformat()

class ColoredConsoleHandler(logging.StreamHandler):
    """StreamHandler that applies ANSI colors based on log level."""

    def format(self, record: logging.LogRecord) -> str:
        """Formats the log record with colors if the stream is a TTY."""
        # Standard formatting first
        msg = super().format(record)
        
        # Determine color
        color = WHITE
        if record.levelno >= logging.ERROR:
            color = RED
        elif record.levelno >= logging.WARNING:
            color = YELLOW
        elif record.levelno >= logging.INFO:
            color = GREEN
        elif record.levelno == logging.DEBUG:
            color = CYAN

        # Apply color if output is a terminal
        if self.stream.isatty():
             # We can't just wrap the whole message because the formatter likely
             # produced [Time] [Level] [File] Message. 
             # We want to colorize the Level and potentially the Message.
             # However, for simplicity and robustness in this custom handler,
             # let's colorize the whole line for errors/warnings, or just the level.
             # Custom format defined in Logger class is:
             # [TIME] [LEVEL] [FILE:LINE] MESSAGE
             
             # Let's replace the level name with a colored version in the string
             levelname = record.levelname
             msg = msg.replace(f"[{levelname}]", f"[{color}{levelname}{RESET}]")
             
             # If Error, color the message too
             if record.levelno >= logging.ERROR:
                 msg = f"{msg} {color}(Stack Trace follows if available){RESET}"

        return msg

class Logger:
    """Singleton-like logger factory for the application."""

    _instance = None

    @staticmethod
    def setup(name: str = "plaid_local", level: int = logging.INFO) -> logging.Logger:
        """Configures and returns a logger instance.

        Args:
            name (str): The name of the logger.
            level (int): Logging level (default: INFO).

        Returns:
            logging.Logger: Configured logger.
        """
        logger = logging.getLogger(name)
        logger.setLevel(level)
        
        # Avoid adding handlers multiple times if setup is called repeatedly
        if logger.hasHandlers():
            return logger

        # Create Handler
        handler = ColoredConsoleHandler(sys.stdout)
        handler.setLevel(level)

        # Create Formatter
        # Format: [HH:MM:SS PST] [LEVEL] [file.py:line] Message
        # Note: 'PST' is hardcoded text here because formatTime handles the actual conversion
        fmt = "[%(asctime)s PST] [%(levelname)s] [%(filename)s:%(lineno)d] %(message)s"
        datefmt = "%H:%M:%S"
        
        formatter = PSTFormatter(fmt, datefmt=datefmt)
        handler.setFormatter(formatter)

        logger.addHandler(handler)
        return logger

    @staticmethod
    def log_exception(logger: logging.Logger, msg: str, exc_info: Any = None) -> None:
        """Logs an error with a full stack trace.

        Args:
            logger (logging.Logger): The logger instance.
            msg (str): The error message.
            exc_info: The exception object or tuple (optional). If None, 
                      sys.exc_info() is used if available.
        """
        if exc_info is None:
            exc_info = sys.exc_info()
        
        logger.error(msg)
        
        # Format stack trace
        if exc_info and exc_info[0]:
            tb_lines = traceback.format_exception(*exc_info)
            tb_text = "".join(tb_lines)
            # Print stack trace in Red
            if sys.stdout.isatty():
                print(f"{RED}{tb_text}{RESET}", file=sys.stderr)
            else:
                print(tb_text, file=sys.stderr)

# Global accessor
def get_logger(name: str) -> logging.Logger:
    """Returns a configured logger instance for the given name.

    Args:
        name (str): The name of the logger.

    Returns:
        logging.Logger: The configured logger.
    """
    return Logger.setup(name)

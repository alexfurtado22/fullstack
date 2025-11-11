# app/logging_config.py
import logging
import sys
from pathlib import Path

from loguru import logger

from .config import get_settings

# Ensure logs folder exists
Path("logs").mkdir(exist_ok=True)

settings = get_settings()
IS_DEVELOPMENT = settings.ENVIRONMENT == "development"

# Remove default handlers
logger.remove()

LEVEL_EMOJIS = {
    "TRACE": "🔍",
    "DEBUG": "🐛",
    "INFO": "ℹ️ ",
    "SUCCESS": "✅",
    "WARNING": "⚠️",
    "ERROR": "❌",
    "CRITICAL": "🔥",
    "SQLALCHEMY": "🧩",
}


def formatter(record):
    """Custom console log format (safe for missing extras)."""
    level_name = record["level"].name
    emoji = LEVEL_EMOJIS.get(level_name, "💬")
    user = record["extra"].get("user", "system")
    method = record["extra"].get("method", "")
    path = record["extra"].get("path", "")

    # 👇 FIX: Escape the function name to prevent color tag errors
    func_name = record["function"].replace("<", r"\<").replace(">", r"\>")

    if record["name"].startswith("sqlalchemy"):
        emoji = LEVEL_EMOJIS["SQLALCHEMY"]
        return (
            f"<green>{record['time']:YYYY-MM-DD HH:mm:ss}</green> "
            f"| <cyan>{emoji} SQL</cyan> "
            f"| <cyan>{record['name']}</cyan>:<cyan>{func_name}</cyan>:<cyan>{record['line']}</cyan> "
            f"| 👤 <magenta>{user}</magenta> "
            f"- <cyan>{record['message']}</cyan>\n"
        )

    return (
        f"<green>{record['time']:YYYY-MM-DD HH:mm:ss}</green> "
        f"| <level>{emoji} {level_name:<8}</level> "
        f"| <cyan>{record['name']}</cyan>:<cyan>{func_name}</cyan>:<cyan>{record['line']}</cyan> "
        f"| <blue>{method} {path}</blue> "
        f"| 👤 <magenta>{user}</magenta> "
        f"- <level>{record['message']}</level>\n"
    )


LOG_LEVEL = "DEBUG" if IS_DEVELOPMENT else "INFO"

logger.add(
    sys.stderr,
    format=formatter,
    colorize=True,
    level=LOG_LEVEL,
    enqueue=not IS_DEVELOPMENT,
    backtrace=True,
    diagnose=False,
)


def file_formatter(record):
    user = record["extra"].get("user", "system")
    method = record["extra"].get("method", "")
    path = record["extra"].get("path", "")
    emoji = LEVEL_EMOJIS.get(record["level"].name, "💬")

    # 👇 FIX: Escape the function name
    func_name = record["function"].replace("<", r"\<").replace(">", r"\>")

    if record["name"].startswith("sqlalchemy"):
        emoji = LEVEL_EMOJIS["SQLALCHEMY"]

    return (
        f"{record['time']:YYYY-MM-DD HH:mm:ss} | {emoji} {record['level'].name:<8} | "
        f"{record['name']}:{func_name}:{record['line']} | "
        f"{method} {path} | {user} - {record['message']}\n"
    )


logger.add(
    "logs/{time:YYYY-MM-DD}.log",
    rotation="1 week",
    compression="zip",
    level="DEBUG",
    format=file_formatter,
    enqueue=not IS_DEVELOPMENT,
)


class InterceptHandler(logging.Handler):
    def emit(self, record: logging.LogRecord):
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        frame, depth = sys._getframe(6), 6
        while frame and frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(
            level, record.getMessage()
        )


logging.root.handlers = [InterceptHandler()]
logging.root.setLevel(0)

for name in ["uvicorn", "uvicorn.access", "uvicorn.error"]:
    logging.getLogger(name).handlers = []
    logging.getLogger(name).propagate = True

logging.getLogger("sqlalchemy.engine").setLevel(logging.INFO)
logging.getLogger("sqlalchemy.pool").setLevel(logging.WARNING)

for name in list(logging.root.manager.loggerDict):
    if name.startswith("sqlalchemy"):
        sa_logger = logging.getLogger(name)
        sa_logger.handlers.clear()
        sa_logger.addHandler(InterceptHandler())  # 👈 TYPO FIXED
        sa_logger.propagate = False

logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
logging.getLogger("python_multipart").setLevel(logging.INFO)
logging.getLogger("httpx").setLevel(logging.INFO)
logging.getLogger("httpcore").setLevel(logging.INFO)
